import json

def get_user_preferences(group_size: int, travel_date: str, location: str, interests: list) -> str:
    """Xác định nhu cầu của người dùng gồm số lượng người, ngày đi, vị trí xuất phát và sở thích vui chơi."""
    return f"""Người dùng đi nhóm {group_size} người vào {travel_date}, xuất phát từ {location}. 
Nhóm thích: {', '.join(interests)}."""

def search_vinwonders_destinations(location: str, interests: list) -> str:
    """Tìm điểm VinWonders phù hợp với vị trí và sở thích."""
    return """Có 2 nhóm lựa chọn phù hợp:
1. VinWonders Hà Nội / Grand Park: phù hợp nếu muốn đi gần, tiết kiệm thời gian di chuyển.
2. VinWonders Nha Trang hoặc Phú Quốc: phù hợp nếu kết hợp du lịch dài ngày, có nhiều show và trải nghiệm quy mô lớn hơn.
Vì xuất phát từ Hà Nội, ưu tiên đề xuất VinWonders Hà Nội / Grand Park."""

def check_current_promotions(destination: str, travel_date: str) -> str:
    """Kiểm tra các khuyến mãi hiện tại cho điểm đến được chọn."""
    return f"""Tìm thấy một số nhóm ưu đãi liên quan cho {destination} vào {travel_date}:
- Ưu đãi vui chơi tại Grand Park.
- Ưu đãi đặt vé online hoặc trên app VinWonders.
- Combo vé theo nhóm hoặc theo mùa hè nếu còn áp dụng.
- Voucher ăn uống hoặc ưu đãi dịch vụ đi kèm tùy chương trình."""

def check_events_and_shows(destination: str, travel_date: str) -> str:
    """Kiểm tra sự kiện hoặc show hiện tại / sắp diễn ra trong ngày."""
    return f"""Các nội dung giải trí có thể có tại {destination} trong ngày {travel_date}:
- Show/Event theo lịch vận hành của điểm đến.
- Hoạt động check-in và mini game theo khung giờ.
- Các chương trình biểu diễn hoặc sự kiện mùa hè nếu đang áp dụng."""

def build_itinerary(destination: str, preferences: list, promotions: list, events: list) -> str:
    """Xây dựng lịch trình vui chơi trong ngày dựa trên điểm đến, sở thích, khuyến mãi và sự kiện."""
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

def execute_vinwonders_tool(tool_name: str, args_dict: dict) -> str:
    if tool_name == "get_user_preferences":
        return get_user_preferences(**args_dict)
    elif tool_name == "search_vinwonders_destinations":
        return search_vinwonders_destinations(**args_dict)
    elif tool_name == "check_current_promotions":
        return check_current_promotions(**args_dict)
    elif tool_name == "check_events_and_shows":
        return check_events_and_shows(**args_dict)
    elif tool_name == "build_itinerary":
        return build_itinerary(**args_dict)
    else:
        return f"Tool {tool_name} not found."
