from __future__ import annotations
import streamlit as st


def render_question_preview(q: dict):
    st.markdown(f"### {q.get('id', '')} — {q.get('title', '')}")
    st.caption(f"{q.get('topic','')} • {q.get('subtopic','')} • {q.get('difficulty','')} • {q.get('type','')}")

    st.markdown("#### Question")
    st.write(q.get("prompt", ""))

    context = q.get("context")
    if context and str(context).strip():
        with st.expander("Context", expanded=False):
            st.write(context)

    artifacts = q.get("artifacts") or {}
    sample_docs = artifacts.get("sample_docs") or []
    if sample_docs:
        with st.expander("Sample docs", expanded=False):
            st.json(sample_docs)

    # Choices
    st.markdown("#### Choices")
    for c in q.get("choices", []):
        st.write(f"**{c.get('key')}**. {c.get('text')}")

    # Answer (shown only in preview/admin)
    st.markdown("#### Answer")
    ans = (q.get("answer") or {}).get("keys", [])
    st.write(", ".join(ans) if ans else "-")

    # Explanation blocks
    r = q.get("rationale") or {}
    st.markdown("#### Explanation")

    rule = r.get("rule", "")
    if rule:
        st.success(f"**RULE:** {rule}")

    correct_why = r.get("correct_why") or []
    if correct_why:
        st.markdown("**Why correct**")
        for b in correct_why:
            st.write(f"- {b}")

    wrong_why = r.get("wrong_why") or {}
    if wrong_why:
        st.markdown("**Why others are wrong**")
        for k in ["A", "B", "C", "D"]:
            if k in wrong_why:
                st.write(f"- **{k}**: {wrong_why[k]}")

    trap = r.get("trap")
    if trap and str(trap).strip():
        st.info(f"**Trap:** {trap}")

    mini_demo = r.get("mini_demo")
    if mini_demo and str(mini_demo).strip():
        with st.expander("Mini demo", expanded=False):
            st.code(mini_demo, language="javascript")
