"""OutRun2006 Localization Controller v2 entrypoint."""
import json
import os
from pathlib import Path
from core import Pipeline


def main():
    config = json.loads(Path("config.json").read_text(encoding="utf-8"))
    if os.getenv("CONTROLLER_MODE", "localization") != "localization":
        raise RuntimeError("Controller isolation violation")
    return Pipeline(config).run()


if __name__ == "__main__":
    print(main())
