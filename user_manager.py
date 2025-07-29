
import streamlit as st
from pymongo import MongoClient
from datetime import datetime

class UserManager:
    def __init__(self):
        self.mongo_uri = st.secrets["mongo_uri"]
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client["quiz_app"]
        self.users_collection = self.db["users"]
        self.user_stats_collection = self.db["user_stats"]
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize user session state"""
        if "current_user" not in st.session_state:
            st.session_state["current_user"] = None
        if "user_logged_in" not in st.session_state:
            st.session_state["user_logged_in"] = False
    
    def create_user(self, username, email):
        """Create a new user"""
        try:
            # Check if user already exists
            if self.users_collection.find_one({"username": username}):
                return False, "Username already exists"
            
            if self.users_collection.find_one({"email": email}):
                return False, "Email already exists"
            
            # Create new user
            user_doc = {
                "username": username,
                "email": email,
                "created_at": datetime.utcnow(),
                "last_login": datetime.utcnow()
            }
            
            result = self.users_collection.insert_one(user_doc)
            
            # Initialize user stats
            self.initialize_user_stats(str(result.inserted_id))
            
            return True, "User created successfully"
        except Exception as e:
            return False, f"Error creating user: {str(e)}"
    
    def login_user(self, username):
        """Login user by username"""
        user = self.users_collection.find_one({"username": username})
        if user:
            # Update last login
            self.users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            
            st.session_state["current_user"] = user
            st.session_state["user_logged_in"] = True
            return True, "Login successful"
        return False, "User not found"
    
    def logout_user(self):
        """Logout current user"""
        st.session_state["current_user"] = None
        st.session_state["user_logged_in"] = False
    
    def get_current_user(self):
        """Get current logged in user"""
        return st.session_state.get("current_user")
    
    def is_logged_in(self):
        """Check if user is logged in"""
        return st.session_state.get("user_logged_in", False)
    
    def initialize_user_stats(self, user_id):
        """Initialize stats for a new user"""
        exam_domains = {
            "CRUD Operations": {"correct": 0, "total": 0},
            "Aggregation": {"correct": 0, "total": 0},
            "Indexing": {"correct": 0, "total": 0},
            "Data Modeling": {"correct": 0, "total": 0},
            "Tools & Deployment": {"correct": 0, "total": 0}
        }
        
        stats_doc = {
            "user_id": user_id,
            "domain_stats": exam_domains,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        self.user_stats_collection.insert_one(stats_doc)
    
    def get_user_stats(self, user_id):
        """Get user statistics"""
        stats = self.user_stats_collection.find_one({"user_id": user_id})
        return stats["domain_stats"] if stats else None
    
    def update_user_stats(self, user_id, domain, is_correct):
        """Update user statistics"""
        update_query = {
            f"domain_stats.{domain}.total": {"$inc": 1},
            "updated_at": datetime.utcnow()
        }
        
        if is_correct:
            update_query[f"domain_stats.{domain}.correct"] = {"$inc": 1}
        
        self.user_stats_collection.update_one(
            {"user_id": user_id},
            {"$inc": {f"domain_stats.{domain}.total": 1, 
                     f"domain_stats.{domain}.correct": 1 if is_correct else 0},
             "$set": {"updated_at": datetime.utcnow()}}
        )
    
    def get_all_users(self):
        """Get all users (for admin purposes)"""
        return list(self.users_collection.find({}, {"password": 0}))
