from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import date, timedelta

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


def pct(a: float, b: float) -> float:
    return round((a / b) * 100, 2) if b else 0.0


def top_n_dict(d: dict, n: int = 6, reverse: bool = True):
    items = sorted(d.items(), key=lambda x: x[1], reverse=reverse)
    return items[:n]


def make_plan(
    horizon_days: int,
    minutes_per_day: int,
    revision_count: int,
    last_mock_pct: float | None,
    weakest_topics: list[str],
    exam_pool_size: int,
):
    # Heuristics:
    # - If revision big or last mock low => more Revision + targeted Practice
    # - If last mock decent => more timed mocks and error reduction
    # - Maintain daily bank growth (even 3–5 Q/day) for momentum

    blocks = max(2, minutes_per_day // 25)  # pomodoro-style blocks

    # target distribution
    if last_mock_pct is None:
        # early stage: build concepts + bank
        rev_share = 0.35
        prac_share = 0.45
        mock_share = 0.20
    elif last_mock_pct < 65:
        rev_share = 0.45
        prac_share = 0.40
        mock_share = 0.15
    elif last_mock_pct < 75:
        rev_share = 0.40
        prac_share = 0.35
        mock_share = 0.25
    else:
        rev_share = 0.30
        prac_share = 0.30
        mock_share = 0.40

    # adjust based on revision pile
    if revision_count >= 80:
        rev_share += 0.10
        prac_share -= 0.05
        mock_share -= 0.05
    elif revision_count <= 10:
        rev_share -= 0.10
        prac_share += 0.05
        mock_share += 0.05

    # clamp
    rev_share = max(0.15, min(0.60, rev_share))
    prac_share = max(0.15, min(0.60, prac_share))
    mock_share = max(0.10, min(0.50, mock_share))

    # daily targets in blocks
    rev_blocks = max(1, round(blocks * rev_share))
    prac_blocks = max(1, round(blocks * prac_share))
    mock_blocks = max(1, blocks - rev_blocks - prac_blocks)

    # mock frequency baseline
    if exam_pool_size < 25:
        # too early for realistic mocks
        mock_every = 4
    elif exam_pool_size < 50:
        mock_every = 3
    else:
        mock_every = 2 if (last_mock_pct or 0) < 75 else 2

    # bank growth targets
    # keep it sustainable; exam pool should grow steadily
    if exam_pool_size < 50:
        new_q_per_day = 5
    else:
        new_q_per_day = 3

    plan = []
    start = date.today()

    for i in range(horizon_days):
        day = start + timedelta(days=i)

        # choose focus topic for the day
        focus_topic = weakest_topics[i % max(1, len(weakest_topics))] if weakest_topics else "Mixed"

        is_mock_day = (i % mock_every == mock_every - 1)

        items = []
        items.append(f"**Focus topic:** {focus_topic}")

        # Revision
        items.append(f"**Revision:** {rev_blocks} blocks (aim: clear 8–15 items depending on difficulty)")

        # Practice
        items.append(f"**Practice:** {prac_blocks} blocks (target: 15–25 questions, slow & accurate)")

        # Mock / Timed
        if is_mock_day:
            items.append(f"**Mock exam:** {mock_blocks} blocks (timed) → then push wrong to Revision")
        else:
            items.append(f"**Timed drill:** {mock_blocks} blocks (speed set: 10–15 Q, no peeking)")

        # Bank growth (content)
        items.append(f"**Question bank growth:** add **{new_q_per_day}** new questions (at least 2 exam-level)")

        # Build ritual
        items.append("**End-of-day ritual (5 mins):** Validate → Build → Quick Stats check")

        plan.append((day.isoformat(), items))

    return {
        "blocks": blocks,
        "rev_blocks": rev_blocks,
        "prac_blocks": prac_blocks,
        "mock_blocks": mock_blocks,
        "mock_every": mock_every,
        "new_q_per_day": new_q_per_day,
        "plan": plan,
    }


# -------------------------
# Page
# -------------------------
st.set_page_config(page_title="Study Plan", layout="wide")
st.title("Study Plan")

questions = load_jsonl(JSONL_PATH)
revision = load_json(REVISION_PATH, {"items": {}})
history = load_json(MOCK_HISTORY_PATH, {"attempts": []})

published = [q for q in questions if q.get("status") == "published"]
exam_pool = [q for q in published if (q.get("exam_relevance") or {}).get("pool") == "exam"]

rev_items = revision.get("items") or {}
attempts = history.get("attempts") or []

# Weak topics from revision (counts)
by_id = {q.get("id"): q for q in questions if q.get("id")}
rev_topic_counts = {}
for qid in rev_items.keys():
    q = by_id.get(qid)
    if not q:
        continue
    t = q.get("topic", "Unknown")
    rev_topic_counts[t] = rev_topic_counts.get(t, 0) + 1

# Weak topics from mocks (lowest accuracy)
weak_from_mocks = []
last_mock_pct = None
if attempts:
    last_mock_pct = attempts[-1].get("pct", None)

    agg = {}
    for a in attempts:
        bt = a.get("by_topic") or {}
        for topic, vals in bt.items():
            agg.setdefault(topic, {"correct": 0, "total": 0})
            agg[topic]["correct"] += vals.get("correct", 0)
            agg[topic]["total"] += vals.get("total", 0)

    acc = []
    for topic, vals in agg.items():
        total = vals["total"]
        correct = vals["correct"]
        acc.append((topic, pct(correct, total)))
    acc.sort(key=lambda x: x[1])  # weakest first
    weak_from_mocks = [t for t, _p in acc[:6]]

# Merge weak topic list (revision first, then mocks)
weakest_topics = []
weakest_topics.extend([t for t, _c in top_n_dict(rev_topic_counts, n=6)])
for t in weak_from_mocks:
    if t not in weakest_topics:
        weakest_topics.append(t)

# -------------------------
# Inputs (no sidebar)
# -------------------------
st.markdown("### Plan settings")

c1, c2, c3 = st.columns([1.2, 1.2, 2.6])
with c1:
    horizon = st.selectbox("Horizon", [7, 14, 21], index=0)
with c2:
    minutes = st.selectbox("Daily time (minutes)", [50, 75, 100, 125, 150, 200], index=2)
with c3:
    st.caption(
        "This plan adapts based on your revision pile + mock performance. "
        "It assumes you keep adding high-quality questions as you study."
    )

# quick context cards
k1, k2, k3, k4 = st.columns(4)
k1.metric("Published bank", str(len(published)))
k2.metric("Exam pool", str(len(exam_pool)))
k3.metric("Revision queue", str(len(rev_items)))
k4.metric("Last mock %", f"{last_mock_pct}%" if last_mock_pct is not None else "—")

st.divider()

# show weak areas
st.markdown("### Current weak areas (used for focus rotation)")
if weakest_topics:
    st.write(", ".join([f"**{t}**" for t in weakest_topics]))
else:
    st.write("**Mixed** (no revision/mocks yet)")

# generate plan
plan_obj = make_plan(
    horizon_days=horizon,
    minutes_per_day=minutes,
    revision_count=len(rev_items),
    last_mock_pct=last_mock_pct,
    weakest_topics=weakest_topics,
    exam_pool_size=len(exam_pool),
)

st.divider()
st.markdown("## Daily plan")

st.write(
    f"Daily blocks: **{plan_obj['blocks']}** "
    f"(Revision: **{plan_obj['rev_blocks']}**, Practice: **{plan_obj['prac_blocks']}**, Timed/Mock: **{plan_obj['mock_blocks']}**). "
    f"Mock frequency: **every {plan_obj['mock_every']} days**. "
    f"New questions/day: **{plan_obj['new_q_per_day']}**."
)

for day, items in plan_obj["plan"]:
    st.markdown(f"### {day}")
    for it in items:
        st.write(f"- {it}")

st.divider()
st.markdown("## Daily commands (copy-paste)")

st.code(
    "\n".join(
        [
            "python -m scripts.validate_bank",
            "python -m scripts.build_bank",
            "",
            "# Run apps:",
            "streamlit run pages/1_Practice.py",
            "streamlit run pages/2_Mock_Exam.py",
            "streamlit run pages/3_Revision.py",
            "streamlit run pages/4_Stats.py",
        ]
    ),
    language="bash",
)

st.divider()
st.markdown("## Rules to keep quality high (your guardrail)")

st.write("- If it’s not exam-pattern / not a trap / too easy → it stays **learning pool**, not mock pool.")
st.write("- Every exam-level question must include: **RULE + correct_why + wrong_why + trap + mini_demo**.")
st.write("- Keep practice blind: user never sees learning vs exam label.")
