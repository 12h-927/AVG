"""FastAPI 应用入口。

启动命令：uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from api.routes import router
from api.ws import manager
from engine.state import SimulationState
from engine.simulation import SimulationEngine

app = FastAPI(title="AGV 物流调度平台", version="1.0.0")

# 注册 REST 路由
app.include_router(router)


@app.websocket("/ws/simulation")
async def ws_simulation(websocket: WebSocket):
    """WebSocket 端点：推送仿真状态。"""
    await manager.connect(websocket)
    try:
        # 连接时立即推送一次当前状态
        state = SimulationState.get_instance()
        await websocket.send_json(state.get_status())
        # 保持连接，仿真循环会通过 manager.broadcast 自动推送
        while True:
            await __import__("asyncio").sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket 异常: {e}")
        manager.disconnect(websocket)


@app.on_event("startup")
async def on_startup():
    """启动时初始化仿真状态。"""
    SimulationState.get_instance()
    SimulationEngine.get_instance()
    print("AGV 物流调度平台启动完成")
    print("访问 http://localhost:8000 查看仿真界面")


# 挂载静态文件
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def index():
    """返回主页面。"""
    return FileResponse(os.path.join(static_dir, "index.html"))
