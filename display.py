import streamlit as st
from pymongo import MongoClient
from bson import ObjectId
import json

# === CONFIG ===
st.set_page_config(page_title="MongoDB Question Preview", layout="wide")

# === MONGODB CONNECTION ===
mongo_uri = st.secrets["mongo_uri"]  # .streamlit/secrets.toml
client = MongoClient(mongo_uri)
db = client["quiz_app"]
collection = db["questions"]

st.title("👀 MongoDB Question Previewer (DB → UI)")
st.caption("Load questions from MongoDB one-by-one, verify display, and flag formatting/schema issues.")

# ---------------------------
# Helpers
# ---------------------------
def safe_get(d, path, default=None):
    """path like 'explanation.why_correct'"""
    cur = d
    for key in path.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur

def to_str_id(x):
    return str(x) if isinstance(x, ObjectId) else str(x)

# ---------------------------
# Fetch IDs (lightweight)
# ---------------------------
query_filter = {"status": {"$in": ["active", "draft"]}}  # change if you want all
sort_by = [("created_at", 1)]  # oldest first; change to -1 for latest first

docs = list(collection.find(query_filter, {"question_id": 1, "topic": 1, "subtopic": 1}).sort(sort_by))

if not docs:
    st.warning("No questions found in DB with the current filter.")
    st.stop()

# Sidebar controls
st.sidebar.header("Controls")

mode = st.sidebar.radio("Load mode", ["By index", "By question_id", "By _id"])

selected_doc = None

if mode == "By index":
    idx = st.sidebar.number_input("Question #", min_value=1, max_value=len(docs), value=1, step=1)
    meta = docs[idx - 1]
    selected_doc = collection.find_one({"_id": meta["_id"]})

elif mode == "By question_id":
    qids = [d.get("question_id", f"(missing) {to_str_id(d['_id'])}") for d in docs]
    chosen = st.sidebar.selectbox("question_id", options=qids, index=0)
    selected_doc = collection.find_one({"question_id": chosen})

else:  # By _id
    ids = [to_str_id(d["_id"]) for d in docs]
    chosen = st.sidebar.selectbox("_id", options=ids, index=0)
    selected_doc = collection.find_one({"_id": ObjectId(chosen)})

if not selected_doc:
    st.error("Failed to load selected question.")
    st.stop()

q = selected_doc

# ---------------------------
# UI: Preview layout
# ---------------------------
left, right = st.columns([2, 1], gap="large")

with left:
    st.subheader(f"{q.get('question_id', '(no question_id)')} — {q.get('topic','(no topic)')}")
    st.write(f"**Subtopic:** {q.get('subtopic','—')}  |  **Difficulty:** {q.get('difficulty','—')}  |  **Type:** {q.get('type','—')}")
    st.write(f"**Mongo _id:** `{to_str_id(q.get('_id'))}`")

    stem = q.get("stem", "")
    if stem:
        st.markdown("### Stem")
        st.markdown(stem)
    else:
        st.warning("Missing `stem` field.")

    sample_docs = q.get("sample_docs")
    if sample_docs:
        st.markdown("### Sample Documents")
        st.json(sample_docs)

    operation = q.get("operation")
    if operation:
        st.markdown("### Operation")
        # If operation is stored as string, show as code
        if isinstance(operation, str):
            st.code(operation, language="javascript")
        else:
            st.json(operation)

    options = q.get("options", [])
    st.markdown("### Options")
    if not options:
        st.warning("No `options` found.")
    else:
        # Render options cleanly
        option_map = {opt.get("key"): opt.get("text", "") for opt in options}
        keys = [opt.get("key") for opt in options if opt.get("key") is not None]

        selected = st.radio(
            "Pick one (preview only)",
            options=keys,
            format_func=lambda k: f"{k}. {option_map.get(k,'')}",
            index=0 if keys else None
        )

    # Answer + explanation reveal
    if st.button("✅ Show Answer & Explanation"):
        st.success(f"Answer: {', '.join(q.get('answers', []))}")

        exp = q.get("explanation", {})
        if not exp:
            st.warning("No `explanation` object found.")
        else:
            st.markdown("### Explanation")

            why_correct = safe_get(q, "explanation.why_correct", [])
            why_incorrect = safe_get(q, "explanation.why_incorrect", [])
            mini_examples = safe_get(q, "explanation.mini_examples", [])
            takeaway = safe_get(q, "explanation.takeaway", "")

            if why_correct:
                st.markdown("**Why correct**")
                for line in why_correct:
                    st.markdown(f"- {line}")

            if why_incorrect:
                st.markdown("**Why incorrect**")
                for line in why_incorrect:
                    st.markdown(f"- {line}")

            if mini_examples:
                st.markdown("**Mini examples**")
                for ex in mini_examples:
                    st.code(ex, language="javascript")

            if takeaway:
                st.info(f"💡 Takeaway: {takeaway}")

with right:
    st.subheader("🔎 Quick Schema Checks")

    missing = []
    required = ["question_id", "topic", "subtopic", "difficulty", "type", "stem", "options", "answers", "explanation"]
    for k in required:
        if k not in q:
            missing.append(k)

    if missing:
        st.error("Missing required fields:")
        st.write(missing)
    else:
        st.success("All required fields present ✅")

    # Option key sanity
    opts = q.get("options", [])
    if opts:
        keys = [o.get("key") for o in opts]
        if len(keys) != len(set(keys)):
            st.warning("Duplicate option keys found.")
        if any(k is None for k in keys):
            st.warning("Some options missing `key`.")

    # Answer sanity
    answers = q.get("answers", [])
    opt_keys = {o.get("key") for o in opts}
    bad_answers = [a for a in answers if a not in opt_keys]
    if bad_answers:
        st.warning(f"Answers not present in options: {bad_answers}")

    # Raw doc viewer
    st.markdown("---")
    with st.expander("📦 View Raw Document (as stored in DB)"):
        # ObjectId is not JSON serializable; convert for display
        q_copy = dict(q)
        q_copy["_id"] = to_str_id(q_copy.get("_id"))
        st.json(q_copy)
