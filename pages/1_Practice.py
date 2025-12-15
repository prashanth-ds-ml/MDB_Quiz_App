from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

# --- make repo root importable (works even if run from pages/) ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JSONL_PATH = ROOT / "question_bank" / "v2" / "questions.jsonl"
REVISION_PATH = ROOT / "data" / "revision.json"


def load_questions():
    if not JSONL_PATH.exists():
        return []
    rows = []
    with JSONL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def load_revision():
    if not REVISION_PATH.exists():
        return {"items": {}}
    try:
        return json.loads(REVISION_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"items": {}}


def save_revision(state: dict):
    REVISION_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVISION_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def add_wrong_to_revision(q: dict, selected: list[str], source: str = "practice"):
    qid = q.get("id")
    if not qid:
        return

    rev = load_revision()
    items = rev.setdefault("items", {})

    rec = items.get(
        qid,
        {
            "qid": qid,
            "added_at": now_iso(),
            "last_seen": None,
            "times_seen": 0,
            "times_wrong": 0,
            "times_correct": 0,
            "last_selected": [],
            "source": source,
        },
    )

    rec["last_seen"] = now_iso()
    rec["times_seen"] += 1
    rec["times_wrong"] += 1
    rec["last_selected"] = selected
    rec["source"] = source  # last source wins (fine)

    items[qid] = rec
    save_revision(rev)


def pick_question(questions, topic=None, difficulty=None, only_published=True):
    pool = questions
    if only_published:
        pool = [q for q in pool if q.get("status") == "published"]
    if topic and topic != "All":
        pool = [q for q in pool if q.get("topic") == topic]
    if difficulty and difficulty != "All":
        pool = [q for q in pool if q.get("difficulty") == difficulty]
    if not pool:
        return None
    return random.choice(pool)


def grade(q: dict, user_keys: list[str]) -> bool:
    correct = set((q.get("answer") or {}).get("keys", []))
    return set(user_keys) == correct


st.set_page_config(page_title="Practice", layout="wide")
st.title("Practice")

questions = load_questions()
if not questions:
    st.error("No questions found. Run: python -m scripts.build_bank")
    st.stop()

# Sidebar filters (kept minimal, but still useful)
st.sidebar.markdown("### Filters")
published_only = st.sidebar.checkbox("Published only", value=True)

topics = sorted({q.get("topic", "Unknown") for q in questions})
diffs = sorted({q.get("difficulty", "Unknown") for q in questions})

topic = st.sidebar.selectbox("Topic", ["All"] + topics)
difficulty = st.sidebar.selectbox("Difficulty", ["All"] + diffs)

# Session state
if "current_q" not in st.session_state:
    st.session_state.current_q = pick_question(
        questions, topic=topic, difficulty=difficulty, only_published=published_only
    )
if "answered" not in st.session_state:
    st.session_state.answered = False
if "user_keys" not in st.session_state:
    st.session_state.user_keys = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None  # "correct" | "wrong" | None


# Apply filters / new question
if st.sidebar.button("New question"):
    st.session_state.current_q = pick_question(
        questions, topic=topic, difficulty=difficulty, only_published=published_only
    )
    st.session_state.answered = False
    st.session_state.user_keys = []
    st.session_state.last_result = None
    # reset checkboxes for multi-select (if any)
    for k in list(st.session_state.keys()):
        if str(k).startswith("opt_"):
            del st.session_state[k]
    st.rerun()

q = st.session_state.current_q
if not q:
    st.warning("No questions match your filters.")
    st.stop()

# --- Header ---
st.markdown(f"## {q.get('title','')}")
st.caption(f"{q.get('id','')} • {q.get('topic','')} • {q.get('subtopic','')} • {q.get('difficulty','')}")

st.divider()

# --- Question ---
st.markdown("### Question")
st.write(q.get("prompt", ""))

# Context (shown directly)
context = q.get("context")
if context and str(context).strip():
    st.markdown("### Context")
    st.caption(context)

# Sample docs (shown directly)
artifacts = q.get("artifacts") or {}
sample_docs = artifacts.get("sample_docs") or []
if sample_docs:
    st.markdown("### Sample docs")
    st.json(sample_docs)

st.divider()

# --- Options / Answer input ---
st.markdown("### Options")

qtype = q.get("type", "single")
choices = q.get("choices", [])
choice_map = {c["key"]: c["text"] for c in choices}

user_keys: list[str] = []

if qtype == "multi":
    selected = []
    for k in ["A", "B", "C", "D"]:
        if k in choice_map:
            if st.checkbox(f"{k}. {choice_map[k]}", key=f"opt_{q['id']}_{k}"):
                selected.append(k)
    user_keys = selected
else:
    # single
    keys = [c["key"] for c in choices]
    labels = [f"{k}. {choice_map[k]}" for k in keys]
    picked = st.radio("Select one", options=labels, index=0)
    user_keys = [picked.split(".")[0]]

col1, col2, col3 = st.columns([1, 1, 6])

with col1:
    if st.button("Submit", type="primary"):
        st.session_state.answered = True
        st.session_state.user_keys = user_keys

        # Add to revision if wrong
        if not grade(q, user_keys):
            add_wrong_to_revision(q, user_keys, source="practice")
            st.session_state.last_result = "wrong"
        else:
            st.session_state.last_result = "correct"

with col2:
    if st.button("Next"):
        st.session_state.current_q = pick_question(
            questions, topic=topic, difficulty=difficulty, only_published=published_only
        )
        st.session_state.answered = False
        st.session_state.user_keys = []
        st.session_state.last_result = None
        for k in list(st.session_state.keys()):
            if str(k).startswith("opt_"):
                del st.session_state[k]
        st.rerun()

st.divider()

# --- Explanation (only after submit) ---
if st.session_state.answered:
    is_correct = grade(q, st.session_state.user_keys)

    if is_correct:
        st.success("✅ Correct")
    else:
        st.error("❌ Incorrect")
        correct_keys = (q.get("answer") or {}).get("keys", [])
        if correct_keys:
            st.info(f"Correct answer: **{', '.join(correct_keys)}**")
        st.caption("Added to Revision automatically.")

    r = q.get("rationale") or {}

    # RULE banner
    rule = r.get("rule", "")
    if rule and str(rule).strip():
        st.success(f"**RULE:** {rule}")

    # Why correct
    st.markdown("### Why correct")
    correct_why = r.get("correct_why") or []
    if correct_why:
        for b in correct_why:
            st.write(f"- {b}")
    else:
        st.write("- (missing)")

    # Why wrong
    st.markdown("### Why others are wrong")
    wrong_why = r.get("wrong_why") or {}
    any_wrong = False
    for k in ["A", "B", "C", "D"]:
        if k in wrong_why:
            st.write(f"- **{k}**: {wrong_why[k]}")
            any_wrong = True
    if not any_wrong:
        st.write("- (missing)")

    # Trap
    trap = r.get("trap")
    if trap and str(trap).strip():
        st.info(f"**Trap:** {trap}")

    # Mini demo (shown directly)
    mini_demo = r.get("mini_demo")
    if mini_demo and str(mini_demo).strip():
        st.markdown("### Mini demo")
        st.code(mini_demo, language="javascript")

# IMPORTANT:
# - We intentionally do NOT show q["exam_relevance"]["pool"] anywhere in Practice mode.
# - Pool classification is strictly internal for mock exams.
