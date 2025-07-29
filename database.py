
import streamlit as st
from pymongo import MongoClient
import random

class QuizDatabase:
    def __init__(self):
        self.mongo_uri = st.secrets["mongo_uri"]
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client["quiz_app"]
        self.collection = self.db["questions"]
    
    def get_random_question(self):
        """Get a random question from the database"""
        return self.collection.aggregate([{"$sample": {"size": 1}}]).next()
    
    def get_filtered_question(self, domain_keywords):
        """Get a random question filtered by domain keywords"""
        if domain_keywords:
            query = {"$or": [{"topic": {"$regex": keyword, "$options": "i"}} for keyword in domain_keywords]}
            questions = list(self.collection.aggregate([{"$match": query}, {"$sample": {"size": 1}}]))
            return questions[0] if questions else self.get_random_question()
        return self.get_random_question()
    
    def get_question_count(self):
        """Get total number of questions in database"""
        return self.collection.count_documents({})
