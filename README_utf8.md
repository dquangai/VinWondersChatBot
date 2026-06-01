# VinWonders Travel Assistant

VinWonders Travel Assistant là chatbot tư vấn du lịch sử dụng mô hình ReAct Agent để hỗ trợ người dùng lên kế hoạch vui chơi tại VinWonders. Ứng dụng có thể gợi ý điểm đến phù hợp, kiểm tra nhóm thông tin khuyến mãi, tham khảo show hoặc sự kiện, và đề xuất lịch trình vui chơi trong ngày dựa trên nhu cầu của người dùng.

## Thành viên thực hiện

| Họ và tên | Mã sinh viên |
| --- | --- |
| Đoàn Minh Quang | 2A202600757 |
| Trương Thành Thảo | 2A202600735 |

## Mục tiêu dự án

Dự án được xây dựng nhằm mô phỏng một trợ lý du lịch thông minh cho VinWonders, trong đó chatbot có khả năng:

- Hiểu yêu cầu tư vấn du lịch bằng tiếng Việt.
- Hỏi thêm thông tin khi yêu cầu của người dùng chưa đủ rõ.
- Sử dụng các công cụ nội bộ theo vòng lặp Thought, Action, Observation, Final Answer.
- Tóm tắt nhu cầu người dùng như ngày đi, số người, nơi xuất phát và sở thích.
- Đưa ra gợi ý điểm đến, ưu đãi, show hoặc sự kiện, và lịch trình tham khảo.

## Tính năng chính

- **Chatbot ReAct Agent**: điều phối suy luận và gọi tool theo từng bước.
- **Giao diện web**: giao diện chat trực quan, có khung thông tin chuyến đi và gợi ý nhanh.
- **Chế độ CLI**: hỗ trợ chạy chatbot trực tiếp trong terminal.
- **Hỗ trợ nhiều nhà cung cấp LLM**: OpenAI, Gemini và mô hình local thông qua `llama-cpp-python`.
- **Telemetry cơ bản**: ghi log sự kiện agent, tool call và lỗi vào thư mục `logs`.
- **Cấu hình linh hoạt**: sử dụng file `.env` để thay đổi provider, model, host và port.

## Kiến trúc tổng quan

```text
Mini-Project/
├── backend/
│   ├── __init__.py
│   └── app.py                  # HTTP server và API chat
├── frontend/
│   └── index.html              # Giao diện web
├── src/
│   ├── agent/
│   │   └── agent.py            # ReAct Agent
│   ├── core/
│   │   ├── llm_provider.py     # Interface provider
│   │   ├── openai_provider.py  # Provider OpenAI
│   │   ├── gemini_provider.py  # Provider Gemini
│   │   └── local_provider.py   # Provider local GGUF
│   ├── telemetry/
│   │   ├── logger.py           # Structured logger
│   │   └── metrics.py          # Theo dõi metric cơ bản
│   └── tools/
│       └── vinwonders_tools.py # Tool tư vấn VinWonders
├── main.py                     # Entry point CLI
├── web_app.py                  # Entry point web app
├── requirements.txt            # Thư viện phụ thuộc
├── .env.example                # File cấu hình mẫu
└── README.md
```

## Công nghệ sử dụng

- Python 3.10+
- `http.server` cho backend web đơn giản
- HTML, CSS, JavaScript thuần cho frontend
- OpenAI API
- Google Generative AI API
- `llama-cpp-python` cho mô hình local
- `python-dotenv` cho cấu hình môi trường

## Cài đặt

### 1. Clone hoặc mở project

```bash
cd VinWondersChatBot
```

### 2. Tạo môi trường ảo

Trên Windows:

```bash
py -m venv .venv
.venv\Scripts\activate
```

Trên macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Cài đặt thư viện

```bash
pip install -r requirements.txt
```

Lưu ý: `llama-cpp-python` có thể cần thêm công cụ build tùy theo hệ điều hành. Nếu chỉ dùng OpenAI hoặc Gemini, bạn có thể chưa cần cấu hình model local.

## Cấu hình môi trường

Tạo file `.env` từ file mẫu:

```bash
copy .env.example .env
```

Trên macOS/Linux:

```bash
cp .env.example .env
```

Các biến cấu hình quan trọng:

| Biến | Ý nghĩa |
| --- | --- |
| `DEFAULT_PROVIDER` | Provider mặc định: `openai`, `gemini` hoặc `local` |
| `DEFAULT_MODEL` | Tên model sử dụng |
| `OPENAI_API_KEY` | API key cho OpenAI |
| `GEMINI_API_KEY` | API key cho Gemini |
| `LOCAL_MODEL_PATH` | Đường dẫn tới file model GGUF khi dùng provider local |
| `WEB_HOST` | Host chạy web app |
| `WEB_PORT` | Port chạy web app |
| `FRONTEND_DIR` | Đường dẫn thư mục frontend |
| `LOG_LEVEL` | Mức log, ví dụ `INFO`, `DEBUG`, `ERROR` |
| `AGENT_VERBOSE` | Bật hoặc tắt log chi tiết của agent |

Ví dụ cấu hình dùng OpenAI:

```env
DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4o
OPENAI_API_KEY=your_openai_api_key_here
WEB_HOST=127.0.0.1
WEB_PORT=7860
```

Ví dụ cấu hình dùng Gemini:

```env
DEFAULT_PROVIDER=gemini
DEFAULT_MODEL=gemini-1.5-flash
GEMINI_API_KEY=your_gemini_api_key_here
WEB_HOST=127.0.0.1
WEB_PORT=7860
```

## Cách chạy ứng dụng

### Chạy giao diện web

```bash
py web_app.py
```

Sau đó mở trình duyệt tại:

```text
http://127.0.0.1:7860
```

### Chạy chatbot trong terminal

```bash
py main.py
```

Một số lệnh nhanh trong CLI:

| Lệnh | Chức năng |
| --- | --- |
| `demo` | Chạy kịch bản mẫu |
| `help` | Hiển thị gợi ý sử dụng |
| `clear` | Xóa màn hình terminal |
| `q`, `quit`, `exit` | Thoát chương trình |

## API chính

Backend cung cấp các endpoint:

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| `GET` | `/api/health` | Kiểm tra trạng thái backend |
| `POST` | `/api/chat` | Gửi tin nhắn người dùng và nhận câu trả lời chatbot |

Ví dụ request tới `/api/chat`:

```json
{
  "message": "Tôi muốn đi VinWonders cuối tuần này cùng nhóm bạn.",
  "history": []
}
```

Ví dụ response:

```json
{
  "answer": "Nội dung tư vấn của chatbot",
  "trip": {
    "group_size": 4,
    "travel_date": "cuối tuần này",
    "location": "Hà Nội",
    "destination": "VinWonders Phú Quốc",
    "interests": ["trò chơi cảm giác mạnh"]
  },
  "trace": [],
  "provider": "gemini",
  "model": "gemini-1.5-flash"
}
```

## Luồng hoạt động của Agent

ReAct Agent xử lý yêu cầu theo các bước:

1. Nhận câu hỏi từ người dùng.
2. Cập nhật ngữ cảnh hội thoại ngắn hạn.
3. Xác định intent như tư vấn điểm đến, kiểm tra khuyến mãi, xem show hoặc lập lịch trình.
4. Hỏi thêm thông tin nếu dữ liệu còn thiếu.
5. Gọi tool phù hợp.
6. Tổng hợp kết quả và trả lời bằng tiếng Việt tự nhiên.

Các tool chính:

| Tool | Mô tả |
| --- | --- |
| `get_user_preferences` | Tóm tắt nhu cầu người dùng |
| `search_vinwonders_destinations` | Gợi ý điểm VinWonders phù hợp |
| `check_current_promotions` | Trả về nhóm thông tin ưu đãi tham khảo |
| `check_events_and_shows` | Trả về nhóm thông tin show hoặc sự kiện tham khảo |
| `build_itinerary` | Xây dựng lịch trình vui chơi trong ngày |

## Lưu ý dữ liệu

Thông tin khuyến mãi, giá vé, lịch show và sự kiện trong project hiện là dữ liệu mô phỏng để phục vụ demo luồng agent. Khi sử dụng trong thực tế, cần kết nối tới nguồn dữ liệu chính thức hoặc nhắc người dùng kiểm tra lại trên website/app VinWonders trước khi đặt vé và thanh toán.

## Kiểm thử

Hiện project đã khai báo `pytest` trong `requirements.txt`. Có thể chạy kiểm thử bằng lệnh:

```bash
py -m pytest
```

Nếu chưa có test case, lệnh trên sẽ báo không tìm thấy bài kiểm thử. Nên bổ sung unit test cho các phần:

- Phân loại intent trong `ReActAgent`.
- Xử lý context hội thoại.
- Gọi tool trong `vinwonders_tools.py`.
- API `/api/chat` và `/api/health`.

## Hướng phát triển

- Tách session backend theo từng người dùng để tránh dùng chung ngữ cảnh.
- Kết nối dữ liệu khuyến mãi và lịch show với nguồn chính thức.
- Bổ sung test tự động cho agent, tool và API.
- Cải thiện logic chọn điểm đến theo khoảng cách, ngân sách và thời gian di chuyển.
- Thêm streaming response cho giao diện web.
- Triển khai ứng dụng bằng Docker hoặc nền tảng cloud.

## Quy tắc bảo mật

- Không commit file `.env` thật lên Git.
- Không chia sẻ API key trong mã nguồn hoặc log.
- Kiểm tra lại quyền truy cập model trước khi chạy provider OpenAI hoặc Gemini.
- Khi dùng model local, chỉ tải model từ nguồn đáng tin cậy.

## License

Dự án được xây dựng phục vụ mục đích học tập và thực hành xây dựng AI Agent.
