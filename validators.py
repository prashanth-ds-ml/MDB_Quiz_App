# validators.py

# Allowed keys in question documents
ALLOWED_KEYS = {
    "_id", "question_id", "stem", "topic", "subtopic",
    "options", "answers", "explanation", "difficulty",
    "author", "status", "created_at", "updated_at",
    "type", "version", "index", "operation", "document_before",
    "sample_doc", "sample_docs"
}

VALID_TOPICS = {
    "MongoDB Overview", "CRUD Operations", "Indexing", "Data Modeling",
    "Querying", "Aggregation"
}

VALID_DIFFICULTIES = {"Easy", "Medium", "Hard", "Unknown"}

def validate_keys(question_dict):
    invalid_keys = [key for key in question_dict.keys() if key not in ALLOWED_KEYS]
    if invalid_keys:
        return False, f"Invalid keys found: {invalid_keys}"
    return True, ""

def validate_topic(topic):
    if topic not in VALID_TOPICS:
        return False, f"Invalid topic: {topic}"
    return True, ""

def validate_difficulty(difficulty):
    if difficulty not in VALID_DIFFICULTIES:
        return False, f"Invalid difficulty: {difficulty}"
    return True, ""

def validate_options(options):
    if not isinstance(options, list) or len(options) == 0:
        return False, "Options must be a non-empty list"
    if not all(isinstance(opt, str) for opt in options):
        return False, "All options must be strings"
    return True, ""

def validate_answers(answers, options):
    if not isinstance(answers, list) or len(answers) == 0:
        return False, "Answers must be a non-empty list"
    for ans in answers:
        # Accept index (int) or string value matching options
        if not ((isinstance(ans, int) and 0 <= ans < len(options)) or (isinstance(ans, str) and ans in options)):
            return False, f"Invalid answer: {ans} not in options"
    return True, ""

def validate_question(question_dict):
    # Run all validations and collect errors
    errors = []
    valid, msg = validate_keys(question_dict)
    if not valid:
        errors.append(msg)

    topic = question_dict.get("topic")
    if topic:
        valid, msg = validate_topic(topic)
        if not valid:
            errors.append(msg)

    difficulty = question_dict.get("difficulty")
    if difficulty:
        valid, msg = validate_difficulty(difficulty)
        if not valid:
            errors.append(msg)

    options = question_dict.get("options")
    if options:
        valid, msg = validate_options(options)
        if not valid:
            errors.append(msg)
    else:
        errors.append("Missing options field")

    answers = question_dict.get("answers")
    if answers and options:
        valid, msg = validate_answers(answers, options)
        if not valid:
            errors.append(msg)
    else:
        errors.append("Missing answers or options field")

    if errors:
        return False, errors
    return True, []

