import json
import urllib.parse
import urllib.request


DEMO_DEFAULTS = {
    "group_size": 4,
    "travel_date": "2026-06-07",
    "location": "Hà Nội",
    "interests": ["trò chơi cảm giác mạnh", "show buổi tối", "khuyến mãi vé", "check-in"],
    "destination": "VinWonders Hà Nội / Grand Park",
}


LOCATION_COORDINATES = {
    "hà nội": ("Hà Nội", 21.0285, 105.8542),
    "ha noi": ("Hà Nội", 21.0285, 105.8542),
    "tp.hcm": ("TP.HCM", 10.8231, 106.6297),
    "tphcm": ("TP.HCM", 10.8231, 106.6297),
    "hồ chí minh": ("TP.HCM", 10.8231, 106.6297),
    "ho chi minh": ("TP.HCM", 10.8231, 106.6297),
    "sài gòn": ("TP.HCM", 10.8231, 106.6297),
    "sai gon": ("TP.HCM", 10.8231, 106.6297),
    "đà nẵng": ("Đà Nẵng", 16.0544, 108.2022),
    "da nang": ("Đà Nẵng", 16.0544, 108.2022),
    "nha trang": ("Nha Trang", 12.2388, 109.1967),
    "phú quốc": ("Phú Quốc", 10.2899, 103.9840),
    "phu quoc": ("Phú Quốc", 10.2899, 103.9840),
    "hội an": ("Hội An", 15.8801, 108.3380),
    "hoi an": ("Hội An", 15.8801, 108.3380),
    "nam hội an": ("Nam Hội An", 15.7942, 108.4145),
    "nam hoi an": ("Nam Hội An", 15.7942, 108.4145),
}


WEATHER_CODE_LABELS = {
    0: "trời quang",
    1: "ít mây",
    2: "mây rải rác",
    3: "nhiều mây",
    45: "sương mù",
    48: "sương mù đóng băng",
    51: "mưa phùn nhẹ",
    53: "mưa phùn vừa",
    55: "mưa phùn dày",
    61: "mưa nhẹ",
    63: "mưa vừa",
    65: "mưa to",
    80: "mưa rào nhẹ",
    81: "mưa rào vừa",
    82: "mưa rào mạnh",
    95: "dông",
    96: "dông kèm mưa đá nhẹ",
    99: "dông kèm mưa đá mạnh",
}


def _date_label(travel_date: str) -> str:
    if travel_date == DEMO_DEFAULTS["travel_date"]:
        return "cuối tuần"
    return travel_date


def _as_list(value, fallback: list) -> list:
    if isinstance(value, list) and value:
        return value
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return fallback


def _resolve_location(location: str):
    normalized = str(location or "").lower().strip()
    for keyword, value in LOCATION_COORDINATES.items():
        if keyword in normalized:
            return value
    return None


def get_current_weather(location: str = DEMO_DEFAULTS["location"]) -> str:
    """Kiểm tra thời tiết hiện tại tại một địa điểm phổ biến ở Việt Nam."""
    resolved = _resolve_location(location)
    if not resolved:
        return json.dumps({
            "status": "unsupported_location",
            "message": (
                "Mình chưa có tọa độ thời tiết cho địa điểm này. "
                "Bạn hãy thử hỏi với Hà Nội, TP.HCM, Đà Nẵng, Nha Trang, Phú Quốc hoặc Hội An."
            ),
            "location": location,
        }, ensure_ascii=False)

    location_name, latitude, longitude = resolved
    params = urllib.parse.urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,rain,showers,weather_code",
        "timezone": "Asia/Bangkok",
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return json.dumps({
            "status": "error",
            "message": (
                "Chưa kiểm tra được thời tiết hiện tại do không kết nối được nguồn dữ liệu thời tiết. "
                "Bạn có thể thử lại sau hoặc kiểm tra thêm trên ứng dụng thời tiết."
            ),
            "detail": str(exc),
            "location": location_name,
        }, ensure_ascii=False)

    current = payload.get("current", {})
    precipitation = float(current.get("precipitation") or 0)
    rain = float(current.get("rain") or 0)
    showers = float(current.get("showers") or 0)
    weather_code = current.get("weather_code")
    is_raining = precipitation > 0 or rain > 0 or showers > 0 or weather_code in {
        51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99
    }

    return json.dumps({
        "status": "ok",
        "location": location_name,
        "time": current.get("time"),
        "temperature_c": current.get("temperature_2m"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "precipitation_mm": precipitation,
        "rain_mm": rain,
        "showers_mm": showers,
        "weather_code": weather_code,
        "weather": WEATHER_CODE_LABELS.get(weather_code, "không rõ"),
        "is_raining": is_raining,
        "advice": (
            "Đang có mưa hoặc khả năng mưa, nên mang áo mưa/ô và ưu tiên hoạt động trong nhà."
            if is_raining
            else "Hiện chưa ghi nhận mưa tại thời điểm cập nhật, nhưng bạn vẫn nên kiểm tra lại trước khi đi."
        ),
        "source": "Open-Meteo",
    }, ensure_ascii=False)


def get_user_preferences(
    group_size: int = DEMO_DEFAULTS["group_size"],
    travel_date: str = DEMO_DEFAULTS["travel_date"],
    location: str = DEMO_DEFAULTS["location"],
    interests: list = None,
) -> str:
    """Xác định nhu cầu của người dùng gồm số lượng người, ngày đi, vị trí xuất phát và sở thích vui chơi."""
    interests = _as_list(interests, DEMO_DEFAULTS["interests"])
    return f"""Người dùng đi nhóm {group_size} người vào {travel_date}, xuất phát từ {location}. 
Nhóm thích {', '.join(interests)}.

Tóm tắt theo kịch bản: người dùng đi nhóm {group_size} người vào {_date_label(travel_date)}, xuất phát từ {location}.
Nhóm thích trò chơi cảm giác mạnh, show giải trí buổi tối, ưu đãi vé và các điểm check-in đẹp."""


def search_vinwonders_destinations(
    location: str = DEMO_DEFAULTS["location"],
    interests: list = None,
) -> str:
    """Tìm điểm VinWonders phù hợp với vị trí và sở thích."""
    interests = _as_list(interests, DEMO_DEFAULTS["interests"])
    return """Có 2 nhóm lựa chọn phù hợp:
1. VinWonders Hà Nội / Grand Park: phù hợp nếu muốn đi gần, tiết kiệm thời gian di chuyển.
2. VinWonders Nha Trang hoặc Phú Quốc: phù hợp nếu kết hợp du lịch dài ngày, có nhiều show và trải nghiệm quy mô lớn hơn.

Vì người dùng muốn đi cuối tuần và xuất phát từ Hà Nội, agent ưu tiên đề xuất VinWonders Hà Nội / Grand Park."""


def check_current_promotions(
    destination: str = DEMO_DEFAULTS["destination"],
    travel_date: str = DEMO_DEFAULTS["travel_date"],
) -> str:
    """Kiểm tra các khuyến mãi hiện tại cho điểm đến được chọn."""
    return f"""Tìm thấy một số nhóm ưu đãi liên quan cho {destination} vào {travel_date}:
- Ưu đãi vui chơi tại Grand Park.
- Ưu đãi đặt vé online hoặc trên app VinWonders.
- Combo vé theo nhóm hoặc theo mùa hè nếu còn áp dụng.
- Voucher ăn uống hoặc ưu đãi dịch vụ đi kèm tùy chương trình.

Agent cần nhắc người dùng kiểm tra điều kiện áp dụng, thời hạn khuyến mãi và giá cuối cùng trên kênh đặt vé chính thức trước khi thanh toán."""


def check_events_and_shows(
    destination: str = DEMO_DEFAULTS["destination"],
    travel_date: str = DEMO_DEFAULTS["travel_date"],
) -> str:
    """Kiểm tra sự kiện hoặc show hiện tại / sắp diễn ra trong ngày."""
    return f"""Các nội dung giải trí có thể có tại {destination} trong ngày {travel_date}:
- Show/Event theo lịch vận hành của điểm đến.
- Hoạt động check-in và mini game theo khung giờ.
- Các chương trình biểu diễn hoặc sự kiện mùa hè nếu đang áp dụng.

Lưu ý: Lịch show có thể thay đổi theo ngày, thời tiết hoặc kế hoạch vận hành. Agent cần khuyến nghị người dùng kiểm tra lại lịch show trên website/app trước khi đi."""


def build_itinerary(
    destination: str = DEMO_DEFAULTS["destination"],
    preferences: list = None,
    promotions: list = None,
    events: list = None,
) -> str:
    """Xây dựng lịch trình vui chơi trong ngày dựa trên điểm đến, sở thích, khuyến mãi và sự kiện."""
    preferences = _as_list(preferences, DEMO_DEFAULTS["interests"])
    promotions = _as_list(promotions, ["ưu đãi Grand Park", "ưu đãi đặt vé online/app", "voucher ăn uống nếu có"])
    events = _as_list(events, [f"show/event theo lịch ngày {DEMO_DEFAULTS['travel_date']}"])
    return f"""Lịch trình đề xuất tại {destination}:
- 09:00 - 10:00: Di chuyển, gửi xe và check-in cổng vào.
- 10:00 - 12:00: Chơi các trò chính hoặc trò cảm giác mạnh.
- 12:00 - 13:30: Ăn trưa, nghỉ ngơi, ưu tiên dùng voucher hoặc combo ăn uống nếu có.
- 13:30 - 16:00: Tham quan, chụp ảnh, trải nghiệm các khu check-in.
- 16:00 - 18:00: Chơi các trò nhẹ hơn, mua sắm hoặc ăn uống.
- 18:00 - 20:00: Xem show hoặc sự kiện buổi tối nếu lịch ngày hôm đó có tổ chức."""

vinwonders_tools = [
    {
        "name": "get_user_preferences",
        "description": "Xác định nhu cầu của người dùng gồm số lượng người, ngày đi, vị trí xuất phát và sở thích vui chơi.",
        "parameters": ["group_size", "travel_date", "location", "interests"]
    },
    {
        "name": "search_vinwonders_destinations",
        "description": "Tìm điểm VinWonders phù hợp với vị trí và sở thích.",
        "parameters": ["location", "interests"]
    },
    {
        "name": "check_current_promotions",
        "description": "Kiểm tra các khuyến mãi hiện tại cho điểm đến được chọn để giúp người dùng tiết kiệm chi phí.",
        "parameters": ["destination", "travel_date"]
    },
    {
        "name": "check_events_and_shows",
        "description": "Kiểm tra sự kiện hoặc show hiện tại / sắp diễn ra trong ngày người dùng dự định đi.",
        "parameters": ["destination", "travel_date"]
    },
    {
        "name": "build_itinerary",
        "description": "Xây dựng lịch trình vui chơi trong ngày dựa trên điểm đến, sở thích, khuyến mãi và sự kiện.",
        "parameters": ["destination", "preferences", "promotions", "events"]
    },
    {
        "name": "get_current_weather",
        "description": "Kiểm tra thời tiết hiện tại tại một địa điểm, ví dụ người dùng hỏi Hà Nội đang mưa không.",
        "parameters": ["location"]
    }
]


def _call_with_supported_args(func, args_dict: dict) -> str:
    supported_args = func.__code__.co_varnames[:func.__code__.co_argcount]
    filtered_args = {key: value for key, value in args_dict.items() if key in supported_args}
    return func(**filtered_args)


def execute_vinwonders_tool(tool_name: str, args_dict: dict) -> str:
    args_dict = args_dict or {}
    if tool_name == "get_user_preferences":
        return _call_with_supported_args(get_user_preferences, args_dict)
    elif tool_name == "search_vinwonders_destinations":
        return _call_with_supported_args(search_vinwonders_destinations, args_dict)
    elif tool_name == "check_current_promotions":
        return _call_with_supported_args(check_current_promotions, args_dict)
    elif tool_name == "check_events_and_shows":
        return _call_with_supported_args(check_events_and_shows, args_dict)
    elif tool_name == "build_itinerary":
        return _call_with_supported_args(build_itinerary, args_dict)
    elif tool_name == "get_current_weather":
        return _call_with_supported_args(get_current_weather, args_dict)
    else:
        return f"Tool {tool_name} not found."
