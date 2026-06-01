import json
import os
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


from src.tools.vinwonders_tools import vinwonders_tools


FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", ROOT_DIR / "frontend"))

if not FRONTEND_DIR.is_absolute():
    FRONTEND_DIR = ROOT_DIR / FRONTEND_DIR


HOST = os.getenv("WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("WEB_PORT", "7860"))

DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "gemini")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")

agent_lock = Lock()
agent_instance = None


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
                "provider": os.getenv("DEFAULT_PROVIDER", DEFAULT_PROVIDER),
                "model": os.getenv("DEFAULT_MODEL", DEFAULT_MODEL),
                "frontend_dir": str(FRONTEND_DIR),
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