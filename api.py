import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from dotenv import load_dotenv
from src.agent.agent import ReActAgent
from src.tools.vinwonders_tools import vinwonders_tools

# Load environment variables
load_dotenv()

app = FastAPI(title="ViVu AI Backend")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LLM Provider Init
def get_llm_provider():
    provider_name = os.getenv("DEFAULT_PROVIDER", "openai").lower()
    if provider_name == "openai":
        from src.core.openai_provider import OpenAIProvider
        return OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=os.getenv("DEFAULT_MODEL", "gpt-4o")
        )
    elif provider_name == "gemini":
        from src.core.gemini_provider import GeminiProvider
        return GeminiProvider(
            api_key=os.getenv("GEMINI_API_KEY"),
            model_name=os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
        )
    else:
        raise ValueError(f"Unknown provider: {provider_name}")

# Khởi tạo Agent 1 lần
try:
    llm = get_llm_provider()
    agent = ReActAgent(llm=llm, tools=vinwonders_tools, max_steps=10)
except Exception as e:
    print(f"Failed to initialize LLM: {e}")
    agent = None

class ChatRequest(BaseModel):
    message: str
    history: Optional[str] = ""

class LocationData(BaseModel):
    name: str
    rating: float
    reviews: str
    time: str
    price: str
    description: str
    images: List[str]

class ChatResponse(BaseModel):
    reply: str
    location: Optional[LocationData] = None

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not agent:
        return ChatResponse(reply="Agent is not initialized due to missing API keys.")

    # Xây dựng prompt chứa lịch sử
    if request.history:
        prompt = f"Lịch sử hội thoại trước đó:\n{request.history}\n\nNgười dùng mới nói: {request.message}"
    else:
        prompt = request.message

    # Gọi Agent
    try:
        final_answer = agent.run(prompt)
    except Exception as e:
        final_answer = f"Lỗi hệ thống: {str(e)}"

    # Phân tích kết quả xem có gợi ý địa điểm nào cụ thể không (Mock logic)
    # Trong thực tế, Agent có thể trả về JSON cấu trúc thay vì text thuần
    location_data = None
    if "Thác Datanla" in final_answer or "Đà Lạt" in final_answer:
        location_data = LocationData(
            name="Thác Datanla Đà Lạt",
            rating=4.2,
            reviews="1.2k đánh giá",
            time="07:30 - 17:00",
            price="30.000đ - 170.000đ",
            description="Một trong những thác nước đẹp và dễ tiếp cận nhất Đà Lạt. Nổi tiếng với hệ thống máng trượt xuyên rừng thông dài nhất Đông Nam Á.",
            images=[
                "https://images.unsplash.com/photo-1559592413-7cec4d0cae2b?w=500&q=80",
                "https://images.unsplash.com/photo-1614095818965-02102f4fc6ac?w=500&q=80",
                "https://images.unsplash.com/photo-1596422846543-74c6e91ec088?w=500&q=80",
                "https://images.unsplash.com/photo-1582298538104-fe2e74c878f1?w=500&q=80"
            ]
        )
    elif "Nha Trang" in final_answer:
        location_data = LocationData(
            name="VinWonders Nha Trang",
            rating=4.8,
            reviews="10k đánh giá",
            time="08:00 - 20:00",
            price="600.000đ - 800.000đ",
            description="Công viên giải trí ven biển lớn nhất miền Trung với hàng loạt trò chơi mạo hiểm và show diễn thực cảnh.",
            images=[
                "https://images.unsplash.com/photo-1583417319070-4a69db38a482?w=500&q=80",
                "https://images.unsplash.com/photo-1540541338287-41700207dee6?w=500&q=80",
                "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=500&q=80"
            ]
        )

    return ChatResponse(reply=final_answer, location=location_data)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
