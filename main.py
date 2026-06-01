import os
import sys
from dotenv import load_dotenv
from src.agent.agent import ReActAgent
from src.tools.vinwonders_tools import vinwonders_tools
from src.telemetry.logger import logger

def get_llm_provider():
    provider_name = os.getenv("DEFAULT_PROVIDER", "gemini").lower()
    
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
    elif provider_name == "local":
        from src.core.local_provider import LocalProvider
        return LocalProvider(
            model_path=os.getenv("LOCAL_MODEL_PATH")
        )
    else:
        raise ValueError(f"Unknown provider: {provider_name}")

def main():
    # Load environment variables
    load_dotenv()
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    print("="*60)
    print("🚀 Khởi động VinWonders Tour Guide Chatbot...")
    print("Gõ 'quit', 'exit' hoặc 'q' để thoát.")
    print("="*60)
    
    try:
        llm = get_llm_provider()
    except Exception as e:
        print(f"Error initializing LLM provider: {e}")
        return

    agent = ReActAgent(llm=llm, tools=vinwonders_tools, max_steps=10)
    
    # Lịch sử hội thoại để Agent có thể nhớ bối cảnh các câu trước
    conversation_history = ""

    while True:
        try:
            user_input = input("\n👤 Bạn: ")
            if user_input.strip().lower() in ['quit', 'exit', 'q']:
                print("👋 Tạm biệt! Hẹn gặp lại.")
                break
            if not user_input.strip():
                continue
            
            # Đưa ngữ cảnh lịch sử vào input nếu có
            if conversation_history:
                prompt_to_agent = f"Lịch sử hội thoại trước đó:\n{conversation_history}\n\nNgười dùng mới nói: {user_input}"
            else:
                prompt_to_agent = user_input

            print("\n🤖 Agent đang suy nghĩ...")
            
            # Chạy ReAct Agent
            final_answer = agent.run(prompt_to_agent)
            
            print("=" * 60)
            print(f"🤖 Chatbot: {final_answer}")
            print("=" * 60)
            
            # Cập nhật lịch sử hội thoại (giữ lại 1-2 lượt gần nhất để tránh quá dài)
            conversation_history += f"User: {user_input}\nAgent: {final_answer}\n"
            
            # Giới hạn lịch sử khoảng 1000 ký tự cuối để tránh đầy context window
            if len(conversation_history) > 1000:
                conversation_history = "..." + conversation_history[-1000:]

        except KeyboardInterrupt:
            print("\n👋 Tạm biệt! Hẹn gặp lại.")
            break
        except Exception as e:
            print(f"\n❌ Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    main()
