import streamlit as st
from database import QuizDatabase
from stats import StatsManager
from exam_mode import ExamModeManager
from question_display import QuestionDisplay
from dashboard import Dashboard

# === PAGE CONFIG ===
st.set_page_config(page_title="MongoDB Associate Exam Prep", layout="wide")

# === INITIALIZE COMPONENTS ===
db = QuizDatabase()
stats_manager = StatsManager()
exam_manager = ExamModeManager()
question_display = QuestionDisplay(stats_manager)
dashboard = Dashboard(stats_manager)

# === SESSION STATE SETUP ===
if "question_doc" not in st.session_state:
    st.session_state["question_doc"] = None
if "submitted" not in st.session_state:
    st.session_state["submitted"] = False

# === SIDEBAR NAVIGATION ===
st.sidebar.title("📚 MongoDB Associate Exam Prep")
page = st.sidebar.selectbox("Choose Mode:", ["🎯 Practice Mode", "⏱️ Exam Simulation", "📊 Progress Dashboard"])

# === PRACTICE MODE ===
if page == "🎯 Practice Mode":
    st.title("🎯 Practice Mode")

    # Topic Filter
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_domain = st.selectbox(
            "Choose Exam Domain:",
            ["All Topics"] + list(stats_manager.exam_domains.keys())
        )

    with col2:
        if st.button("🔄 New Question"):
            domain_keywords = stats_manager.exam_domains.get(selected_domain) if selected_domain != "All Topics" else None
            st.session_state["question_doc"] = db.get_filtered_question(domain_keywords)
            st.session_state["submitted"] = False
            st.rerun()

    # Get question if none exists
    if st.session_state["question_doc"] is None:
        domain_keywords = stats_manager.exam_domains.get(selected_domain) if selected_domain != "All Topics" else None
        st.session_state["question_doc"] = db.get_filtered_question(domain_keywords)

    question_doc = st.session_state["question_doc"]

    # Display Question
    selected, current_domain = question_display.display_question(question_doc, "practice")

    # Submit Button
    if st.button("✅ Submit Answer") and not st.session_state["submitted"]:
        result = question_display.process_answer(selected, question_doc, current_domain, show_explanation=True)
        if result is not None:
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
                exam_manager.start_exam()
                st.session_state["question_doc"] = db.get_random_question()
                st.session_state["submitted"] = False
                st.rerun()

    else:
        # Check if time is up
        if exam_manager.is_time_up():
            st.error("⏰ Time's up! Exam ended.")
            exam_manager.end_exam()
            st.stop()

        # Display timer and progress
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⏰ Time Remaining", exam_manager.get_time_display())

        with col2:
            st.metric("📝 Question", f"{st.session_state['exam_questions_answered'] + 1}/10")

        with col3:
            if st.button("🛑 End Exam"):
                exam_manager.end_exam()
                st.success("Exam ended successfully!")
                st.rerun()

        # Question display
        if st.session_state["question_doc"]:
            question_doc = st.session_state["question_doc"]

            st.markdown("---")
            selected, current_domain = question_display.display_question(question_doc, "exam")

            if st.button("➡️ Next Question") and not st.session_state["submitted"]:
                result = question_display.process_answer(selected, question_doc, current_domain, show_explanation=False)
                if result is not None:
                    exam_manager.next_question()

                    if exam_manager.is_exam_complete():
                        exam_manager.end_exam()
                        st.success("🎉 Exam completed!")
                        st.rerun()
                    else:
                        st.session_state["question_doc"] = db.get_random_question()
                        st.session_state["submitted"] = False
                        st.rerun()

# === PROGRESS DASHBOARD ===
elif page == "📊 Progress Dashboard":
    st.title("📊 Your Progress Dashboard")

    # Display overview metrics
    dashboard.display_overview_metrics()

    st.markdown("---")

    # Display domain performance
    domain_df = dashboard.display_domain_performance()

    # Display recommendations
    dashboard.display_recommendations(domain_df)