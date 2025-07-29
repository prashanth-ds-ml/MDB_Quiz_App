
import streamlit as st
from datetime import datetime, timedelta

import streamlit as st
from datetime import datetime, timedelta

class ExamModeManager:
    def __init__(self, user_manager=None):
        self.user_manager = user_manager
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize exam mode session state variables"""
        if "exam_mode" not in st.session_state:
            st.session_state["exam_mode"] = False
        if "exam_start_time" not in st.session_state:
            st.session_state["exam_start_time"] = None
        if "exam_questions_answered" not in st.session_state:
            st.session_state["exam_questions_answered"] = 0
        if "exam_total_questions" not in st.session_state:
            st.session_state["exam_total_questions"] = 10
        if "exam_time_limit" not in st.session_state:
            st.session_state["exam_time_limit"] = 20
        if "exam_correct_answers" not in st.session_state:
            st.session_state["exam_correct_answers"] = 0
        if "exam_number" not in st.session_state:
            st.session_state["exam_number"] = 1
    
    def start_exam(self, total_questions=10, time_limit=20):
        """Start the exam mode with custom settings"""
        st.session_state["exam_mode"] = True
        st.session_state["exam_start_time"] = datetime.now()
        st.session_state["exam_questions_answered"] = 0
        st.session_state["exam_total_questions"] = total_questions
        st.session_state["exam_time_limit"] = time_limit
        st.session_state["exam_correct_answers"] = 0
        
        # Get next exam number for user
        if self.user_manager and self.user_manager.is_logged_in():
            current_user = self.user_manager.get_current_user()
            if current_user:
                st.session_state["exam_number"] = self.user_manager.get_next_exam_number(str(current_user["_id"]))
    
    def end_exam(self):
        """End the exam mode"""
        st.session_state["exam_mode"] = False
    
    def get_remaining_time(self):
        """Calculate remaining time in exam"""
        if not st.session_state["exam_start_time"]:
            return None
        
        elapsed_time = datetime.now() - st.session_state["exam_start_time"]
        remaining_time = timedelta(minutes=st.session_state["exam_time_limit"]) - elapsed_time
        return remaining_time
    
    def is_time_up(self):
        """Check if exam time is up"""
        remaining_time = self.get_remaining_time()
        return remaining_time and remaining_time.total_seconds() <= 0
    
    def get_time_display(self):
        """Get formatted time display for UI"""
        remaining_time = self.get_remaining_time()
        if remaining_time:
            minutes_left = int(remaining_time.total_seconds() // 60)
            seconds_left = int(remaining_time.total_seconds() % 60)
            return f"{minutes_left}:{seconds_left:02d}"
        return "00:00"
    
    def next_question(self):
        """Move to next question in exam"""
        st.session_state["exam_questions_answered"] += 1
    
    def is_exam_complete(self):
        """Check if exam is complete"""
        return st.session_state["exam_questions_answered"] >= st.session_state["exam_total_questions"]
    
    def record_answer(self, is_correct):
        """Record an answer during exam"""
        if is_correct:
            st.session_state["exam_correct_answers"] += 1
    
    def save_exam_result(self):
        """Save exam result to database"""
        if not self.user_manager or not self.user_manager.is_logged_in():
            return
        
        current_user = self.user_manager.get_current_user()
        if not current_user:
            return
        
        # Calculate exam statistics
        total_questions = st.session_state["exam_total_questions"]
        correct_answers = st.session_state["exam_correct_answers"]
        accuracy = round((correct_answers / total_questions) * 100, 1) if total_questions > 0 else 0
        
        # Calculate time taken
        if st.session_state["exam_start_time"]:
            time_taken = datetime.now() - st.session_state["exam_start_time"]
            time_taken_minutes = round(time_taken.total_seconds() / 60, 1)
        else:
            time_taken_minutes = 0
        
        exam_data = {
            "exam_number": st.session_state["exam_number"],
            "score": correct_answers,
            "total_questions": total_questions,
            "time_limit": st.session_state["exam_time_limit"],
            "time_taken": time_taken_minutes,
            "accuracy": accuracy
        }
        
        self.user_manager.save_exam_result(str(current_user["_id"]), exam_data)
    
    def get_exam_summary(self):
        """Get current exam summary"""
        return {
            "exam_number": st.session_state.get("exam_number", 1),
            "questions_answered": st.session_state.get("exam_questions_answered", 0),
            "total_questions": st.session_state.get("exam_total_questions", 10),
            "correct_answers": st.session_state.get("exam_correct_answers", 0),
            "time_limit": st.session_state.get("exam_time_limit", 20)
        }
