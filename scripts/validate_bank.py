import glob
import sys
import yaml
from pathlib import Path

from src.domain.models import QuestionV2

ROOT = Path(__file__).resolve().parents[1]
BANK_DIR = ROOT / "question_bank" / "v2" / "questions"

def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    files = sorted(glob.glob(str(BANK_DIR / "*.yaml")))
    if not files:
        print(f"No YAML files found in {BANK_DIR}")
        return 1

    ids = set()
    errors = []
    ok = 0

    for fp in files:
        p = Path(fp)
        if p.name.startswith("_"):
            continue
        try:
            obj = load_yaml(p)
            q = QuestionV2.model_validate(obj)

            if q.id in ids:
                raise ValueError(f"Duplicate id detected: {q.id}")
            ids.add(q.id)

            # Extra guardrail for exam pool quality (still hidden from users)
            if q.exam_relevance.pool == "exam":
                # must have trap OR mini_demo for medium/hard (upgrade quality)
                if q.difficulty in ("medium", "hard") and not (q.rationale.trap or q.rationale.mini_demo):
                    raise ValueError("Exam question (medium/hard) must include rationale.trap or rationale.mini_demo")

            ok += 1
        except Exception as e:
            errors.append((p.name, str(e)))

    if errors:
        print("\nVALIDATION FAILED ❌\n")
        for name, msg in errors:
            print(f"- {name}: {msg}")
        print(f"\nValid: {ok}, Invalid: {len(errors)}")
        return 1

    print(f"VALIDATION PASSED ✅  ({ok} questions)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
