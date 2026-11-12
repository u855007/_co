#!/usr/bin/env python3
"""Nand2Tetris Project 6: two-pass Hack assembler (.asm -> .hack)."""

import argparse
import re
from pathlib import Path

COMP = {
    "0": "0101010", "1": "0111111", "-1": "0111010",
    "D": "0001100", "A": "0110000", "M": "1110000",
    "!D": "0001101", "!A": "0110001", "!M": "1110001",
    "-D": "0001111", "-A": "0110011", "-M": "1110011",
    "D+1": "0011111", "A+1": "0110111", "M+1": "1110111",
    "D-1": "0001110", "A-1": "0110010", "M-1": "1110010",
    "D+A": "0000010", "D+M": "1000010",
    "D-A": "0010011", "D-M": "1010011",
    "A-D": "0000111", "M-D": "1000111",
    "D&A": "0000000", "D&M": "1000000",
    "D|A": "0010101", "D|M": "1010101",
}

JUMP = {
    "": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
    "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111",
}

SYMBOL_PATTERN = re.compile(r"[A-Za-z_.$:][A-Za-z0-9_.$:]*\Z")


def predefined_symbols():
    table = {"SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
             "SCREEN": 16384, "KBD": 24576}
    table.update({f"R{i}": i for i in range(16)})
    return table


def clean_source(source):
    """Keep nonempty commands together with their original line numbers."""
    commands = []
    for line_no, raw_line in enumerate(source.splitlines(), start=1):
        line = "".join(raw_line.split("//", 1)[0].split())
        if line:
            commands.append((line_no, line))
    return commands


def check_symbol(name, line_no):
    if not SYMBOL_PATTERN.fullmatch(name):
        raise ValueError(f"第 {line_no} 行：不合法的符號 {name!r}")


def assemble(source):
    commands = clean_source(source)
    symbols = predefined_symbols()
    instructions = []
    rom_address = 0

    # Pass 1: assign ROM addresses to (LABEL) declarations.
    for line_no, cmd in commands:
        if cmd.startswith("("):
            if not cmd.endswith(")"):
                raise ValueError(f"第 {line_no} 行：標籤缺少右括號：{cmd}")
            label = cmd[1:-1]
            check_symbol(label, line_no)
            if label in symbols:
                raise ValueError(f"第 {line_no} 行：重複或保留的標籤 {label!r}")
            if rom_address > 32767:
                raise ValueError(f"第 {line_no} 行：ROM 位址超出 15 位元範圍")
            symbols[label] = rom_address
        else:
            if rom_address > 32767:
                raise ValueError(f"第 {line_no} 行：程式超出 Hack ROM 容量")
            instructions.append((line_no, cmd))
            rom_address += 1

    # Pass 2: allocate variables starting from RAM[16], translate instructions.
    ram_address = 16
    output = []
    for line_no, cmd in instructions:
        if cmd.startswith("@"):
            operand = cmd[1:]
            if operand.isascii() and operand.isdecimal():
                address = int(operand)
            else:
                check_symbol(operand, line_no)
                if operand not in symbols:
                    if ram_address > 32767:
                        raise ValueError(f"第 {line_no} 行：變數位址超出範圍")
                    symbols[operand] = ram_address
                    ram_address += 1
                address = symbols[operand]
            if not 0 <= address <= 32767:
                raise ValueError(f"第 {line_no} 行：A 指令位址超出範圍：{address}")
            output.append(f"{address:016b}")
            continue

        # C instruction syntax: [dest=]comp[;jump]
        if cmd.count("=") > 1 or cmd.count(";") > 1:
            raise ValueError(f"第 {line_no} 行：C 指令格式錯誤：{cmd}")
        left, sep, jump = cmd.partition(";")
        if not sep:
            jump = ""
        dest, eq, comp = left.partition("=")
        if not eq:
            comp, dest = left, ""

        if comp not in COMP:
            raise ValueError(f"第 {line_no} 行：不支援的 comp：{comp!r}")
        if jump not in JUMP:
            raise ValueError(f"第 {line_no} 行：不支援的 jump：{jump!r}")
        if any(ch not in "ADM" for ch in dest) or len(set(dest)) != len(dest):
            raise ValueError(f"第 {line_no} 行：不合法的 dest：{dest!r}")

        dest_bits = f"{int('A' in dest)}{int('D' in dest)}{int('M' in dest)}"
        output.append("111" + COMP[comp] + dest_bits + JUMP[jump])

    return "\n".join(output) + ("\n" if output else "")


def main():
    parser = argparse.ArgumentParser(description="Nand2Tetris Hack 組譯器")
    parser.add_argument("input", type=Path, help="輸入的 .asm 檔案")
    args = parser.parse_args()
    path = args.input
    if path.suffix.lower() != ".asm":
        parser.error("輸入檔案必須是 .asm")
    try:
        binary = assemble(path.read_text(encoding="utf-8-sig"))
        output_path = path.with_suffix(".hack")
        output_path.write_text(binary, encoding="utf-8", newline="\n")
    except (OSError, UnicodeError, ValueError) as exc:
        parser.exit(status=1, message=f"組譯失敗：{exc}\n")
    print(f"組譯成功：{output_path}")


if __name__ == "__main__":
    main()
