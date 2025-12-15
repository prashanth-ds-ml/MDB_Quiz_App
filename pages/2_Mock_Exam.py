from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

# --- repo root import fix ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JSONL_PATH = ROOT / "question_bank" / "v2" / "questions.jsonl"
REVISION_PATH = ROOT / "data" / "revision.json"
MOCK_HISTORY_PATH = ROOT / "data" / "mock_history.json"


# -------------------------
# Query params helpers (works across Streamlit versions)
# -------------------------
def get_qp() -> dict:
    try:
        # Streamlit >= 1.30
        return dict(st.query_params)
    except Exception:
        try:
            return st.experimental_get_query_params()
        except Exception:
            return {}


def set_qp(**kwargs):
    # kwargs values: str or None (None removes)
    try:
        # Streamlit >= 1.30
        for k, v in kwargs.items():
            if v is None:
                if k in st.query_params:
                    del st.query_params[k]
            else:
                st.query_params[k] = str(v)
    except Exception:
        # older
        qp = st.experimental_get_query_params()
        for k, v in kwargs.items():
            if v is None:
                qp.pop(k, None)
            else:
                qp[k] = [str(v)]
        st.experimental_set_query_params(**qp)


# -------------------------
# IO helpers
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


def add_wrong_to_revision(q: dict, selected: list[str], source: str = "mock"):
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
    rec["source"] = source

    items[qid] = rec
    save_revision(rev)


def load_mock_history():
    if not MOCK_HISTORY_PATH.exists():
        return {"attempts": []}
    try:
        return json.loads(MOCK_HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"attempts": []}


def save_mock_history(state: dict):
    MOCK_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MOCK_HISTORY_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# -------------------------
# Pool helpers
# -------------------------
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


def sample_without_replacement(items: list[dict], n: int) -> list[dict]:
    if n <= 0:
        return []
    if len(items) <= n:
        return list(items)
    return random.sample(items, n)


# -------------------------
# Official weighting helpers (domain quotas)
# -------------------------
OFFICIAL_DOMAIN_PCTS = {
    "OVERVIEW_DOCUMENT_MODEL": 0.08,
    "CRUD": 0.51,
    "INDEXES": 0.17,
    "DATA_MODELING": 0.04,
    "TOOLS_TOOLING": 0.02,
    "DRIVERS": 0.18,
}

DOMAIN_ORDER_FILL = [
    "CRUD",
    "DRIVERS",
    "INDEXES",
    "OVERVIEW_DOCUMENT_MODEL",
    "DATA_MODELING",
    "TOOLS_TOOLING",
]


def normalize_domain(q: dict) -> str:
    d = (q.get("domain") or "").strip().upper()
    if d:
        d = d.replace("&", "AND").replace("/", "_").replace("-", "_").replace(" ", "_")
        alias = {
            "OVERVIEW": "OVERVIEW_DOCUMENT_MODEL",
            "DOCUMENT_MODEL": "OVERVIEW_DOCUMENT_MODEL",
            "OVERVIEW_DOCUMENT": "OVERVIEW_DOCUMENT_MODEL",
            "DOC_MODEL": "OVERVIEW_DOCUMENT_MODEL",
            "INDEX": "INDEXES",
            "INDEXING": "INDEXES",
            "TOOLS": "TOOLS_TOOLING",
            "TOOLING": "TOOLS_TOOLING",
            "DRIVER": "DRIVERS",
        }
        return alias.get(d, d)

    txt = f"{q.get('topic','')} {q.get('subtopic','')}".lower()
    if any(k in txt for k in ["crud", "insert", "update", "delete", "find", "aggregate", "aggregation", "pipeline"]):
        return "CRUD"
    if "index" in txt:
        return "INDEXES"
    if any(k in txt for k in ["driver", "pymongo", "motor", "uri", "tls", "retrywrites"]):
        return "DRIVERS"
    if any(k in txt for k in ["model", "schema", "embedding", "reference", "normalize", "denormal"]):
        return "DATA_MODELING"
    if any(k in txt for k in ["mongosh", "atlas", "compass", "dump", "restore", "import", "export"]):
        return "TOOLS_TOOLING"
    return "OVERVIEW_DOCUMENT_MODEL"


def compute_domain_quotas(total_q: int) -> dict[str, int]:
    raw = {k: OFFICIAL_DOMAIN_PCTS[k] * total_q for k in OFFICIAL_DOMAIN_PCTS}
    quotas = {k: int(round(v)) for k, v in raw.items()}

    for k in quotas:
        quotas[k] = max(0, quotas[k])

    s = sum(quotas.values())
    if s != total_q:
        diff = total_q - s
        i = 0
        while diff != 0:
            k = DOMAIN_ORDER_FILL[i % len(DOMAIN_ORDER_FILL)]
            if diff > 0:
                quotas[k] += 1
                diff -= 1
            else:
                if quotas[k] > 0:
                    quotas[k] -= 1
                    diff += 1
            i += 1

    s = sum(quotas.values())
    if s != total_q:
        quotas["CRUD"] += (total_q - s)
    return quotas


def select_official_exam_questions(exam_pool: list[dict], total_q: int) -> tuple[list[dict], dict]:
    quotas = compute_domain_quotas(total_q)
    buckets: dict[str, list[dict]] = {k: [] for k in OFFICIAL_DOMAIN_PCTS.keys()}
    for q in exam_pool:
        d = normalize_domain(q)
        if d in buckets:
            buckets[d].append(q)

    chosen: list[dict] = []
    chosen_ids: set[str] = set()
    shortages: dict[str, int] = {}

    for d, qn in quotas.items():
        pool = [q for q in buckets.get(d, []) if q.get("id") and q["id"] not in chosen_ids]
        pick = min(qn, len(pool))
        picked = sample_without_replacement(pool, pick)
        for qq in picked:
            chosen.append(qq)
            chosen_ids.add(qq["id"])
        if pick < qn:
            shortages[d] = qn - pick

    remaining = [q for q in exam_pool if q.get("id") and q["id"] not in chosen_ids]
    fill_needed = total_q - len(chosen)
    if fill_needed > 0:
        chosen.extend(sample_without_replacement(remaining, min(fill_needed, len(remaining))))

    random.shuffle(chosen)
    dbg = {"quotas": quotas, "shortages": shortages, "selected": len(chosen)}
    return chosen, dbg


def select_any_pool_random(published_all: list[dict], total_q: int) -> tuple[list[dict], dict]:
    uniq = {}
    for q in published_all:
        qid = q.get("id")
        if qid:
            uniq[qid] = q
    items = list(uniq.values())
    chosen = sample_without_replacement(items, min(int(total_q), len(items)))
    random.shuffle(chosen)
    return chosen, {"selected": len(chosen), "pool_size": len(items)}


# -------------------------
# Attempt helpers
# -------------------------
def new_attempt_id() -> str:
    return f"a{int(time.time())}{random.randint(1000, 9999)}"


def reset_attempt():
    for k in ["attempt", "mock_logged", "revision_pushed"]:
        if k in st.session_state:
            del st.session_state[k]
    for k in list(st.session_state.keys()):
        if str(k).startswith("mock_opt_") or str(k).startswith("mock_radio_"):
            del st.session_state[k]
    set_qp(autosubmit=None)


def push_wrong_to_revision(order: list[str], by_id: dict, answers: dict):
    if st.session_state.get("revision_pushed") is True:
        return
    for qid in order:
        q = by_id.get(qid)
        if not q:
            continue
        selected = answers.get(qid, [])
        if not grade_one(q, selected):
            add_wrong_to_revision(q, selected, source="mock")
    st.session_state.revision_pushed = True


def log_mock_attempt(attempt: dict, by_id: dict):
    if st.session_state.get("mock_logged") is True:
        return

    order = attempt["order"]
    answers = attempt["answers"]
    total = len(order)
    score = 0
    wrong_ids = []

    for qid in order:
        q = by_id.get(qid)
        if not q:
            continue
        ok = grade_one(q, answers.get(qid, []))
        score += 1 if ok else 0
        if not ok:
            wrong_ids.append(qid)

    hist = load_mock_history()
    hist.setdefault("attempts", []).append(
        {
            "ts": now_iso(),
            "attempt_id": attempt["attempt_id"],
            "mode": attempt["mode"],
            "selection_mode": attempt["selection_mode"],
            "total": total,
            "score": score,
            "pct": round((score / max(1, total)) * 100, 2),
            "duration_sec": attempt["duration_sec"],
            "wrong_ids": wrong_ids,
        }
    )
    save_mock_history(hist)
    st.session_state.mock_logged = True


# -------------------------
# JS ticking timer (client-side)
# -------------------------
def render_js_timer(end_ts: float, attempt_id: str):
    # When time is up, add ?autosubmit=<attempt_id> and reload.
    # Timer itself updates in browser every second without Streamlit reruns.
    html = f"""
    <div style="display:flex; gap:10px; align-items:center;">
      <div style="font-size:14px; color: #666;">Time left</div>
      <div id="timer" style="font-size:22px; font-weight:700;">--:--</div>
    </div>

    <script>
      const endTs = {end_ts} * 1000;
      const attemptId = "{attempt_id}";

      function fmt(ms) {{
        ms = Math.max(0, ms);
        const totalSec = Math.floor(ms/1000);
        const m = String(Math.floor(totalSec/60)).padStart(2,'0');
        const s = String(totalSec % 60).padStart(2,'0');
        return `${{m}}:${{s}}`;
      }}

      function setQP(key, value) {{
        const url = new URL(window.parent.location.href);
        url.searchParams.set(key, value);
        window.parent.location.href = url.toString();
      }}

      function tick() {{
        const now = Date.now();
        const rem = endTs - now;
        const el = document.getElementById('timer');
        if (el) el.textContent = fmt(rem);

        if (rem <= 0) {{
          // force submit
          setQP("autosubmit", attemptId);
        }}
      }}

      tick();
      setInterval(tick, 1000);
    </script>
    """
    components.html(html, height=55)


# -------------------------
# Page
# -------------------------
st.set_page_config(page_title="Mock Exam", layout="wide")
st.title("Mock Exam")

all_questions = load_questions()
if not all_questions:
    st.error("No questions found. Run: python -m scripts.build_bank")
    st.stop()

published_all = [q for q in all_questions if is_published(q)]
published_exam = [q for q in published_all if is_exam_pool(q)]

by_id = {q.get("id"): q for q in published_all if q.get("id")}

# Settings UI (only when no active attempt)
if "attempt" not in st.session_state:
    st.markdown("### Exam Settings")
    colA, colB, colC = st.columns([1.3, 1, 1])

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
            total_q = st.number_input("Questions", min_value=5, max_value=200, value=25, step=1)
        elif mode.startswith("Quick"):
            total_q = 15
        else:
            total_q = 53

    with colC:
        if mode == "Custom":
            duration_min = st.number_input("Minutes", min_value=5, max_value=240, value=75, step=5)
        elif mode.startswith("Quick"):
            duration_min = 20
        else:
            duration_min = 75

    st.caption(
        "Official Simulation = exam-only + official weightage. "
        "Quick Drill/Custom = random from whole published bank. "
        "Pool labels stay hidden while practicing."
    )

    c1, c2 = st.columns([1, 5])
    with c1:
        start = st.button("Start", type="primary")
    with c2:
        st.write("")

    if start:
        # always start fresh
        reset_attempt()

        if mode.startswith("Official"):
            if len(published_exam) == 0:
                st.error("No published EXAM questions available.")
                st.stop()
            chosen, dbg = select_official_exam_questions(published_exam, int(total_q))
            selection_mode = "official_exam_only_strict"
        else:
            if len(published_all) == 0:
                st.error("No published questions available.")
                st.stop()
            chosen, dbg = select_any_pool_random(published_all, int(total_q))
            selection_mode = "any_pool_random"

        attempt_id = new_attempt_id()
        started_at = time.time()
        duration_sec = int(duration_min * 60)
        end_ts = started_at + duration_sec

        st.session_state.attempt = {
            "attempt_id": attempt_id,
            "mode": mode,
            "selection_mode": selection_mode,
            "total_q": int(total_q),
            "duration_sec": duration_sec,
            "started_at": started_at,
            "end_ts": end_ts,
            "order": [q["id"] for q in chosen if q.get("id")],
            "idx": 0,
            "answers": {},
            "marked": set(),
            "submitted": False,
            "selection_debug": dbg,
        }

        # Clear autosubmit param just in case
        set_qp(autosubmit=None)
        st.rerun()

    st.stop()


# -------------------------
# Active attempt view (Typeform)
# -------------------------
attempt = st.session_state.attempt

# Handle JS autosubmit signal
qp = get_qp()
autosubmit = qp.get("autosubmit")
if isinstance(autosubmit, list):
    autosubmit = autosubmit[0] if autosubmit else None

if autosubmit and (str(autosubmit) == attempt["attempt_id"]) and not attempt["submitted"]:
    attempt["submitted"] = True
    st.session_state.attempt = attempt
    set_qp(autosubmit=None)
    st.rerun()

# Server-side enforcement too
if (time.time() >= attempt["end_ts"]) and not attempt["submitted"]:
    attempt["submitted"] = True
    st.session_state.attempt = attempt
    st.rerun()

order = attempt["order"]
if not order:
    st.error("No questions selected for this attempt. Add more published questions.")
    reset_attempt()
    st.stop()

# Top bar (timer + progress)
top1, top2, top3, top4 = st.columns([1.3, 2.2, 1.2, 1.3])

with top1:
    # JS ticking timer (real exam feel)
    render_js_timer(attempt["end_ts"], attempt["attempt_id"])

with top2:
    idx = attempt["idx"]
    st.progress(min(1.0, (idx + 1) / max(1, len(order))))
    st.caption(f"Question {idx + 1} / {len(order)}")

with top3:
    answered_count = sum(1 for _qid, ans in attempt["answers"].items() if ans)
    st.metric("Answered", f"{answered_count}/{len(order)}")

with top4:
    marked_count = len(attempt["marked"])
    st.metric("Marked", str(marked_count))

st.divider()

# Auto submit view
if attempt["submitted"]:
    push_wrong_to_revision(order, by_id, attempt["answers"])
    log_mock_attempt(attempt, by_id)

    # Score + Review
    score = 0
    detailed = []
    for qid in order:
        q = by_id.get(qid)
        if not q:
            continue
        sel = attempt["answers"].get(qid, [])
        ok = grade_one(q, sel)
        score += 1 if ok else 0
        detailed.append((qid, ok, sel, (q.get("answer") or {}).get("keys", [])))

    pct = (score / max(1, len(order))) * 100
    st.markdown("## Results")
    st.metric("Score", f"{score}/{len(order)} ({pct:.1f}%)")
    st.caption("Incorrect questions were added to Revision automatically. Attempt saved to Stats.")

    st.divider()
    st.markdown("## Review (with explanations)")

    for qid, ok, selected, correct in detailed:
        q = by_id.get(qid)
        if not q:
            continue

        st.markdown(f"### {qid} — {q.get('title','')}")
        st.caption(f"{q.get('topic','')} • {q.get('subtopic','')} • {q.get('difficulty','')}")

        if ok:
            st.success("✅ Correct")
        else:
            st.error("❌ Incorrect")
            st.info(f"Your answer: **{', '.join(selected) if selected else '(none)'}**")
            st.info(f"Correct answer: **{', '.join(correct) if correct else '(missing)'}**")

        st.markdown("#### Question")
        st.write(q.get("prompt", ""))

        r = q.get("rationale") or {}
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

    cA, cB = st.columns([1, 6])
    with cA:
        if st.button("Start new attempt", type="primary"):
            reset_attempt()
            st.rerun()
    st.stop()

# Active question (Typeform)
idx = attempt["idx"]
qid = order[idx]
q = by_id.get(qid)

if not q:
    st.error(f"Question not found in bank: {qid}")
    reset_attempt()
    st.stop()

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

prev = attempt["answers"].get(qid, [])
selected_keys: list[str] = []

if qtype == "multi":
    for k in ["A", "B", "C", "D"]:
        if k not in choice_map:
            continue
        default_checked = k in prev
        ck = st.checkbox(
            f"{k}. {choice_map[k]}",
            value=default_checked,
            key=f"mock_opt_{qid}_{k}",
        )
        if ck:
            selected_keys.append(k)
else:
    keys = [c["key"] for c in choices]
    labels = [f"{k}. {choice_map[k]}" for k in keys]
    default_index = 0
    if prev and prev[0] in keys:
        default_index = keys.index(prev[0])
    picked = st.radio(
        "Select one",
        options=labels,
        index=default_index,
        key=f"mock_radio_{qid}",
    )
    selected_keys = [picked.split(".")[0]]

attempt["answers"][qid] = selected_keys
st.session_state.attempt = attempt

# Navigation
nav1, nav2, nav3, nav4, nav5 = st.columns([1, 1, 1.4, 1.2, 4.4])

with nav1:
    if st.button("Prev", disabled=idx == 0):
        attempt["idx"] = max(0, idx - 1)
        st.session_state.attempt = attempt
        st.rerun()

with nav2:
    if st.button("Next", disabled=idx >= len(order) - 1):
        attempt["idx"] = min(len(order) - 1, idx + 1)
        st.session_state.attempt = attempt
        st.rerun()

with nav3:
    marked = attempt["marked"]
    is_marked = qid in marked
    if st.button("Unmark" if is_marked else "Mark for review"):
        if is_marked:
            marked.remove(qid)
        else:
            marked.add(qid)
        attempt["marked"] = marked
        st.session_state.attempt = attempt
        st.rerun()

with nav4:
    if st.button("Submit", type="primary"):
        attempt["submitted"] = True
        st.session_state.attempt = attempt
        st.rerun()

st.caption("Typeform mode: one question at a time. No explanations until submission. Pool labels hidden by design.")
