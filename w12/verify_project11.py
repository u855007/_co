"""Compile the six Project 11 examples and run them in the official VM emulator."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJECTS = ("Seven", "ConvertToBin", "Square", "Average", "Pong", "ComplexArrays")
# Skip busy-wait delays in the interactive tests while preserving the other Sys services.
FAST_WAIT = "function Sys.wait 0\npush constant 0\nreturn\n"


def main():
    tools = ROOT / "tools"
    libraries = ("Hack", "HackGUI", "Simulators", "SimulatorsGUI", "Compilers")
    classpath = os.pathsep.join([".", *(f"bin/lib/{name}.jar" for name in libraries)])
    with TemporaryDirectory(prefix="nand-project11-") as temporary:
        output = Path(temporary)
        for name in PROJECTS:
            directory = output / name
            subprocess.run(
                [sys.executable, HERE / "JackCompiler.py", ROOT / "11" / name, "-o", directory],
                check=True,
            )
            # The emulator's headless mode runs the bundled Jack OS VM files.
            for source in (tools / "OS").glob("*.vm"):
                code = source.read_text(encoding="utf-8")
                if source.name == "Sys.vm" and name in {"Square", "Pong"}:
                    start = code.index("function Sys.wait ")
                    end = code.index("function Sys.error ", start)
                    code = code[:start] + FAST_WAIT + code[end:]
                (directory / source.name).write_text(code, encoding="utf-8")
        subprocess.run(
            ["java", "-Djava.awt.headless=true", "-cp", classpath, HERE / "VerifyProject11.java", output],
            cwd=tools,
            check=True,
        )


if __name__ == "__main__":
    main()
