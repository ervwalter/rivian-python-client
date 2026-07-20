"""Generate and verify the checked-in Parallax protobuf modules."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROTO_DIR = ROOT / "src" / "rivian" / "proto"
GENERATED_FILES = ("parallax_pb2.py", "parallax_pb2.pyi")


def generate(output: Path) -> None:
    """Generate Python source and type information into output."""
    subprocess.run(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"--proto_path={PROTO_DIR}",
            f"--python_out={output}",
            f"--pyi_out={output}",
            str(PROTO_DIR / "parallax.proto"),
        ],
        check=True,
    )


def main() -> int:
    """Generate modules or check that the checked-in modules are current."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="fail if generated files differ"
    )
    args = parser.parse_args()

    if not args.check:
        generate(PROTO_DIR)
        return 0

    with tempfile.TemporaryDirectory() as temporary_directory:
        output = Path(temporary_directory)
        generate(output)
        stale = [
            name
            for name in GENERATED_FILES
            if (output / name).read_bytes() != (PROTO_DIR / name).read_bytes()
        ]
    if stale:
        print(
            "Generated protobuf modules are stale: " + ", ".join(stale),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
