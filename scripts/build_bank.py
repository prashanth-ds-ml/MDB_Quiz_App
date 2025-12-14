import glob
import json
import yaml
from pathlib import Path

from src.domain.models import QuestionV2

ROOT = Path(__file__).resolve().parents[1]
BANK_DIR = ROOT / "question_bank" / "v2" / "questions"
OUT_JSONL = ROOT / "question_bank" / "v2" / "questions.jsonl"
META = ROOT / "question_bank" / "v2" / "bank.meta.json"

def main():
    files = sorted(glob.glob(str(BANK_DIR / "*.yaml")))
    built = 0
    published = 0

    rows = []
    for fp in files:
        p = Path(fp)
        if p.name.startswith("_"):
            continue
        with p.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        q = QuestionV2.model_validate(raw)
        d = q.model_dump()
        rows.append(d)
        built += 1
        if q.status == "published":
            published += 1

    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    META.write_text(json.dumps({
        "schema_version": "2.0",
        "built_questions": built,
        "published_questions": published
    }, indent=2), encoding="utf-8")

    print(f"Built {built} questions → {OUT_JSONL}")
    print(f"Published: {published}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
