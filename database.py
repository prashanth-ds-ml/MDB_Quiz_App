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
            # Create a more comprehensive query that checks topic, subtopic, and stem fields
            query = {
                "$or": []
            }

            # Add searches for each keyword in multiple fields
            for keyword in domain_keywords:
                query["$or"].extend([
                    {"topic": {"$regex": keyword, "$options": "i"}},
                    {"subtopic": {"$regex": keyword, "$options": "i"}},
                    {"stem": {"$regex": keyword, "$options": "i"}},
                    {"explanation": {"$regex": keyword, "$options": "i"}}
                ])

            # Debug: Let's see what we're searching for
            print(f"Searching for keywords: {domain_keywords}")
            print(f"Query: {query}")

            # First try to get a filtered question
            questions = list(self.collection.aggregate([{"$match": query}, {"$sample": {"size": 1}}]))

            if questions:
                print(f"Found question with topic: {questions[0].get('topic', 'N/A')}")
                return questions[0]
            else:
                # Debug: Check what topics exist in the database
                all_topics = list(self.collection.distinct("topic"))
                print(f"Available topics in database: {all_topics[:10]}...")  # Show first 10
                return None
        return self.get_random_question()

    def get_question_count(self):
        """Get total number of questions in database"""
        return self.collection.count_documents({})