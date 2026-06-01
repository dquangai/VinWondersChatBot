import re
import json
from typing import List, Dict, Any, Optional

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.tools.vinwonders_tools import execute_vinwonders_tool


class ReActAgent:
    """
    A ReAct-style Agent that follows the Thought-Action-Observation loop.

    Upgraded goals:
    - Ask the user step-by-step before using tools.
    - Do not execute actions if required information is missing.
    - Smarter intent routing.
    - Less rigid than fixed demo flow.
    - Uses only necessary tools.
    - Supports follow-up questions with session context.
    - Produces more natural and diverse Vietnamese travel recommendations.
    """

    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 10,
        verbose: bool = False,
        answer_style: str = "adaptive",
        enable_fallback_repair: bool = True,
        allow_demo_defaults: bool = False,
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.verbose = verbose
        self.history = []
        self.last_trace = []
        self.answer_style = answer_style
        self.enable_fallback_repair = enable_fallback_repair
        self.allow_demo_defaults = allow_demo_defaults

        # Short-term memory for one running server/session.
        self.session_context = {
            "group_size": None,
            "travel_date": None,
            "location": None,
            "interests": [],
            "destination": None,
            "budget": None,
            "group_type": None,
            "last_intent": None,
            "last_question": None,
        }

    def get_system_prompt(self) -> str:
        """
        System prompt that instructs the agent to follow ReAct,
        while using intent routing and adaptive responses.
        """
        tool_descriptions = "\n".join([
            f"- {t['name']}: {t['description']}\n  Parameters: {t['parameters']}"
            for t in self.tools
        ])

        context_text = json.dumps(
            self.session_context,
            ensure_ascii=False,
            indent=2
        )

        return f"""You are an intelligent Vietnamese travel assistant for VinWonders.

You have access to the following tools:
{tool_descriptions}

Current known user context:
{context_text}

LANGUAGE AND TONE:
- Always respond to the user in Vietnamese.
- Tone: friendly, practical, natural, upbeat, and easy to understand.
- Avoid robotic, repetitive, or template-like wording.
- Be like a real travel consultant.
- Do not overpromise.
- Do not invent prices, promotions, opening hours, show schedules, or event details.
- If information may change, remind the user to recheck official VinWonders channels before visiting or paying.

CLARIFICATION FIRST POLICY:
- Do not call tools immediately if the user's request is too vague.
- Before using tools for travel planning, make sure you know enough key information.
- Ask one short Vietnamese clarification question at a time.
- Do not ask many questions at once.
- After the user answers, continue from the known context.
- Only call tools when the required information for the user's intent is sufficient.
- If required information is missing, ask a clarification question using Final Answer.
- If you ask a clarification question, do not output Action.

REQUIRED INFORMATION BY INTENT:
For full_trip_planning, try to know:
- travel_date
- group_size or group_type
- location or departure city
- interests

For destination_recommendation, try to know:
- location or departure city
- group_size or group_type
- interests

For promotion_check, try to know:
- destination or intended VinWonders location
- travel_date if available

For event_show_check, try to know:
- destination
- travel_date

For itinerary_planning, try to know:
- destination
- travel_date
- group_size or group_type
- interests

CORE BEHAVIOR:
- First understand the user's intent.
- Use only the tools needed for that intent.
- Do not call all tools for every question.
- Reuse known context from the conversation when possible.
- If the request is simple, answer simply.
- If the request asks for full planning and enough information is known, provide a rich travel-consultant style answer.

INTENT ROUTING:
Classify the user's request into one of these intents before choosing tools:

1. greeting:
   - User only greets or small-talks.
   - Do not use tools.
   - Reply warmly and ask what trip they want to plan.

2. destination_recommendation:
   - User asks where to go, which VinWonders destination is suitable, or asks for recommendation.
   - Use get_user_preferences if useful.
   - Then use search_vinwonders_destinations.

3. promotion_check:
   - User asks about ticket discounts, vouchers, combo, deals, or promotions.
   - Use check_current_promotions only when destination/date context is sufficient.

4. event_show_check:
   - User asks about show, performance, event, fireworks, parade, evening activities.
   - Use check_events_and_shows only when destination/date context is sufficient.

5. itinerary_planning:
   - User asks for schedule, route, timeline, one-day plan, or itinerary.
   - Use get_user_preferences if useful.
   - If destination is unknown, use search_vinwonders_destinations first.
   - Then use build_itinerary.

6. full_trip_planning:
   - User wants complete planning including destination, promotion, show/event, and itinerary.
   - Use full flow only after enough information is known:
     get_user_preferences -> search_vinwonders_destinations -> check_current_promotions -> check_events_and_shows -> build_itinerary.
   - If useful, also use estimate_trip_budget, get_transportation_advice, build_travel_checklist, or get_current_weather.

7. comparison:
   - User asks to compare destinations/options.
   - Use compare_vinwonders_options when enough preference context is known.
   - Provide pros, cons, and best-fit recommendation.

8. follow_up:
   - User asks a follow-up based on the previous answer.
   - Use known context.
   - Only call tools if new factual/current data is needed.

9. weather_check:
   - User asks about current weather, rain, sun, temperature, or whether a location is raining.
   - Use get_current_weather when location context is available.
   - If location is missing, ask one short question for the location.

10. budget_planning:
   - User asks about budget, estimated cost, spending plan, or how much money to prepare.
   - Use estimate_trip_budget when destination and group size are known.
   - Mention that ticket prices must be checked on official channels.

11. transportation_advice:
   - User asks how to get there, transportation, route, shuttle, car, bus, flight, pickup/dropoff.
   - Use get_transportation_advice when departure location and destination are known.

12. checklist_preparation:
   - User asks what to prepare, what to bring, packing list, or trip checklist.
   - Use build_travel_checklist when destination/context is known.

TOOL USE POLICY:
- Use only listed tools.
- Do not call tools that are not available.
- Do not call every tool unless the user asks for complete trip planning.
- For partial requests, call only the relevant tool(s).
- For follow-ups, avoid repeating unnecessary tools.
- If a tool returns empty or uncertain data, explain that clearly and give safe next steps.
- For weather questions, use get_current_weather and mention the data source/time if available.
- For budget, transportation, and checklist requests, use the specialized tools instead of answering generically.
- Tool observations are structured JSON; read the fields and turn them into a polished consultant-style answer.

DEMO DEFAULTS:
- Demo defaults are only allowed if the application explicitly enables them.
- If demo defaults are not enabled, ask the user step-by-step for missing information.

ANSWER MODES:
Choose the best answer mode based on the user's request:
- quick_answer: short and direct.
- travel_consultant: complete trip planning.
- comparison: pros/cons and best fit.
- budget_saver: focus on promotions, ticket tips, and cost saving.
- friend_group: thrill rides, check-in, group activities, evening shows.
- family_friendly: gentle activities, rest time, meals, safety.
- couple_trip: photo spots, relaxed schedule, evening activities.
- rainy_day_backup: flexible indoor/backup plan.

FINAL ANSWER GUIDELINES:
- Do not always use the exact same structure.
- Match the structure to the user's intent.
- Use clear sections and bullets when helpful.
- Make the answer practical, not generic.
- Add alternatives when useful.
- Add tips only when relevant.

For full_trip_planning, include:
1. Điểm đến phù hợp.
2. Khuyến mãi hiện tại + reminder to check official channels before payment.
3. Sự kiện/show hiện tại hoặc sắp diễn ra + reminder to recheck schedule before visiting.
4. Lịch trình vui chơi đề xuất trong ngày.
5. Extra helpful suggestions relevant to the user.

For simple requests:
- Keep the final answer concise.
- Do not force the full 4-part structure.

For comparison:
- Include pros, cons, and best for whom.

For itinerary:
- Use a timeline format.

For promotions:
- Mention uncertainty if applicable and remind user to verify official channels.

REACT FORMAT:
Use this format:

Thought: brief reasoning.
Action: tool_name({{"param1": "value1", "param2": ["list1", "list2"]}})
Observation: result of the tool call.
... repeat Thought/Action/Observation until you have enough information.
Final Answer: your final response to the user.

IMPORTANT FORMAT RULES:
- Your Action must be exactly formatted as:
  Action: tool_name({{...JSON arguments...}})
- Wait for the Observation before continuing.
- If you output an Action, stop generating and DO NOT hallucinate the Observation.
- All JSON arguments in Action must be strictly valid JSON.
- Do not include Markdown code fences in Action.
- Do not call tools that are not listed.
"""

    def run(self, user_input: str) -> str:
        """
        ReAct loop logic with clarification-first gate.
        """
        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": getattr(self.llm, "model_name", "unknown")
        })

        self.last_trace = []

        # 0. Update context from the user's latest message first.
        self._update_context_from_text(user_input)

        # 1. Clarification-first gate.
        # If required info is missing, ask one question and DO NOT call tools.
        clarification = self._maybe_ask_before_tools(user_input)

        if clarification:
            self.last_trace.append({
                "step": 0,
                "type": "clarification",
                "final_answer": clarification,
                "context": dict(self.session_context),
            })

            logger.log_event("AGENT_END", {
                "steps": 0,
                "status": "clarification_needed"
            })

            return clarification

        direct_answer = self._maybe_direct_tool_answer(user_input)
        if direct_answer:
            logger.log_event("AGENT_END", {
                "steps": len(self.last_trace),
                "status": "direct_tool_answer"
            })
            return direct_answer

        current_prompt = self._build_initial_prompt(user_input)
        steps = 0
        system_prompt = self.get_system_prompt()

        action_regex = re.compile(
            r"Action(?:\s*\d+)?:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\((\{.*?\})\)",
            re.DOTALL
        )

        final_answer_regex = re.compile(
            r"Final Answer(?:\s*\d+)?:\s*(.*)",
            re.DOTALL
        )

        while steps < self.max_steps:
            result = self.llm.generate(current_prompt, system_prompt=system_prompt)
            result_text = self._extract_llm_content(result).strip()

            trace_step = {
                "step": steps + 1,
                "llm_output": result_text,
            }

            if self.verbose:
                print(f"\n[Step {steps + 1}] LLM Output:\n{result_text}\n")

            # 2. Check final answer.
            final_match = final_answer_regex.search(result_text)

            if final_match:
                final_answer = final_match.group(1).strip()
                final_answer = self._polish_final_answer(final_answer)

                trace_step["type"] = "final"
                trace_step["final_answer"] = final_answer
                self.last_trace.append(trace_step)

                self._update_context_from_text(user_input)
                self._update_context_from_trace(self.last_trace)

                logger.log_event("AGENT_END", {
                    "steps": steps + 1,
                    "status": "success"
                })

                return final_answer

            # 3. Parse and execute action.
            action_match = action_regex.search(result_text)

            if action_match:
                tool_name = action_match.group(1).strip()
                args_str = action_match.group(2).strip()

                args_dict = self._safe_parse_json(args_str)
                args_dict = self._enrich_args_with_context(tool_name, args_dict)

                if not self._is_valid_tool(tool_name):
                    observation = self._tool_error(
                        f"Tool '{tool_name}' is not available. Available tools: {self._tool_names()}."
                    )
                else:
                    observation = self._execute_tool(tool_name, args_dict)

                compact_observation = self._compact_observation(observation)

                trace_step.update({
                    "type": "tool",
                    "tool": tool_name,
                    "arguments": args_dict,
                    "observation": observation,
                })

                self.last_trace.append(trace_step)

                self._update_context_from_args(args_dict)
                self._update_context_from_observation(tool_name, observation)

                if self.verbose:
                    print(f"Observation: {compact_observation}\n")

                current_prompt += (
                    f"\n\n{result_text}"
                    f"\nObservation: {compact_observation}\n"
                )

            else:
                # 4. If malformed output, repair instead of returning too early.
                trace_step["type"] = "malformed_output"
                self.last_trace.append(trace_step)

                if self.enable_fallback_repair:
                    current_prompt += self._build_repair_instruction(result_text)
                else:
                    logger.log_event("AGENT_END", {
                        "steps": steps + 1,
                        "status": "direct_answer"
                    })
                    return result_text

            steps += 1

        logger.log_event("AGENT_END", {
            "steps": steps,
            "status": "max_steps_reached"
        })

        return (
            "Mình chưa thể hoàn tất tư vấn vì agent đã đạt số bước tối đa. "
            "Bạn có thể hỏi ngắn hơn một chút, ví dụ: "
            "'Gợi ý lịch trình VinWonders cuối tuần này cho nhóm 4 người từ Hà Nội'."
        )

    def _build_initial_prompt(self, user_input: str) -> str:
        """
        Build initial prompt with adaptive guidance.
        """
        context_text = json.dumps(
            self.session_context,
            ensure_ascii=False,
            indent=2
        )

        return f"""User request:
{user_input}

Known context:
{context_text}

Please help the user as a VinWonders travel assistant.

Instructions:
- First infer the user's intent.
- Use only the tools needed for that intent.
- If this is a simple greeting, answer directly without tools.
- If this is a follow-up question, reuse known context.
- If information is missing and necessary, ask at most one short clarification question.
- If the user asks for full planning, use the full tool flow.
- Final answer must be natural Vietnamese and adapted to the user's request.
"""

    # ---------------------------------------------------------------------
    # Clarification-first logic
    # ---------------------------------------------------------------------

    def _maybe_ask_before_tools(self, user_input: str) -> Optional[str]:
        """
        Ask one step-by-step clarification question before tool usage
        if the user request is not specific enough.
        """
        intent = self._classify_intent_lightweight(user_input)
        self.session_context["last_intent"] = intent

        if intent == "greeting":
            self.session_context["last_question"] = "trip_type"
            return (
                "Chào bạn 👋 Bạn muốn mình tư vấn chuyến đi VinWonders theo kiểu nào? "
                "Ví dụ: đi cuối tuần, đi nhóm bạn, đi gia đình, tìm khuyến mãi, "
                "xem show hoặc lên lịch trình 1 ngày."
            )

        if intent == "general":
            self.session_context["last_question"] = "trip_type"
            return (
                "Bạn muốn mình hỗ trợ phần nào cho chuyến đi VinWonders? "
                "Mình có thể tư vấn điểm đến, khuyến mãi vé, show/sự kiện hoặc lịch trình trong ngày."
            )

        if self.allow_demo_defaults and self._looks_like_demo_full_planning(user_input):
            self._apply_demo_defaults()
            return None

        missing = self._get_missing_required_info(intent)

        if not missing:
            return None

        question = self._build_clarification_question(intent, missing)
        return question

    def _classify_intent_lightweight(self, text: str) -> str:
        """
        Lightweight deterministic intent classification before LLM/tool usage.
        This prevents the agent from calling tools too early.
        """
        lowered = str(text or "").lower().strip()

        greeting_words = ["xin chào", "chào", "hello", "hi", "hey"]
        if lowered in greeting_words or (
            len(lowered) <= 12 and any(word == lowered for word in greeting_words)
        ):
            return "greeting"

        if any(w in lowered for w in [
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
        ]):
            return "weather_check"

        full_plan_keywords = [
            "tư vấn",
            "đi vinwonders",
            "muốn đi vinwonders",
            "lên kế hoạch",
            "đề xuất chuyến đi",
            "gợi ý chuyến đi",
            "gợi ý điểm vui chơi",
        ]

        if any(w in lowered for w in full_plan_keywords) and any(w in lowered for w in [
            "lịch trình",
            "khuyến mãi",
            "ưu đãi",
            "show",
            "sự kiện",
            "điểm vui chơi",
            "ngân sách",
            "chi phí",
            "di chuyển",
        ]):
            return "full_trip_planning"

        if any(w in lowered for w in [
            "ngân sách",
            "chi phí",
            "bao nhiêu tiền",
            "tốn bao nhiêu",
            "dự trù",
            "budget",
            "ước tính",
        ]):
            return "budget_planning"

        if any(w in lowered for w in [
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
        ]):
            return "transportation_advice"

        if any(w in lowered for w in [
            "mang gì",
            "chuẩn bị gì",
            "checklist",
            "packing",
            "cần chuẩn bị",
            "đồ cần mang",
            "hành lý",
        ]):
            return "checklist_preparation"

        if any(w in lowered for w in [
            "so sánh",
            "khác nhau",
            "nên chọn cái nào",
            "phú quốc hay nha trang",
            "nha trang hay phú quốc",
            "cái nào phù hợp hơn",
        ]):
            return "comparison"

        if any(w in lowered for w in [
            "khuyến mãi",
            "ưu đãi",
            "voucher",
            "giảm giá",
            "combo",
            "vé rẻ",
            "giá vé",
            "vé",
        ]):
            return "promotion_check"

        if any(w in lowered for w in [
            "show",
            "sự kiện",
            "biểu diễn",
            "nhạc nước",
            "pháo hoa",
            "parade",
            "buổi tối",
        ]):
            return "event_show_check"

        if any(w in lowered for w in [
            "lịch trình",
            "kế hoạch",
            "timeline",
            "chơi trong ngày",
            "1 ngày",
            "một ngày",
            "đi như thế nào",
            "sắp xếp",
        ]):
            return "itinerary_planning"

        full_plan_keywords = [
            "tư vấn",
            "đi vinwonders",
            "muốn đi vinwonders",
            "lên kế hoạch",
            "đề xuất chuyến đi",
            "gợi ý chuyến đi",
            "gợi ý điểm vui chơi",
        ]

        if any(w in lowered for w in full_plan_keywords):
            return "full_trip_planning"

        if any(w in lowered for w in [
            "đi đâu",
            "điểm đến",
            "vinwonders nào",
            "nên đi",
            "phù hợp",
        ]):
            return "destination_recommendation"

        # If the user replies with details after a previous clarification,
        # infer that the previous intent is still active.
        last_intent = self.session_context.get("last_intent")
        if last_intent in [
            "full_trip_planning",
            "destination_recommendation",
            "promotion_check",
            "event_show_check",
            "itinerary_planning",
            "comparison",
            "weather_check",
            "budget_planning",
            "transportation_advice",
            "checklist_preparation",
        ]:
            return last_intent

        return "general"

    def _get_missing_required_info(self, intent: str) -> List[str]:
        """
        Return missing info based on the intent and current session_context.
        """
        ctx = self.session_context

        def empty(key: str) -> bool:
            return ctx.get(key) in [None, "", []]

        missing = []

        if intent == "full_trip_planning":
            if empty("travel_date"):
                missing.append("travel_date")
            if empty("group_size") and empty("group_type"):
                missing.append("group")
            if empty("location"):
                missing.append("location")
            if empty("interests"):
                missing.append("interests")

        elif intent == "destination_recommendation":
            if empty("location"):
                missing.append("location")
            if empty("group_size") and empty("group_type"):
                missing.append("group")
            if empty("interests"):
                missing.append("interests")

        elif intent == "promotion_check":
            if empty("destination"):
                missing.append("destination")
            if empty("travel_date"):
                missing.append("travel_date")

        elif intent == "event_show_check":
            if empty("destination"):
                missing.append("destination")
            if empty("travel_date"):
                missing.append("travel_date")

        elif intent == "itinerary_planning":
            if empty("destination"):
                missing.append("destination")
            if empty("travel_date"):
                missing.append("travel_date")
            if empty("group_size") and empty("group_type"):
                missing.append("group")
            if empty("interests"):
                missing.append("interests")

        elif intent == "comparison":
            if empty("location"):
                missing.append("location")
            if empty("interests"):
                missing.append("interests")

        elif intent == "weather_check":
            if empty("location"):
                missing.append("location")

        elif intent == "budget_planning":
            if empty("destination"):
                missing.append("destination")
            if empty("group_size") and empty("group_type"):
                missing.append("group")

        elif intent == "transportation_advice":
            if empty("destination"):
                missing.append("destination")
            if empty("location"):
                missing.append("location")

        elif intent == "checklist_preparation":
            if empty("destination"):
                missing.append("destination")

        return missing

    def _build_clarification_question(self, intent: str, missing: List[str]) -> str:
        """
        Ask only one important question at a time.
        """
        if not missing:
            return ""

        priority = ["travel_date", "group", "location", "destination", "interests"]
        first_missing = None

        for key in priority:
            if key in missing:
                first_missing = key
                break

        if first_missing == "travel_date":
            self.session_context["last_question"] = "travel_date"
            return (
                "Bạn dự định đi VinWonders vào ngày nào vậy? "
                "Nếu chưa chốt, bạn có thể nói kiểu như “cuối tuần này” hoặc “thứ Bảy tuần này”."
            )

        if first_missing == "group":
            self.session_context["last_question"] = "group"
            return (
                "Bạn đi cùng ai và khoảng bao nhiêu người? "
                "Ví dụ: nhóm bạn 4 người, gia đình có trẻ nhỏ, hoặc đi cặp đôi."
            )

        if first_missing == "location":
            self.session_context["last_question"] = "location"
            return (
                "Bạn xuất phát từ đâu để mình chọn điểm VinWonders phù hợp hơn? "
                "Ví dụ: Hà Nội, TP.HCM, Đà Nẵng, Nha Trang hoặc Phú Quốc."
            )

        if first_missing == "destination":
            self.session_context["last_question"] = "destination"
            return (
                "Bạn muốn kiểm tra cho VinWonders ở điểm nào? "
                "Ví dụ: VinWonders Phú Quốc, VinWonders Nha Trang hoặc VinWonders Nam Hội An."
            )

        if first_missing == "interests":
            self.session_context["last_question"] = "interests"
            return (
                "Bạn thích trải nghiệm kiểu nào hơn: trò chơi cảm giác mạnh, show buổi tối, "
                "check-in chụp ảnh, đi nhẹ nhàng, hay ưu tiên khuyến mãi vé?"
            )

        self.session_context["last_question"] = "general_info"
        return (
            "Bạn cho mình thêm một chút thông tin về ngày đi, số người và nơi xuất phát nhé. "
            "Mình sẽ tư vấn chính xác hơn."
        )

    def _looks_like_demo_full_planning(self, text: str) -> bool:
        """
        Detect demo-like full planning request.
        Only used if allow_demo_defaults=True.
        """
        lowered = str(text or "").lower()

        return (
            "vinwonders" in lowered
            and any(w in lowered for w in ["cuối tuần", "nhóm bạn", "bạn bè"])
            and any(w in lowered for w in ["gợi ý", "tư vấn", "lịch trình", "khuyến mãi", "show"])
        )

    def _apply_demo_defaults(self) -> None:
        """
        Apply demo defaults when explicitly enabled.
        """
        self.session_context.update({
            "group_size": 4,
            "travel_date": "2026-06-07",
            "location": "Hà Nội",
            "interests": [
                "trò chơi cảm giác mạnh",
                "show buổi tối",
                "khuyến mãi vé",
                "check-in",
            ],
            "group_type": "friends",
        })

    # ---------------------------------------------------------------------
    # Core helpers
    # ---------------------------------------------------------------------

    def _extract_llm_content(self, result: Any) -> str:
        """
        Providers return a metadata dict; the ReAct parser only needs the text.
        """
        if isinstance(result, dict):
            content = result.get("content", "")

            if isinstance(content, str):
                return content

            return json.dumps(content, ensure_ascii=False)

        return str(result)

    def _safe_parse_json(self, args_str: str) -> dict:
        """
        Parse JSON arguments robustly.
        """
        if not args_str:
            return {}

        try:
            return json.loads(args_str)
        except json.JSONDecodeError:
            pass

        cleaned = args_str.strip()

        cleaned = (
            cleaned
            .replace("“", "\"")
            .replace("”", "\"")
            .replace("‘", "'")
            .replace("’", "'")
        )

        cleaned = cleaned.replace("'", "\"")
        cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.log_event("JSON_PARSE_ERROR", {
                "raw_args": args_str,
                "cleaned_args": cleaned
            })
            return {}

    def _execute_tool(self, tool_name: str, args_dict: dict) -> str:
        """
        Execute tools by name.
        """
        logger.log_event("TOOL_CALL", {
            "tool": tool_name,
            "args": args_dict
        })

        try:
            return execute_vinwonders_tool(tool_name, args_dict)
        except Exception as e:
            logger.log_event("TOOL_ERROR", {
                "tool": tool_name,
                "args": args_dict,
                "error": str(e)
            })

            return self._tool_error(
                f"Tool execution failed for '{tool_name}': {str(e)}"
            )

    def _is_valid_tool(self, tool_name: str) -> bool:
        """
        Check whether the requested tool exists.
        """
        return tool_name in self._tool_names()

    def _tool_names(self) -> List[str]:
        """
        Return available tool names.
        """
        return [t.get("name") for t in self.tools]

    def _tool_error(self, message: str) -> str:
        """
        Standardized tool error observation.
        """
        return json.dumps({
            "status": "error",
            "message": message
        }, ensure_ascii=False)

    def _maybe_direct_tool_answer(self, user_input: str) -> Optional[str]:
        """
        Deterministic shortcut for specialized travel intents.
        This prevents the LLM from answering "I cannot access data" before using a tool.
        """
        intent = self.session_context.get("last_intent") or self._classify_intent_lightweight(user_input)

        direct_tools = {
            "weather_check": "get_current_weather",
            "budget_planning": "estimate_trip_budget",
            "transportation_advice": "get_transportation_advice",
            "checklist_preparation": "build_travel_checklist",
        }

        tool_name = direct_tools.get(intent)
        if not tool_name:
            return None

        args = self._direct_tool_args(tool_name)
        observation = self._execute_tool(tool_name, args)
        parsed = self._try_parse_json(observation)

        self.last_trace.append({
            "step": 1,
            "type": "tool",
            "tool": tool_name,
            "arguments": args,
            "observation": observation,
            "direct": True,
        })

        self._update_context_from_args(args)
        self._update_context_from_observation(tool_name, observation)

        answer = self._format_direct_tool_answer(intent, parsed, observation)
        self.last_trace.append({
            "step": 2,
            "type": "final",
            "final_answer": answer,
            "direct": True,
        })
        return answer

    def _direct_tool_args(self, tool_name: str) -> dict:
        """
        Build deterministic tool arguments from session context.
        """
        def clean(args: dict) -> dict:
            return {
                key: value
                for key, value in args.items()
                if value not in [None, "", []]
            }

        ctx = self.session_context
        common = {
            "destination": ctx.get("destination"),
            "location": ctx.get("location"),
            "group_size": ctx.get("group_size"),
            "travel_date": ctx.get("travel_date"),
            "group_type": ctx.get("group_type"),
            "interests": ctx.get("interests", []),
        }

        if tool_name == "get_current_weather":
            return clean({"location": ctx.get("location")})

        if tool_name == "estimate_trip_budget":
            return clean({
                "destination": ctx.get("destination"),
                "group_size": ctx.get("group_size") or 1,
                "budget_level": ctx.get("budget") or "standard",
                "include_transport": True,
            })

        if tool_name == "get_transportation_advice":
            return clean({
                "destination": ctx.get("destination"),
                "location": ctx.get("location"),
                "group_size": ctx.get("group_size") or 1,
            })

        if tool_name == "build_travel_checklist":
            common["travel_date"] = ctx.get("travel_date") or "ngày bạn dự định đi"
            return clean(common)

        return clean(common)

    def _format_direct_tool_answer(
        self,
        intent: str,
        parsed: Optional[Any],
        raw_observation: str,
    ) -> str:
        """
        Convert structured tool JSON into a concise Vietnamese consultant answer.
        """
        if not isinstance(parsed, dict):
            return str(raw_observation)

        if intent == "weather_check":
            return self._format_weather_answer(parsed)

        if intent == "budget_planning":
            return self._format_budget_answer(parsed)

        if intent == "transportation_advice":
            return self._format_transportation_answer(parsed)

        if intent == "checklist_preparation":
            return self._format_checklist_answer(parsed)

        return json.dumps(parsed, ensure_ascii=False)

    def _format_weather_answer(self, data: dict) -> str:
        if data.get("status") != "ok":
            return data.get("message", "Mình chưa kiểm tra được thời tiết hiện tại.")

        is_raining = data.get("is_raining")
        location = data.get("location", "địa điểm này")
        weather = data.get("weather", "không rõ")
        time = data.get("time", "thời điểm cập nhật")
        temperature = data.get("temperature_c")
        humidity = data.get("humidity_percent")
        precipitation = data.get("precipitation_mm")
        source = data.get("source", "nguồn thời tiết")

        rain_text = "có dấu hiệu mưa/dông" if is_raining else "chưa ghi nhận mưa"
        return (
            f"Theo {source} lúc {time}, {location} hiện {rain_text}: {weather}. "
            f"Nhiệt độ khoảng {temperature}°C, độ ẩm {humidity}%, lượng mưa ghi nhận {precipitation} mm.\n\n"
            f"Gợi ý: {data.get('advice', 'Bạn nên kiểm tra lại thời tiết ngay trước khi đi.')}"
        )

    def _format_budget_answer(self, data: dict) -> str:
        if data.get("status") not in {"planning_estimate", "ok"}:
            return data.get("message", "Mình chưa ước tính được ngân sách.")

        estimate = data.get("estimate_excluding_tickets_vnd", {})
        min_cost = self._format_vnd(estimate.get("min"))
        max_cost = self._format_vnd(estimate.get("max"))
        destination = data.get("destination", "VinWonders")
        group_size = data.get("group_size", "nhóm")

        tips = "\n".join(f"- {tip}" for tip in data.get("saving_tips", [])[:3])
        return (
            f"Với {group_size} người đi {destination}, ngân sách tham khảo chưa gồm vé vào cổng khoảng "
            f"{min_cost} - {max_cost}.\n\n"
            f"Lưu ý: {data.get('ticket_note', 'Giá vé cần kiểm tra trên kênh chính thức.')}\n\n"
            f"Mẹo tiết kiệm:\n{tips}"
        )

    def _format_transportation_answer(self, data: dict) -> str:
        if data.get("status") != "ok":
            return data.get("message", "Mình chưa tư vấn được phương án di chuyển.")

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

    def _format_checklist_answer(self, data: dict) -> str:
        if data.get("status") != "ok":
            return data.get("message", "Mình chưa tạo được checklist.")

        travel_date = data.get("travel_date") or "ngày bạn dự định đi"
        sections = []
        for section in data.get("checklist", []):
            items = ", ".join(section.get("items", []))
            sections.append(f"- {section.get('category')}: {items}")

        return (
            f"Checklist chuẩn bị cho {data.get('destination', 'VinWonders')} "
            f"({travel_date}):\n"
            + "\n".join(sections)
            + f"\n\nGợi ý: {data.get('consultant_note', 'Bạn nên kiểm tra lại trước ngày đi.')}"
        )

    def _format_vnd(self, value: Any) -> str:
        try:
            return f"{int(value):,} VND".replace(",", ".")
        except (TypeError, ValueError):
            return "chưa rõ"

    def _compact_observation(self, observation: Any, max_chars: int = 3500) -> str:
        """
        Compact long observations to keep prompt stable.
        """
        if not isinstance(observation, str):
            observation = json.dumps(observation, ensure_ascii=False)

        observation = observation.strip()

        if len(observation) <= max_chars:
            return observation

        return (
            observation[:max_chars]
            + "\n...[Observation truncated for context stability]..."
        )

    def _build_repair_instruction(self, bad_output: str) -> str:
        """
        Ask the model to repair malformed ReAct output.
        """
        return f"""

The previous assistant output did not follow the required ReAct format.

Previous output:
{bad_output}

Please continue correctly using exactly one of these formats:

If you need a tool:
Thought: brief reasoning.
Action: tool_name({{"key": "value"}})

If you have enough information:
Final Answer: Vietnamese final answer for the user.

Remember:
- Do not invent Observation.
- If you output Action, stop immediately after Action.
- Use only available tools.
"""

    def _polish_final_answer(self, answer: str) -> str:
        """
        Lightweight post-processing for final answer.
        """
        answer = answer.strip()

        if not answer:
            return (
                "Mình đã xử lý xong nhưng chưa tạo được câu trả lời hoàn chỉnh. "
                "Bạn có thể thử hỏi lại với thông tin cụ thể hơn nhé."
            )

        return answer

    def _enrich_args_with_context(self, tool_name: str, args_dict: dict) -> dict:
        """
        Fill missing tool arguments from session context when safe.
        """
        if not isinstance(args_dict, dict):
            args_dict = {}

        enriched = dict(args_dict)

        context_keys = [
            "group_size",
            "travel_date",
            "location",
            "destination",
            "budget",
            "group_type",
        ]

        for key in context_keys:
            if (
                enriched.get(key) in [None, "", []]
                and self.session_context.get(key) not in [None, "", []]
            ):
                enriched[key] = self.session_context.get(key)

        if enriched.get("interests") in [None, "", []]:
            interests = self.session_context.get("interests", [])
            if interests:
                enriched["interests"] = interests

        # Some tools may expect date instead of travel_date.
        if "travel_date" in enriched and "date" not in enriched:
            if tool_name in [
                "check_current_promotions",
                "check_events_and_shows",
                "build_itinerary",
                "get_current_weather",
            ]:
                enriched.setdefault("date", enriched.get("travel_date"))

        return enriched

    def _update_context_from_args(self, args_dict: dict) -> None:
        """
        Update short-term context from tool arguments.
        """
        if not isinstance(args_dict, dict):
            return

        mapping = {
            "group_size": "group_size",
            "travel_date": "travel_date",
            "date": "travel_date",
            "location": "location",
            "departure": "location",
            "departure_city": "location",
            "destination": "destination",
            "destination_name": "destination",
            "budget": "budget",
            "group_type": "group_type",
        }

        for source_key, target_key in mapping.items():
            value = args_dict.get(source_key)

            if value not in [None, "", []]:
                self.session_context[target_key] = value

        interests = args_dict.get("interests")

        if isinstance(interests, str) and interests.strip():
            self.session_context["interests"] = [interests.strip()]
        elif isinstance(interests, list) and interests:
            self.session_context["interests"] = [
                str(item).strip()
                for item in interests
                if str(item).strip()
            ]

    def _update_context_from_observation(self, tool_name: str, observation: Any) -> None:
        """
        Try to update context from tool observation if it is JSON-like.
        """
        parsed = self._try_parse_json(observation)

        if not isinstance(parsed, dict):
            return

        possible_destination = (
            parsed.get("destination")
            or parsed.get("destination_name")
            or parsed.get("recommended_destination")
            or parsed.get("name")
        )

        if possible_destination:
            self.session_context["destination"] = possible_destination

        if tool_name:
            self.session_context["last_intent"] = tool_name

    def _update_context_from_trace(self, trace: list) -> None:
        """
        Update context from the whole trace.
        """
        if not isinstance(trace, list):
            return

        for item in trace:
            if item.get("type") == "tool":
                self._update_context_from_args(item.get("arguments", {}))
                self._update_context_from_observation(
                    item.get("tool", ""),
                    item.get("observation", "")
                )

    def _update_context_from_text(self, text: str) -> None:
        """
        Lightweight heuristic extraction from user text.
        This helps the agent ask step-by-step and avoid asking again.
        """
        if not isinstance(text, str):
            return

        lowered = text.lower()

        # Group type
        if any(word in lowered for word in ["nhóm bạn", "bạn bè", "cùng bạn", "team", "nhóm mình"]):
            self.session_context["group_type"] = "friends"

        if any(word in lowered for word in ["gia đình", "trẻ em", "con nhỏ", "bố mẹ", "ba mẹ"]):
            self.session_context["group_type"] = "family"

        if any(word in lowered for word in ["cặp đôi", "người yêu", "hẹn hò", "hai đứa"]):
            self.session_context["group_type"] = "couple"

        # Group size, e.g. "4 người", "nhóm 5 người"
        group_match = re.search(r"(\d+)\s*(người|bạn|thành viên)", lowered)
        if group_match:
            try:
                self.session_context["group_size"] = int(group_match.group(1))
            except ValueError:
                pass

        # Date-ish expressions
        if "cuối tuần" in lowered:
            self.session_context["travel_date"] = "cuối tuần này"

        if "thứ bảy" in lowered or "thứ 7" in lowered:
            self.session_context["travel_date"] = "thứ Bảy"

        if "chủ nhật" in lowered:
            self.session_context["travel_date"] = "Chủ nhật"

        date_match = re.search(r"(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)", lowered)
        if date_match:
            self.session_context["travel_date"] = date_match.group(1)

        # Location and destination
        location_keywords = {
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

        destination_keywords = {
            "vinwonders phú quốc": "VinWonders Phú Quốc",
            "vinwonders phu quoc": "VinWonders Phú Quốc",
            "vinwonders nha trang": "VinWonders Nha Trang",
            "vinwonders nam hội an": "VinWonders Nam Hội An",
            "vinwonders nam hoi an": "VinWonders Nam Hội An",
        }

        for keyword, normalized in destination_keywords.items():
            if keyword in lowered:
                self.session_context["destination"] = normalized

        for keyword, normalized in location_keywords.items():
            if keyword in lowered:
                # If user directly mentions VinWonders + city, store destination.
                if "vinwonders" in lowered and normalized in [
                    "Phú Quốc",
                    "Nha Trang",
                    "Nam Hội An",
                ]:
                    self.session_context["destination"] = f"VinWonders {normalized}"
                else:
                    # Otherwise treat as departure/current location.
                    self.session_context["location"] = normalized

        # Interests
        interest_keywords = {
            "trò chơi cảm giác mạnh": ["cảm giác mạnh", "tàu lượn", "mạo hiểm", "adventure"],
            "show buổi tối": ["show", "buổi tối", "nhạc nước", "firework", "pháo hoa", "biểu diễn"],
            "khuyến mãi vé": ["khuyến mãi", "ưu đãi", "giảm giá", "voucher", "combo", "vé rẻ"],
            "check-in": ["check-in", "chụp ảnh", "sống ảo", "ảnh đẹp", "checkin"],
            "ăn uống": ["ăn uống", "nhà hàng", "buffet", "ăn trưa", "ăn tối"],
            "đi nhẹ nhàng": ["nhẹ nhàng", "không mạo hiểm", "thư giãn", "nghỉ ngơi"],
        }

        current_interests = set(self.session_context.get("interests") or [])

        for interest, keywords in interest_keywords.items():
            if any(keyword in lowered for keyword in keywords):
                current_interests.add(interest)

        if current_interests:
            self.session_context["interests"] = list(current_interests)

    def _try_parse_json(self, value: Any) -> Optional[Any]:
        """
        Parse JSON if possible.
        """
        if isinstance(value, (dict, list)):
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

    def reset_context(self) -> None:
        """
        Optional helper for backend if you want to reset agent memory.
        """
        self.history = []
        self.last_trace = []
        self.session_context = {
            "group_size": None,
            "travel_date": None,
            "location": None,
            "interests": [],
            "destination": None,
            "budget": None,
            "group_type": None,
            "last_intent": None,
            "last_question": None,
        }
