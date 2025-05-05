import streamlit as st
from pymongo import MongoClient
import random

# === MONGODB CONNECTION ===
mongo_uri = st.secrets["mongo_uri"]
client = MongoClient(mongo_uri)
db = client["quiz_app"]
collection = db["questions"]

# === PAGE CONFIG ===
st.set_page_config(page_title="MongoDB Quiz Practice", layout="centered")
st.title("🧠 MongoDB Quiz Practice")

# === SESSION STATE SETUP ===
if "question_doc" not in st.session_state:
    st.session_state["question_doc"] = collection.aggregate([{"$sample": {"size": 1}}]).next()
if "submitted" not in st.session_state:
    st.session_state["submitted"] = False

question_doc = st.session_state["question_doc"]

# === DISPLAY QUESTION ===
st.subheader(f"Topic: {question_doc['topic']} ({question_doc.get('difficulty', 'N/A')})")
st.markdown(f"**Q: {question_doc['stem']}**")

# === OPTIONS ===
options = [f"{opt['key']}: {opt['text']}" for opt in question_doc["options"]]
selected = st.radio("Choose your answer:", options, index=None, key="selected_answer")

# === SUBMIT BUTTON ===
if st.button("✅ Submit Answer") and not st.session_state["submitted"]:
    if selected is None:
        st.warning("Please select an answer before submitting.")
    else:
        chosen_key = selected.split(":")[0]
        correct_keys = question_doc["answers"]

        if chosen_key in correct_keys:
            st.success("✅ Correct!")
        else:
            st.error("❌ Incorrect.")

        st.markdown("---")
        st.markdown("### 📘 Explanation")
        st.markdown(question_doc["explanation"], unsafe_allow_html=True)
        st.session_state["submitted"] = True

# === NEXT QUESTION ===
if st.session_state["submitted"]:
    if st.button("🔄 Try Another Question"):
        st.session_state["question_doc"] = collection.aggregate([{"$sample": {"size": 1}}]).next()
        st.session_state["submitted"] = False
        st.rerun()
