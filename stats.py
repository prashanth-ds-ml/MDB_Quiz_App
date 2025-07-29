
import streamlit as st

class StatsManager:
    def __init__(self, user_manager=None):
        self.exam_domains = {
            "CRUD Operations": ["CRUD", "Insert", "Update", "Delete", "Find"],
            "Aggregation": ["Aggregation", "Pipeline", "Match", "Group", "Project"],
            "Indexing": ["Indexes", "Index", "Compound Indexes", "Text Index"],
            "Data Modeling": ["Schema", "Data Model", "Document Design", "References"],
            "Tools & Deployment": ["Tools", "Deployment", "Compass", "Atlas", "Mongosh"]
        }
        self.user_manager = user_manager
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize user statistics in session state"""
        if "user_stats" not in st.session_state:
            all_domains = list(self.exam_domains.keys()) + ["Other"]
            st.session_state["user_stats"] = {
                domain: {"correct": 0, "total": 0} 
                for domain in all_domains
            }
    
    def get_question_domain(self, topic):
        """Determine which exam domain a question belongs to"""
        for domain, keywords in self.exam_domains.items():
            if any(keyword.lower() in topic.lower() for keyword in keywords):
                return domain
        return "Other"
    
    def update_stats(self, domain, is_correct):
        """Update user statistics for a specific domain"""
        # Ensure the domain exists in user_stats
        if domain not in st.session_state["user_stats"]:
            st.session_state["user_stats"][domain] = {"correct": 0, "total": 0}
        
        # Update session state for immediate UI update
        st.session_state["user_stats"][domain]["total"] += 1
        if is_correct:
            st.session_state["user_stats"][domain]["correct"] += 1
        
        # Update database if user is logged in
        if self.user_manager and self.user_manager.is_logged_in():
            current_user = self.user_manager.get_current_user()
            if current_user:
                self.user_manager.update_user_stats(str(current_user["_id"]), domain, is_correct)
    
    def calculate_accuracy(self, domain_stats):
        """Calculate accuracy percentage for given stats"""
        if domain_stats["total"] == 0:
            return 0
        return round((domain_stats["correct"] / domain_stats["total"]) * 100, 1)
    
    def get_overall_stats(self):
        """Get overall statistics across all domains"""
        total_questions = sum([stats["total"] for stats in st.session_state["user_stats"].values()])
        total_correct = sum([stats["correct"] for stats in st.session_state["user_stats"].values()])
        overall_accuracy = self.calculate_accuracy({"correct": total_correct, "total": total_questions})
        return total_questions, total_correct, overall_accuracy
    
    def get_domain_data(self):
        """Get formatted data for domain performance visualization"""
        domain_data = []
        for domain, stats in st.session_state["user_stats"].items():
            accuracy = self.calculate_accuracy(stats)
            domain_data.append({
                "Domain": domain,
                "Questions Attempted": stats["total"],
                "Accuracy (%)": accuracy,
                "Correct": stats["correct"]
            })
        return domain_data
    
    def load_user_stats_from_db(self):
        """Load user statistics from database"""
        if self.user_manager and self.user_manager.is_logged_in():
            current_user = self.user_manager.get_current_user()
            if current_user:
                db_stats = self.user_manager.get_user_stats(str(current_user["_id"]))
                if db_stats:
                    st.session_state["user_stats"] = db_stats
    
    def get_recommendations(self, domain_data):
        """Generate study recommendations based on performance"""
        weak_areas = [d["Domain"] for d in domain_data if d["Accuracy (%)"] < 70 and d["Questions Attempted"] > 0]
        strong_areas = [d["Domain"] for d in domain_data if d["Accuracy (%)"] >= 80 and d["Questions Attempted"] > 0]
        untested_areas = [domain for domain, stats in st.session_state["user_stats"].items() if stats["total"] == 0]
        
        return weak_areas, strong_areas, untested_areas
