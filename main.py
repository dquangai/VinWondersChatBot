import os
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        if not os.path.exists(".env"):
            return False
        with open(".env", "r", encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]
                os.environ.setdefault(key.strip(), value)
        return True

load_dotenv()

from src.agent.agent import ReActAgent
from src.tools.vinwonders_tools import vinwonders_tools

SAMPLE_REQUEST = """Tôi muốn đi VinWonders vào cuối tuần này cùng nhóm bạn.
Hãy gợi ý điểm vui chơi phù hợp, kiểm tra khuyến mãi hiện tại, sự kiện hoặc show đang có / sắp diễn ra,
rồi đề xuất lịch trình vui chơi hợp lý trong ngày."""


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
            model_name=os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
        )
    elif provider_name == "local":
        from src.core.local_provider import LocalProvider
        return LocalProvider(
            model_path=os.getenv("LOCAL_MODEL_PATH")
        )
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


def print_header():
    provider = os.getenv("DEFAULT_PROVIDER", "gemini")
    model = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
    print("=" * 72)
    print("🎡 VinWonders Tour Guide Agent")
    print(f"Provider: {provider} | Model: {model}")
    print("-" * 72)
    print("Nhập câu hỏi để agent tư vấn điểm vui chơi, ưu đãi, show và lịch trình.")
    print("Lệnh nhanh: demo | help | clear | q")
    print("=" * 72)


def print_help():
    print("\nGợi ý nhập:")
    print("- Tôi muốn đi VinWonders vào cuối tuần này cùng nhóm bạn.")
    print("- Nhóm 4 người từ Hà Nội, thích trò cảm giác mạnh và show buổi tối.")
    print("- demo: chạy đúng kịch bản mẫu trong Agent.md")
    print("- clear: làm sạch màn hình")
    print("- q / quit / exit: thoát chương trình")


def main():
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    print_header()
    
    try:
        llm = get_llm_provider()
    except Exception as e:
        print(f"❌ Không khởi tạo được LLM provider: {e}")
        return

    verbose_agent = os.getenv("AGENT_VERBOSE", "false").lower() in {"1", "true", "yes", "on"}
    agent = ReActAgent(llm=llm, tools=vinwonders_tools, max_steps=10, verbose=verbose_agent)
    
    # Lịch sử hội thoại để Agent có thể nhớ bối cảnh các câu trước
    conversation_history = ""

    while True:
        try:
            user_input = input("\n👤 Bạn: ").strip()
            command = user_input.lower()

            if command in ['quit', 'exit', 'q']:
                print("👋 Tạm biệt! Hẹn gặp lại.")
                break
            if command == "help":
                print_help()
                continue
            if command == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                print_header()
                continue
            if command == "demo":
                user_input = SAMPLE_REQUEST
                print("\n📌 Đang chạy kịch bản mẫu:")
                print(user_input)
            if not user_input:
                print("Bạn nhập yêu cầu du lịch VinWonders để mình tư vấn nhé.")
                continue
            
            # Đưa ngữ cảnh lịch sử vào input nếu có
            if conversation_history:
                prompt_to_agent = f"Lịch sử hội thoại trước đó:\n{conversation_history}\n\nNgười dùng mới nói: {user_input}"
            else:
                prompt_to_agent = user_input

            print("\n🤖 Agent đang phân tích nhu cầu và gọi tool phù hợp...")
            
            # Chạy ReAct Agent
            final_answer = agent.run(prompt_to_agent)
            
            print("\n" + "=" * 72)
            print(f"🤖 Chatbot:\n{final_answer}")
            print("=" * 72)
            
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
