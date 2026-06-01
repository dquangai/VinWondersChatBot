# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Đoàn Minh Quang
- **Student ID**: 2A202600757
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

- **Modules Implementated**: `src/tools/vinwonders_tools.py`, `src/agent/agent.py`
- **Code Highlights**: Implemented the core `build_itinerary` and `search_vinwonders_destinations` tools. Set up the dynamic ReAct loop in `agent.py` to correctly parse `Thought`, `Action`, `Action Input`, and `Observation`.
- **Documentation**: Developed the tool schemas so the LLM clearly understands the JSON input requirements for each VinWonders function, allowing seamless integration with the ReAct loop.

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: Agent was caught in a loop repeatedly calling `check_events_and_shows` with invalid locations.
- **Log Source**: `logs/agent_trace.log` showed `Action: check_events_and_shows`, `Action Input: {"location": "Hà Nội"}` resulting in empty data, but the agent kept trying.
- **Diagnosis**: The LLM did not know the exact valid keys for locations in the mocked data, causing it to guess blindly.
- **Solution**: Updated the tool description in `vinwonders_tools.py` to explicitly list the supported locations (e.g., "Phú Quốc", "Nha Trang", "Nam Hội An") so the LLM selects from a valid enum.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: The `Thought` block forced the LLM to plan its steps. Instead of immediately guessing an itinerary, it explicitly noted "I need to check promotions first" and "I need to find the show times", leading to a highly structured and accurate final response.
2.  **Reliability**: The Agent performed *worse* than the Chatbot on extremely simple conversational queries (e.g., "Chào bạn"), as it sometimes over-engineered the response by trying to find a tool to call instead of just saying hello.
3.  **Observation**: The environment feedback was crucial. When a tool returned "No promotions found", the observation allowed the agent to adjust its final answer to "Hiện tại chưa có ưu đãi" rather than hallucinating a fake discount.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: Move the current `http.server` backend to a robust framework like FastAPI with asynchronous tool execution.
- **Safety**: Add a moderation layer before the LLM processes the user input to block inappropriate requests.
- **Performance**: Implement semantic caching (e.g., using Redis) so repeated queries for the same itinerary/shows don't trigger unnecessary LLM API calls and tool executions.

---
