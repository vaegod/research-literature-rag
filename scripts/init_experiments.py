from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.tools.experiment_tool import load_experiment_records


def main() -> None:
    settings = get_settings()
    records = load_experiment_records(settings.experiment_records_path)
    print(f"Experiment records: {len(records)}")
    print(json.dumps(records[:2], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
