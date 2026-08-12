import logging


logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    return text.strip().lower()


def _canonical_match(mapping: dict) -> dict:
    result = {}
    for k, v in mapping.items():
        ks = str(k).strip()
        vs = str(v).strip()
        ck = ks[0].upper() if ks and ks[0].isalpha() else ks
        cv = vs[0] if vs and vs[0].isdigit() else vs
        result[ck] = cv
    return result


def grade_answer(question: dict, student_answer) -> tuple[bool, dict]:
    qtype = question.get("type", "")

    if qtype == "fill":
        expected = _normalize(str(question.get("answer", "")))
        actual = _normalize(str(student_answer or ""))
        return actual == expected, {"expected": expected, "actual": actual}

    if qtype == "true_false":
        rmap = {"true": True, "false": False, "1": True, "0": False, "对": True, "错": False, "是": True, "否": False}
        if isinstance(student_answer, str):
            student_answer = rmap.get(_normalize(student_answer))
        expected = question.get("answer", False)
        return student_answer == expected, {"expected": expected, "actual": student_answer}

    if qtype == "single":
        expected = question.get("answer")
        return student_answer == expected, {"expected": expected, "actual": student_answer}

    if qtype == "multiple":
        answers = question.get("answers", [])
        given = sorted(student_answer) if isinstance(student_answer, list) else []
        return given == sorted(answers), {"expected": sorted(answers), "actual": given}

    if qtype == "match":
        matches = question.get("matches", {})
        actual = dict(student_answer) if isinstance(student_answer, dict) else {}
        return _canonical_match(actual) == _canonical_match(matches), {
            "expected": matches, "actual": actual,
        }

    return False, {"error": f"unknown type {qtype}"}


def grade_exam(questions: list[dict], answers: list[dict], pass_score: int) -> dict:
    correct = 0
    total = len(questions)
    results = []
    submitted = {a.get("question_id"): a.get("answer") for a in answers}

    for q in questions:
        qid = q["id"]
        student_answer = submitted.get(qid)
        ok, info = grade_answer(q, student_answer)
        if ok:
            correct += 1
        results.append({"question_id": qid, "correct": ok, **info})

    score = (correct / total * 100) if total > 0 else 0
    passed = score >= pass_score

    return {
        "completed": len(answers),
        "correct": correct,
        "total": total,
        "score": round(score, 1),
        "passed": passed,
        "results": results,
    }


def summarize_results(student_results: list[dict], questions: list[dict]) -> dict:
    total_students = len(student_results)
    if total_students == 0:
        return {
            "total_students": 0,
            "average_score": 0,
            "pass_rate": 0,
            "per_question_accuracy": [],
            "knowledge_coverage": "",
        }

    scores = [r.get("score", 0) for r in student_results]
    avg = sum(scores) / total_students
    passed_count = sum(1 for r in student_results if r.get("passed"))
    pass_rate = (passed_count / total_students * 100) if total_students > 0 else 0

    per_question = []
    for q in questions:
        qid = q["id"]
        correct_count = 0
        total_answers = 0
        for r in student_results:
            for detail in r.get("results", []):
                if detail.get("question_id") == qid:
                    total_answers += 1
                    if detail.get("correct"):
                        correct_count += 1
        accuracy = (correct_count / total_answers * 100) if total_answers > 0 else 0
        per_question.append({
            "question_id": qid,
            "type": q.get("type"),
            "question": q.get("question", "")[:100],
            "accuracy": round(accuracy, 1),
            "correct": correct_count,
            "total_answers": total_answers,
        })

    return {
        "total_students": total_students,
        "average_score": round(avg, 1),
        "pass_rate": round(pass_rate, 1),
        "per_question_accuracy": per_question,
    }
