"""Localization Controller v2 entrypoint."""
import json
from pathlib import Path
from core import Pipeline


def main():
    config = json.loads(Path("config.json").read_text(encoding="utf-8"))
    Pipeline(config).run()


if __name__ == "__main__":
    main()
