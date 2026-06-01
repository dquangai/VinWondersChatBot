import json
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


DEMO_DEFAULTS = {
    "group_size": 4,
    "travel_date": "2026-06-07",
    "location": "Hà Nội",
    "interests": ["trò chơi cảm giác mạnh", "show buổi tối", "khuyến mãi vé", "check-in"],
    "destination": "VinWonders Hà Nội",
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


DESTINATION_CATALOG = {
    "hanoi": {
        "name": "VinWonders Hà Nội",
        "aliases": ["vinwonders hà nội", "vinwonders ha noi", "hà nội", "ha noi", "wave park", "water park"],
        "region": "Miền Bắc",
        "city": "Hà Nội",
        "best_for": ["nhóm bạn", "gia đình", "đi trong ngày", "tiết kiệm thời gian"],
        "strengths": ["đi gần", "vui chơi nước", "check-in", "phù hợp cuối tuần"],
        "highlights": [
            "Phù hợp lịch trình 1 ngày nếu xuất phát từ Hà Nội.",
            "Dễ kết hợp ăn uống, cafe và check-in trong khu đô thị.",
            "Hợp với nhóm muốn đi nhanh, không cần bay xa.",
        ],
        "cautions": [
            "Một số hoạt động ngoài trời phụ thuộc thời tiết.",
            "Nên kiểm tra lịch vận hành theo mùa trước khi đi.",
        ],
        "interest_tags": ["check-in", "đi nhẹ nhàng", "ăn uống", "khuyến mãi vé"],
        "group_tags": ["friends", "family", "couple"],
        "budget_fit": "medium",
        "weather_sensitive": True,
        "shows": [
            "Hoạt động check-in theo khung giờ",
            "Mini game hoặc hoạt động cộng đồng tùy lịch vận hành",
        ],
    },
    "nha_trang": {
        "name": "VinWonders Nha Trang",
        "aliases": ["vinwonders nha trang", "nha trang"],
        "region": "Miền Trung",
        "city": "Nha Trang",
        "best_for": ["nhóm bạn", "cặp đôi", "gia đình", "du lịch biển"],
        "strengths": ["cảm giác mạnh", "show buổi tối", "check-in", "kết hợp nghỉ dưỡng"],
        "highlights": [
            "Hợp với nhóm thích trò chơi, show và không khí biển.",
            "Có nhiều góc chụp ảnh và trải nghiệm phù hợp lịch trình cả ngày.",
            "Dễ kết hợp nghỉ dưỡng Nha Trang nếu đi 2 ngày 1 đêm trở lên.",
        ],
        "cautions": [
            "Cần tính thêm thời gian di chuyển qua khu vui chơi.",
            "Nên đặt vé và kiểm tra lịch show trước ngày đi.",
        ],
        "interest_tags": ["trò chơi cảm giác mạnh", "show buổi tối", "check-in", "ăn uống"],
        "group_tags": ["friends", "family", "couple"],
        "budget_fit": "medium",
        "weather_sensitive": True,
        "shows": [
            "Show nhạc nước hoặc biểu diễn buổi tối nếu lịch vận hành có",
            "Hoạt động biểu diễn đường phố theo mùa",
        ],
    },
    "phu_quoc": {
        "name": "VinWonders Phú Quốc",
        "aliases": ["vinwonders phú quốc", "vinwonders phu quoc", "phú quốc", "phu quoc"],
        "region": "Miền Nam",
        "city": "Phú Quốc",
        "best_for": ["gia đình", "nhóm bạn", "du lịch dài ngày", "kết hợp nghỉ dưỡng"],
        "strengths": ["quy mô lớn", "show buổi tối", "check-in", "gia đình", "cảm giác mạnh"],
        "highlights": [
            "Phù hợp chuyến nghỉ dưỡng 2-3 ngày, không chỉ đi trong ngày.",
            "Hợp với nhóm muốn nhiều trải nghiệm, show và ảnh đẹp.",
            "Dễ kết hợp Grand World, Safari hoặc nghỉ dưỡng biển.",
        ],
        "cautions": [
            "Cần dự trù chi phí vé máy bay, khách sạn và di chuyển nội đảo.",
            "Nên có lịch trình sớm để tránh bị quá tải hoạt động trong một ngày.",
        ],
        "interest_tags": ["trò chơi cảm giác mạnh", "show buổi tối", "check-in", "ăn uống", "đi nhẹ nhàng"],
        "group_tags": ["friends", "family", "couple"],
        "budget_fit": "premium",
        "weather_sensitive": True,
        "shows": [
            "Show hoặc hoạt động biểu diễn theo lịch công viên",
            "Hoạt động buổi tối trong khu tổ hợp nếu còn lịch vận hành",
        ],
    },
    "nam_hoi_an": {
        "name": "VinWonders Nam Hội An",
        "aliases": ["vinwonders nam hội an", "vinwonders nam hoi an", "nam hội an", "nam hoi an", "hội an", "hoi an"],
        "region": "Miền Trung",
        "city": "Nam Hội An",
        "best_for": ["gia đình", "nhóm có trẻ nhỏ", "trải nghiệm văn hóa", "đi từ Đà Nẵng/Hội An"],
        "strengths": ["gia đình", "văn hóa", "check-in", "đi nhẹ nhàng"],
        "highlights": [
            "Hợp với gia đình hoặc nhóm muốn lịch trình nhẹ, nhiều điểm tham quan.",
            "Dễ kết hợp Hội An, Đà Nẵng trong chuyến 2-3 ngày.",
            "Phù hợp khi nhóm có trẻ nhỏ hoặc người lớn tuổi.",
        ],
        "cautions": [
            "Nên chọn khung giờ mát để tham quan ngoài trời.",
            "Nếu đi từ Đà Nẵng cần tính thời gian di chuyển hai chiều.",
        ],
        "interest_tags": ["đi nhẹ nhàng", "check-in", "ăn uống", "gia đình"],
        "group_tags": ["family", "couple", "friends"],
        "budget_fit": "medium",
        "weather_sensitive": True,
        "shows": [
            "Hoạt động văn hóa hoặc biểu diễn theo lịch vận hành",
            "Các điểm tham quan/chụp ảnh phù hợp gia đình",
        ],
    },
}


LOCATION_DESTINATION_HINTS = {
    "hà nội": ["hanoi", "nha_trang", "phu_quoc"],
    "ha noi": ["hanoi", "nha_trang", "phu_quoc"],
    "tp.hcm": ["phu_quoc", "nam_hoi_an", "nha_trang"],
    "tphcm": ["phu_quoc", "nam_hoi_an", "nha_trang"],
    "hồ chí minh": ["phu_quoc", "nam_hoi_an", "nha_trang"],
    "ho chi minh": ["phu_quoc", "nam_hoi_an", "nha_trang"],
    "sài gòn": ["phu_quoc", "nam_hoi_an", "nha_trang"],
    "sai gon": ["phu_quoc", "nam_hoi_an", "nha_trang"],
    "đà nẵng": ["nam_hoi_an", "nha_trang", "phu_quoc"],
    "da nang": ["nam_hoi_an", "nha_trang", "phu_quoc"],
    "hội an": ["nam_hoi_an", "nha_trang", "phu_quoc"],
    "hoi an": ["nam_hoi_an", "nha_trang", "phu_quoc"],
    "nha trang": ["nha_trang", "nam_hoi_an", "phu_quoc"],
    "phú quốc": ["phu_quoc", "nha_trang", "nam_hoi_an"],
    "phu quoc": ["phu_quoc", "nha_trang", "nam_hoi_an"],
}


GENERAL_DESTINATION_CATALOG = {
    "da_lat": {
        "name": "Đà Lạt",
        "aliases": ["đà lạt", "da lat"],
        "style": "nghỉ dưỡng khí hậu mát, check-in, cafe, thiên nhiên",
        "best_for": ["cặp đôi", "nhóm bạn", "gia đình thích lịch nhẹ"],
        "highlights": ["hồ Xuân Hương", "đồi chè/cafe view cao", "thác hoặc khu thiên nhiên", "chợ đêm"],
        "food": ["lẩu gà lá é", "bánh căn", "sữa đậu nành", "cafe đặc sản"],
        "ideal_duration": "3 ngày 2 đêm",
        "budget_per_day_vnd": (700000, 1500000),
        "transport": [
            "Từ TP.HCM có thể đi xe khách đêm hoặc máy bay tới sân bay Liên Khương.",
            "Trong thành phố nên thuê xe máy nếu quen đường, hoặc dùng taxi/xe công nghệ cho nhóm gia đình.",
        ],
        "cautions": ["thời tiết thay đổi nhanh", "cuối tuần dễ kẹt xe ở điểm hot", "nên đặt phòng sớm mùa cao điểm"],
    },
    "sapa": {
        "name": "Sapa",
        "aliases": ["sapa", "sa pa"],
        "style": "núi, săn mây, bản làng, nghỉ dưỡng",
        "best_for": ["nhóm bạn", "cặp đôi", "người thích thiên nhiên"],
        "highlights": ["Fansipan", "bản Cát Cát/Tả Van", "nhà thờ đá", "săn mây"],
        "food": ["thắng cố", "cá hồi/cá tầm", "đồ nướng", "rau xứ lạnh"],
        "ideal_duration": "3 ngày 2 đêm",
        "budget_per_day_vnd": (800000, 1700000),
        "transport": [
            "Từ Hà Nội đi limousine/xe giường nằm hoặc tàu tới Lào Cai rồi nối xe lên Sapa.",
            "Nên thuê xe địa phương nếu đi bản xa hoặc nhóm có trẻ nhỏ/người lớn tuổi.",
        ],
        "cautions": ["mùa mưa đường bản có thể trơn", "nên mang áo ấm", "kiểm tra thời tiết nếu muốn săn mây"],
    },
    "ha_long": {
        "name": "Hạ Long",
        "aliases": ["hạ long", "ha long", "vịnh hạ long", "vinh ha long"],
        "style": "biển, du thuyền, nghỉ dưỡng, gia đình",
        "best_for": ["gia đình", "nhóm bạn", "team building"],
        "highlights": ["vịnh Hạ Long", "du thuyền/ngắm vịnh", "Sun World nếu phù hợp", "hải sản"],
        "food": ["chả mực", "hải sản", "sam biển", "bún bề bề"],
        "ideal_duration": "2 ngày 1 đêm hoặc 3 ngày 2 đêm",
        "budget_per_day_vnd": (900000, 2200000),
        "transport": [
            "Từ Hà Nội đi cao tốc bằng xe riêng, limousine hoặc xe khách.",
            "Nếu đặt du thuyền, nên xác nhận bến đón và giờ boarding trước.",
        ],
        "cautions": ["tour vịnh phụ thuộc thời tiết", "nên đặt dịch vụ uy tín", "mùa cao điểm giá phòng tăng nhanh"],
    },
    "da_nang": {
        "name": "Đà Nẵng",
        "aliases": ["đà nẵng", "da nang"],
        "style": "biển, thành phố dễ đi, ẩm thực, kết hợp Hội An",
        "best_for": ["gia đình", "nhóm bạn", "cặp đôi"],
        "highlights": ["Mỹ Khê", "Bà Nà Hills", "Sơn Trà", "Hội An nếu có thêm thời gian"],
        "food": ["mì Quảng", "bánh tráng cuốn thịt heo", "hải sản", "bún chả cá"],
        "ideal_duration": "3 ngày 2 đêm",
        "budget_per_day_vnd": (800000, 1800000),
        "transport": [
            "Di chuyển tới Đà Nẵng bằng máy bay/tàu/xe khách tùy nơi xuất phát.",
            "Trong thành phố có thể dùng taxi/xe công nghệ, thuê xe máy hoặc thuê xe riêng nếu đi gia đình.",
        ],
        "cautions": ["mùa mưa biển động", "Bà Nà/Hội An cần tách khung thời gian rõ", "giờ cao điểm ven biển khá đông"],
    },
    "hue": {
        "name": "Huế",
        "aliases": ["huế", "hue"],
        "style": "văn hóa, di sản, ẩm thực, lịch nhẹ",
        "best_for": ["gia đình", "cặp đôi", "người thích văn hóa"],
        "highlights": ["Đại Nội", "lăng vua", "sông Hương", "chùa Thiên Mụ"],
        "food": ["bún bò Huế", "cơm hến", "bánh bèo/nậm/lọc", "chè Huế"],
        "ideal_duration": "2 ngày 1 đêm hoặc 3 ngày 2 đêm",
        "budget_per_day_vnd": (600000, 1400000),
        "transport": [
            "Có thể tới Huế bằng máy bay, tàu hỏa hoặc đi từ Đà Nẵng qua đèo Hải Vân.",
            "Trong thành phố nên dùng taxi/xe công nghệ hoặc thuê xe theo tuyến lăng tẩm.",
        ],
        "cautions": ["mùa hè khá nóng", "cần giày dễ đi bộ", "nên tránh nhồi quá nhiều điểm di tích trong một ngày"],
    },
    "ninh_binh": {
        "name": "Ninh Bình",
        "aliases": ["ninh bình", "ninh binh", "tràng an", "trang an", "tam cốc", "tam coc"],
        "style": "thiên nhiên, chèo thuyền, di sản, đi gần Hà Nội",
        "best_for": ["gia đình", "nhóm bạn", "người thích cảnh quan"],
        "highlights": ["Tràng An/Tam Cốc", "Hang Múa", "Bái Đính", "cố đô Hoa Lư"],
        "food": ["cơm cháy", "dê núi", "ốc núi", "miến lươn"],
        "ideal_duration": "1-2 ngày",
        "budget_per_day_vnd": (500000, 1200000),
        "transport": [
            "Từ Hà Nội đi xe khách, limousine, tàu hoặc xe riêng đều thuận tiện.",
            "Nên thuê xe máy/xe riêng tại địa phương nếu muốn ghép nhiều điểm.",
        ],
        "cautions": ["nắng gắt ở Hang Múa", "nên đặt vé thuyền sớm cuối tuần", "mang mũ/nước uống"],
    },
}


def _json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize(text: Any) -> str:
    return str(text or "").lower().strip()


def _safe_int(value: Any, fallback: int = 1) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else fallback
    except (TypeError, ValueError):
        return fallback


def _as_list(value: Any, fallback: Optional[List[str]] = None) -> List[str]:
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned or list(fallback or [])
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return _as_list(parsed, fallback)
            if isinstance(parsed, dict):
                for key in [
                    "interests",
                    "preferences",
                    "promotions",
                    "events",
                    "shows",
                    "recommendations",
                    "items",
                    "data",
                ]:
                    if isinstance(parsed.get(key), list):
                        return _as_list(parsed[key], fallback)
        except json.JSONDecodeError:
            pass
        return [part.strip() for part in re.split(r"[,;/\n]+", value) if part.strip()]
    return list(fallback or [])


def _date_label(travel_date: str) -> str:
    if travel_date == DEMO_DEFAULTS["travel_date"]:
        return "cuối tuần"
    return str(travel_date or "ngày bạn dự định đi")


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _resolve_location(location: str):
    normalized = _normalize(location)
    for keyword, value in LOCATION_COORDINATES.items():
        if keyword in normalized:
            return value
    return None


def _destination_key(destination: str = "", location: str = "") -> str:
    destination_text = _normalize(destination)
    location_text = _normalize(location)

    for key, info in DESTINATION_CATALOG.items():
        if any(alias in destination_text for alias in info["aliases"]):
            return key

    for key, info in DESTINATION_CATALOG.items():
        if destination_text and any(alias in destination_text for alias in info["aliases"]):
            return key

    for keyword, candidates in LOCATION_DESTINATION_HINTS.items():
        if keyword in location_text:
            return candidates[0]

    return "hanoi"


def _destination_info(destination: str = "", location: str = "") -> Dict[str, Any]:
    return DESTINATION_CATALOG[_destination_key(destination, location)]


def _general_destination_info(destination: str) -> Optional[Dict[str, Any]]:
    destination_text = _normalize(destination)
    for info in GENERAL_DESTINATION_CATALOG.values():
        if any(alias in destination_text for alias in info["aliases"]):
            return info
    return None


def _infer_general_travel_concerns(
    text: str = "",
    interests: Optional[List[str]] = None,
    budget_level: str = "",
    duration_days: Any = None,
) -> List[str]:
    source = " ".join([_normalize(text), _normalize(budget_level), " ".join(interests or []).lower()])
    concerns = []

    concern_keywords = {
        "budget": ["ngân sách", "tiết kiệm", "giá rẻ", "rẻ", "chi phí", "bao nhiêu tiền", "budget"],
        "time": ["ít ngày", "ngắn ngày", "cuối tuần", "1 ngày", "2 ngày", "không có nhiều thời gian", "time"],
        "family": ["gia đình", "trẻ nhỏ", "con nhỏ", "người lớn tuổi", "ba mẹ", "bố mẹ"],
        "couple": ["cặp đôi", "người yêu", "hẹn hò", "kỷ niệm"],
        "friends": ["nhóm bạn", "bạn bè", "team", "đông người"],
        "relax": ["nghỉ dưỡng", "chill", "thư giãn", "resort", "nghỉ ngơi"],
        "adventure": ["khám phá", "trekking", "mạo hiểm", "hoạt động ngoài trời", "trải nghiệm"],
        "food": ["ăn uống", "ẩm thực", "món ngon", "food"],
        "weather": ["mưa", "thời tiết", "nắng", "lạnh", "săn mây"],
    }

    for concern, keywords in concern_keywords.items():
        if any(keyword in source for keyword in keywords):
            concerns.append(concern)

    try:
        if int(duration_days or 0) <= 2 and int(duration_days or 0) > 0:
            concerns.append("time")
    except (TypeError, ValueError):
        pass

    return list(dict.fromkeys(concerns))


def _general_case_suggestions(destination_name: str, concerns: List[str]) -> List[Dict[str, Any]]:
    suggestions = {
        "budget": {
            "case": "Vấn đề ngân sách",
            "suggestion": f"Ưu tiên tour/plan tiết kiệm cho {destination_name}: đi ngày thường, chọn homestay/khách sạn vừa phải, ghép xe hoặc combo vé + phòng nếu có.",
            "question": "Bạn muốn giữ ngân sách khoảng bao nhiêu mỗi người?",
        },
        "time": {
            "case": "Vấn đề thời gian",
            "suggestion": f"Nếu ít thời gian, nên chọn lịch trình ngắn ngày tại {destination_name}, tập trung 2-3 điểm chính thay vì đi quá dày.",
            "question": "Bạn có bao nhiêu ngày: 1 ngày, 2 ngày 1 đêm hay 3 ngày 2 đêm?",
        },
        "family": {
            "case": "Đi gia đình/trẻ nhỏ",
            "suggestion": "Nên chọn lịch nhẹ, ít di chuyển, có điểm nghỉ giữa chặng, ưu tiên khách sạn gần trung tâm và phương tiện riêng.",
            "question": "Trong nhóm có trẻ nhỏ hoặc người lớn tuổi không?",
        },
        "couple": {
            "case": "Đi cặp đôi",
            "suggestion": "Nên ưu tiên lịch chill, điểm check-in đẹp, cafe/ăn tối có không gian riêng và không nhồi quá nhiều điểm.",
            "question": "Bạn muốn chuyến đi thiên về lãng mạn, nghỉ dưỡng hay khám phá?",
        },
        "friends": {
            "case": "Đi nhóm bạn",
            "suggestion": "Có thể chọn lịch năng động hơn: check-in, ăn uống, hoạt động buổi tối và chia chi phí theo nhóm.",
            "question": "Nhóm bạn thích vui chơi sôi động, ăn uống hay khám phá thiên nhiên hơn?",
        },
        "relax": {
            "case": "Muốn nghỉ dưỡng",
            "suggestion": "Nên giảm số điểm tham quan, chọn nơi ở tốt hơn một chút và chừa nhiều thời gian nghỉ/cafe/spa.",
            "question": "Bạn muốn nghỉ dưỡng yên tĩnh hay vẫn có vài điểm check-in nhẹ?",
        },
        "adventure": {
            "case": "Muốn khám phá/trải nghiệm",
            "suggestion": "Nên chọn tour có hoạt động ngoài trời, nhưng cần kiểm tra thời tiết và sức khỏe nhóm trước khi chốt.",
            "question": "Bạn có ưu tiên trekking, biển, núi, hoạt động nước hay trải nghiệm địa phương?",
        },
        "food": {
            "case": "Ưu tiên ẩm thực",
            "suggestion": "Có thể thiết kế lịch theo bản đồ món ăn: mỗi buổi chọn một khu ăn uống, tránh di chuyển vòng quanh quá nhiều.",
            "question": "Bạn muốn ăn đặc sản địa phương, quán nổi tiếng hay quán giá hợp lý?",
        },
        "weather": {
            "case": "Lo thời tiết",
            "suggestion": "Nên có phương án dự phòng trong nhà, lịch linh hoạt theo buổi và kiểm tra thời tiết sát ngày đi.",
            "question": "Bạn đi vào ngày nào để mình cân nhắc rủi ro mưa/nắng/lạnh?",
        },
    }

    ordered = concerns or ["budget", "time", "family", "relax"]
    return [suggestions[key] for key in ordered if key in suggestions]


def _infer_group_type(group_size: Any = None, group_type: str = "", interests: Optional[List[str]] = None) -> str:
    group_type_text = _normalize(group_type)
    interests_text = " ".join(interests or []).lower()

    if group_type_text in {"friends", "family", "couple"}:
        return group_type_text
    if _contains_any(group_type_text + " " + interests_text, ["gia đình", "trẻ", "con nhỏ", "family"]):
        return "family"
    if _contains_any(group_type_text + " " + interests_text, ["cặp đôi", "người yêu", "hẹn hò", "couple"]):
        return "couple"
    if _contains_any(group_type_text + " " + interests_text, ["nhóm bạn", "bạn bè", "team", "friends"]):
        return "friends"

    parsed_size = _safe_int(group_size, fallback=0)
    if parsed_size >= 3:
        return "friends"
    if parsed_size == 2:
        return "couple"
    return "traveler"


def _score_destination(info: Dict[str, Any], location: str, interests: List[str], group_type: str, budget: str) -> Dict[str, Any]:
    score = 50
    reasons = []
    warnings = []
    location_text = _normalize(location)
    interest_text = " ".join(interests).lower()
    budget_text = _normalize(budget)

    for keyword, candidates in LOCATION_DESTINATION_HINTS.items():
        if keyword in location_text and info["name"] == DESTINATION_CATALOG[candidates[0]]["name"]:
            score += 22
            reasons.append("điểm đến thuận tiện nhất theo nơi xuất phát")
            break

    for tag in info["interest_tags"]:
        if tag in interest_text:
            score += 10
            reasons.append(f"hợp sở thích {tag}")

    if group_type in info["group_tags"]:
        score += 8
        reasons.append("phù hợp kiểu nhóm đi cùng")

    if budget_text:
        if budget_text in ["tiết kiệm", "low", "budget"] and info["budget_fit"] == "premium":
            score -= 8
            warnings.append("cần dự trù ngân sách cao hơn vì có thể phát sinh vé máy bay/khách sạn")
        elif budget_text in ["cao cấp", "premium", "thoải mái"] and info["budget_fit"] == "premium":
            score += 6
            reasons.append("phù hợp chuyến đi nghỉ dưỡng rộng ngân sách")

    if not reasons:
        reasons.append("cân bằng giữa vui chơi, check-in và trải nghiệm trong ngày")

    return {
        "destination": info["name"],
        "score": min(score, 100),
        "best_for": info["best_for"],
        "reasons": reasons[:4],
        "highlights": info["highlights"],
        "cautions": warnings + info["cautions"][:2],
    }


def get_current_weather(location: str = DEMO_DEFAULTS["location"]) -> str:
    """Kiểm tra thời tiết hiện tại tại một địa điểm phổ biến ở Việt Nam."""
    resolved = _resolve_location(location)
    if not resolved:
        return _json({
            "status": "unsupported_location",
            "message": (
                "Mình chưa có tọa độ thời tiết cho địa điểm này. "
                "Bạn hãy thử hỏi với Hà Nội, TP.HCM, Đà Nẵng, Nha Trang, Phú Quốc hoặc Hội An."
            ),
            "location": location,
        })

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
        return _json({
            "status": "error",
            "message": (
                "Chưa kiểm tra được thời tiết hiện tại do không kết nối được nguồn dữ liệu thời tiết. "
                "Bạn có thể thử lại sau hoặc kiểm tra thêm trên ứng dụng thời tiết."
            ),
            "detail": str(exc),
            "location": location_name,
        })

    current = payload.get("current", {})
    precipitation = float(current.get("precipitation") or 0)
    rain = float(current.get("rain") or 0)
    showers = float(current.get("showers") or 0)
    weather_code = current.get("weather_code")
    is_raining = precipitation > 0 or rain > 0 or showers > 0 or weather_code in {
        51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99
    }

    return _json({
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
    })


def get_user_preferences(
    group_size: int = DEMO_DEFAULTS["group_size"],
    travel_date: str = DEMO_DEFAULTS["travel_date"],
    location: str = DEMO_DEFAULTS["location"],
    interests: list = None,
    budget: str = "",
    group_type: str = "",
) -> str:
    """Chuẩn hóa nhu cầu người dùng thành travel profile có cấu trúc."""
    interest_list = _as_list(interests, DEMO_DEFAULTS["interests"])
    parsed_group_size = _safe_int(group_size, DEMO_DEFAULTS["group_size"])
    inferred_group_type = _infer_group_type(parsed_group_size, group_type, interest_list)

    missing_fields = []
    if not travel_date:
        missing_fields.append("travel_date")
    if not location:
        missing_fields.append("location")
    if not interest_list:
        missing_fields.append("interests")

    return _json({
        "status": "ok",
        "profile": {
            "group_size": parsed_group_size,
            "group_type": inferred_group_type,
            "travel_date": travel_date,
            "location": location,
            "interests": interest_list,
            "budget": budget or "chưa rõ",
        },
        "consultant_summary": (
            f"Nhóm {parsed_group_size} người dự định đi {_date_label(travel_date)}, "
            f"xuất phát từ {location}, quan tâm {', '.join(interest_list)}."
        ),
        "missing_fields": missing_fields,
        "next_best_action": (
            "search_vinwonders_destinations"
            if not missing_fields
            else "ask_one_clarification_question"
        ),
    })


def search_vinwonders_destinations(
    location: str = DEMO_DEFAULTS["location"],
    interests: list = None,
    group_size: int = DEMO_DEFAULTS["group_size"],
    group_type: str = "",
    budget: str = "",
    travel_date: str = "",
) -> str:
    """Tìm và xếp hạng điểm VinWonders phù hợp như một tư vấn viên du lịch."""
    interest_list = _as_list(interests, DEMO_DEFAULTS["interests"])
    inferred_group_type = _infer_group_type(group_size, group_type, interest_list)

    ranked = sorted(
        [
            _score_destination(info, location, interest_list, inferred_group_type, budget)
            for info in DESTINATION_CATALOG.values()
        ],
        key=lambda item: item["score"],
        reverse=True,
    )
    recommended = ranked[0]

    return _json({
        "status": "ok",
        "destination": recommended["destination"],
        "recommended_destination": recommended["destination"],
        "travel_date": travel_date or "chưa rõ",
        "recommendations": ranked,
        "decision_factors": {
            "departure": location,
            "group_type": inferred_group_type,
            "interests": interest_list,
            "budget": budget or "chưa rõ",
        },
        "consultant_note": (
            f"Ưu tiên {recommended['destination']} vì {', '.join(recommended['reasons'])}. "
            "Nếu thông tin giá vé/lịch vận hành quan trọng, cần kiểm tra lại kênh chính thức trước khi đặt."
        ),
    })


def compare_vinwonders_options(
    location: str = DEMO_DEFAULTS["location"],
    interests: list = None,
    group_type: str = "",
    budget: str = "",
) -> str:
    """So sánh các điểm VinWonders theo nhu cầu, ưu/nhược điểm và best fit."""
    interest_list = _as_list(interests, DEMO_DEFAULTS["interests"])
    inferred_group_type = _infer_group_type(group_type=group_type, interests=interest_list)
    comparison = []

    for info in DESTINATION_CATALOG.values():
        scored = _score_destination(info, location, interest_list, inferred_group_type, budget)
        comparison.append({
            "destination": info["name"],
            "score": scored["score"],
            "best_for": info["best_for"],
            "pros": info["highlights"][:3],
            "cons_or_cautions": scored["cautions"][:3],
            "best_fit_if": scored["reasons"][:3],
        })

    comparison.sort(key=lambda item: item["score"], reverse=True)

    return _json({
        "status": "ok",
        "recommended_destination": comparison[0]["destination"],
        "comparison": comparison,
        "consultant_note": "Chọn điểm có score cao nhất nếu ưu tiên độ phù hợp; chọn Phú Quốc/Nha Trang nếu muốn chuyến nghỉ dưỡng nhiều trải nghiệm hơn.",
    })


def check_current_promotions(
    destination: str = DEMO_DEFAULTS["destination"],
    travel_date: str = DEMO_DEFAULTS["travel_date"],
    group_size: int = DEMO_DEFAULTS["group_size"],
    budget: str = "",
) -> str:
    """Gợi ý nhóm ưu đãi cần kiểm tra và cách săn vé an toàn."""
    info = _destination_info(destination)
    parsed_group_size = _safe_int(group_size, DEMO_DEFAULTS["group_size"])

    promotions = [
        {
            "name": "Ưu đãi đặt vé online/app",
            "fit": "mọi nhóm",
            "how_to_use": "kiểm tra website/app chính thức trước khi thanh toán",
            "risk_note": "giá và điều kiện áp dụng có thể đổi theo ngày",
        },
        {
            "name": "Combo vé + ăn uống/dịch vụ",
            "fit": "nhóm muốn kiểm soát chi phí trong ngày",
            "how_to_use": "so sánh combo với mua lẻ theo nhu cầu thực tế",
            "risk_note": "cần xem kỹ thời hạn dùng voucher và điểm áp dụng",
        },
    ]

    if parsed_group_size >= 4:
        promotions.append({
            "name": "Ưu đãi nhóm hoặc gói gia đình",
            "fit": f"nhóm {parsed_group_size} người",
            "how_to_use": "tìm gói theo số lượng người trước khi mua vé lẻ",
            "risk_note": "có thể yêu cầu mua cùng lúc hoặc đi cùng ngày",
        })

    if _normalize(budget) in ["tiết kiệm", "low", "budget", "vé rẻ"]:
        promotions.append({
            "name": "Mẹo tiết kiệm",
            "fit": "người dùng ưu tiên chi phí thấp",
            "how_to_use": "đặt sớm, tránh ngày cao điểm, kiểm tra mã giảm giá ngân hàng/ví điện tử",
            "risk_note": "không nên mua vé từ nguồn không rõ uy tín",
        })

    return _json({
        "status": "reference_data",
        "destination": info["name"],
        "travel_date": travel_date,
        "promotions": promotions,
        "booking_tips": [
            "So sánh giá cuối cùng sau phí trước khi thanh toán.",
            "Chụp lại điều kiện voucher, hạn dùng và chính sách đổi/hủy.",
            "Ưu tiên kênh chính thức hoặc đại lý uy tín.",
        ],
        "disclaimer": "Tool không thay thế dữ liệu giá vé real-time; cần kiểm tra lại kênh chính thức VinWonders trước khi đặt.",
    })


def check_events_and_shows(
    destination: str = DEMO_DEFAULTS["destination"],
    travel_date: str = DEMO_DEFAULTS["travel_date"],
    interests: list = None,
) -> str:
    """Gợi ý show/sự kiện nên kiểm tra theo điểm đến và sở thích."""
    info = _destination_info(destination)
    interest_list = _as_list(interests, [])
    wants_evening = _contains_any(" ".join(interest_list).lower(), ["show", "buổi tối", "pháo hoa", "nhạc nước"])

    events = [
        {
            "name": show,
            "best_time": "chiều/tối" if wants_evening else "theo lịch vận hành trong ngày",
            "planning_tip": "kiểm tra khung giờ ngay khi tới cổng hoặc trên app/website chính thức",
        }
        for show in info["shows"]
    ]

    if "check-in" in " ".join(interest_list).lower():
        events.append({
            "name": "Khung giờ check-in ánh sáng đẹp",
            "best_time": "sáng sớm hoặc sau 16:00",
            "planning_tip": "ưu tiên chụp ảnh trước khi chơi các hoạt động dễ ướt/mệt",
        })

    return _json({
        "status": "reference_data",
        "destination": info["name"],
        "travel_date": travel_date,
        "events": events,
        "show_strategy": [
            "Chốt 1 show chính trước, sau đó xếp trò chơi quanh khung giờ đó.",
            "Có mặt trước show 15-30 phút nếu đi cuối tuần hoặc nhóm đông.",
            "Chuẩn bị phương án thay thế nếu show ngoài trời bị ảnh hưởng bởi thời tiết.",
        ],
        "disclaimer": "Lịch show/sự kiện có thể thay đổi theo ngày, thời tiết và kế hoạch vận hành.",
    })


def estimate_trip_budget(
    destination: str = DEMO_DEFAULTS["destination"],
    group_size: int = DEMO_DEFAULTS["group_size"],
    budget_level: str = "standard",
    include_transport: bool = True,
) -> str:
    """Ước tính ngân sách lập kế hoạch, không thay thế bảng giá chính thức."""
    info = _destination_info(destination)
    size = _safe_int(group_size, DEMO_DEFAULTS["group_size"])
    level = _normalize(budget_level)

    meal_band = (120000, 220000) if level in ["tiết kiệm", "budget", "low"] else (180000, 350000)
    snack_band = (50000, 120000)
    local_transport_band = (120000, 450000) if include_transport else (0, 0)
    buffer_band = (100000, 250000)

    total_min = size * (meal_band[0] + snack_band[0]) + local_transport_band[0] + buffer_band[0]
    total_max = size * (meal_band[1] + snack_band[1]) + local_transport_band[1] + buffer_band[1]

    return _json({
        "status": "planning_estimate",
        "destination": info["name"],
        "group_size": size,
        "currency": "VND",
        "ticket_note": "Chưa cộng giá vé vì giá thay đổi theo kênh bán, ngày đi và chương trình khuyến mãi.",
        "estimate_excluding_tickets_vnd": {
            "min": total_min,
            "max": total_max,
        },
        "items": [
            {"name": "Ăn chính", "per_person_range_vnd": meal_band},
            {"name": "Nước/ăn nhẹ", "per_person_range_vnd": snack_band},
            {"name": "Di chuyển nội đô/địa phương", "group_range_vnd": local_transport_band},
            {"name": "Dự phòng phát sinh", "group_range_vnd": buffer_band},
        ],
        "saving_tips": [
            "Mua vé sớm hoặc canh combo chính thức.",
            "Đi nhóm nên so sánh gói combo với mua lẻ.",
            "Mang nước/đồ cá nhân theo đúng quy định điểm đến để giảm phát sinh.",
        ],
    })


def get_transportation_advice(
    destination: str = DEMO_DEFAULTS["destination"],
    location: str = DEMO_DEFAULTS["location"],
    group_size: int = DEMO_DEFAULTS["group_size"],
) -> str:
    """Tư vấn cách di chuyển theo nơi xuất phát, điểm đến và quy mô nhóm."""
    info = _destination_info(destination, location)
    size = _safe_int(group_size, DEMO_DEFAULTS["group_size"])
    location_text = _normalize(location)

    if info["city"].lower() in location_text:
        routes = [
            {
                "mode": "Taxi/xe công nghệ",
                "best_for": "nhóm nhỏ muốn linh hoạt",
                "tip": "đặt xe chiều về sớm nếu ra về sau show tối",
            },
            {
                "mode": "Xe cá nhân",
                "best_for": "gia đình hoặc nhóm có nhiều đồ",
                "tip": "kiểm tra bãi gửi xe, điểm đón trả và giờ đóng cổng",
            },
        ]
    elif info["name"] in ["VinWonders Phú Quốc", "VinWonders Nha Trang"]:
        routes = [
            {
                "mode": "Máy bay + xe đưa đón/taxi",
                "best_for": "chuyến 2 ngày 1 đêm trở lên",
                "tip": "không nên xếp lịch công viên quá sát giờ hạ cánh",
            },
            {
                "mode": "Combo khách sạn + vé + đưa đón",
                "best_for": "nhóm muốn giảm khâu tự đặt",
                "tip": "so sánh tổng giá cuối cùng với tự đặt từng phần",
            },
        ]
    else:
        routes = [
            {
                "mode": "Xe riêng/xe hợp đồng",
                "best_for": f"nhóm {size} người cần chủ động giờ đi về",
                "tip": "chốt giờ đón trước, nhất là khi xem show tối",
            },
            {
                "mode": "Xe khách/tour ghép",
                "best_for": "người muốn tiết kiệm chi phí di chuyển",
                "tip": "kiểm tra điểm đón, điểm trả và giờ về trước khi đặt",
            },
        ]

    return _json({
        "status": "ok",
        "from": location,
        "destination": info["name"],
        "group_size": size,
        "routes": routes,
        "consultant_note": "Nên chốt phương án chiều về trước khi đi, đặc biệt nếu lịch có show buổi tối hoặc trẻ nhỏ.",
    })


def build_travel_checklist(
    destination: str = DEMO_DEFAULTS["destination"],
    travel_date: str = DEMO_DEFAULTS["travel_date"],
    group_type: str = "",
    interests: list = None,
    weather_condition: str = "",
) -> str:
    """Tạo checklist chuẩn bị trước chuyến đi."""
    info = _destination_info(destination)
    interest_list = _as_list(interests, DEMO_DEFAULTS["interests"])
    inferred_group_type = _infer_group_type(group_type=group_type, interests=interest_list)
    weather_text = _normalize(weather_condition)

    checklist = [
        {"category": "Vé và giấy tờ", "items": ["vé/QR đặt chỗ", "CCCD hoặc giấy tờ cần thiết", "ảnh chụp điều kiện voucher"]},
        {"category": "Đồ cá nhân", "items": ["pin dự phòng", "kem chống nắng", "mũ/nón", "chai nước theo quy định"]},
        {"category": "Lịch trình", "items": ["lưu giờ mở cửa", "chọn 1-2 show ưu tiên", "đặt điểm hẹn nếu đi nhóm đông"]},
    ]

    if info["weather_sensitive"] or "mưa" in weather_text or "dông" in weather_text:
        checklist.append({"category": "Phòng thời tiết", "items": ["áo mưa mỏng/ô", "túi chống nước", "dép/sandal dễ khô"]})

    if _contains_any(" ".join(interest_list).lower(), ["nước", "water", "bơi"]):
        checklist.append({"category": "Hoạt động nước", "items": ["đồ bơi", "khăn nhanh khô", "túi đựng đồ ướt"]})

    if inferred_group_type == "family":
        checklist.append({"category": "Gia đình/trẻ nhỏ", "items": ["đồ ăn nhẹ phù hợp", "thuốc cá nhân", "áo khoác mỏng", "ảnh trẻ nhỏ phòng lạc"]})

    return _json({
        "status": "ok",
        "destination": info["name"],
        "travel_date": travel_date or "ngày bạn dự định đi",
        "checklist": checklist,
        "consultant_note": "Checklist nên được rà lại trước ngày đi 1 ngày vì thời tiết và lịch vận hành có thể thay đổi.",
    })


def build_itinerary(
    destination: str = DEMO_DEFAULTS["destination"],
    preferences: list = None,
    promotions: list = None,
    events: list = None,
    travel_date: str = DEMO_DEFAULTS["travel_date"],
    group_size: int = DEMO_DEFAULTS["group_size"],
    interests: list = None,
    pace: str = "balanced",
    weather_condition: str = "",
) -> str:
    """Xây dựng lịch trình vui chơi trong ngày dựa trên profile, thời tiết và ưu tiên trải nghiệm."""
    info = _destination_info(destination)
    preference_list = _as_list(preferences, [])
    interest_list = _as_list(interests, preference_list or DEMO_DEFAULTS["interests"])
    event_list = _as_list(events, info["shows"])
    promotion_list = _as_list(promotions, ["kiểm tra ưu đãi online/app", "combo ăn uống nếu phù hợp"])
    interest_text = " ".join(interest_list).lower()
    weather_text = _normalize(weather_condition)
    rainy = "mưa" in weather_text or "dông" in weather_text

    morning_focus = "các trò nổi bật và khu ít phải xếp hàng"
    if "trò chơi cảm giác mạnh" in interest_text:
        morning_focus = "trò cảm giác mạnh trước khi trời nắng/mệt"
    elif "check-in" in interest_text:
        morning_focus = "check-in các điểm đẹp trước khi đông khách"

    afternoon_focus = "tham quan, ăn uống và trải nghiệm nhẹ"
    if rainy:
        afternoon_focus = "ưu tiên khu trong nhà/khu có mái che và nghỉ ăn uống"

    evening_focus = "show hoặc hoạt động buổi tối"
    if not event_list:
        evening_focus = "ăn tối, mua sắm nhẹ và ra về linh hoạt"

    itinerary = [
        {
            "time": "08:30 - 09:30",
            "focus": "đến nơi và vào cổng",
            "actions": ["di chuyển sớm", "đổi/vào vé", "chụp ảnh cổng", "kiểm tra lịch show trong ngày"],
        },
        {
            "time": "09:30 - 12:00",
            "focus": morning_focus,
            "actions": ["chơi 2-3 hoạt động ưu tiên", "xếp hàng trò hot trước", "giữ sức nếu đi cả ngày"],
        },
        {
            "time": "12:00 - 13:30",
            "focus": "ăn trưa và hồi sức",
            "actions": ["dùng combo/voucher nếu có", "uống đủ nước", "chốt lịch buổi chiều"],
        },
        {
            "time": "13:30 - 16:30",
            "focus": afternoon_focus,
            "actions": ["tham quan khu còn lại", "chụp ảnh", "chơi hoạt động nhẹ", "nghỉ giữa chặng"],
        },
        {
            "time": "16:30 - 18:00",
            "focus": "khung giờ đẹp cho ảnh và hoạt động ngoài trời",
            "actions": ["quay lại điểm check-in đẹp", "ăn nhẹ", "chuẩn bị vị trí xem show nếu có"],
        },
        {
            "time": "18:00 - 20:00",
            "focus": evening_focus,
            "actions": [event_list[0] if event_list else "ra về linh hoạt", "đặt xe chiều về sớm", "kiểm tra đồ cá nhân"],
        },
    ]

    return _json({
        "status": "ok",
        "destination": info["name"],
        "travel_date": travel_date,
        "group_size": _safe_int(group_size, DEMO_DEFAULTS["group_size"]),
        "pace": pace,
        "itinerary": itinerary,
        "promotion_usage": promotion_list[:3],
        "rainy_day_adjustments": [
            "đổi các hoạt động ngoài trời sang khung ít mưa",
            "ưu tiên ăn uống, khu trong nhà hoặc điểm có mái che",
            "theo dõi thông báo vận hành nếu có dông/mưa lớn",
        ] if rainy else [],
        "consultant_tips": [
            "Không nên nhồi quá nhiều show/trò trong một ngày.",
            "Chốt 3 trải nghiệm ưu tiên trước, phần còn lại để linh hoạt.",
            "Kiểm tra lại lịch vận hành và giá vé chính thức trước khi đi.",
        ],
    })


def plan_general_trip(
    destination: str,
    departure: str = "",
    group_size: int = 1,
    travel_date: str = "",
    duration_days: int = 3,
    interests: list = None,
    budget_level: str = "standard",
    user_message: str = "",
) -> str:
    """Xử lý yêu cầu du lịch ngoài VinWonders theo hướng hỏi nhu cầu trước."""
    info = _general_destination_info(destination)
    interest_list = _as_list(interests, [])
    size = _safe_int(group_size, 1)
    days = _safe_int(duration_days, 3)
    concerns = _infer_general_travel_concerns(user_message, interest_list, budget_level, duration_days)

    if not info:
        return _json({
            "status": "outside_vinwonders_need_clarification",
            "scope": "outside_vinwonders",
            "destination": destination,
            "apology": "Mình xin lỗi, hiện mình tư vấn chuyên sâu nhất cho VinWonders.",
            "message": "Tuy vậy mình vẫn có thể hỗ trợ định hướng chuyến đi nếu bạn cho mình biết lý do và mong muốn chính.",
            "clarifying_questions": [
                "Bạn muốn đổi sang điểm này vì ngân sách, thời gian, khoảng cách, thời tiết hay sở thích trải nghiệm?",
                "Bạn đi mấy người, đi mấy ngày và xuất phát từ đâu?",
                "Bạn muốn ưu tiên nghỉ dưỡng, vui chơi, ẩm thực, check-in hay khám phá?",
            ],
            "case_suggestions": _general_case_suggestions(destination or "điểm bạn muốn đi", concerns),
            "supported_destinations": [item["name"] for item in GENERAL_DESTINATION_CATALOG.values()],
        })

    min_day, max_day = info["budget_per_day_vnd"]
    if _normalize(budget_level) in {"tiết kiệm", "budget", "low"}:
        min_day = int(min_day * 0.8)
        max_day = int(max_day * 0.85)
    elif _normalize(budget_level) in {"cao cấp", "premium", "thoải mái"}:
        min_day = int(min_day * 1.25)
        max_day = int(max_day * 1.6)

    return _json({
        "status": "outside_vinwonders_need_clarification",
        "scope": "outside_vinwonders",
        "apology": "Mình xin lỗi, hiện mình tư vấn chuyên sâu nhất cho VinWonders.",
        "message": (
            f"Nếu bạn muốn đi {info['name']}, mình cần hiểu lý do và mong muốn chính để gợi ý đúng hơn."
        ),
        "destination": info["name"],
        "departure": departure or "chưa rõ",
        "group_size": size,
        "travel_date": travel_date or "chưa rõ",
        "duration_days": days,
        "style": info["style"],
        "best_for": info["best_for"],
        "interests": interest_list,
        "clarifying_questions": [
            "Bạn chọn điểm này vì ngân sách, thời gian, khoảng cách, thời tiết hay sở thích riêng?",
            "Bạn muốn đi mấy ngày và khoảng ngân sách mỗi người là bao nhiêu?",
            "Nhóm đi cùng là gia đình, cặp đôi, nhóm bạn hay có trẻ nhỏ/người lớn tuổi?",
        ],
        "case_suggestions": _general_case_suggestions(info["name"], concerns),
        "quick_direction": {
            "highlights": info["highlights"][:4],
            "food_suggestions": info["food"][:4],
            "transport": info["transport"][:2],
            "ideal_duration": info["ideal_duration"],
        },
        "budget_reference_vnd": {
            "per_person_total_min": min_day * days,
            "per_person_total_max": max_day * days,
            "group_total_min": min_day * days * size,
            "group_total_max": max_day * days * size,
            "note": "Ước tính tham khảo cho ăn uống, di chuyển nội địa/ngày và lưu trú phổ thông; chưa thay thế giá vé máy bay/khách sạn real-time.",
        },
        "cautions": info["cautions"],
        "consultant_note": (
            "Không chốt tour ngay khi thiếu nhu cầu. Hãy hỏi lý do đi, ràng buộc ngân sách/thời gian "
            "và kiểu trải nghiệm trước, rồi mới đề xuất tour phù hợp."
        ),
    })


vinwonders_tools = [
    {
        "name": "get_user_preferences",
        "description": "Chuẩn hóa nhu cầu người dùng thành travel profile gồm nhóm đi, ngày đi, nơi xuất phát, sở thích và ngân sách.",
        "parameters": ["group_size", "travel_date", "location", "interests", "budget", "group_type"],
    },
    {
        "name": "search_vinwonders_destinations",
        "description": "Xếp hạng và gợi ý điểm VinWonders phù hợp theo nơi xuất phát, sở thích, nhóm đi và ngân sách.",
        "parameters": ["location", "interests", "group_size", "group_type", "budget", "travel_date"],
    },
    {
        "name": "compare_vinwonders_options",
        "description": "So sánh nhiều điểm VinWonders bằng ưu/nhược điểm, score phù hợp và best-fit recommendation.",
        "parameters": ["location", "interests", "group_type", "budget"],
    },
    {
        "name": "check_current_promotions",
        "description": "Gợi ý nhóm ưu đãi, combo, mẹo săn vé và checklist xác minh trước khi thanh toán.",
        "parameters": ["destination", "travel_date", "group_size", "budget"],
    },
    {
        "name": "check_events_and_shows",
        "description": "Gợi ý show/sự kiện nên kiểm tra theo điểm đến, ngày đi và sở thích.",
        "parameters": ["destination", "travel_date", "interests"],
    },
    {
        "name": "estimate_trip_budget",
        "description": "Ước tính ngân sách lập kế hoạch cho ăn uống, di chuyển địa phương và phát sinh, không thay thế giá vé chính thức.",
        "parameters": ["destination", "group_size", "budget_level", "include_transport"],
    },
    {
        "name": "get_transportation_advice",
        "description": "Tư vấn cách di chuyển theo nơi xuất phát, điểm đến và quy mô nhóm.",
        "parameters": ["destination", "location", "group_size"],
    },
    {
        "name": "build_travel_checklist",
        "description": "Tạo checklist chuẩn bị trước chuyến đi theo điểm đến, ngày đi, nhóm đi, sở thích và thời tiết.",
        "parameters": ["destination", "travel_date", "group_type", "interests", "weather_condition"],
    },
    {
        "name": "build_itinerary",
        "description": "Xây dựng lịch trình vui chơi trong ngày dựa trên điểm đến, sở thích, ưu đãi, show, thời tiết và pace.",
        "parameters": ["destination", "preferences", "promotions", "events", "travel_date", "group_size", "interests", "pace", "weather_condition"],
    },
    {
        "name": "get_current_weather",
        "description": "Kiểm tra thời tiết hiện tại tại một địa điểm, ví dụ người dùng hỏi Hà Nội đang mưa không.",
        "parameters": ["location"],
    },
    {
        "name": "plan_general_trip",
        "description": "Tư vấn chuyến du lịch ngoài hệ VinWonders cho các điểm phổ biến như Đà Lạt, Sapa, Hạ Long, Đà Nẵng, Huế, Ninh Bình.",
        "parameters": ["destination", "departure", "group_size", "travel_date", "duration_days", "interests", "budget_level"],
    },
]


TOOL_FUNCTIONS = {
    "get_user_preferences": get_user_preferences,
    "search_vinwonders_destinations": search_vinwonders_destinations,
    "compare_vinwonders_options": compare_vinwonders_options,
    "check_current_promotions": check_current_promotions,
    "check_events_and_shows": check_events_and_shows,
    "estimate_trip_budget": estimate_trip_budget,
    "get_transportation_advice": get_transportation_advice,
    "build_travel_checklist": build_travel_checklist,
    "build_itinerary": build_itinerary,
    "get_current_weather": get_current_weather,
    "plan_general_trip": plan_general_trip,
}


def _call_with_supported_args(func, args_dict: dict) -> str:
    supported_args = func.__code__.co_varnames[:func.__code__.co_argcount]
    filtered_args = {key: value for key, value in (args_dict or {}).items() if key in supported_args}
    return func(**filtered_args)


def execute_vinwonders_tool(tool_name: str, args_dict: dict) -> str:
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return _json({
            "status": "error",
            "message": f"Tool {tool_name} not found.",
            "available_tools": sorted(TOOL_FUNCTIONS),
        })
    return _call_with_supported_args(func, args_dict or {})
