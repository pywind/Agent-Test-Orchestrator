"""CLI entrypoint for running the orchestrator."""
from __future__ import annotations

import argparse
import json

from .agent import run_cli


def main() -> None:
    parser = argparse.ArgumentParser(description="Asynchronous ReWOO orchestrator")
    parser.add_argument("--doc", required=True, help="Path to the document pack input")
    args = parser.parse_args()

    outcome = run_cli(args.doc)
    print(json.dumps(outcome.to_dict(), indent=2, default=str))


if __name__ == "__main__":
    main()
