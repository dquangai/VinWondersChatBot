import json

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
