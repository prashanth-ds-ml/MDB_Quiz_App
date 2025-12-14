from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

import streamlit as st

# --- make repo root importable (works even if run from pages/) ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JSONL_PATH = ROOT / "question_bank" / "v2" / "questions.jsonl"


# -------------------------
# Helpers
# -------------------------
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


def is_exam_pool(q: dict) -> bool:
    er = q.get("exam_relevance") or {}
    return er.get("pool") == "exam"


def is_published(q: dict) -> bool:
    return q.get("status") == "published"


def grade_one(q: dict, selected: list[str]) -> bool:
    correct = set((q.get("answer") or {}).get("keys", []))
    return set(selected) == correct


def format_mmss(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


def reset_exam_state():
    for k in [
        "exam_started",
        "exam_start_ts",
        "exam_order",
        "exam_idx",
        "exam_answers",
        "exam_submitted",
        "exam_submit_ts",
        "exam_settings",
    ]:
        if k in st.session_state:
            del st.session_state[k]
    # clear option checkbox state keys
    for k in list(st.session_state.keys()):
        if str(k).startswith("mock_opt_"):
            del st.session_state[k]


# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="Mock Exam", layout="wide")
st.title("Mock Exam")

all_questions = load_questions()
if not all_questions:
    st.error("No questions found. Run: python -m scripts.build_bank")
    st.stop()

exam_pool = [q for q in all_questions if is_published(q) and is_exam_pool(q)]
if len(exam_pool) < 10:
    st.warning(
        f"Your EXAM pool is small ({len(exam_pool)} published exam questions). "
        "You can still test the flow, but aim to grow this pool."
    )

# -------------------------
# Settings (before start)
# -------------------------
st.markdown("### Exam Settings")

colA, colB, colC = st.columns([1.2, 1, 1])

with colA:
    mode = st.selectbox(
        "Mode",
        [
            "Official Simulation (75 min, 53 Q)",
            "Quick Drill (20 min, 15 Q)",
            "Custom",
        ],
        index=0,
    )

with colB:
    if mode == "Custom":
        total_q = st.number_input("Questions", min_value=5, max_value=100, value=25, step=1)
    elif mode.startswith("Quick"):
        total_q = 15
    else:
        total_q = 53

with colC:
    if mode == "Custom":
        duration_min = st.number_input("Minutes", min_value=5, max_value=180, value=75, step=5)
    elif mode.startswith("Quick"):
        duration_min = 20
    else:
        duration_min = 75

# difficulty mix (optional)
mix = st.selectbox(
    "Difficulty mix (internal selection only)",
    [
        "Balanced (default)",
        "Easy-heavy",
        "Hard-heavy",
        "All difficulties equally",
    ],
    index=0,
)

st.caption(
    "Note: This page uses **only the exam pool** internally, but you will never see pool labels while taking the exam."
)

# -------------------------
# Start / Reset controls
# -------------------------
col1, col2, col3 = st.columns([1, 1, 6])

with col1:
    start_clicked = st.button("Start exam", type="primary")

with col2:
    reset_clicked = st.button("Reset")

if reset_clicked:
    reset_exam_state()
    st.success("Exam state cleared. You can start fresh.")
    st.stop()

# -------------------------
# Init exam state
# -------------------------
if "exam_started" not in st.session_state:
    st.session_state.exam_started = False

if start_clicked and not st.session_state.exam_started:
    if len(exam_pool) == 0:
        st.error("No published exam-pool questions available.")
        st.stop()

    # Build selection list with difficulty mix
    easy = [q for q in exam_pool if q.get("difficulty") == "easy"]
    med = [q for q in exam_pool if q.get("difficulty") == "medium"]
    hard = [q for q in exam_pool if q.get("difficulty") == "hard"]

    def sample(lst, n):
        if not lst:
            return []
        if len(lst) >= n:
            return random.sample(lst, n)
        # if not enough, sample with wrap-around (but keep unique by id later)
        return random.sample(lst, len(lst))

    if mix == "Easy-heavy":
        # 50/35/15
        n_easy = int(total_q * 0.50)
        n_med = int(total_q * 0.35)
        n_hard = total_q - n_easy - n_med
    elif mix == "Hard-heavy":
        # 20/40/40
        n_easy = int(total_q * 0.20)
        n_med = int(total_q * 0.40)
        n_hard = total_q - n_easy - n_med
    elif mix == "All difficulties equally":
        n_easy = total_q // 3
        n_med = total_q // 3
        n_hard = total_q - n_easy - n_med
    else:
        # Balanced default: 30/45/25
        n_easy = int(total_q * 0.30)
        n_med = int(total_q * 0.45)
        n_hard = total_q - n_easy - n_med

    chosen = []
    chosen.extend(sample(easy, n_easy))
    chosen.extend(sample(med, n_med))
    chosen.extend(sample(hard, n_hard))

    # If chosen list is short due to lack in buckets, fill from overall pool
    chosen_ids = {q.get("id") for q in chosen}
    if len(chosen) < total_q:
        remaining = [q for q in exam_pool if q.get("id") not in chosen_ids]
        fill_n = total_q - len(chosen)
        chosen.extend(random.sample(remaining, min(fill_n, len(remaining))))

    # Final fallback: if still short, allow from exam_pool (no repeats) as much as possible
    chosen = [q for q in chosen if q.get("id")]
    unique = {}
    for q in chosen:
        unique[q["id"]] = q
    chosen = list(unique.values())

    random.shuffle(chosen)

    st.session_state.exam_settings = {
        "total_q": total_q,
        "duration_sec": int(duration_min * 60),
        "mix": mix,
    }
    st.session_state.exam_started = True
    st.session_state.exam_start_ts = time.time()
    st.session_state.exam_order = [q["id"] for q in chosen]
    st.session_state.exam_idx = 0
    st.session_state.exam_answers = {}  # qid -> list[str]
    st.session_state.exam_submitted = False
    st.session_state.exam_submit_ts = None

    # clear any previous checkbox state
    for k in list(st.session_state.keys()):
        if str(k).startswith("mock_opt_"):
            del st.session_state[k]

# -------------------------
# If not started, stop here
# -------------------------
if not st.session_state.exam_started:
    st.info("Click **Start exam** to begin.")
    st.stop()

# -------------------------
# Timer + auto-submit
# -------------------------
settings = st.session_state.exam_settings
elapsed = int(time.time() - st.session_state.exam_start_ts)
remaining = settings["duration_sec"] - elapsed

# auto-refresh each second (keeps timer live)
st_autorefresh = st.autorefresh(interval=1000, key="mock_timer_refresh")

timer_col, prog_col, info_col = st.columns([1.2, 2.5, 2.3])

with timer_col:
    if remaining > 0:
        st.metric("Time left", format_mmss(remaining))
    else:
        st.metric("Time left", "00:00")

with prog_col:
    total = len(st.session_state.exam_order)
    idx = st.session_state.exam_idx
    st.progress(min(1.0, (idx + 1) / max(1, total)))
    st.caption(f"Question {idx + 1} / {total}")

with info_col:
    answered_count = sum(1 for _qid, ans in st.session_state.exam_answers.items() if ans)
    st.metric("Answered", f"{answered_count}/{total}")

# Auto-submit when time is up
if remaining <= 0 and not st.session_state.exam_submitted:
    st.session_state.exam_submitted = True
    st.session_state.exam_submit_ts = time.time()

# -------------------------
# Build index for fast lookup by id
# -------------------------
by_id = {q.get("id"): q for q in exam_pool}
order = st.session_state.exam_order
current_id = order[st.session_state.exam_idx]
q = by_id.get(current_id)

if not q:
    st.error(f"Question not found in bank: {current_id}")
    st.stop()

# -------------------------
# Exam submitted view
# -------------------------
if st.session_state.exam_submitted:
    st.divider()
    st.markdown("## Results")

    # score
    score = 0
    detailed = []
    for qid in order:
        qq = by_id.get(qid)
        if not qq:
            continue
        selected = st.session_state.exam_answers.get(qid, [])
        ok = grade_one(qq, selected)
        score += 1 if ok else 0
        detailed.append((qid, ok, selected, (qq.get("answer") or {}).get("keys", [])))

    pct = (score / max(1, len(order))) * 100
    st.metric("Score", f"{score}/{len(order)} ({pct:.1f}%)")

    # quick breakdown
    wrong = [d for d in detailed if not d[1]]
    st.write(f"Incorrect: **{len(wrong)}**")

    st.divider()
    st.markdown("## Review (with explanations)")

    # Show a compact review list
    for qid, ok, selected, correct in detailed:
        qq = by_id.get(qid)
        if not qq:
            continue

        st.markdown(f"### {qid} — {qq.get('title','')}")
        st.caption(f"{qq.get('topic','')} • {qq.get('subtopic','')} • {qq.get('difficulty','')}")

        if ok:
            st.success("✅ Correct")
        else:
            st.error("❌ Incorrect")
            st.info(f"Your answer: **{', '.join(selected) if selected else '(none)'}**")
            st.info(f"Correct answer: **{', '.join(correct) if correct else '(missing)'}**")

        st.markdown("#### Question")
        st.write(qq.get("prompt", ""))

        # Explanation (same clean style as Practice)
        r = qq.get("rationale") or {}
        rule = r.get("rule", "")
        if rule and str(rule).strip():
            st.success(f"**RULE:** {rule}")

        st.markdown("#### Why correct")
        for b in (r.get("correct_why") or []):
            st.write(f"- {b}")

        st.markdown("#### Why others are wrong")
        wrong_why = r.get("wrong_why") or {}
        for k in ["A", "B", "C", "D"]:
            if k in wrong_why:
                st.write(f"- **{k}**: {wrong_why[k]}")

        trap = r.get("trap")
        if trap and str(trap).strip():
            st.info(f"**Trap:** {trap}")

        mini_demo = r.get("mini_demo")
        if mini_demo and str(mini_demo).strip():
            st.markdown("#### Mini demo")
            st.code(mini_demo, language="javascript")

        st.divider()

    if st.button("Start a new exam"):
        reset_exam_state()
        st.rerun()

    st.stop()

# -------------------------
# Render current question (exam mode: no explanations)
# -------------------------
st.divider()
st.markdown(f"## {q.get('title','')}")
st.caption(f"{q.get('id','')} • {q.get('topic','')} • {q.get('subtopic','')} • {q.get('difficulty','')}")

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

# restore previous answer (if any)
prev = st.session_state.exam_answers.get(current_id, [])

selected_keys: list[str] = []

if qtype == "multi":
    for k in ["A", "B", "C", "D"]:
        if k not in choice_map:
            continue
        default_checked = k in prev
        ck = st.checkbox(
            f"{k}. {choice_map[k]}",
            value=default_checked,
            key=f"mock_opt_{current_id}_{k}",
        )
        if ck:
            selected_keys.append(k)
else:
    keys = [c["key"] for c in choices]
    labels = [f"{k}. {choice_map[k]}" for k in keys]
    # default index
    default_index = 0
    if prev and prev[0] in keys:
        default_index = keys.index(prev[0])
    picked = st.radio(
        "Select one",
        options=labels,
        index=default_index,
        key=f"mock_radio_{current_id}",
    )
    selected_keys = [picked.split(".")[0]]

# Save answer immediately (no submit button needed for exam)
st.session_state.exam_answers[current_id] = selected_keys

nav1, nav2, nav3, nav4 = st.columns([1, 1, 1.2, 4.8])

with nav1:
    if st.button("Prev", disabled=st.session_state.exam_idx == 0):
        st.session_state.exam_idx -= 1
        st.rerun()

with nav2:
    if st.button("Next", disabled=st.session_state.exam_idx >= len(order) - 1):
        st.session_state.exam_idx += 1
        st.rerun()

with nav3:
    if st.button("Submit exam", type="primary"):
        st.session_state.exam_submitted = True
        st.session_state.exam_submit_ts = time.time()
        st.rerun()

# important note
st.caption("Mock exam mode: no explanations until you submit. Pool type is hidden by design.")
