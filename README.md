# MDB_Quiz_App

## Question-Bank Document Shape

This is a Practice app where people who are preparing for the MongoDB Associate Python developer Exam can come and practice for the exam 

The quiz app stores each question (QA pair) as a single document in the **`questions`** collection:

```
{
  "_id": "673b1f3e9d9f000001", 
  "question_id": "DOCMODEL-Q11",

  "topic": "MongoDB Overview & Document Model",
  "subtopic": "Null vs missing field behavior",
  "difficulty": "Intermediate",

  "type": "single",
  "stem": "Given two documents — one with email: null and another with no email field — which documents will be returned by the query db.users.find({ email: null })?",
  
  "sample_docs": [
    { "_id": 1, "name": "Pranay", "email": null },
    { "_id": 2, "name": "Vipplav" }
  ],

  "options": [
    { "key": "A", "text": "Only { _id: 1, name: 'Pranay', email: null }" },
    { "key": "B", "text": "Only { _id: 2, name: 'Vipplav' }" },
    { "key": "C", "text": "Both documents (_id: 1 and _id: 2)" },
    { "key": "D", "text": "Neither of the documents" }
  ],

  "answers": ["C"],

  "explanation": {
    "why_correct": [
      "db.users.find({ email: null }) returns documents where the field is explicitly null OR where the field is missing."
    ],
    "why_incorrect": [
      "A: Incomplete because missing fields also match.",
      "B: Incomplete because explicit nulls also match.",
      "D: Incorrect — both match."
    ],
    "mini_examples": [
      "db.users.find({ email: null }) → matches both null and missing.",
      "db.users.find({ email: null, email: { $exists: true } }) → matches only explicit null."
    ],
    "takeaway": "Equality match on null also matches documents where the field does not exist."
  },

  "version": 1,
  "status": "active",
  "author": "prashanth",
  "created_at": "2025-11-02T00:00:00Z",
  "updated_at": "2025-11-02T00:00:00Z"
}
```

1. make updates to the code for exam preparation
