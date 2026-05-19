"""CLI: `python -m webpilot.agent.cli "<brief>"`."""

import argparse
import asyncio

from dotenv import load_dotenv

from .runner import run_brief_local


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run the WebPilot agent on a brief.")
    parser.add_argument("brief", help="Natural-language research brief.")
    parser.add_argument("--no-headless", action="store_true", help="Show the browser window.")
    args = parser.parse_args()

    report = asyncio.run(run_brief_local(args.brief, headless=not args.no_headless))
    print(report)


if __name__ == "__main__":
    main()
