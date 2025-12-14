import streamlit as st
from database import QuizDatabase
import json
from bson import ObjectId
import datetime
import re
from validators import validate_topic

def display_summary(db):
    total_questions = db.get_question_count()
    topic_counts_cursor = db.collection.aggregate([
        {"$group": {"_id": "$topic", "count": {"$sum": 1}}}
    ])
    topic_counts = {doc['_id']: doc['count'] for doc in topic_counts_cursor}

    st.markdown(f"## Total Questions: {total_questions}")
    st.markdown("### Questions by Topic:")
    for topic, count in topic_counts.items():
        st.write(f"- **{topic}**: {count}")

def display_question_ids(db):
    st.header("Question IDs by Topic")

    topics = db.collection.distinct("topic")
    selected_topic = st.selectbox("Select Topic", topics)

    if selected_topic:
        question_cursor = db.collection.find({"topic": selected_topic}, {"question_id": 1})
        question_ids = [doc.get("question_id", str(doc.get("_id"))) for doc in question_cursor]

        st.write(f"Total questions in topic '{selected_topic}': {len(question_ids)}")
        st.write("Question IDs:")
        for qid in question_ids:
            st.write(qid)

def get_next_question_id(collection, topic, prefix_map):
    prefix = prefix_map.get(topic, topic[:4].lower())
    regex = f"^{prefix}(\\d+)$"
    last_doc = collection.find(
        {"question_id": {"$regex": regex}}
    ).sort("question_id", -1).limit(1)

    last_num = 0
    for doc in last_doc:
        qid = doc.get("question_id", "")
        match = re.match(regex, qid)
        if match:
            last_num = int(match.group(1))
    next_num = last_num + 1
    return f"{prefix}{next_num:02d}"

def upload_questions(db):
    st.header("Upload Questions (Single or Multiple)")

    prefix_map = {
        "CRUD Operations": "crud",
        "Querying": "qry",
        "Indexing": "idx",
        "Aggregation": "agg",
        "MongoDB Overview": "ovw",
        "Data Modeling": "dm",
    }

    uploaded_file = st.file_uploader("Upload JSON file", type="json")
    json_text = st.text_area("Or paste single question JSON here", height=700)

    input_data = None
    if uploaded_file:
        try:
            input_data = json.load(uploaded_file)
        except Exception as e:
            st.error(f"Failed to load JSON from file: {e}")
    elif json_text.strip():
        try:
            input_data = json.loads(json_text.strip())
        except Exception as e:
            st.error(f"Invalid JSON input: {e}")

    if input_data:
        if isinstance(input_data, dict):
            input_data = [input_data]  # Normalize to list

        if not isinstance(input_data, list):
            st.error("Input must be a JSON object or list of objects")
            return

        invalid_topics = []
        for doc in input_data:
            # Remove _id if present to avoid duplicate key error
            if '_id' in doc:
                del doc['_id']

            topic = doc.get("topic")
            valid_topic, msg = validate_topic(topic)
            if not valid_topic:
                invalid_topics.append(topic)
            else:
                doc.setdefault("created_at", datetime.datetime.utcnow())
                doc.setdefault("updated_at", datetime.datetime.utcnow())
                if not doc.get("question_id") or doc.get("question_id") == "AUTO":
                    doc["question_id"] = get_next_question_id(db.collection, topic, prefix_map)

        if invalid_topics:
            st.error(f"Invalid topics detected: {set(invalid_topics)}. Please fix before uploading.")
        else:
            try:
                result = db.collection.insert_many(input_data)
                st.success(f"Inserted {len(result.inserted_ids)} questions successfully.")
            except Exception as e:
                st.error(f"Failed to insert questions: {e}")


def edit_delete_question(db):
    st.header("Edit or Delete Question by question_id")
    qid = st.text_input("Enter question_id to fetch")

    if qid:
        doc = db.collection.find_one({"question_id": qid})
        if doc:
            with st.form("edit_question_form"):
                stem = st.text_area("Question Stem", doc.get("stem", ""))
                topic = st.text_input("Topic", doc.get("topic", ""))
                subtopic = st.text_input("Subtopic", doc.get("subtopic", ""))
                difficulty = st.text_input("Difficulty", doc.get("difficulty", ""))
                # Convert options items to strings safely
                options_list = doc.get("options", [])
                options_str_list = []
                for opt in options_list:
                    if isinstance(opt, dict):
                        # Convert dict to JSON string, or customize as needed
                        options_str_list.append(json.dumps(opt))
                    else:
                        options_str_list.append(str(opt))

                options = st.text_area("Options (one per line)", "\n".join(options_str_list),height = 300)
                answers = st.text_area("Answers (comma separated indices or texts)", ", ".join(map(str, doc.get("answers", []))))
                explanation = st.text_area("Explanation", doc.get("explanation", ""),height = 300)
                submitted = st.form_submit_button("Save Changes")
                delete_btn = st.form_submit_button("Delete Question")

                if submitted:
                    # Prepare updated doc
                    updated_doc = {
                        "stem": stem,
                        "topic": topic,
                        "subtopic": subtopic,
                        "difficulty": difficulty,
                        "options": [opt.strip() for opt in options.split("\n") if opt.strip()],
                        "answers": [ans.strip() for ans in answers.split(",") if ans.strip()],
                        "explanation": explanation,
                        "updated_at": datetime.datetime.utcnow()
                    }
                    try:
                        db.collection.update_one({"_id": doc["_id"]}, {"$set": updated_doc})
                        st.success(f"Updated question '{qid}'")
                    except Exception as e:
                        st.error(f"Error updating: {e}")

                if delete_btn:
                    try:
                        db.collection.delete_one({"_id": doc["_id"]})
                        st.success(f"Deleted question '{qid}'")
                    except Exception as e:
                        st.error(f"Error deleting: {e}")
        else:
            st.error(f"No question found with question_id '{qid}'.")

def main():
    st.title("Admin Interface: Quiz Management")

    db = QuizDatabase()

    st.sidebar.title("Navigation")
    option = st.sidebar.radio("Go to", ("Summary", "Questions by Topic", "Upload Questions", "Edit/Delete Question"))

    if option == "Summary":
        display_summary(db)
    elif option == "Questions by Topic":
        display_question_ids(db)
    elif option == "Upload Questions":
        upload_questions(db)
    elif option == "Edit/Delete Question":
        edit_delete_question(db)

if __name__ == "__main__":
    main()
