"""REST API 路由。"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from engine.state import SimulationState
from engine.simulation import SimulationEngine
from api.ws import manager

router = APIRouter(prefix="/api")


@router.post("/sim/start")
async def start_simulation():
    """启动仿真。"""
    engine = SimulationEngine.get_instance()
    ok = engine.start(manager.broadcast)
    return {"ok": ok, "running": engine.state.running}


@router.post("/sim/stop")
async def stop_simulation():
    """停止仿真。"""
    engine = SimulationEngine.get_instance()
    engine.stop()
    return {"ok": True, "running": False}


@router.post("/sim/reset")
async def reset_simulation():
    """重置仿真。"""
    engine = SimulationEngine.get_instance()
    engine.reset()
    return {"ok": True, "running": False}


@router.get("/sim/status")
async def get_status():
    """获取当前状态快照。"""
    state = SimulationState.get_instance()
    return state.get_status()


@router.get("/config")
async def get_config():
    """获取当前配置。"""
    from core.config import config
    return {
        "WIDTH": config.WIDTH,
        "HEIGHT": config.HEIGHT,
        "blockLength": config.blockLength,
        "MAX_ROBOT_COUNT": config.MAX_ROBOT_COUNT,
        "ROBOT_SPEED": config.ROBOT_SPEED,
        "ROBOT_WAIT_TIME": config.ROBOT_WAIT_TIME,
        "ROBOT_ACCELERATION_TIME": config.ROBOT_ACCELERATION_TIME,
        "cargoMax": config.cargoMax,
        "MaxloadP": config.MaxloadP,
        "MaxloadR": config.MaxloadR,
        "distriCenter": config.distriCenter,
        "timeDis": config.timeDis,
        "saftyPos": config.saftyPos,
    }


class ConfigUpdate(BaseModel):
    """配置更新请求体。"""
    MAX_ROBOT_COUNT: Optional[int] = None
    ROBOT_SPEED: Optional[float] = None
    ROBOT_WAIT_TIME: Optional[float] = None
    cargoMax: Optional[int] = None


@router.post("/config")
async def update_config(cfg: ConfigUpdate):
    """修改配置（需重置后生效）。"""
    from core.config import config
    if cfg.MAX_ROBOT_COUNT is not None:
        config.MAX_ROBOT_COUNT = cfg.MAX_ROBOT_COUNT
    if cfg.ROBOT_SPEED is not None:
        config.ROBOT_SPEED = cfg.ROBOT_SPEED
    if cfg.ROBOT_WAIT_TIME is not None:
        config.ROBOT_WAIT_TIME = cfg.ROBOT_WAIT_TIME
    if cfg.cargoMax is not None:
        config.cargoMax = cfg.cargoMax
    return {"ok": True, "msg": "配置已更新，请点击重置仿真使其生效"}
