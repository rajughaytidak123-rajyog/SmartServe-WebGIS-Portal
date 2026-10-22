import os
import sys
import uvicorn
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("=" * 70)
    print("  SMARTSERVE GIS - FASTAPI SPATIAL BACKEND SERVER")
    print("=" * 70)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("[*] Starting server at: http://127.0.0.1:8000")
    print("[*] Interactive Swagger UI: http://127.0.0.1:8000/docs")
    print("[*] ReDoc API Reference: http://127.0.0.1:8000/redoc")
    print("[*] Health Check: http://127.0.0.1:8000/health")
    print("=" * 70)

    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
