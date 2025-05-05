# MDB_Quiz_App

{
  _id:        ObjectId("..."),

  /* — CLASSIFICATION — */
  topic:      "Indexes",
  subtopic:   "Compound Indexes",  // optional
  difficulty: "Intermediate",     // Beginner | Intermediate | Advanced
  weight:     1.0,                // optional; default 1

  /* — QUESTION BODY — */
  type:       "single",           // single | multi | true_false | code
  stem:       "Which of the following statements about compound indexes is TRUE?",
  options: [
    { key: "A", text: "Order of fields does not matter." },
    { key: "B", text: "They can cover queries that include all indexed fields." },
    { key: "C", text: "They slow down equality matches more than range queries." },
    { key: "D", text: "You cannot create more than one compound index per collection." }
  ],
  answers: ["B"],
  explanation: "A compound index can *cover* a query when every field in …",

  /* — OPTIONAL AUTHORING — */
  version: 1,
  status:  "active",              // active | draft | retired
  author:  "prashanth",
  created_at: ISODate(),
  updated_at: ISODate()
}
