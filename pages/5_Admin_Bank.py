from __future__ import annotations

import json
import subprocess
from pathlib import Path

import streamlit as st
import yaml

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.components import render_question_preview

ROOT = Path(__file__).resolve().parents[1]
YAML_DIR = ROOT / "question_bank" / "v2" / "questions"
JSONL_PATH = ROOT / "question_bank" / "v2" / "questions.jsonl"


def run_cmd(cmd: list[str]) -> tuple[int, str]:
    """Run command and return (returncode, combined_output)."""
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out.strip()


def list_yaml_files():
    YAML_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted([p for p in YAML_DIR.glob("*.yaml") if not p.name.startswith("_")])
    return files


def load_jsonl_questions():
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


def admin_gate():
    # Optional admin password gate.
    # If you don't set ADMIN_PASSWORD in secrets, the page is open.
    pw = None
    try:
        pw = st.secrets.get("ADMIN_PASSWORD")
    except Exception:
        pw = None

    if not pw:
        return True

    st.warning("Admin access required.")
    entered = st.text_input("Enter admin password", type="password")
    return entered == pw


st.set_page_config(page_title="Admin — Bank Tools", layout="wide")

st.title("Admin — Question Bank Tools")

if not admin_gate():
    st.stop()

tabs = st.tabs(["Paste YAML → Save", "Validate", "Build", "Preview", "Bank Health"])

# -------------------------
# Tab 1: Paste YAML → Save
# -------------------------
with tabs[0]:
    st.subheader("Paste full YAML and save to the bank")

    default_yaml = """schema_version: "2.0"

id: "CRUD-Q003"
title: "Your short title"
topic: "CRUD"
subtopic: "find() basics"
difficulty: "easy"
type: "single"
tags: ["tag1", "tag2"]

exam_relevance:
  pool: "learning"
  confidence: "high"

prompt: >
  Write the question stem here.

context: >
  Optional scenario.

artifacts:
  sample_docs: []
  snippets: []
  notes: []

choices:
  - key: "A"
    text: "Option A"
  - key: "B"
    text: "Option B"
  - key: "C"
    text: "Option C"
  - key: "D"
    text: "Option D"

answer:
  keys: ["B"]

rationale:
  rule: >
    One-line memory hook.

  correct_why:
    - "Why correct (bullet)"

  wrong_why:
    A: "Why A wrong"
    C: "Why C wrong"
    D: "Why D wrong"

  trap: >
    Optional trap.

  mini_demo: |
    // Optional mongosh snippet

status: "draft"
author: "prashanth"
updated_at: "2025-12-14"
"""

    yaml_text = st.text_area("YAML", value=default_yaml, height=520)

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        save_mode = st.radio("Save mode", ["Save as Draft", "Save as Published"], horizontal=False)
    with col2:
        overwrite = st.checkbox("Allow overwrite if file exists", value=False)

    if st.button("Save YAML to bank", type="primary"):
        try:
            obj = yaml.safe_load(yaml_text)
            if not isinstance(obj, dict):
                raise ValueError("YAML must parse to a mapping (key/value object).")

            qid = obj.get("id")
            if not qid or not str(qid).strip():
                raise ValueError("Missing required field: id")

            # Enforce save mode
            obj["status"] = "published" if save_mode == "Save as Published" else "draft"

            YAML_DIR.mkdir(parents=True, exist_ok=True)
            out_path = YAML_DIR / f"{qid}.yaml"

            if out_path.exists() and not overwrite:
                raise ValueError(f"File already exists: {out_path.name}. Enable overwrite to replace it.")

            with out_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True, width=110)

            st.success(f"Saved: {out_path.relative_to(ROOT)}")
            st.info("Next: run Validate tab → then Build tab.")
        except Exception as e:
            st.error(f"Save failed: {e}")

# -------------------------
# Tab 2: Validate
# -------------------------
with tabs[1]:
    st.subheader("Validate bank (YAML)")

    if st.button("Run validation", type="primary"):
        rc, out = run_cmd(["python", "-m", "scripts.validate_bank"])
        if rc == 0:
            st.success(out or "VALIDATION PASSED ✅")
        else:
            st.error("VALIDATION FAILED ❌")
            st.code(out or "(no output)", language="text")

# -------------------------
# Tab 3: Build
# -------------------------
with tabs[2]:
    st.subheader("Build bank (compile YAML → JSONL)")

    if st.button("Build JSONL", type="primary"):
        rc, out = run_cmd(["python", "-m", "scripts.build_bank"])
        if rc == 0:
            st.success("Build successful ✅")
            st.code(out or "(no output)", language="text")
        else:
            st.error("Build failed ❌")
            st.code(out or "(no output)", language="text")

# -------------------------
# Tab 4: Preview
# -------------------------
with tabs[3]:
    st.subheader("Preview how a question will render")

    questions = load_jsonl_questions()
    if not questions:
        st.info("No compiled questions found. Run Build first.")
    else:
        ids = [q.get("id", "") for q in questions if q.get("id")]
        selected = st.selectbox("Select question", ids)

        q = next((x for x in questions if x.get("id") == selected), None)
        if q:
            # IMPORTANT: do not show pool information to the user in normal flows.
            # In admin preview, we still avoid highlighting pool by default.
            render_question_preview(q)

# -------------------------
# Tab 5: Bank Health
# -------------------------
with tabs[4]:
    st.subheader("Bank health overview")

    yfiles = list_yaml_files()
    st.write(f"YAML files: **{len(yfiles)}** in `{YAML_DIR.relative_to(ROOT)}`")

    questions = load_jsonl_questions()
    st.write(f"Compiled JSONL questions: **{len(questions)}**")

    if questions:
        published = sum(1 for q in questions if q.get("status") == "published")
        drafts = sum(1 for q in questions if q.get("status") == "draft")
        st.write(f"Published: **{published}** | Draft: **{drafts}**")

        # quick distribution
        by_topic = {}
        by_diff = {}
        for q in questions:
            by_topic[q.get("topic", "Unknown")] = by_topic.get(q.get("topic", "Unknown"), 0) + 1
            by_diff[q.get("difficulty", "Unknown")] = by_diff.get(q.get("difficulty", "Unknown"), 0) + 1

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**By topic**")
            st.json(by_topic)
        with c2:
            st.markdown("**By difficulty**")
            st.json(by_diff)
