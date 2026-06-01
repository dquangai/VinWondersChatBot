# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: VinWonders Team
- **Team Members**: 
    - Đoàn Minh Quang (2A202600757),
    - Trương Thành Thảo (2A202600735)

---

## 1. Executive Summary

*Brief overview of the agent's goal and success rate compared to the baseline chatbot.*

- **Success Rate**: 90% on 20 test cases
- **Key Outcome**: Our VinWonders Travel Assistant agent successfully solved complex, multi-step queries (such as planning a full itinerary including shows and promotions) 50% more effectively than the baseline chatbot by effectively using the custom VinWonders tools.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation
The system employs a ReAct (Reasoning and Acting) loop where the agent receives the user's travel request, updates the short-term context, determines the intent, and iteratively uses Thought, Action, and Observation to gather necessary information before formulating a Final Answer in natural Vietnamese.

### 2.2 Tool Definitions (Inventory)
| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `get_user_preferences` | `json` | Tóm tắt nhu cầu người dùng (ngày đi, số người, nơi xuất phát, sở thích). |
| `search_vinwonders_destinations` | `json` | Gợi ý điểm đến VinWonders phù hợp dựa trên sở thích và vị trí. |
| `check_current_promotions` | `json` | Kiểm tra và trả về nhóm thông tin ưu đãi tham khảo. |
| `check_events_and_shows` | `json` | Trả về thông tin show hoặc sự kiện tham khảo tại các cơ sở. |
| `build_itinerary` | `json` | Xây dựng lịch trình vui chơi trong ngày chi tiết. |

### 2.3 LLM Providers Used
- **Primary**: OpenAI (GPT-4o) / Gemini (Gemini 1.5 Flash)
- **Secondary (Backup)**: Local GGUF model via `llama-cpp-python`

---

## 3. Telemetry & Performance Dashboard

*Analyze the industry metrics collected during the final test run.*

- **Average Latency (P50)**: 1800ms
- **Max Latency (P99)**: 4200ms
- **Average Tokens per Task**: 850 tokens (due to multiple tool observations)
- **Total Cost of Test Suite**: $0.12 (using GPT-4o and Gemini combined)

---

## 4. Root Cause Analysis (RCA) - Failure Traces

*Deep dive into why the agent failed.*

### Case Study: Missing Required Tool Arguments
- **Input**: "Gợi ý cho tôi lịch trình đi VinWonders."
- **Observation**: Agent called `build_itinerary()` without providing necessary parameters like `destination` or `group_size`.
- **Root Cause**: The prompt lacked strict enforcement for the agent to ask clarifying questions before calling the `build_itinerary` tool.
- **Fix**: Updated the ReAct prompt to mandate calling `get_user_preferences` and asking the user for missing info before building an itinerary.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Prompt v1 vs Prompt v2
- **Diff**: Added explicit instruction: "Hỏi thêm thông tin khi yêu cầu của người dùng chưa đủ rõ trước khi gọi tool lịch trình."
- **Result**: Reduced premature tool calls by 40% and improved itinerary relevance.

### Experiment 2 (Bonus): Chatbot vs Agent
| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| Simple Q ("VinWonders ở đâu?") | Correct | Correct | Draw |
| Multi-step ("Lịch trình Phú Quốc có show gì?") | Hallucinated show times | Correctly fetched from tools | **Agent** |

---

## 6. Production Readiness Review

*Considerations for taking this system to a real-world environment.*

- **Security**: Need to securely manage API keys (OpenAI, Gemini) and sanitize user inputs to prevent prompt injection.
- **Guardrails**: Limit the ReAct loop to a maximum of 5 iterations to avoid infinite loops and excessive billing.
- **Scaling**: Connect tools to the official VinWonders database/API instead of mocked data, and implement user session management in the backend to separate conversational contexts.

---
