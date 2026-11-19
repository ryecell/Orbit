import pytest

import ai_providers as ai

FOLDERS = ["Personal", "Math", "Science"]


def test_provider_choice_from_env():
    assert ai.provider_name({}) is None
    assert ai.provider_name({"GEMINI_API_KEY": "x"}) == "gemini"
    assert ai.provider_name({"AI_API_KEY": "x"}) == "openai"
    assert ai.provider_name({"ANTHROPIC_API_KEY": "x"}) == "anthropic"
    assert ai.provider_name({"AI_PROVIDER": "Groq-ish", "GEMINI_API_KEY": "x"}) == "groq-ish"  # explicit wins
    assert ai.provider_name({"GEMINI_API_KEY": "x", "ANTHROPIC_API_KEY": "y"}) == "gemini"


def test_extract_json_handles_fences_and_chatter():
    assert ai.extract_json('{"a": 1}') == {"a": 1}
    assert ai.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert ai.extract_json('Sure! Here you go: {"a": 1} Hope that helps') == {"a": 1}
    for bad in ["", "no json here", "[1,2]", "{broken"]:
        with pytest.raises(ai.AIError):
            ai.extract_json(bad)


def test_normalize_result_repairs_model_output():
    r = ai.normalize_result({"title": "  Notes  ", "folder": "math", "tags": "#Algebra, algebra, Limits", "summary": "ok"}, FOLDERS)
    assert r == {"title": "Notes", "folder": "Math", "tags": ["algebra", "limits"], "summary": "ok"}
    # unknown folder falls back to the first real one; junk types don't crash
    r = ai.normalize_result({"folder": "Made up", "tags": None, "title": None}, FOLDERS)
    assert r["folder"] == "Personal" and r["tags"] == [] and r["title"] == "Untitled note"
    assert len(ai.normalize_result({"tags": [f"t{i}" for i in range(20)]}, FOLDERS)["tags"]) == 5


def test_request_shapes():
    g = ai.gemini_request("m", "QUJD", "image/png", "p")
    assert g["contents"][0]["parts"][0]["inline_data"] == {"mime_type": "image/png", "data": "QUJD"}
    assert g["generationConfig"]["responseMimeType"] == "application/json"
    o = ai.openai_request("m", "QUJD", "image/png", "p")
    assert o["messages"][0]["content"][1]["image_url"]["url"] == "data:image/png;base64,QUJD"


def test_response_parsing():
    assert ai.gemini_text({"candidates": [{"content": {"parts": [{"text": "a"}, {"text": "b"}]}}]}) == "ab"
    with pytest.raises(ai.AIError):
        ai.gemini_text({"promptFeedback": {"blockReason": "SAFETY"}})
    assert ai.openai_text({"choices": [{"message": {"content": "hi"}}]}) == "hi"
    with pytest.raises(ai.AIError):
        ai.openai_text({})


def test_daily_quota():
    q = ai.DailyQuota()
    assert q.try_consume("u1", 2, 3, today="d1") is None
    assert q.try_consume("u1", 2, 3, today="d1") is None
    assert "AI scans" in q.try_consume("u1", 2, 3, today="d1")        # per-user cap
    assert q.try_consume("u2", 2, 3, today="d1") is None
    assert "quota" in q.try_consume("u3", 2, 3, today="d1")           # global cap
    q.refund("u1")
    assert q.try_consume("u1", 2, 4, today="d1") is None              # refund frees one
    assert q.try_consume("u1", 2, 3, today="d2") is None              # new day resets


def test_limits_parse_env():
    assert ai.limits({}) == (10, 200)
    assert ai.limits({"AI_DAILY_LIMIT_PER_USER": "3", "AI_DAILY_LIMIT_TOTAL": "x"}) == (3, 200)
