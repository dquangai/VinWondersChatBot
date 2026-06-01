DEMO_DEFAULTS = {
    "group_size": 4,
    "travel_date": "2026-06-07",
    "location": "Hà Nội",
    "interests": ["trò chơi cảm giác mạnh", "show buổi tối", "khuyến mãi vé", "check-in"],
    "destination": "VinWonders Hà Nội / Grand Park",
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
    else:
        return f"Tool {tool_name} not found."
