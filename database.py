
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
            # Create a more comprehensive query that checks both topic and subtopic fields
            query = {
                "$or": [
                    {"topic": {"$regex": keyword, "$options": "i"}} for keyword in domain_keywords
                ] + [
                    {"subtopic": {"$regex": keyword, "$options": "i"}} for keyword in domain_keywords
                ]
            }
            
            # Debug: Print the query and check what topics exist
            print(f"Filtering with keywords: {domain_keywords}")
            print(f"Query: {query}")
            
            # Check what topics actually exist in the database
            all_topics = list(self.collection.distinct("topic"))
            all_subtopics = list(self.collection.distinct("subtopic"))
            print(f"Available topics: {all_topics}")
            print(f"Available subtopics: {all_subtopics}")
            
            # First try to get a filtered question
            questions = list(self.collection.aggregate([{"$match": query}, {"$sample": {"size": 1}}]))
            
            if questions:
                print(f"Found filtered question: {questions[0]['topic']}")
                return questions[0]
            else:
                # If no questions found for this domain, return None
                print(f"No questions found for keywords: {domain_keywords}")
                return None
        return self.get_random_question()
    
    def get_question_count(self):
        """Get total number of questions in database"""
        return self.collection.count_documents({})
