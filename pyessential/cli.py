import argparse
import sys

from ._version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyessential",
        description="PyEssential - a collection of Python utilities and decorators.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())