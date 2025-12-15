from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JSONL_PATH = ROOT / "question_bank" / "v2" / "questions.jsonl"
REVISION_PATH = ROOT / "data" / "revision.json"
MOCK_HISTORY_PATH = ROOT / "data" / "mock_history.json"


def load_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


st.set_page_config(page_title="Stats", layout="wide")
st.title("Stats")

questions = load_jsonl(JSONL_PATH)
revision = load_json(REVISION_PATH, {"items": {}})
history = load_json(MOCK_HISTORY_PATH, {"attempts": []})

published = [q for q in questions if q.get("status") == "published"]
exam_pool = [q for q in published if (q.get("exam_relevance") or {}).get("pool") == "exam"]
learn_pool = [q for q in published if (q.get("exam_relevance") or {}).get("pool") == "learning"]

rev_items = revision.get("items") or {}
attempts = history.get("attempts") or []

# --- Top KPIs ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("Published Questions", str(len(published)))
k2.metric("Exam Pool", str(len(exam_pool)))
k3.metric("Learning Pool", str(len(learn_pool)))
k4.metric("Revision Queue", str(len(rev_items)))

st.divider()

# --- Mock performance summary ---
st.markdown("## Mock Exam Performance")

if not attempts:
    st.info("No mock attempts yet. Take one mock exam to populate stats.")
else:
    last = attempts[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Last Score", f"{last.get('score',0)}/{last.get('total',0)}")
    c2.metric("Last %", f"{last.get('pct',0)}%")
    c3.metric("Attempts", str(len(attempts)))

    best = max(attempts, key=lambda a: a.get("pct", 0))
    c4.metric("Best %", f"{best.get('pct',0)}%")

    # show recent attempts table-like
    st.markdown("### Recent attempts (latest 10)")
    for a in attempts[-10:][::-1]:
        st.write(
            f"- **{a.get('ts','')}** — {a.get('score',0)}/{a.get('total',0)} "
            f"({a.get('pct',0)}%) • mix: {a.get('mode','')}"
        )

st.divider()

# --- Weak areas (from Revision + mock history) ---
st.markdown("## Weak Areas")

# From revision: count by topic/difficulty
by_topic = {}
by_diff = {}

# Map question id -> topic/diff
by_id = {q.get("id"): q for q in questions if q.get("id")}

for qid, rec in rev_items.items():
    q = by_id.get(qid)
    if not q:
        continue
    t = q.get("topic", "Unknown")
    d = q.get("difficulty", "Unknown")

    by_topic[t] = by_topic.get(t, 0) + 1
    by_diff[d] = by_diff.get(d, 0) + 1

c1, c2 = st.columns(2)

with c1:
    st.markdown("### Revision count by Topic")
    if by_topic:
        st.json(dict(sorted(by_topic.items(), key=lambda x: x[1], reverse=True)))
    else:
        st.write("No revision items yet.")

with c2:
    st.markdown("### Revision count by Difficulty")
    if by_diff:
        st.json(dict(sorted(by_diff.items(), key=lambda x: x[1], reverse=True)))
    else:
        st.write("No revision items yet.")

st.divider()

# --- Topic accuracy from mocks (aggregated) ---
st.markdown("## Accuracy by Topic (from mocks)")

if not attempts:
    st.info("Take at least 1 mock exam to see accuracy breakdown.")
else:
    agg = {}
    for a in attempts:
        bt = a.get("by_topic") or {}
        for topic, vals in bt.items():
            agg.setdefault(topic, {"correct": 0, "total": 0})
            agg[topic]["correct"] += vals.get("correct", 0)
            agg[topic]["total"] += vals.get("total", 0)

    # compute accuracy
    acc = []
    for topic, vals in agg.items():
        total = vals["total"]
        correct = vals["correct"]
        pct = (correct / total) * 100 if total else 0
        acc.append((topic, correct, total, pct))

    acc.sort(key=lambda x: x[3])  # weakest first

    st.markdown("### Weakest topics first")
    for topic, correct, total, pct in acc[:12]:
        st.write(f"- **{topic}**: {correct}/{total} ({pct:.1f}%)")

st.divider()

# --- Quick action suggestions ---
st.markdown("## What to do next")

if len(rev_items) > 0:
    st.write("✅ Do a **Revision session** until your revision queue drops.")
else:
    st.write("✅ Your revision queue is empty — take a mock exam to discover weak areas.")

if attempts:
    last_pct = attempts[-1].get("pct", 0)
    if last_pct < 70:
        st.write("✅ Focus on **Concept repair** (Practice + Revision), then retake mock.")
    else:
        st.write("✅ Focus on **timed mocks** and reducing silly mistakes.")
else:
    st.write("✅ Take your first mock exam once you have ~30 exam-pool questions.")
