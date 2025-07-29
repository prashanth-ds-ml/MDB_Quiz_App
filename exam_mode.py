
import streamlit as st
from datetime import datetime, timedelta

class ExamModeManager:
    def __init__(self):
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
    
    def start_exam(self):
        """Start the exam mode"""
        st.session_state["exam_mode"] = True
        st.session_state["exam_start_time"] = datetime.now()
        st.session_state["exam_questions_answered"] = 0
    
    def end_exam(self):
        """End the exam mode"""
        st.session_state["exam_mode"] = False
    
    def get_remaining_time(self):
        """Calculate remaining time in exam (20 minutes total)"""
        if not st.session_state["exam_start_time"]:
            return None
        
        elapsed_time = datetime.now() - st.session_state["exam_start_time"]
        remaining_time = timedelta(minutes=20) - elapsed_time
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
