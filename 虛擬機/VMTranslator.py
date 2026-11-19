#!/usr/bin/env python3
"""Translate nand2tetris VM programs (projects 7 and 8) into Hack assembly."""

import argparse
import re
from pathlib import Path


BINARY = {"add": "D+M", "sub": "M-D", "and": "D&M", "or": "D|M"}
UNARY = {"neg": "-M", "not": "!M"}
COMPARE = {"eq": "JEQ", "lt": "JLT", "gt": "JGT"}
BASE = {"local": "LCL", "argument": "ARG", "this": "THIS", "that": "THAT"}
SEGMENTS = {*BASE, "constant", "static", "temp", "pointer"}
BRANCH = {"label", "goto", "if-goto"}
ARITY = {
    **dict.fromkeys((*BINARY, *UNARY, *COMPARE, "return"), 0),
    **dict.fromkeys(BRANCH, 1),
    **dict.fromkeys(("push", "pop", "function", "call"), 2),
}
SYMBOL = re.compile(r"[A-Za-z_.$:][A-Za-z0-9_.$:]*")
SAVED_SEGMENTS = ("LCL", "ARG", "THIS", "THAT")


def parse(path):
    commands = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        words = line.partition("//")[0].split()
        if not words:
            continue
        op, *args = words
        where = f"{path}:{line_no}"
        if op not in ARITY or len(args) != ARITY[op]:
            raise ValueError(f"{where}：無法辨識指令或參數數量有誤：{' '.join(words)}")
        if op in BRANCH or op in ("function", "call"):
            if not SYMBOL.fullmatch(args[0]):
                raise ValueError(f"{where}：不合法的名稱 {args[0]!r}")
        if len(args) == 2:
            if not re.fullmatch(r"[0-9]+", args[1]):
                raise ValueError(f"{where}：需要非負整數，讀到 {args[1]!r}")
            index = int(args[1])
            limit = 32767
            if op in ("push", "pop"):
                segment = args[0]
                if segment not in SEGMENTS or (op == "pop" and segment == "constant"):
                    raise ValueError(f"{where}：不支援 {op} {segment}")
                limit = {"pointer": 1, "temp": 7, "static": 239}.get(segment, limit)
            if index > limit:
                raise ValueError(f"{where}：{op} {args[0]} 的數值必須介於 0 和 {limit}")
            args[1] = index
        commands.append((line_no, op, args))
    return commands


class CodeWriter:
    def __init__(self):
        self.lines = []
        self.symbols = {}
        self.used = {"SP", *SAVED_SEGMENTS, "SCREEN", "KBD", *(f"R{i}" for i in range(16))}
        self.serial = 0

    def emit(self, *lines):
        self.lines.extend(lines)

    def unique(self, purpose):
        while True:
            self.serial += 1
            name = f"__VM${purpose}.{self.serial}"
            if name not in self.used:
                self.used.add(name)
                return name

    def symbol(self, key, name):
        # Hack shares one namespace for function labels, branch labels and statics.
        if key not in self.symbols:
            if name in self.used or not SYMBOL.fullmatch(name):
                name = self.unique("symbol")
            self.used.add(name)
            self.symbols[key] = name
        return self.symbols[key]

    def push_d(self):
        self.emit("@SP", "A=M", "M=D", "@SP", "M=M+1")

    def pop_d(self):
        self.emit("@SP", "AM=M-1", "D=M")

    def memory(self, op, segment, index):
        if segment == "constant":
            self.emit(f"@{index}", "D=A")
            self.push_d()
            return

        if segment in BASE:
            self.emit(f"@{index}", "D=A", f"@{BASE[segment]}")
            if op == "push":
                self.emit("A=D+M", "D=M")
                self.push_d()
            else:
                self.emit("D=D+M", "@R13", "M=D")
                self.pop_d()
                self.emit("@R13", "A=M", "M=D")
            return

        if segment == "pointer":
            address = ("THIS", "THAT")[index]
        elif segment == "temp":
            address = f"R{5 + index}"
        else:
            address = self.symbol(("static", self.file, index), f"{self.file}.{index}")
        if op == "push":
            self.emit(f"@{address}", "D=M")
            self.push_d()
        else:
            self.pop_d()
            self.emit(f"@{address}", "M=D")

    def compare(self, op):
        yes = self.unique("true")
        no = self.unique("false")
        end = self.unique("end")
        self.pop_d()  # y in D, x at SP-1
        if op != "eq":
            # Opposite signs decide the result immediately. Only subtract like signs.
            x_negative = self.unique("xneg")
            same_sign = self.unique("same")
            self.emit("@R13", "M=D", "@SP", "A=M-1", "D=M", f"@{x_negative}", "D;JLT")
            self.emit("@R13", "D=M", f"@{yes if op == 'gt' else no}", "D;JLT")
            self.emit(f"@{same_sign}", "0;JMP", f"({x_negative})")
            self.emit("@R13", "D=M", f"@{yes if op == 'lt' else no}", "D;JGE")
            self.emit(f"({same_sign})")
        self.emit("@SP", "A=M-1", "D=M-D", f"@{yes}", f"D;{COMPARE[op]}")
        self.emit(f"({no})", "D=0", f"@{end}", "0;JMP", f"({yes})", "D=-1")
        self.emit(f"({end})", "@SP", "A=M-1", "M=D")

    def function(self, name, locals_count):
        self.scope = ("function", name)
        label = self.symbol(self.scope, name)
        self.emit(f"({label})")
        if locals_count:
            loop = self.unique("locals")
            self.emit(f"@{locals_count}", "D=A", f"({loop})", "@SP", "A=M", "M=0")
            self.emit("@SP", "M=M+1", "D=D-1", f"@{loop}", "D;JGT")

    def call(self, name, args_count):
        target = self.symbol(("function", name), name)
        resume = self.unique("return")
        self.emit(f"@{resume}", "D=A")
        self.push_d()
        for reg in SAVED_SEGMENTS:
            self.emit(f"@{reg}", "D=M")
            self.push_d()
        self.emit("@SP", "D=M", "@5", "D=D-A", f"@{args_count}", "D=D-A", "@ARG", "M=D")
        self.emit("@SP", "D=M", "@LCL", "M=D", f"@{target}", "0;JMP", f"({resume})")

    def return_from_call(self):
        # Save the return address before *ARG is overwritten in a zero-argument call.
        self.emit("@LCL", "D=M", "@R13", "M=D", "@5", "A=D-A", "D=M", "@R14", "M=D")
        self.pop_d()
        self.emit("@ARG", "A=M", "M=D", "@ARG", "D=M+1", "@SP", "M=D")
        for reg in reversed(SAVED_SEGMENTS):
            self.emit("@R13", "AM=M-1", "D=M", f"@{reg}", "M=D")
        self.emit("@R14", "A=M", "0;JMP")

    def bootstrap(self):
        self.emit("// Bootstrap", "@256", "D=A", "@SP", "M=D")
        self.call("Sys.init", 0)
        halt = self.unique("halt")
        self.emit(f"({halt})", f"@{halt}", "0;JMP")

    def write_file(self, path, commands):
        self.file = path.stem
        self.scope = ("file", self.file)
        for _, op, args in commands:
            self.emit("// " + " ".join(map(str, (op, *args))))
            if op in BINARY:
                self.pop_d()
                self.emit("A=A-1", f"M={BINARY[op]}")
            elif op in UNARY:
                self.emit("@SP", "A=M-1", f"M={UNARY[op]}")
            elif op in COMPARE:
                self.compare(op)
            elif op in ("push", "pop"):
                self.memory(op, *args)
            elif op in BRANCH:
                label = self.symbol((*self.scope, args[0]), f"{self.scope[1]}${args[0]}")
                if op == "label":
                    self.emit(f"({label})")
                elif op == "goto":
                    self.emit(f"@{label}", "0;JMP")
                else:
                    self.pop_d()
                    self.emit(f"@{label}", "D;JNE")
            elif op == "function":
                self.function(*args)
            elif op == "call":
                self.call(*args)
            else:  # return
                self.return_from_call()


def translate(source, bootstrap="auto"):
    source = source.resolve()
    if source.is_dir():
        files = sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower() == ".vm")
        if not files:
            raise ValueError(f"{source}：資料夾中沒有 .vm 檔")
        output = source / (source.name + ".asm")
    elif source.is_file() and source.suffix.lower() == ".vm":
        files = [source]
        output = source.with_suffix(".asm")
    else:
        raise ValueError(f"{source}：請指定現有的 .vm 檔或資料夾")

    programs = [(path, parse(path)) for path in files]
    functions = set()
    for path, commands in programs:
        scope = ("file", path.stem)
        labels = set()
        jumps = []
        for line, op, args in commands:
            if op == "function":
                name = args[0]
                if name in functions:
                    raise ValueError(f"{path}:{line}：函式 {name} 重複定義")
                functions.add(name)
                scope = ("function", name)
            elif op == "label":
                key = (*scope, args[0])
                if key in labels:
                    raise ValueError(f"{path}:{line}：標籤 {args[0]} 重複定義")
                labels.add(key)
            elif op in ("goto", "if-goto"):
                jumps.append((line, (*scope, args[0])))
        for line, key in jumps:
            if key not in labels:
                raise ValueError(f"{path}:{line}：此範圍內未定義標籤 {key[-1]}")

    writer = CodeWriter()
    if bootstrap == "always" or (bootstrap == "auto" and "Sys.init" in functions):
        if "Sys.init" not in functions:
            raise ValueError("啟動程式需要輸入檔定義 Sys.init")
        writer.bootstrap()
    for path, commands in programs:
        writer.write_file(path, commands)
    output.write_text("\n".join(writer.lines) + "\n", encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", default=Path("."), help=".vm 檔或資料夾")
    parser.add_argument("--bootstrap", choices=("auto", "always", "never"), default="auto",
                        help="預設 auto：輸入定義 Sys.init 時才加入啟動程式")
    args = parser.parse_args()
    try:
        print(translate(args.source, args.bootstrap))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
