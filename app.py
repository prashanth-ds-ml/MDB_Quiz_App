from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JSONL_PATH = ROOT / "question_bank" / "v2" / "questions.jsonl"
REVISION_PATH = ROOT / "data" / "revision.json"
MOCK_HISTORY_PATH = ROOT / "data" / "mock_history.json"


def load_jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


st.set_page_config(page_title="MongoDB Exam Prep", layout="wide")

st.markdown("# MongoDB Exam Prep")
st.caption("Practice → Mock → Revision → Stats. Built to feel like an exam-prep product, not a demo.")

# --- KPIs ---
q_count = load_jsonl_count(JSONL_PATH)
revision = load_json(REVISION_PATH, {"items": {}})
history = load_json(MOCK_HISTORY_PATH, {"attempts": []})

rev_count = len((revision.get("items") or {}))
attempts = (history.get("attempts") or [])
last_pct = attempts[-1].get("pct") if attempts else None

k1, k2, k3, k4 = st.columns(4)
k1.metric("Questions (compiled)", str(q_count))
k2.metric("Revision queue", str(rev_count))
k3.metric("Mock attempts", str(len(attempts)))
k4.metric("Last mock %", f"{last_pct}%" if last_pct is not None else "—")

st.divider()

# --- Main actions ---
st.markdown("## Start")

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("🟦 Practice", type="primary", use_container_width=True):
        st.switch_page("pages/1_Practice.py")
    st.caption("Learn concepts + explanations. Wrong answers go to Revision automatically.")

with c2:
    if st.button("🟥 Mock Exam", type="primary", use_container_width=True):
        st.switch_page("pages/2_Mock_Exam.py")
    st.caption("Timed exam simulation. Wrong answers are added to Revision on submit.")

with c3:
    if st.button("🟨 Revision", type="primary", use_container_width=True):
        st.switch_page("pages/3_Revision.py")
    st.caption("Your mistakes bank. Repeat until weak areas disappear.")

st.divider()

st.markdown("## Track")

t1, t2, t3 = st.columns(3)
with t1:
    if st.button("📊 Stats", use_container_width=True):
        st.switch_page("pages/4_Stats.py")
    st.caption("See progress, weak topics, and mock performance.")

with t2:
    if st.button("🗓️ Study Plan", use_container_width=True):
        st.switch_page("pages/6_Study_Plan.py")
    st.caption("Auto plan for 7/14/21 days based on weak areas.")

with t3:
    if st.button("🛠️ Admin (Author Console)", use_container_width=True):
        st.switch_page("pages/5_Admin_Bank.py")
    st.caption("Paste YAML → Save → Validate → Build → Preview.")

st.divider()

# --- Quick hints ---
st.markdown("## Daily loop (recommended)")
st.code(
    "\n".join(
        [
            "1) Add questions (Admin) → Validate → Build",
            "2) Practice (blind pool) → wrong goes to Revision",
            "3) Mock (timed) → wrong goes to Revision + attempt logged",
            "4) Revision → clear weak areas",
            "5) Stats → decide focus topics",
        ]
    ),
    language="text",
)

st.caption("Tip: run the app from repo root:  `streamlit run app.py`")
