from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from pymongo import MongoClient
from bson import ObjectId

# ============================================================
# UPDATED NORMALIZER (lenient for draft, strict for active)
# - Auto-migrates older docs missing `explanation`
# - Accepts Beginner/Medium/Advanced difficulty mapping
# - Flags only truly broken docs (stem/options/answers/type/etc.)
# - If status=active -> requires explanation.why_correct + takeaway
# ============================================================

ALLOWED_TYPES = {"single", "multi"}
ALLOWED_STATUS = {"active", "draft", "archived"}
ALLOWED_DIFFICULTY = {"Easy", "Intermediate", "Hard"}

REQUIRED_TOP_LEVEL = [
    "question_id", "topic", "subtopic", "difficulty", "type",
    "stem", "options", "answers",
    "version", "status", "author"
]

def now_utc():
    return datetime.now(timezone.utc)

def normalize_str(x: Any) -> str:
    if x is None:
        return ""
    s = str(x)
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s

def ensure_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]

def normalize_option_key(k: Any) -> str:
    k = normalize_str(k).upper()
    if len(k) == 1 and "A" <= k <= "Z":
        return k
    return k

def normalize_difficulty(val: Any) -> str:
    v = normalize_str(val).lower()
    mapping = {
        "beginner": "Easy",
        "easy": "Easy",
        "intermediate": "Intermediate",
        "medium": "Intermediate",
        "hard": "Hard",
        "advanced": "Hard",
    }
    return mapping.get(v, v.capitalize() if v else "")

def normalize_question(doc: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """
    Returns: (normalized_doc, warnings, errors)
    - warnings: non-fatal issues / auto-fixes
    - errors: must-fix issues (doc gets flagged)
    """
    warnings: List[str] = []
    errors: List[str] = []

    q = dict(doc)  # copy

    # --- Normalize common string fields
    for f in ["question_id", "topic", "subtopic", "difficulty", "type", "stem", "status", "author"]:
        if f in q:
            q[f] = normalize_str(q[f])

    # --- Defaults
    if "version" not in q or q["version"] in (None, ""):
        q["version"] = 1
        warnings.append("Set default version=1")

    if "status" not in q or not q["status"]:
        q["status"] = "draft"
        warnings.append("Set default status=draft")

    if q["status"] not in ALLOWED_STATUS:
        warnings.append(f"Non-standard status '{q['status']}' (allowed set: {sorted(ALLOWED_STATUS)})")

    # --- Difficulty mapping
    if q.get("difficulty"):
        q["difficulty"] = normalize_difficulty(q["difficulty"])
    else:
        q["difficulty"] = "Easy"
        warnings.append("Filled missing difficulty=Easy")

    if q["difficulty"] not in ALLOWED_DIFFICULTY:
        warnings.append(f"Difficulty '{q['difficulty']}' not in standard set {sorted(ALLOWED_DIFFICULTY)}")

    # --- Type normalization
    if q.get("type"):
        q["type"] = q["type"].lower()
    if q.get("type") not in ALLOWED_TYPES:
        errors.append(f"Invalid type '{q.get('type')}'. Allowed: {sorted(ALLOWED_TYPES)}")

    # --- timestamps (fill missing only)
    if "created_at" not in q:
        q["created_at"] = now_utc()
        warnings.append("Filled missing created_at")
    if "updated_at" not in q:
        q["updated_at"] = now_utc()
        warnings.append("Filled missing updated_at")

    # --- Options
    opts = q.get("options")
    if opts is None:
        errors.append("Missing 'options'")
        opts = []
    if not isinstance(opts, list):
        errors.append("'options' must be a list")
        opts = []

    norm_opts = []
    seen_keys = set()
    for i, opt in enumerate(opts):
        if not isinstance(opt, dict):
            errors.append(f"Option[{i}] is not an object")
            continue

        ok = normalize_option_key(opt.get("key"))
        ot = normalize_str(opt.get("text"))

        if not ok:
            errors.append(f"Option[{i}] missing key")
        if not ot:
            errors.append(f"Option[{i}] missing text")

        if ok and ok in seen_keys:
            errors.append(f"Duplicate option key: {ok}")
        if ok:
            seen_keys.add(ok)

        norm_opts.append({"key": ok, "text": ot})

    q["options"] = norm_opts

    # Must have at least 2 options
    if len(norm_opts) < 2:
        errors.append("Must have at least 2 options")

    # --- Answers
    ans = q.get("answers")
    if ans is None:
        errors.append("Missing 'answers'")
        ans = []
    ans = ensure_list(ans)
    ans = [normalize_option_key(a) for a in ans if normalize_str(a)]
    q["answers"] = ans

    opt_key_set = {o["key"] for o in norm_opts if o.get("key")}
    bad_answers = [a for a in ans if a not in opt_key_set]
    if bad_answers:
        errors.append(f"Answers not present in options: {bad_answers}")

    if q.get("type") == "single" and len(ans) != 1:
        errors.append("type=single must have exactly 1 answer")
    if q.get("type") == "multi" and len(ans) < 1:
        errors.append("type=multi must have at least 1 answer")

    # --- Stem
    if not q.get("stem"):
        errors.append("Missing/empty 'stem'")

    # --- Explanation (LENIENT for draft, STRICT for active)
    exp = q.get("explanation")

    # Auto-create explanation object if missing / invalid
    if exp is None or not isinstance(exp, dict):
        exp = {}
        warnings.append("Missing/invalid 'explanation' → auto-created")

    exp["why_correct"] = [normalize_str(x) for x in ensure_list(exp.get("why_correct")) if normalize_str(x)]
    exp["why_incorrect"] = [normalize_str(x) for x in ensure_list(exp.get("why_incorrect")) if normalize_str(x)]
    exp["takeaway"] = normalize_str(exp.get("takeaway"))

    if "mini_examples" in exp:
        exp["mini_examples"] = [normalize_str(x) for x in ensure_list(exp.get("mini_examples")) if normalize_str(x)]
    else:
        exp["mini_examples"] = []

    # Auto-fill takeaway if empty (keeps UI uniform)
    if not exp["takeaway"]:
        exp["takeaway"] = "Key rule: focus on the MongoDB behavior tested in the stem and eliminate trap options."
        warnings.append("explanation.takeaway was empty → auto-filled default")

    q["explanation"] = exp

    # Strictness: only enforce explanation completeness for ACTIVE questions
    if q.get("status") == "active":
        if not exp["why_correct"]:
            errors.append("ACTIVE question requires explanation.why_correct (non-empty)")
        if not exp["takeaway"]:
            errors.append("ACTIVE question requires explanation.takeaway (non-empty)")

    # --- Required top-level check (explanation not required here)
    for f in REQUIRED_TOP_LEVEL:
        if f not in q or q[f] in (None, "", []):
            errors.append(f"Missing/empty required field: {f}")

    return q, warnings, errors


def main():
    # 🔴 TEMP: Hardcoded URI (remove later)
    mongo_uri = "mongodb+srv://prashanth01071995:pravip2025@cluster0.xq0bvx8.mongodb.net/"

    client = MongoClient(mongo_uri)
    db = client["quiz_app"]
    col = db["questions"]

    # Process all docs (or filter)
    cursor = col.find({})

    total = ok = flagged = updated = 0

    for doc in cursor:
        total += 1
        qid = doc.get("question_id", str(doc.get("_id")))

        norm, warns, errs = normalize_question(doc)

        if errs:
            flagged += 1
            print(f"\n❌ {qid} has ERRORS:")
            print(f"  Mongo _id: {doc.get('_id')}")
            for e in errs:
                print(f"  - {e}")
            if warns:
                print("  ⚠ warnings:")
                for w in warns:
                    print(f"    - {w}")

            # Flag in DB (non-destructive)
            col.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "flagged": True,
                    "flag_reason": errs[:12],
                    "updated_at": now_utc()
                }}
            )
            continue

        ok += 1

        # Write normalized form back (safe because no errors)
        norm.pop("_id", None)
        col.update_one({"_id": doc["_id"]}, {"$set": norm})
        updated += 1

        # Optionally clear any previous flags if now OK
        col.update_one(
            {"_id": doc["_id"]},
            {"$unset": {"flagged": "", "flag_reason": ""}}
        )

        if warns:
            print(f"\n⚠ {qid} normalized with warnings:")
            print(f"  Mongo _id: {doc.get('_id')}")
            for w in warns:
                print(f"  - {w}")

    print("\n====================")
    print(f"Total: {total}")
    print(f"OK: {ok}")
    print(f"Flagged (errors): {flagged}")
    print(f"Updated (normalized): {updated}")
    print("====================")


if __name__ == "__main__":
    main()
