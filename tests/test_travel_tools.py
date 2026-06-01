import json

from backend import app as backend_app
from src.agent.agent import ReActAgent
from src.tools.vinwonders_tools import execute_vinwonders_tool, vinwonders_tools


class FakeLLM:
    model_name = "fake"

    def generate(self, prompt, system_prompt=None):
        return {"content": "Final Answer: ok"}

    def stream(self, prompt, system_prompt=None):
        yield "ok"


def load_tool(tool_name, args):
    return json.loads(execute_vinwonders_tool(tool_name, args))


def test_destination_recommendation_is_structured():
    payload = load_tool("search_vinwonders_destinations", {
        "location": "Hà Nội",
        "interests": ["check-in", "khuyến mãi vé"],
        "group_size": 4,
    })

    assert payload["status"] == "ok"
    assert payload["recommended_destination"]
    assert isinstance(payload["recommendations"], list)
    assert payload["recommendations"][0]["score"] >= payload["recommendations"][-1]["score"]


def test_budget_estimate_does_not_fake_ticket_price():
    payload = load_tool("estimate_trip_budget", {
        "destination": "VinWonders Nha Trang",
        "group_size": 3,
    })

    assert payload["status"] == "planning_estimate"
    assert "Chưa cộng giá vé" in payload["ticket_note"]
    assert payload["estimate_excluding_tickets_vnd"]["max"] > payload["estimate_excluding_tickets_vnd"]["min"]


def test_unknown_tool_returns_available_tools():
    payload = json.loads(execute_vinwonders_tool("missing_tool", {}))

    assert payload["status"] == "error"
    assert "available_tools" in payload


def test_agent_classifies_professional_travel_intents():
    agent = ReActAgent(FakeLLM(), vinwonders_tools)

    samples = {
        "Hà Nội đang mưa k": "weather_check",
        "Đi VinWonders Phú Quốc nhóm 4 người tốn bao nhiêu tiền": "budget_planning",
        "Từ Đà Nẵng đi VinWonders Nam Hội An bằng gì": "transportation_advice",
        "Đi VinWonders Nha Trang cần chuẩn bị gì": "checklist_preparation",
    }

    for text, expected in samples.items():
        agent.reset_context()
        agent._update_context_from_text(text)
        assert agent._classify_intent_lightweight(text) == expected


def test_weather_question_uses_direct_tool(monkeypatch):
    agent = ReActAgent(FakeLLM(), vinwonders_tools)

    def fake_execute(tool_name, args):
        assert tool_name == "get_current_weather"
        assert args["location"] == "Hà Nội"
        return json.dumps({
            "status": "ok",
            "location": "Hà Nội",
            "time": "2026-06-01T16:00",
            "temperature_c": 33.5,
            "humidity_percent": 65,
            "precipitation_mm": 0,
            "weather": "dông",
            "is_raining": True,
            "advice": "Nên mang ô hoặc áo mưa.",
            "source": "Open-Meteo",
        }, ensure_ascii=False)

    monkeypatch.setattr(agent, "_execute_tool", fake_execute)

    answer = agent.run("Hà Nội đang mưa k")

    assert "Open-Meteo" in answer
    assert "Hà Nội" in answer
    assert "mưa" in answer
    assert agent.last_trace[0]["direct"] is True


def test_budget_question_uses_direct_tool_not_fake_llm():
    agent = ReActAgent(FakeLLM(), vinwonders_tools)

    answer = agent.run("Đi VinWonders Phú Quốc nhóm 4 người tốn bao nhiêu tiền")

    assert "ngân sách tham khảo" in answer
    assert "chưa gồm vé" in answer
    assert "Final Answer: ok" not in answer


def test_backend_direct_weather_router(monkeypatch):
    def fake_execute(tool_name, args):
        assert tool_name == "get_current_weather"
        assert args == {"location": "Hà Nội"}
        return json.dumps({
            "status": "ok",
            "location": "Hà Nội",
            "time": "2026-06-01T16:00",
            "temperature_c": 33.5,
            "humidity_percent": 65,
            "precipitation_mm": 0,
            "weather": "dông",
            "is_raining": True,
            "advice": "Nên mang ô hoặc áo mưa.",
            "source": "Open-Meteo",
        }, ensure_ascii=False)

    monkeypatch.setattr(backend_app, "execute_vinwonders_tool", fake_execute)

    response = backend_app.direct_tool_response("Thời tiết hà nội")

    assert response is not None
    assert response["trace"][0]["tool"] == "get_current_weather"
    assert "Open-Meteo" in response["answer"]
    assert "Hà Nội" in response["answer"]


def test_general_destination_asks_needs_before_suggesting_tour():
    payload = load_tool("plan_general_trip", {
        "destination": "Đà Lạt",
        "group_size": 2,
        "duration_days": 2,
        "budget_level": "tiết kiệm",
        "user_message": "Tôi muốn đi du lịch Đà Lạt nhưng ngân sách thấp",
    })

    assert payload["status"] == "outside_vinwonders_need_clarification"
    assert payload["scope"] == "outside_vinwonders"
    assert "xin lỗi" in payload["apology"].lower()
    assert any(item["case"] == "Vấn đề ngân sách" for item in payload["case_suggestions"])


def test_backend_general_destination_router():
    response = backend_app.direct_tool_response("Tôi muốn đi du lịch Đà Lạt nhưng ngân sách thấp")

    assert response is not None
    assert response["trace"][0]["tool"] == "plan_general_trip"
    assert "Mình xin lỗi" in response["answer"]
    assert "Vấn đề ngân sách" in response["answer"]
    assert "ngân sách" in response["answer"].lower()
