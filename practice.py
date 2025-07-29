
import streamlit as st
from pymongo import MongoClient
import random
import time
from datetime import datetime, timedelta
import plotly.express as px
import pandas as pd

# === MONGODB CONNECTION ===
mongo_uri = st.secrets["mongo_uri"]
client = MongoClient(mongo_uri)
db = client["quiz_app"]
collection = db["questions"]

# === PAGE CONFIG ===
st.set_page_config(page_title="MongoDB Associate Exam Prep", layout="wide")

# === EXAM DOMAINS FOR MONGODB ASSOCIATE ===
EXAM_DOMAINS = {
    "CRUD Operations": ["CRUD", "Insert", "Update", "Delete", "Find"],
    "Aggregation": ["Aggregation", "Pipeline", "Match", "Group", "Project"],
    "Indexing": ["Indexes", "Index", "Compound Indexes", "Text Index"],
    "Data Modeling": ["Schema", "Data Model", "Document Design", "References"],
    "Tools & Deployment": ["Tools", "Deployment", "Compass", "Atlas", "Mongosh"]
}

# === SESSION STATE SETUP ===
if "user_stats" not in st.session_state:
    st.session_state["user_stats"] = {domain: {"correct": 0, "total": 0} for domain in EXAM_DOMAINS.keys()}
if "question_doc" not in st.session_state:
    st.session_state["question_doc"] = None
if "submitted" not in st.session_state:
    st.session_state["submitted"] = False
if "exam_mode" not in st.session_state:
    st.session_state["exam_mode"] = False
if "exam_start_time" not in st.session_state:
    st.session_state["exam_start_time"] = None
if "exam_questions_answered" not in st.session_state:
    st.session_state["exam_questions_answered"] = 0
if "exam_total_questions" not in st.session_state:
    st.session_state["exam_total_questions"] = 10

# === SIDEBAR NAVIGATION ===
st.sidebar.title("📚 MongoDB Associate Exam Prep")
page = st.sidebar.selectbox("Choose Mode:", ["🎯 Practice Mode", "⏱️ Exam Simulation", "📊 Progress Dashboard"])

# === HELPER FUNCTIONS ===
def get_question_domain(topic):
    """Determine which exam domain a question belongs to"""
    for domain, keywords in EXAM_DOMAINS.items():
        if any(keyword.lower() in topic.lower() for keyword in keywords):
            return domain
    return "Other"

def get_filtered_question(selected_domain=None):
    """Get a random question, optionally filtered by domain"""
    if selected_domain and selected_domain != "All Topics":
        keywords = EXAM_DOMAINS.get(selected_domain, [])
        query = {"$or": [{"topic": {"$regex": keyword, "$options": "i"}} for keyword in keywords]}
        questions = list(collection.aggregate([{"$match": query}, {"$sample": {"size": 1}}]))
        return questions[0] if questions else collection.aggregate([{"$sample": {"size": 1}}]).next()
    else:
        return collection.aggregate([{"$sample": {"size": 1}}]).next()

def update_stats(domain, is_correct):
    """Update user statistics"""
    st.session_state["user_stats"][domain]["total"] += 1
    if is_correct:
        st.session_state["user_stats"][domain]["correct"] += 1

def calculate_accuracy(domain_stats):
    """Calculate accuracy percentage"""
    if domain_stats["total"] == 0:
        return 0
    return round((domain_stats["correct"] / domain_stats["total"]) * 100, 1)

# === PRACTICE MODE ===
if page == "🎯 Practice Mode":
    st.title("🎯 Practice Mode")
    
    # Topic Filter
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_domain = st.selectbox(
            "Choose Exam Domain:",
            ["All Topics"] + list(EXAM_DOMAINS.keys())
        )
    
    with col2:
        if st.button("🔄 New Question"):
            st.session_state["question_doc"] = get_filtered_question(selected_domain)
            st.session_state["submitted"] = False
            st.rerun()
    
    # Get question if none exists
    if st.session_state["question_doc"] is None:
        st.session_state["question_doc"] = get_filtered_question(selected_domain)
    
    question_doc = st.session_state["question_doc"]
    current_domain = get_question_domain(question_doc['topic'])
    
    # Display Question
    st.subheader(f"Domain: {current_domain}")
    st.markdown(f"**Topic:** {question_doc['topic']} | **Difficulty:** {question_doc.get('difficulty', 'N/A')}")
    st.markdown(f"**Q: {question_doc['stem']}**")
    
    # Options
    options = [f"{opt['key']}: {opt['text']}" for opt in question_doc["options"]]
    selected = st.radio("Choose your answer:", options, index=None, key="selected_answer")
    
    # Submit Button
    if st.button("✅ Submit Answer") and not st.session_state["submitted"]:
        if selected is None:
            st.warning("Please select an answer before submitting.")
        else:
            chosen_key = selected.split(":")[0]
            correct_keys = question_doc["answers"]
            is_correct = chosen_key in correct_keys
            
            # Update statistics
            update_stats(current_domain, is_correct)
            
            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error("❌ Incorrect.")
                st.info(f"Correct answer(s): {', '.join(correct_keys)}")
            
            st.markdown("---")
            st.markdown("### 📘 Explanation")
            st.markdown(question_doc["explanation"], unsafe_allow_html=True)
            st.session_state["submitted"] = True

# === EXAM SIMULATION MODE ===
elif page == "⏱️ Exam Simulation":
    st.title("⏱️ Exam Simulation Mode")
    
    if not st.session_state["exam_mode"]:
        st.markdown("### Ready for your MongoDB Associate practice exam?")
        st.info("This simulation includes 10 questions with a 20-minute time limit.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Start Exam", type="primary"):
                st.session_state["exam_mode"] = True
                st.session_state["exam_start_time"] = datetime.now()
                st.session_state["exam_questions_answered"] = 0
                st.session_state["question_doc"] = get_filtered_question()
                st.session_state["submitted"] = False
                st.rerun()
    
    else:
        # Calculate remaining time
        elapsed_time = datetime.now() - st.session_state["exam_start_time"]
        remaining_time = timedelta(minutes=20) - elapsed_time
        
        if remaining_time.total_seconds() <= 0:
            st.error("⏰ Time's up! Exam ended.")
            st.session_state["exam_mode"] = False
            st.stop()
        
        # Display timer and progress
        col1, col2, col3 = st.columns(3)
        with col1:
            minutes_left = int(remaining_time.total_seconds() // 60)
            seconds_left = int(remaining_time.total_seconds() % 60)
            st.metric("⏰ Time Remaining", f"{minutes_left}:{seconds_left:02d}")
        
        with col2:
            st.metric("📝 Question", f"{st.session_state['exam_questions_answered'] + 1}/10")
        
        with col3:
            if st.button("🛑 End Exam"):
                st.session_state["exam_mode"] = False
                st.success("Exam ended successfully!")
                st.rerun()
        
        # Question display (similar to practice mode)
        if st.session_state["question_doc"]:
            question_doc = st.session_state["question_doc"]
            current_domain = get_question_domain(question_doc['topic'])
            
            st.markdown("---")
            st.subheader(f"Domain: {current_domain}")
            st.markdown(f"**Q: {question_doc['stem']}**")
            
            options = [f"{opt['key']}: {opt['text']}" for opt in question_doc["options"]]
            selected = st.radio("Choose your answer:", options, index=None, key="exam_answer")
            
            if st.button("➡️ Next Question") and not st.session_state["submitted"]:
                if selected is None:
                    st.warning("Please select an answer before proceeding.")
                else:
                    chosen_key = selected.split(":")[0]
                    correct_keys = question_doc["answers"]
                    is_correct = chosen_key in correct_keys
                    
                    update_stats(current_domain, is_correct)
                    st.session_state["exam_questions_answered"] += 1
                    
                    if st.session_state["exam_questions_answered"] >= 10:
                        st.session_state["exam_mode"] = False
                        st.success("🎉 Exam completed!")
                        st.rerun()
                    else:
                        st.session_state["question_doc"] = get_filtered_question()
                        st.session_state["submitted"] = False
                        st.rerun()

# === PROGRESS DASHBOARD ===
elif page == "📊 Progress Dashboard":
    st.title("📊 Your Progress Dashboard")
    
    # Overall Statistics
    total_questions = sum([stats["total"] for stats in st.session_state["user_stats"].values()])
    total_correct = sum([stats["correct"] for stats in st.session_state["user_stats"].values()])
    overall_accuracy = calculate_accuracy({"correct": total_correct, "total": total_questions})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Total Questions", total_questions)
    with col2:
        st.metric("✅ Correct Answers", total_correct)
    with col3:
        st.metric("🎯 Overall Accuracy", f"{overall_accuracy}%")
    
    st.markdown("---")
    
    # Domain-wise Performance
    st.subheader("📈 Performance by Exam Domain")
    
    # Prepare data for visualization
    domain_data = []
    for domain, stats in st.session_state["user_stats"].items():
        accuracy = calculate_accuracy(stats)
        domain_data.append({
            "Domain": domain,
            "Questions Attempted": stats["total"],
            "Accuracy (%)": accuracy,
            "Correct": stats["correct"]
        })
    
    if domain_data and any(d["Questions Attempted"] > 0 for d in domain_data):
        df = pd.DataFrame(domain_data)
        df_filtered = df[df["Questions Attempted"] > 0]
        
        # Accuracy chart
        fig = px.bar(df_filtered, x="Domain", y="Accuracy (%)", 
                     title="Accuracy by Exam Domain",
                     color="Accuracy (%)",
                     color_continuous_scale="RdYlGn")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed stats table
        st.subheader("📋 Detailed Statistics")
        st.dataframe(df_filtered, use_container_width=True)
        
        # Recommendations
        st.subheader("💡 Study Recommendations")
        weak_areas = df_filtered[df_filtered["Accuracy (%)"] < 70]["Domain"].tolist()
        strong_areas = df_filtered[df_filtered["Accuracy (%)"] >= 80]["Domain"].tolist()
        
        if weak_areas:
            st.warning(f"**Focus on these areas:** {', '.join(weak_areas)}")
        if strong_areas:
            st.success(f"**Great job on:** {', '.join(strong_areas)}")
        
        untested_areas = [domain for domain, stats in st.session_state["user_stats"].items() if stats["total"] == 0]
        if untested_areas:
            st.info(f"**Haven't practiced yet:** {', '.join(untested_areas)}")
    
    else:
        st.info("Start practicing to see your progress!")
        if st.button("🎯 Go to Practice Mode"):
            st.switch_page("practice.py")
