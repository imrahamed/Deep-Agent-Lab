"""Execute actual agent trials against the configured models and retrieval services."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from deep_agent_lab.evaluation import load_cases, run_evaluation
from deep_agent_lab.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="Compatibility flag; all trials use real services"
    )
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("docs/reports/evaluation.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    with TemporaryDirectory() as directory:
        report = run_evaluation(
            load_cases(root / "data/evaluation/northstar.jsonl"),
            Path(directory),
            trials=args.trials,
            live_settings=Settings(deep_lab_mode="live", langfuse_enabled=False),
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
