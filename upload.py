import streamlit as st
import json
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

# === CONFIG ===
st.set_page_config(page_title="MongoDB QA Uploader", layout="wide")

# === MONGODB CONNECTION ===
mongo_uri = st.secrets["mongo_uri"]  # Define this in .streamlit/secrets.toml
client = MongoClient(mongo_uri)
db = client["quiz_app"]
collection = db["questions"]

# === PAGE HEADER ===
st.title("🧠 MongoDB Question Upload Tool")
st.markdown("Paste a full QA document below and click **Upload to MongoDB**.")

# === TEXT AREA INPUT ===
qa_input = st.text_area("Paste QA JSON here:", height=400)

if st.button("📤 Upload to MongoDB"):
    try:
        # Parse JSON
        qa_doc = json.loads(qa_input)

        # Auto-fill metadata
        qa_doc["_id"] = ObjectId()
        qa_doc["created_at"] = datetime.utcnow()
        qa_doc["updated_at"] = datetime.utcnow()

        # Insert into MongoDB
        collection.insert_one(qa_doc)
        st.success("✅ Uploaded successfully!")
        st.json(qa_doc)

    except Exception as e:
        st.error(f"❌ Upload failed: {e}")
