"""AGV 物流调度平台 - Web 入口

启动方式：
    python main.py
或
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
