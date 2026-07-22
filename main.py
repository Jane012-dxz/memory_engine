"""CLI entry point for Memory Engine."""

import argparse

from config import settings
from data.generator import SyntheticDataGenerator


def main() -> None:
    parser = argparse.ArgumentParser(description="Memory Engine CLI")
    sub = parser.add_subparsers(dest="command")

    seed_parser = sub.add_parser("seed", help="Seed database with synthetic data")
    seed_parser.add_argument("-n", "--count", type=int, default=20, help="Number of samples")

    sub.add_parser("ui", help="Launch Streamlit UI")

    args = parser.parse_args()
    settings.ensure_dirs()

    if args.command == "seed":
        gen = SyntheticDataGenerator()
        created = gen.seed_database(count=args.count)
        print(f"Seeded {created} synthetic memories.")
    elif args.command == "ui":
        import subprocess
        import sys

        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "ui/app.py", "--", f"--server.port={settings.streamlit_port}"],
            check=True,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
