import os
import re
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.tools.vinwonders_tools import execute_vinwonders_tool

class ReActAgent:
    """
    A ReAct-style Agent that follows the Thought-Action-Observation loop.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 10):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        System prompt that instructs the agent to follow ReAct.
        """
        tool_descriptions = "\n".join([
            f"- {t['name']}: {t['description']}\n  Parameters: {t['parameters']}"
            for t in self.tools
        ])
        return f"""You are an intelligent travel assistant for VinWonders. You have access to the following tools:
{tool_descriptions}

<<<<<<< HEAD
Use the following format for your responses:
Thought: your line of reasoning.
=======
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

7. comparison:
   - User asks to compare destinations/options.
   - Use search_vinwonders_destinations only when enough preference context is known.
   - Provide pros, cons, and best-fit recommendation.

8. follow_up:
   - User asks a follow-up based on the previous answer.
   - Use known context.
   - Only call tools if new factual/current data is needed.

9. weather_check:
   - User asks about current weather, rain, sun, temperature, or whether a location is raining.
   - Use get_current_weather when location context is available.
   - If location is missing, ask one short question for the location.

TOOL USE POLICY:
- Use only listed tools.
- Do not call tools that are not available.
- Do not call every tool unless the user asks for complete trip planning.
- For partial requests, call only the relevant tool(s).
- For follow-ups, avoid repeating unnecessary tools.
- If a tool returns empty or uncertain data, explain that clearly and give safe next steps.
- For weather questions, use get_current_weather and mention the data source/time if available.

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
>>>>>>> origin/main
Action: tool_name({{"param1": "value1", "param2": ["list1", "list2"]}})
Observation: result of the tool call.
... (repeat Thought/Action/Observation until you have enough information)
Final Answer: your final response to the user.

IMPORTANT: 
- Your Action must be exactly formatted as: Action: tool_name({{...JSON arguments...}})
- Wait for the Observation before continuing. If you output an Action, stop generating and DO NOT hallucinate the Observation. The system will provide the Observation.
- All JSON arguments in Action must be strictly valid JSON. 
"""

    def run(self, user_input: str) -> str:
        """
        ReAct loop logic.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        current_prompt = user_input
        steps = 0
        system_prompt = self.get_system_prompt()
        
        # Regex to parse the tool call. Example: Action: tool_name({"arg1": "val"})
        action_regex = re.compile(r"Action:\s*(\w+)\s*\((.*?)\)", re.DOTALL)
        final_answer_regex = re.compile(r"Final Answer:\s*(.*)", re.DOTALL)

        while steps < self.max_steps:
            try:
                # Generate LLM response
                response_dict = self.llm.generate(current_prompt, system_prompt=system_prompt)
                result = response_dict.get("content", "")
                print(f"\n[Step {steps + 1}] LLM Output:\n{result}\n")
            except Exception as e:
                import time
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    print(f"\n⚠️ Đạt giới hạn API (Quota Exceeded). Đang chờ 15 giây trước khi thử lại...")
                    time.sleep(15)
                    continue
                else:
                    raise e
            
            # Check for Final Answer
            final_match = final_answer_regex.search(result)
            if final_match:
                final_answer = final_match.group(1).strip()
                logger.log_event("AGENT_END", {"steps": steps + 1, "status": "success"})
                return final_answer
            
            # Parse Thought/Action from result
            action_match = action_regex.search(result)
            if action_match:
                tool_name = action_match.group(1)
                args_str = action_match.group(2).strip()
                
                try:
                    args_dict = json.loads(args_str)
                except json.JSONDecodeError:
                    print("Failed to parse arguments as JSON. Trying to clean it up...")
                    try:
                         # Attempt rudimentary cleanup if it has quotes issues (just for safety)
                         args_dict = json.loads(args_str.replace("'", '"'))
                    except:
                         args_dict = {}

                # Execute tool
                observation = self._execute_tool(tool_name, args_dict)
                print(f"Observation: {observation}\n")
                
                # Append to prompt
                current_prompt += f"\n{result}\nObservation: {observation}\n"
            else:
                # Nếu LLM quên dùng format "Final Answer:" mà chỉ chat bình thường, ta sẽ lấy luôn câu chat đó
                logger.log_event("AGENT_END", {"steps": steps, "status": "conversational_fallback"})
                return result.strip()
            
            steps += 1
<<<<<<< HEAD
            
        logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps_reached"})
        return "Agent reached maximum steps without a final answer."
=======

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
        ]):
            return "full_trip_planning"

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
>>>>>>> origin/main

    def _execute_tool(self, tool_name: str, args_dict: dict) -> str:
        """
        Execute tools by name.
        """
        logger.log_event("TOOL_CALL", {"tool": tool_name, "args": args_dict})
        try:
            return execute_vinwonders_tool(tool_name, args_dict)
        except Exception as e:
<<<<<<< HEAD
            return f"Error executing tool {tool_name}: {str(e)}"
=======
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
>>>>>>> origin/main
