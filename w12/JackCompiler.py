"""Compile Jack classes to the Nand2Tetris virtual machine language."""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from jack_syntax import (
    ArrayAccess, Call, Do, Expression, If, JackError, Let, Return, Unary, While,
    jack_files, read_jack,
)


SEGMENTS = {"static": "static", "field": "this", "argument": "argument", "var": "local"}
BINARY_COMMANDS = {
    "+": "add", "-": "sub", "*": "call Math.multiply 2", "/": "call Math.divide 2",
    "&": "and", "|": "or", "<": "lt", ">": "gt", "=": "eq",
}
UNARY_COMMANDS = {"-": "neg", "~": "not"}


@dataclass(frozen=True)
class Symbol:
    type_name: str
    kind: str
    index: int

    @property
    def location(self):
        return f"{SEGMENTS[self.kind]} {self.index}"


class SymbolTable:
    """Track class variables separately from parameters and locals."""

    def __init__(self, path):
        self.path = path
        self.class_scope = {}
        self.subroutine_scope = {}
        self.counts = dict.fromkeys(SEGMENTS, 0)

    def start_subroutine(self, kind):
        self.subroutine_scope.clear()
        self.counts["argument"] = int(kind == "method")
        self.counts["var"] = 0

    def declare(self, declarations):
        for declaration in declarations:
            kind = declaration.kind
            scope = self.class_scope if kind in {"static", "field"} else self.subroutine_scope
            for name in declaration.names:
                if name.value in scope:
                    raise name.error(self.path, f"duplicate variable {name.value!r}")
                scope[name.value] = Symbol(declaration.type_name, kind, self.counts[kind])
                self.counts[kind] += 1

    def lookup(self, name):
        return self.subroutine_scope.get(name) or self.class_scope.get(name)


class VMCompiler:
    def __init__(self, tree, path):
        self.tree = tree
        self.path = path
        self.class_name = tree.name.value
        self.symbols = SymbolTable(path)
        self.subroutines = {}
        self.lines = []

    def emit(self, *commands):
        self.lines.extend(commands)

    def compile(self):
        if self.class_name != self.path.stem:
            raise self.tree.name.error(self.path, f"class name must match {self.path.stem!r}")
        self.symbols.declare(self.tree.variables)
        for subroutine in self.tree.subroutines:
            name = subroutine.name
            if name.value in self.subroutines:
                raise name.error(self.path, f"duplicate subroutine {name.value!r}")
            self.subroutines[name.value] = subroutine
        for subroutine in self.tree.subroutines:
            self.compile_subroutine(subroutine)
        return "\n".join(self.lines) + ("\n" if self.lines else "")

    def compile_subroutine(self, subroutine):
        self.kind = subroutine.kind
        self.next_label = 0
        self.symbols.start_subroutine(self.kind)
        self.symbols.declare(subroutine.parameters)
        self.symbols.declare(subroutine.locals)
        self.emit(f"function {self.class_name}.{subroutine.name.value} {self.symbols.counts['var']}")
        if self.kind == "method":
            self.emit("push argument 0", "pop pointer 0")
        elif self.kind == "constructor":
            # The Jack OS requires a positive allocation even for a fieldless class.
            self.emit(
                f"push constant {max(1, self.symbols.counts['field'])}",
                "call Memory.alloc 1",
                "pop pointer 0",
            )
        self.statements(subroutine.body)

    def variable(self, token, symbol=None):
        if symbol is None:
            symbol = self.symbols.lookup(token.value)
        if symbol is None:
            raise token.error(self.path, f"undefined variable {token.value!r}")
        if symbol.kind == "field" and self.kind == "function":
            raise token.error(self.path, f"field {token.value!r} requires an object")
        return symbol.location

    def statements(self, statements):
        for statement in statements:
            if isinstance(statement, Let):
                self.assign(statement)
            elif isinstance(statement, If):
                self.branch(statement)
            elif isinstance(statement, While):
                self.loop(statement)
            elif isinstance(statement, Do):
                self.call(statement.call)
                self.emit("pop temp 0")
            elif isinstance(statement, Return):
                if statement.value is None:
                    self.emit("push constant 0")
                else:
                    self.expression(statement.value)
                self.emit("return")

    def assign(self, statement):
        target = statement.target
        if isinstance(target, ArrayAccess):
            self.array_address(target)
            self.expression(statement.value)
            # Evaluating the right side can change THAT, so restore the target address here.
            self.emit("pop temp 0", "pop pointer 1", "push temp 0", "pop that 0")
        else:
            self.expression(statement.value)
            self.emit(f"pop {self.variable(target)}")

    def labels(self, *prefixes):
        number = self.next_label
        self.next_label += 1
        return [f"{prefix}{number}" for prefix in prefixes]

    def branch(self, statement):
        then, otherwise, end = self.labels("IF_TRUE", "IF_FALSE", "IF_END")
        self.expression(statement.condition)
        self.emit(f"if-goto {then}", f"goto {otherwise}", f"label {then}")
        self.statements(statement.then_body)
        if statement.else_body is None:
            self.emit(f"label {otherwise}")
        else:
            self.emit(f"goto {end}", f"label {otherwise}")
            self.statements(statement.else_body)
            self.emit(f"label {end}")

    def loop(self, statement):
        start, body, end = self.labels("WHILE_TEST", "WHILE_BODY", "WHILE_END")
        self.emit(f"label {start}")
        self.expression(statement.condition)
        self.emit(f"if-goto {body}", f"goto {end}", f"label {body}")
        self.statements(statement.body)
        self.emit(f"goto {start}", f"label {end}")

    def expression(self, expression):
        self.term(expression.first)
        for operator, term in expression.rest:
            self.term(term)
            self.emit(BINARY_COMMANDS[operator])

    def array_address(self, access):
        self.emit(f"push {self.variable(access.name)}")
        self.expression(access.index)
        self.emit("add")

    def term(self, term):
        if isinstance(term, Expression):
            self.expression(term)
        elif isinstance(term, ArrayAccess):
            self.array_address(term)
            self.emit("pop pointer 1", "push that 0")
        elif isinstance(term, Call):
            self.call(term)
        elif isinstance(term, Unary):
            self.term(term.operand)
            self.emit(UNARY_COMMANDS[term.operator])
        elif term.kind == "identifier":
            self.emit(f"push {self.variable(term)}")
        elif term.kind == "integerConstant":
            self.emit(f"push constant {term.value}")
        elif term.kind == "stringConstant":
            self.string(term)
        elif term.value == "this":
            if self.kind == "function":
                raise term.error(self.path, "'this' requires an object")
            self.emit("push pointer 0")
        else:
            self.emit("push constant 0")
            if term.value == "true":
                self.emit("not")

    def string(self, token):
        if len(token.value) > 32767 or any(ord(character) > 32767 for character in token.value):
            raise token.error(self.path, "string exceeds the VM character or length range")
        self.emit(f"push constant {len(token.value)}", "call String.new 1")
        for character in token.value:
            self.emit(f"push constant {ord(character)}", "call String.appendChar 2")

    def call(self, call):
        argument_count = len(call.arguments)
        if call.receiver is None:
            type_name = self.class_name
            subroutine = self.subroutines.get(call.name.value)
            if subroutine is None:
                raise call.name.error(self.path, f"unknown subroutine {call.name.value!r}")
            if subroutine.kind == "method":
                if self.kind == "function":
                    raise call.name.error(self.path, "method call requires an object")
                self.emit("push pointer 0")
                argument_count += 1
        else:
            receiver = call.receiver
            symbol = self.symbols.lookup(receiver.value)
            if symbol is None:
                type_name = receiver.value
            else:
                type_name = symbol.type_name
                self.emit(f"push {self.variable(receiver, symbol)}")
                argument_count += 1
        for argument in call.arguments:
            self.expression(argument)
        self.emit(f"call {type_name}.{call.name.value} {argument_count}")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path, help="a .jack file or a directory")
    cli.add_argument("-o", "--output-dir", type=Path, help="write VM files into this directory")
    args = cli.parse_args()

    try:
        sources = jack_files(args.source)
        results = []
        for source in sources:
            tree, _, _ = read_jack(source)
            directory = args.output_dir or source.parent
            output = directory / source.with_suffix(".vm").name
            results.append((output, VMCompiler(tree, source).compile()))
        if args.output_dir is not None:
            args.output_dir.mkdir(parents=True, exist_ok=True)
        for path, vm in results:
            path.write_text(vm, encoding="utf-8")
    except (JackError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
