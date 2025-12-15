from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

# --- repo root import fix ---
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


def load_revision():
    if not REVISION_PATH.exists():
        return {"items": {}}  # qid -> record
    try:
        return json.loads(REVISION_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"items": {}}


def save_revision(state: dict):
    REVISION_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVISION_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def grade_one(q: dict, selected: list[str]) -> bool:
    correct = set((q.get("answer") or {}).get("keys", []))
    return set(selected) == correct


def add_to_revision(rev: dict, q: dict, selected: list[str], source: str):
    qid = q.get("id")
    if not qid:
        return

    items = rev.setdefault("items", {})
    rec = items.get(qid, {
        "qid": qid,
        "added_at": now_iso(),
        "last_seen": None,
        "times_seen": 0,
        "times_wrong": 0,
        "times_correct": 0,
        "last_selected": [],
        "source": source,
    })

    rec["last_seen"] = now_iso()
    rec["times_seen"] += 1
    rec["times_wrong"] += 1
    rec["last_selected"] = selected

    items[qid] = rec


def mark_correct(rev: dict, qid: str, selected: list[str]):
    items = rev.setdefault("items", {})
    if qid not in items:
        return
    rec = items[qid]
    rec["last_seen"] = now_iso()
    rec["times_seen"] += 1
    rec["times_correct"] += 1
    rec["last_selected"] = selected
    items[qid] = rec


def remove_from_revision(rev: dict, qid: str):
    items = rev.setdefault("items", {})
    if qid in items:
        del items[qid]


def pick_revision_question(rev: dict, questions_by_id: dict, mode: str):
    items = list((rev.get("items") or {}).values())
    items = [x for x in items if x.get("qid") in questions_by_id]
    if not items:
        return None

    # Simple priority strategies
    if mode == "Most wrong first":
        items.sort(key=lambda x: (x.get("times_wrong", 0), x.get("times_seen", 0)), reverse=True)
        return questions_by_id[items[0]["qid"]]

    if mode == "Least recently seen":
        items.sort(key=lambda x: x.get("last_seen") or "")
        return questions_by_id[items[0]["qid"]]

    # Random
    return questions_by_id[random.choice(items)["qid"]]


# -------------------------
# Page
# -------------------------
st.set_page_config(page_title="Revision", layout="wide")
st.title("Revision")

questions = load_questions()
if not questions:
    st.error("No questions found. Run: python -m scripts.build_bank")
    st.stop()

by_id = {q.get("id"): q for q in questions if q.get("id")}
rev = load_revision()

items = rev.get("items") or {}
count = len(items)

st.markdown("### Your revision queue")
st.write(f"Questions in revision: **{count}**")

col1, col2, col3, col4 = st.columns([1.2, 1.2, 1, 4.6])

with col1:
    mode = st.selectbox("Pick strategy", ["Random", "Most wrong first", "Least recently seen"], index=1)

with col2:
    show_list = st.checkbox("Show full list", value=False)

with col3:
    if st.button("Clear all", type="secondary", disabled=count == 0):
        rev = {"items": {}}
        save_revision(rev)
        st.success("Revision list cleared.")
        st.rerun()

if show_list and count > 0:
    st.markdown("#### Revision items")
    # Show a compact list
    for qid, rec in list(items.items())[:200]:
        q = by_id.get(qid)
        if not q:
            continue
        st.write(
            f"- **{qid}** — {q.get('title','')} "
            f"(wrong: {rec.get('times_wrong',0)}, correct: {rec.get('times_correct',0)})"
        )

st.divider()

# Pick question
q = pick_revision_question(rev, by_id, mode)
if not q:
    st.info("No questions in revision yet. Add wrong answers from Practice/Mock (next patch) or manually add.")
    st.stop()

qid = q.get("id", "")
st.markdown(f"## {q.get('title','')}")
st.caption(f"{qid} • {q.get('topic','')} • {q.get('subtopic','')} • {q.get('difficulty','')}")

st.markdown("### Question")
st.write(q.get("prompt", ""))

context = q.get("context")
if context and str(context).strip():
    st.markdown("### Context")
    st.caption(context)

artifacts = q.get("artifacts") or {}
sample_docs = artifacts.get("sample_docs") or []
if sample_docs:
    st.markdown("### Sample docs")
    st.json(sample_docs)

st.divider()
st.markdown("### Options")

qtype = q.get("type", "single")
choices = q.get("choices", [])
choice_map = {c["key"]: c["text"] for c in choices}

user_keys: list[str] = []

if qtype == "multi":
    selected = []
    for k in ["A", "B", "C", "D"]:
        if k in choice_map:
            if st.checkbox(f"{k}. {choice_map[k]}", key=f"rev_opt_{qid}_{k}"):
                selected.append(k)
    user_keys = selected
else:
    keys = [c["key"] for c in choices]
    labels = [f"{k}. {choice_map[k]}" for k in keys]
    picked = st.radio("Select one", options=labels, index=0, key=f"rev_radio_{qid}")
    user_keys = [picked.split(".")[0]]

colA, colB, colC = st.columns([1, 1.2, 4.8])

with colA:
    if st.button("Submit", type="primary"):
        ok = grade_one(q, user_keys)

        if ok:
            st.success("✅ Correct")
            mark_correct(rev, qid, user_keys)
            save_revision(rev)
        else:
            st.error("❌ Incorrect")
            # keep it in revision and record wrong
            add_to_revision(rev, q, user_keys, source="revision")
            save_revision(rev)

        # show explanation
        r = q.get("rationale") or {}
        rule = r.get("rule", "")
        if rule and str(rule).strip():
            st.success(f"**RULE:** {rule}")

        st.markdown("### Why correct")
        for b in (r.get("correct_why") or []):
            st.write(f"- {b}")

        st.markdown("### Why others are wrong")
        wrong_why = r.get("wrong_why") or {}
        for k in ["A", "B", "C", "D"]:
            if k in wrong_why:
                st.write(f"- **{k}**: {wrong_why[k]}")

        trap = r.get("trap")
        if trap and str(trap).strip():
            st.info(f"**Trap:** {trap}")

        mini_demo = r.get("mini_demo")
        if mini_demo and str(mini_demo).strip():
            st.markdown("### Mini demo")
            st.code(mini_demo, language="javascript")

with colB:
    if st.button("Remove from revision"):
        remove_from_revision(rev, qid)
        save_revision(rev)
        st.success("Removed.")
        st.rerun()

with colC:
    if st.button("Next"):
        # clear widget state for new question
        for k in list(st.session_state.keys()):
            if str(k).startswith("rev_opt_") or str(k).startswith("rev_radio_"):
                del st.session_state[k]
        st.rerun()
