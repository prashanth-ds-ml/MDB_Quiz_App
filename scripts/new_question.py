# scripts/new_question.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_DIR = ROOT / "question_bank" / "v2" / "questions"

ID_RE = re.compile(r"^(?P<prefix>[A-Z0-9]+)-Q(?P<num>\d{3,})$")


@dataclass
class Inputs:
    prefix: str
    title: str
    topic: str
    subtopic: str
    difficulty: str
    qtype: str
    pool: str


def normalize_prefix(s: str) -> str:
    s = s.strip().upper()
    s = re.sub(r"[^A-Z0-9]+", "", s)  # remove spaces/symbols
    if not s:
        raise ValueError("Prefix cannot be empty.")
    return s


def next_id(prefix: str) -> str:
    max_n = 0
    for p in QUESTIONS_DIR.glob(f"{prefix}-Q*.yaml"):
        m = ID_RE.match(p.stem)
        if not m:
            continue
        try:
            n = int(m.group("num"))
            max_n = max(max_n, n)
        except ValueError:
            pass
    return f"{prefix}-Q{max_n + 1:03d}"


def prompt_choice(label: str, choices: list[str], default: str) -> str:
    choices_str = "/".join(choices)
    raw = input(f"{label} ({choices_str}) [default: {default}]: ").strip().lower()
    if not raw:
        raw = default
    if raw not in choices:
        raise ValueError(f"Invalid {label}. Choose one of: {choices_str}")
    return raw


def prompt_text(label: str, default: str | None = None) -> str:
    if default:
        raw = input(f"{label} [default: {default}]: ").strip()
        return raw if raw else default
    return input(f"{label}: ").strip()


def make_question_yaml(inp: Inputs, qid: str) -> dict:
    today = date.today().isoformat()

    return {
        "schema_version": "2.0",
        "id": qid,
        "title": inp.title,
        "topic": inp.topic,
        "subtopic": inp.subtopic,
        "difficulty": inp.difficulty,
        "type": inp.qtype,
        "tags": [],
        # INTERNAL ONLY (never shown in practice UI)
        "exam_relevance": {"pool": inp.pool, "confidence": "high"},
        "prompt": "Write the question stem here.",
        "context": "Optional scenario/context (can be empty).",
        "artifacts": {
            "sample_docs": [],
            "snippets": [],
            "notes": [],
        },
        "choices": [
            {"key": "A", "text": "Option A"},
            {"key": "B", "text": "Option B"},
            {"key": "C", "text": "Option C"},
            {"key": "D", "text": "Option D"},
        ],
        "answer": {"keys": ["B"]},
        "rationale": {
            "rule": "One-line memory hook (must be strong).",
            "correct_why": ["Bullet: why the correct answer is correct."],
            "wrong_why": {
                "A": "Why A is wrong",
                "C": "Why C is wrong",
                "D": "Why D is wrong",
            },
            "trap": "Common misconception (recommended, especially for exam pool).",
            "mini_demo": "mongosh / PyMongo snippet to prove the rule (recommended).",
        },
        "status": "draft",
        "author": "prashanth",
        "updated_at": today,
    }


def main() -> int:
    QUESTIONS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n=== New Question Generator (YAML) ===\n")

    prefix_raw = prompt_text("ID prefix (e.g., CRUD, AGG, IDX, PYMONGO)", "CRUD")
    prefix = normalize_prefix(prefix_raw)

    qid = next_id(prefix)
    filename = QUESTIONS_DIR / f"{qid}.yaml"

    title = prompt_text("Title (short label)", f"{prefix} question {qid}")
    topic = prompt_text("Topic", "CRUD")
    subtopic = prompt_text("Subtopic", "general")

    difficulty = prompt_choice("Difficulty", ["easy", "medium", "hard"], "easy")
    qtype = prompt_choice("Type", ["single", "multi"], "single")

    # IMPORTANT: user should not see pool while practicing.
    # This is internal only for mock exam filtering later.
    pool = prompt_choice("Pool (internal)", ["learning", "exam"], "learning")

    inp = Inputs(
        prefix=prefix,
        title=title,
        topic=topic,
        subtopic=subtopic,
        difficulty=difficulty,
        qtype=qtype,
        pool=pool,
    )

    data = make_question_yaml(inp, qid)

    if filename.exists():
        print(f"\n❌ File already exists: {filename}")
        return 1

    with filename.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=100)

    print(f"\n✅ Created: {filename}")
    print("Next steps:")
    print("  1) Edit the YAML and fill real content")
    print("  2) Validate: python -m scripts.validate_bank")
    print("  3) Build:    python -m scripts.build_bank\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
