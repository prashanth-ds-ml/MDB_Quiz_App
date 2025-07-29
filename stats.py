
import streamlit as st

class StatsManager:
    def __init__(self):
        self.exam_domains = {
            "CRUD Operations": ["CRUD", "Insert", "Update", "Delete", "Find"],
            "Aggregation": ["Aggregation", "Pipeline", "Match", "Group", "Project"],
            "Indexing": ["Indexes", "Index", "Compound Indexes", "Text Index"],
            "Data Modeling": ["Schema", "Data Model", "Document Design", "References"],
            "Tools & Deployment": ["Tools", "Deployment", "Compass", "Atlas", "Mongosh"]
        }
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize user statistics in session state"""
        if "user_stats" not in st.session_state:
            st.session_state["user_stats"] = {
                domain: {"correct": 0, "total": 0} 
                for domain in self.exam_domains.keys()
            }
    
    def get_question_domain(self, topic):
        """Determine which exam domain a question belongs to"""
        for domain, keywords in self.exam_domains.items():
            if any(keyword.lower() in topic.lower() for keyword in keywords):
                return domain
        return "Other"
    
    def update_stats(self, domain, is_correct):
        """Update user statistics for a specific domain"""
        st.session_state["user_stats"][domain]["total"] += 1
        if is_correct:
            st.session_state["user_stats"][domain]["correct"] += 1
    
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
    
    def get_recommendations(self, domain_data):
        """Generate study recommendations based on performance"""
        weak_areas = [d["Domain"] for d in domain_data if d["Accuracy (%)"] < 70 and d["Questions Attempted"] > 0]
        strong_areas = [d["Domain"] for d in domain_data if d["Accuracy (%)"] >= 80 and d["Questions Attempted"] > 0]
        untested_areas = [domain for domain, stats in st.session_state["user_stats"].items() if stats["total"] == 0]
        
        return weak_areas, strong_areas, untested_areas
