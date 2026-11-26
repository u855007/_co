"""Tokenize and parse Jack for both the XML analyzer and the VM compiler."""

import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape


KEYWORDS = set("""
    class constructor function method field static var int char boolean void
    true false null this let do if else while return
""".split())
OPERATORS = set("+-*/&|<>=")
CONSTANTS = {"true", "false", "null", "this"}
CLASS_KINDS = {"static", "field"}
SUBROUTINE_KINDS = {"constructor", "function", "method"}

LEXEME = re.compile(
    r'(?P<space>\s+)|(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)'
    r'|(?P<unfinished_comment>/\*)|(?P<stringConstant>"[^"\r\n]*")'
    r'|(?P<unfinished_string>")|(?P<integerConstant>[0-9][A-Za-z0-9_]*)'
    r'|(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)'
    r'|(?P<symbol>[{}()\[\].,;+*/&|<>=~-])'
)


class JackError(Exception):
    """An invalid Jack input or failed comparison."""


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int

    def error(self, path, message):
        return JackError(f"{path}:{self.line}:{self.column}: {message}")

    def xml(self):
        value = escape(self.value, {'"': "&quot;"})
        return f"<{self.kind}> {value} </{self.kind}>"


def tokenize(source, path):
    tokens = []
    offset = 0
    line = column = 1
    while offset < len(source):
        match = LEXEME.match(source, offset)
        if match is None:
            token = Token("invalid", source[offset], line, column)
            raise token.error(path, f"unexpected character {token.value!r}")

        kind = match.lastgroup
        raw = value = match.group()
        if kind == "unfinished_comment":
            raise Token(kind, value, line, column).error(path, "unclosed block comment")
        if kind == "unfinished_string":
            raise Token(kind, value, line, column).error(path, "unclosed string literal")
        if kind == "integerConstant":
            token = Token(kind, value, line, column)
            if not value.isdecimal():
                raise token.error(path, f"invalid integer literal {value!r}")
            value = value.lstrip("0") or "0"
            if len(value) > 5 or int(value) > 32767:
                raise token.error(path, "integer literal must be from 0 to 32767")
        if kind == "identifier" and value in KEYWORDS:
            kind = "keyword"
        if kind == "stringConstant":
            value = value[1:-1]
        if kind not in {"space", "comment"}:
            tokens.append(Token(kind, value, line, column))

        newlines = raw.count("\n")
        line += newlines
        if newlines:
            column = len(raw.rsplit("\n", 1)[1]) + 1
        else:
            column += len(raw)
        offset = match.end()

    tokens.append(Token("eof", "", line, column))
    return tokens


@dataclass
class Declaration:
    kind: str
    type_name: str
    names: list[Token]


@dataclass
class Expression:
    first: "Term"
    rest: list[tuple[str, "Term"]]


@dataclass
class ArrayAccess:
    name: Token
    index: Expression


@dataclass
class Call:
    receiver: Token | None
    name: Token
    arguments: list[Expression]


@dataclass
class Unary:
    operator: str
    operand: "Term"


Term = Token | ArrayAccess | Call | Unary | Expression


@dataclass
class Let:
    target: Token | ArrayAccess
    value: Expression


@dataclass
class If:
    condition: Expression
    then_body: list["Statement"]
    else_body: list["Statement"] | None


@dataclass
class While:
    condition: Expression
    body: list["Statement"]


@dataclass
class Do:
    call: Call


@dataclass
class Return:
    value: Expression | None


Statement = Let | If | While | Do | Return


@dataclass
class Subroutine:
    kind: str
    name: Token
    parameters: list[Declaration]
    locals: list[Declaration]
    body: list[Statement]


@dataclass
class JackClass:
    name: Token
    variables: list[Declaration]
    subroutines: list[Subroutine]


class Parser:
    def __init__(self, tokens, path, *, emit_xml=False):
        self.tokens = tokens
        self.path = path
        self.position = 0
        self.xml = [] if emit_xml else None
        self.depth = 0

    @property
    def current(self):
        return self.tokens[self.position]

    def at(self, *values):
        return self.current.kind in {"keyword", "symbol"} and self.current.value in values

    def take(self):
        token = self.current
        self.position += 1
        self.write_xml(token.xml() if self.xml is not None else "")
        return token

    def expect(self, value):
        if not self.at(value):
            raise self.expected(repr(value))
        return self.take()

    def identifier(self):
        if self.current.kind != "identifier":
            raise self.expected("identifier")
        return self.take()

    def expected(self, description):
        token = self.current
        actual = "end of file" if token.kind == "eof" else repr(token.value)
        return token.error(self.path, f"expected {description}, found {actual}")

    def write_xml(self, line):
        if self.xml is not None:
            self.xml.append("  " * self.depth + line)

    @contextmanager
    def node(self, tag):
        self.write_xml(f"<{tag}>")
        self.depth += 1
        yield
        self.depth -= 1
        self.write_xml(f"</{tag}>")

    def parse(self):
        with self.node("class"):
            self.expect("class")
            name = self.identifier()
            self.expect("{")
            variables = []
            while self.at(*CLASS_KINDS):
                with self.node("classVarDec"):
                    variables.append(self.declaration())
            subroutines = []
            while self.at(*SUBROUTINE_KINDS):
                subroutines.append(self.subroutine())
            self.expect("}")
        if self.current.kind != "eof":
            raise self.expected("end of file")
        return JackClass(name, variables, subroutines)

    def type_name(self):
        if self.at("int", "char", "boolean"):
            return self.take().value
        return self.identifier().value

    def declaration(self):
        kind = self.take().value
        type_name = self.type_name()
        names = [self.identifier()]
        while self.at(","):
            self.take()
            names.append(self.identifier())
        self.expect(";")
        return Declaration(kind, type_name, names)

    def subroutine(self):
        with self.node("subroutineDec"):
            kind = self.take().value
            if self.at("void"):
                self.take()
            else:
                self.type_name()
            name = self.identifier()
            self.expect("(")
            parameters = self.parameters()
            self.expect(")")
            with self.node("subroutineBody"):
                self.expect("{")
                locals_ = []
                while self.at("var"):
                    with self.node("varDec"):
                        locals_.append(self.declaration())
                body = self.statements()
                self.expect("}")
            return Subroutine(kind, name, parameters, locals_, body)

    def parameters(self):
        with self.node("parameterList"):
            parameters = []
            if not self.at(")"):
                parameters.append(self.parameter())
                while self.at(","):
                    self.take()
                    parameters.append(self.parameter())
            return parameters

    def parameter(self):
        type_name = self.type_name()
        return Declaration("argument", type_name, [self.identifier()])

    def statements(self):
        readers = {
            "let": self.let_statement,
            "if": self.if_statement,
            "while": self.while_statement,
            "do": self.do_statement,
            "return": self.return_statement,
        }
        statements = []
        with self.node("statements"):
            while self.at(*readers):
                keyword = self.current.value
                with self.node(f"{keyword}Statement"):
                    self.take()
                    statements.append(readers[keyword]())
        return statements

    def let_statement(self):
        target = self.identifier()
        if self.at("["):
            target = self.array_access(target)
        self.expect("=")
        value = self.expression()
        self.expect(";")
        return Let(target, value)

    def if_statement(self):
        condition = self.condition()
        then_body = self.block()
        else_body = None
        if self.at("else"):
            self.take()
            else_body = self.block()
        return If(condition, then_body, else_body)

    def while_statement(self):
        return While(self.condition(), self.block())

    def do_statement(self):
        call = self.call(self.identifier())
        self.expect(";")
        return Do(call)

    def return_statement(self):
        value = None if self.at(";") else self.expression()
        self.expect(";")
        return Return(value)

    def condition(self):
        self.expect("(")
        condition = self.expression()
        self.expect(")")
        return condition

    def block(self):
        self.expect("{")
        statements = self.statements()
        self.expect("}")
        return statements

    def expression(self):
        with self.node("expression"):
            first = self.term()
            rest = []
            while self.at(*OPERATORS):
                rest.append((self.take().value, self.term()))
            return Expression(first, rest)

    def term(self):
        with self.node("term"):
            token = self.current
            if token.kind in {"integerConstant", "stringConstant"} or self.at(*CONSTANTS):
                return self.take()
            if self.at("-", "~"):
                return Unary(self.take().value, self.term())
            if self.at("("):
                return self.condition()
            name = self.identifier()
            if self.at("["):
                return self.array_access(name)
            if self.at("(", "."):
                return self.call(name)
            return name

    def array_access(self, name):
        self.expect("[")
        index = self.expression()
        self.expect("]")
        return ArrayAccess(name, index)

    def call(self, name):
        receiver = None
        if self.at("."):
            self.take()
            receiver, name = name, self.identifier()
        self.expect("(")
        with self.node("expressionList"):
            arguments = []
            if not self.at(")"):
                arguments.append(self.expression())
                while self.at(","):
                    self.take()
                    arguments.append(self.expression())
        self.expect(")")
        return Call(receiver, name, arguments)


def read_jack(path, *, emit_xml=False):
    tokens = tokenize(path.read_text(encoding="utf-8-sig"), path)
    parser = Parser(tokens, path, emit_xml=emit_xml)
    tree = parser.parse()
    return tree, tokens[:-1], parser.xml


def jack_files(path: Path):
    """Find the Jack sources in a single file or one application directory."""
    if path.is_file() and path.suffix == ".jack":
        return [path]
    if path.is_dir():
        files = sorted(file for file in path.glob("*.jack") if file.is_file())
        if files:
            return files
    raise JackError(f"{path}: expected a .jack file or a directory containing .jack files")
