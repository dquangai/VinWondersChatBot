"""
Entry point for VinWonders Travel Assistant web app.

Run:
    python web_app.py

Then open:
    http://127.0.0.1:7860
"""

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


try:
    from backend.app import main
except Exception as exc:
    print("=" * 60)
    print("Không thể import backend.app")
    print("=" * 60)
    print(f"Lỗi: {exc}")
    print()
    print("Bạn hãy kiểm tra:")
    print("1. File backend/app.py có tồn tại không.")
    print("2. Thư mục backend có file __init__.py không.")
    print("3. Thư mục src có file __init__.py không.")
    print("4. Bạn đang chạy lệnh ở root project chưa.")
    print()
    print("Lệnh đúng nên là:")
    print("    python web_app.py")
    print("=" * 60)
    raise


if __name__ == "__main__":
    main()