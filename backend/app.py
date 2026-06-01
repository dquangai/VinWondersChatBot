import json
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]


try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        env_path = ROOT_DIR / ".env"
        if not env_path.exists():
            return False

        with env_path.open("r", encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                value = value.strip()

                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]

                os.environ.setdefault(key.strip(), value)

        return True


load_dotenv()


try:
    from src.agent.react_agent import ReActAgent
except ImportError:
    from src.agent.agent import ReActAgent


from src.tools.vinwonders_tools import (
    GENERAL_DESTINATION_CATALOG,
    execute_vinwonders_tool,
    vinwonders_tools,
)


FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", ROOT_DIR / "frontend"))

if not FRONTEND_DIR.is_absolute():
    FRONTEND_DIR = ROOT_DIR / FRONTEND_DIR


HOST = os.getenv("WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("WEB_PORT", "7860"))

DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "gemini")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
CODE_VERSION = "travel-tools-direct-router-v2"

agent_lock = Lock()
agent_instance = None


LOCATION_KEYWORDS = {
    "hà nội": "Hà Nội",
    "ha noi": "Hà Nội",
    "tp.hcm": "TP.HCM",
    "tphcm": "TP.HCM",
    "hồ chí minh": "TP.HCM",
    "ho chi minh": "TP.HCM",
    "sài gòn": "TP.HCM",
    "sai gon": "TP.HCM",
    "đà nẵng": "Đà Nẵng",
    "da nang": "Đà Nẵng",
    "nha trang": "Nha Trang",
    "phú quốc": "Phú Quốc",
    "phu quoc": "Phú Quốc",
    "hội an": "Hội An",
    "hoi an": "Hội An",
    "nam hội an": "Nam Hội An",
    "nam hoi an": "Nam Hội An",
}


DESTINATION_KEYWORDS = {
    "vinwonders phú quốc": "VinWonders Phú Quốc",
    "vinwonders phu quoc": "VinWonders Phú Quốc",
    "vinwonders nha trang": "VinWonders Nha Trang",
    "vinwonders nam hội an": "VinWonders Nam Hội An",
    "vinwonders nam hoi an": "VinWonders Nam Hội An",
    "vinwonders hà nội": "VinWonders Hà Nội",
    "vinwonders ha noi": "VinWonders Hà Nội",
}


GENERAL_DESTINATION_KEYWORDS = {
    alias: info["name"]
    for info in GENERAL_DESTINATION_CATALOG.values()
    for alias in info["aliases"]
}


def get_llm_provider():
    """
    Create LLM provider based on environment variables.
    """
    provider_name = os.getenv("DEFAULT_PROVIDER", "gemini").lower()

    if provider_name == "openai":
        from src.core.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=os.getenv("DEFAULT_MODEL", "gpt-4o"),
        )

    if provider_name == "gemini":
        from src.core.gemini_provider import GeminiProvider

        return GeminiProvider(
            api_key=os.getenv("GEMINI_API_KEY"),
            model_name=os.getenv("DEFAULT_MODEL", "gemini-1.5-flash"),
        )

    if provider_name == "local":
        from src.core.local_provider import LocalProvider

        return LocalProvider(
            model_path=os.getenv("LOCAL_MODEL_PATH")
        )

    raise ValueError(f"Unknown provider: {provider_name}")


def get_agent():
    """
    Singleton agent instance.
    """
    global agent_instance

    if agent_instance is None:
        llm = get_llm_provider()

        try:
            agent_instance = ReActAgent(
                llm=llm,
                tools=vinwonders_tools,
                max_steps=10,
                verbose=False,
                answer_style="friendly_consultant",
            )
        except TypeError:
            agent_instance = ReActAgent(
                llm=llm,
                tools=vinwonders_tools,
                max_steps=10,
                verbose=False,
            )

    return agent_instance


def normalize_text(value: str) -> str:
    return str(value or "").lower().strip()


def extract_location(text: str):
    lowered = normalize_text(text)
    for keyword, location in LOCATION_KEYWORDS.items():
        if keyword in lowered:
            return location
    return None


def extract_destination(text: str):
    lowered = normalize_text(text)
    for keyword, destination in DESTINATION_KEYWORDS.items():
        if keyword in lowered:
            return destination

    location = extract_location(text)
    if location in {"Phú Quốc", "Nha Trang", "Nam Hội An", "Hà Nội"}:
        return f"VinWonders {location}"

    return None


def extract_general_destination(text: str):
    lowered = normalize_text(text)
    for keyword, destination in GENERAL_DESTINATION_KEYWORDS.items():
        if keyword in lowered:
            return destination
    return None


def extract_group_size(text: str):
    match = re.search(r"(\d+)\s*(người|bạn|thành viên)", normalize_text(text))
    if not match:
        return None

    try:
        return int(match.group(1))
    except ValueError:
        return None


def extract_duration_days(text: str):
    lowered = normalize_text(text)
    match = re.search(r"(\d+)\s*(ngày|day)", lowered)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    if "cuối tuần" in lowered or "2 ngày 1 đêm" in lowered:
        return 2
    if "3 ngày 2 đêm" in lowered:
        return 3
    if "4 ngày 3 đêm" in lowered:
        return 4

    return None


def extract_budget_level(text: str):
    lowered = normalize_text(text)
    if any(keyword in lowered for keyword in ["tiết kiệm", "giá rẻ", "rẻ", "budget", "ít tiền"]):
        return "tiết kiệm"
    if any(keyword in lowered for keyword in ["cao cấp", "premium", "thoải mái", "sang"]):
        return "premium"
    return "standard"


def is_general_travel_request(text: str) -> bool:
    lowered = normalize_text(text)
    if "vinwonders" in lowered or "vin wonders" in lowered:
        return False

    has_destination = extract_general_destination(text) is not None
    has_travel_intent = any(keyword in lowered for keyword in [
        "đi du lịch",
        "du lịch",
        "đi chơi",
        "tour",
        "lịch trình",
        "nghỉ dưỡng",
        "tư vấn",
        "muốn đi",
    ])
    return has_destination and has_travel_intent


def is_weather_request(text: str) -> bool:
    lowered = normalize_text(text)
    return any(keyword in lowered for keyword in [
        "thời tiết",
        "thoi tiet",
        "trời mưa",
        "troi mua",
        "đang mưa",
        "dang mua",
        "có mưa",
        "co mua",
        "mưa không",
        "mua khong",
        "mưa k",
        "mua k",
        "nắng không",
        "nang khong",
        "nhiệt độ",
        "nhiet do",
    ])


def is_budget_request(text: str) -> bool:
    lowered = normalize_text(text)
    return any(keyword in lowered for keyword in [
        "ngân sách",
        "chi phí",
        "bao nhiêu tiền",
        "tốn bao nhiêu",
        "dự trù",
        "budget",
        "ước tính",
    ])


def is_transport_request(text: str) -> bool:
    lowered = normalize_text(text)
    return any(keyword in lowered for keyword in [
        "di chuyển",
        "đi bằng gì",
        "bằng gì",
        "đường đi",
        "xe đưa đón",
        "shuttle",
        "taxi",
        "grab",
        "máy bay",
        "xe khách",
        "route",
    ])


def is_checklist_request(text: str) -> bool:
    lowered = normalize_text(text)
    return any(keyword in lowered for keyword in [
        "mang gì",
        "chuẩn bị gì",
        "checklist",
        "packing",
        "cần chuẩn bị",
        "đồ cần mang",
        "hành lý",
    ])


def format_vnd(value):
    try:
        return f"{int(value):,} VND".replace(",", ".")
    except (TypeError, ValueError):
        return "chưa rõ"


def format_weather_answer(data: dict) -> str:
    if data.get("status") != "ok":
        return (
            "Mình đã nhận diện đây là câu hỏi thời tiết và gọi tool thời tiết, "
            f"nhưng hiện chưa lấy được dữ liệu real-time. {data.get('message', '')}".strip()
        )

    rain_text = "có dấu hiệu mưa/dông" if data.get("is_raining") else "chưa ghi nhận mưa"
    return (
        f"Theo {data.get('source', 'nguồn thời tiết')} lúc {data.get('time')}, "
        f"{data.get('location')} hiện {rain_text}: {data.get('weather')}.\n"
        f"Nhiệt độ khoảng {data.get('temperature_c')}°C, độ ẩm {data.get('humidity_percent')}%, "
        f"lượng mưa ghi nhận {data.get('precipitation_mm')} mm.\n\n"
        f"Gợi ý: {data.get('advice', 'Bạn nên kiểm tra lại thời tiết ngay trước khi đi.')}"
    )


def format_budget_answer(data: dict) -> str:
    estimate = data.get("estimate_excluding_tickets_vnd", {})
    tips = "\n".join(f"- {tip}" for tip in data.get("saving_tips", [])[:3])
    return (
        f"Với {data.get('group_size', 'nhóm')} người đi {data.get('destination', 'VinWonders')}, "
        f"ngân sách tham khảo chưa gồm vé vào cổng khoảng "
        f"{format_vnd(estimate.get('min'))} - {format_vnd(estimate.get('max'))}.\n\n"
        f"Lưu ý: {data.get('ticket_note', 'Giá vé cần kiểm tra trên kênh chính thức.')}\n\n"
        f"Mẹo tiết kiệm:\n{tips}"
    )


def format_transport_answer(data: dict) -> str:
    routes = []
    for route in data.get("routes", [])[:3]:
        routes.append(
            f"- {route.get('mode')}: hợp với {route.get('best_for')}. "
            f"Mẹo: {route.get('tip')}"
        )

    return (
        f"Từ {data.get('from', 'nơi xuất phát')} đi {data.get('destination', 'VinWonders')}, "
        "bạn có thể chọn:\n"
        + "\n".join(routes)
        + f"\n\nGợi ý: {data.get('consultant_note', 'Nên chốt chiều về trước khi đi.')}"
    )


def format_checklist_answer(data: dict) -> str:
    sections = []
    for section in data.get("checklist", []):
        items = ", ".join(section.get("items", []))
        sections.append(f"- {section.get('category')}: {items}")

    return (
        f"Checklist chuẩn bị cho {data.get('destination', 'VinWonders')} "
        f"({data.get('travel_date', 'ngày bạn dự định đi')}):\n"
        + "\n".join(sections)
        + f"\n\nGợi ý: {data.get('consultant_note', 'Bạn nên kiểm tra lại trước ngày đi.')}"
    )


def format_general_trip_answer(data: dict) -> str:
    destination = data.get("destination", "điểm bạn muốn đi")
    apology = data.get("apology", "Mình xin lỗi, hiện mình tư vấn chuyên sâu nhất cho VinWonders.")
    message = data.get("message", "Mình cần hiểu thêm mong muốn của bạn để gợi ý phù hợp.")

    cases = []
    for item in data.get("case_suggestions", [])[:5]:
        cases.append(
            f"- {item.get('case')}: {item.get('suggestion')} "
            f"Mình cần biết: {item.get('question')}"
        )

    quick = data.get("quick_direction", {})
    quick_lines = []
    if quick.get("ideal_duration"):
        quick_lines.append(f"- Thời lượng hợp lý: {quick.get('ideal_duration')}")
    if quick.get("highlights"):
        quick_lines.append(f"- Điểm nổi bật: {', '.join(quick.get('highlights', [])[:4])}")
    if quick.get("food_suggestions"):
        quick_lines.append(f"- Ăn uống nên thử: {', '.join(quick.get('food_suggestions', [])[:3])}")

    questions = "\n".join(
        f"- {question}" for question in data.get("clarifying_questions", [])[:3]
    )

    answer = (
        f"{apology}\n\n"
        f"{message}\n\n"
        f"Để mình tư vấn đúng cho chuyến {destination}, bạn cho mình biết thêm:\n"
        f"{questions}"
    )

    if cases:
        answer += "\n\nNếu lý do của bạn là:\n" + "\n".join(cases)

    if quick_lines:
        answer += "\n\nĐịnh hướng nhanh:\n" + "\n".join(quick_lines)

    answer += "\n\nSau khi bạn trả lời 2-3 ý trên, mình sẽ gợi ý tour/lịch trình phù hợp hơn."
    return answer


def direct_tool_response(message: str):
    location = extract_location(message)
    destination = extract_destination(message)
    general_destination = extract_general_destination(message)
    group_size = extract_group_size(message)
    duration_days = extract_duration_days(message)

    if is_weather_request(message):
        if not location:
            return {
                "answer": "Bạn muốn kiểm tra thời tiết ở đâu? Ví dụ: Hà Nội, Nha Trang, Phú Quốc hoặc Đà Nẵng.",
                "trace": [],
            }

        args = {"location": location}
        observation = execute_vinwonders_tool("get_current_weather", args)
        data = try_parse_json(observation) or {}
        return {
            "answer": format_weather_answer(data),
            "trace": [{
                "step": 1,
                "type": "tool",
                "tool": "get_current_weather",
                "arguments": args,
                "observation": observation,
                "direct": True,
            }],
        }

    if is_general_travel_request(message) and general_destination:
        args = {
            "destination": general_destination,
            "departure": location or "",
            "group_size": group_size or 1,
            "duration_days": duration_days or 3,
            "budget_level": extract_budget_level(message),
            "user_message": message,
        }
        observation = execute_vinwonders_tool("plan_general_trip", args)
        data = try_parse_json(observation) or {}
        return {
            "answer": format_general_trip_answer(data),
            "trace": [{
                "step": 1,
                "type": "tool",
                "tool": "plan_general_trip",
                "arguments": args,
                "observation": observation,
                "direct": True,
            }],
        }

    if is_budget_request(message) and destination:
        args = {
            "destination": destination,
            "group_size": group_size or 1,
            "budget_level": "standard",
            "include_transport": True,
        }
        observation = execute_vinwonders_tool("estimate_trip_budget", args)
        data = try_parse_json(observation) or {}
        return {
            "answer": format_budget_answer(data),
            "trace": [{
                "step": 1,
                "type": "tool",
                "tool": "estimate_trip_budget",
                "arguments": args,
                "observation": observation,
                "direct": True,
            }],
        }

    if is_transport_request(message) and destination and location:
        args = {
            "destination": destination,
            "location": location,
            "group_size": group_size or 1,
        }
        observation = execute_vinwonders_tool("get_transportation_advice", args)
        data = try_parse_json(observation) or {}
        return {
            "answer": format_transport_answer(data),
            "trace": [{
                "step": 1,
                "type": "tool",
                "tool": "get_transportation_advice",
                "arguments": args,
                "observation": observation,
                "direct": True,
            }],
        }

    if is_checklist_request(message) and destination:
        args = {
            "destination": destination,
            "travel_date": "ngày bạn dự định đi",
        }
        observation = execute_vinwonders_tool("build_travel_checklist", args)
        data = try_parse_json(observation) or {}
        return {
            "answer": format_checklist_answer(data),
            "trace": [{
                "step": 1,
                "type": "tool",
                "tool": "build_travel_checklist",
                "arguments": args,
                "observation": observation,
                "direct": True,
            }],
        }

    return None


def build_prompt(user_message: str, history: list) -> str:
    """
    Build prompt with short conversation history.
    """
    if not history:
        return user_message

    recent_turns = history[-4:]

    history_text = "\n".join(
        f"User: {item.get('user', '')}\nAgent: {item.get('assistant', '')}"
        for item in recent_turns
        if isinstance(item, dict) and (item.get("user") or item.get("assistant"))
    )

    if not history_text:
        return user_message

    return (
        "Lịch sử hội thoại trước đó:\n"
        f"{history_text}\n\n"
        f"Người dùng mới nói: {user_message}"
    )


def get_trace_item(trace: list, tool_name: str) -> dict:
    """
    Get first trace item by tool name.
    """
    if not isinstance(trace, list):
        return {}

    for item in trace:
        if item.get("type") == "tool" and item.get("tool") == tool_name:
            return item

    return {}


def try_parse_json(value):
    """
    Try parsing string JSON safely.
    """
    if isinstance(value, dict) or isinstance(value, list):
        return value

    if not isinstance(value, str):
        return None

    text = value.strip()

    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        return None


def bullets_from_text(text: str, limit: int = 4) -> list:
    """
    Extract bullets from tool observation text.
    """
    bullets = []

    parsed = try_parse_json(text)

    if isinstance(parsed, dict):
        for key in [
            "promotions",
            "events",
            "shows",
            "items",
            "results",
            "data",
            "recommendations",
        ]:
            value = parsed.get(key)

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        name = (
                            item.get("name")
                            or item.get("title")
                            or item.get("description")
                            or item.get("summary")
                        )
                        if name:
                            bullets.append(str(name))
                    else:
                        bullets.append(str(item))

                    if len(bullets) >= limit:
                        return bullets

            elif isinstance(value, str):
                bullets.append(value)
                if len(bullets) >= limit:
                    return bullets

        for key, value in parsed.items():
            if isinstance(value, str) and value.strip():
                bullets.append(value.strip())
            elif isinstance(value, (int, float)):
                bullets.append(f"{key}: {value}")

            if len(bullets) >= limit:
                return bullets

    for line in str(text or "").splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith(("-", "•", "*")):
            bullets.append(line.lstrip("-•* ").strip())
        elif len(line) <= 140 and any(
            keyword in line.lower()
            for keyword in [
                "khuyến mãi",
                "ưu đãi",
                "show",
                "sự kiện",
                "giảm",
                "vé",
                "diễn ra",
            ]
        ):
            bullets.append(line)

        if len(bullets) >= limit:
            break

    return bullets


def find_argument_from_trace(trace: list, key: str):
    """
    Find an argument value from all tool calls in trace.
    """
    if not isinstance(trace, list):
        return None

    for item in trace:
        args = item.get("arguments", {})
        if isinstance(args, dict) and args.get(key) is not None:
            return args.get(key)

    return None


def summarize_trip(trace: list) -> dict:
    """
    Build lightweight trip summary for frontend sidebar.
    """
    preferences = get_trace_item(trace, "get_user_preferences")
    destination_search = get_trace_item(trace, "search_vinwonders_destinations")
    promotions = get_trace_item(trace, "check_current_promotions")
    events = get_trace_item(trace, "check_events_and_shows")
    itinerary = get_trace_item(trace, "build_itinerary")

    pref_args = preferences.get("arguments", {}) if isinstance(preferences, dict) else {}
    destination_args = {}

    for item in [destination_search, promotions, events, itinerary]:
        args = item.get("arguments", {}) if isinstance(item, dict) else {}

        if isinstance(args, dict):
            destination_args.update(args)

    interests = pref_args.get("interests") or find_argument_from_trace(trace, "interests") or []

    if isinstance(interests, str):
        interests = [interests]

    destination = (
        destination_args.get("destination")
        or destination_args.get("destination_name")
        or destination_args.get("name")
        or find_argument_from_trace(trace, "destination")
        or find_argument_from_trace(trace, "destination_name")
    )

    return {
        "group_size": (
            pref_args.get("group_size")
            or find_argument_from_trace(trace, "group_size")
        ),
        "travel_date": (
            pref_args.get("travel_date")
            or find_argument_from_trace(trace, "travel_date")
            or find_argument_from_trace(trace, "date")
        ),
        "location": (
            pref_args.get("location")
            or find_argument_from_trace(trace, "location")
            or find_argument_from_trace(trace, "departure")
        ),
        "interests": interests,
        "budget": (
            pref_args.get("budget")
            or find_argument_from_trace(trace, "budget")
        ),
        "destination": destination,
        "promotions": bullets_from_text(promotions.get("observation", ""), limit=4),
        "events": bullets_from_text(events.get("observation", ""), limit=4),
    }


def frontend_file(path: str) -> Path:
    """
    Resolve frontend file path safely.
    """
    if path in {"/", "/index.html"}:
        return FRONTEND_DIR / "index.html"

    candidate = (FRONTEND_DIR / path.lstrip("/")).resolve()
    frontend_root = FRONTEND_DIR.resolve()

    if candidate != frontend_root and frontend_root not in candidate.parents:
        return FRONTEND_DIR / "index.html"

    return candidate


def content_type_for(path: Path) -> str:
    """
    Return content type for static files.
    """
    suffix = path.suffix.lower()

    return {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".ico": "image/x-icon",
    }.get(suffix, "application/octet-stream")


class AppHandler(BaseHTTPRequestHandler):
    server_version = "VinWondersBackend/1.1"

    def end_headers(self):
        """
        Add basic CORS and security headers.
        """
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/health":
            self.send_json({
                "status": "ok",
                "code_version": CODE_VERSION,
                "provider": os.getenv("DEFAULT_PROVIDER", DEFAULT_PROVIDER),
                "model": os.getenv("DEFAULT_MODEL", DEFAULT_MODEL),
                "frontend_dir": str(FRONTEND_DIR),
                "tool_count": len(vinwonders_tools),
            })
            return

        file_path = frontend_file(path)

        if file_path.exists() and file_path.is_file():
            self.send_file(file_path)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/chat":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        try:
            payload = self.read_json()

            message = str(payload.get("message", "")).strip()
            history = payload.get("history", [])

            if not message:
                self.send_json(
                    {"error": "Message is required."},
                    HTTPStatus.BAD_REQUEST
                )
                return

            if not isinstance(history, list):
                history = []

            direct = direct_tool_response(message)

            if direct:
                answer = direct["answer"]
                trace = direct.get("trace", [])
                trip = summarize_trip(trace)
            else:
                prompt = build_prompt(message, history)

                with agent_lock:
                    agent = get_agent()
                    answer = agent.run(prompt)
                    trace = getattr(agent, "last_trace", [])
                    trip = summarize_trip(trace)

            self.send_json({
                "answer": answer,
                "trip": trip,
                "trace": trace if os.getenv("ENABLE_TRACE", "false").lower() == "true" else [],
                "provider": os.getenv("DEFAULT_PROVIDER", DEFAULT_PROVIDER),
                "model": os.getenv("DEFAULT_MODEL", DEFAULT_MODEL),
            })

        except json.JSONDecodeError:
            self.send_json(
                {"error": "Invalid JSON body."},
                HTTPStatus.BAD_REQUEST
            )

        except Exception as exc:
            self.send_json(
                {"error": str(exc)},
                HTTPStatus.INTERNAL_SERVER_ERROR
            )

    def read_json(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")

        if not raw_body.strip():
            return {}

        return json.loads(raw_body)

    def send_file(self, file_path: Path):
        body = file_path.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type_for(file_path))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """
        Silence default HTTP logs.
        """
        return


def main():
    """
    Start backend server.
    """
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)

    print("=" * 60)
    print("VinWonders Travel Assistant Backend")
    print("=" * 60)
    print(f"Backend đang chạy tại: http://{HOST}:{PORT}")
    print(f"Frontend directory: {FRONTEND_DIR}")
    print(f"Provider: {os.getenv('DEFAULT_PROVIDER', DEFAULT_PROVIDER)}")
    print(f"Model: {os.getenv('DEFAULT_MODEL', DEFAULT_MODEL)}")
    print("Nhấn Ctrl+C để dừng server.")
    print("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
