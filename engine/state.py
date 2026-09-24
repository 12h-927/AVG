"""全局仿真状态管理器（单例）。

从原 map_board.py 的 MapBoard.__init__ 中提取所有非 GUI 状态，
集中管理地图、AGV 列表、上下货点列表、统计信息等。
"""
from core.config import config
from core.entity import AGV, DownPoint, UpPoint
from core import task_generator


class SimulationState:
    """仿真状态单例。每次 reset() 重新初始化所有数据。"""

    _instance = None

    def __init__(self):
        self.reset()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reset(self):
        """重新初始化整个仿真环境。"""
        # 先重置 config 的全局状态
        config.init()

        # ===== 地图 =====
        self.Map = []
        for i in range(config.HEIGHT):
            col = []
            for j in range(config.WIDTH):
                col.append(0)
            self.Map.append(col)

        # ===== 统计变量 =====
        self.count = 0  # 已搬运数量
        self.time_count = 0  # 仿真时间
        self.busy = 0  # 繁忙机器人数
        self.task1 = 1
        self.no_hypotenuse = False
        self.running = False

        # ===== AGV 列表 =====
        self.agvList = []
        for i in range(config.MAX_ROBOT_COUNT):
            agv = AGV()
            agv.currentPos = config.STOP_POINT[i]
            if i < config.loadPM / 2:
                agv.task = task_generator.generate_task()
                agv.endPos = ((config.MaxPickPoint, 0))
            else:
                agv.endPos = config.STOP_POINT[i]
            agv.stationR = config.endPos1
            agv.taskFinish = 0
            agv.fast = 1
            agv.tempPos = ((-1, -1))
            agv.prevPos = config.STOP_POINT[i]
            self.agvList.append(agv)

        # ===== AGV 颜色（RGB 元组）=====
        self.colorList = [(90, 193, 250)] * config.MAX_ROBOT_COUNT

        # ===== 卸货点列表 =====
        self.downPointList = []
        for i in range(len(config.END_POINT)):
            downPoint = DownPoint()
            downPoint.pos = config.END_POINT[i]
            self.downPointList.append(downPoint)

        # ===== 载货点列表 =====
        self.upPointList = []
        for i in range(len(config.START_POINT)):
            upPoint = UpPoint()
            upPoint.pos = config.START_POINT[i]
            self.upPointList.append(upPoint)

        # ===== 用于记录起始/终止点使用次数（统计图用）=====
        self.sequence_start_point = {}
        self.sequence_end_point = {}

    def get_status(self):
        """获取当前状态的快照，用于 WebSocket 推送给前端。"""
        return {
            "time": self.time_count,
            "count": self.count,
            "busy": self.busy,
            "cargo": config.cargo,
            "cargoMax": config.cargoMax,
            "orderProcessing": config.orderProcessing,
            "distriCenter": config.distriCenter,
            "running": self.running,
            "finish": config.finish if config.cargo == 0 and self.busy == 0 else None,
            # 地图
            "width": config.WIDTH,
            "height": config.HEIGHT,
            "blockLength": config.blockLength,
            # AGV
            "agvs": [
                {
                    "id": i,
                    "x": self.agvList[i].currentPos[0],
                    "y": self.agvList[i].currentPos[1],
                    "color": self.colorList[i],
                    "endPos": list(self.agvList[i].endPos),
                    "lowSpeed": self.agvList[i].lowSpeedFlags,
                }
                for i in range(len(self.agvList))
            ],
            # 载货点
            "upPoints": [
                {
                    "x": config.START_POINT[i][0],
                    "y": config.START_POINT[i][1],
                    "pick": config.pick[i],  # 逻辑
                    "pick1": config.pick1[i],  # 物理
                    "maxLoad": config.MaxloadP,
                }
                for i in range(len(config.START_POINT))
            ],
            # 卸货点
            "downPoints": [
                {
                    "x": self.downPointList[i].pos[0],
                    "y": self.downPointList[i].pos[1],
                    "goods": self.downPointList[i].goodsCount,
                    "status": self.downPointList[i].status,
                    "maxLoad": config.MaxloadR,
                }
                for i in range(len(self.downPointList))
            ],
            # 停车点
            "stopPoints": list(config.STOP_POINT),
            "stopPointsTemp": list(config.STOP_POINT_TEMP),
            # START/END 用于前端识别
            "startPoints": [list(p) for p in config.START_POINT],
            "endPoints": [list(p) for p in config.END_POINT],
        }
