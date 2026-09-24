import random
import itertools


class config:
    """全局配置类。
    
    使用方式：先调用 config.init() 初始化所有列表/坐标，
    再使用 config.START_POINT 等属性。
    """
    # ===== 地图与渲染参数 =====
    WIDTH = 41  # 地图列数
    HEIGHT = 27  # 地图行数
    blockLength = 15  # 绘制画面时每一个节点方块的边长（前端使用）

    # ===== AGV 参数 =====
    MAX_ROBOT_COUNT = 50  # 机器人数量
    ROBOT_SPEED = 2  # 机器人移动速度,单位m/s
    ROBOT_WAIT_TIME = 3  # 机器人载货、卸货的的等待时间，单位s
    ROBOT_ACCELERATION_TIME = 3  # 机器人速度从0加速到最大速度所需时间

    # ===== 货物参数 =====
    cargoMax = 5000  # 总仓库有多少货物

    # ===== 颜色浓度（前端使用）=====
    busyColor = 13  # 卸货点
    busyColorC = 9  # 载货点

    # ===== 运行时全局状态（会被 init 重置）=====
    finish = "30"  # 完成搬运的时间

    check = 0  # 取货点数量
    pick = []  # 货物堆积的情况(逻辑)
    pick1 = []  # 货物堆积的情况(物理)

    saftyPos = (int)((WIDTH - 1) / 7)  # 小车不堵车的安全距离

    loadPs = 1  # 统计出逻辑货物有多少
    loadPM = 1  # 统计出物理货物有多少

    pickPoint = []  # 设置任务分发的
    MaxPickPoint = 0  # 最大的任务载货点
    startPos1 = []  # 用来存开始坐标的
    endPos1 = []  # 用来存结束坐标的

    timeDis = 60  # 一辆人工小车到达的时间间隔
    ArriveTime = 5  # 一辆人工小车分发货物的时间间隔
    disputOn = -1  # 分发的状态
    checkPos = 0  # 当前检查具体到哪个up口了

    debug = 500  # 找路径的时间，如果没找着路就返回，避免死循环

    checkR = 0  # 卸货点数量
    checkR1 = 0  # 上/下卸货点数量
    checkR2 = 0  # 竖卸货点数量

    relW1 = []  # 横向的卸货点货物堆积的情况(上)
    relW2 = []  # 横向的卸货点货物堆积的情况(下)
    relH = []  # 竖向的卸货点货物堆积的情况

    start = -1  # 开始结束判断

    MaxloadP = 30  # 单个载货点最大负载
    MaxloadR = 20  # 单个卸货点最大负载

    cargo = 0  # 总仓库剩余多少件货物
    removeGoods = 120  # 把货物拿走的时间

    UpDistribute = 0  # 用于统计在某一时刻,全部载货点的需求是多大
    distriCenter = 300  # 单次补货
    distriCenterCurr = 0  # 分发中心的当前实时的容积
    kn = 1.2  # 分发中心与全部载货点的容积之比

    orderSize = 0  # 一个订单，大小是分发中心的1/5 - 1/3
    orderCollect = 0  # 订单编号
    orderProcessing = 0  # 记录已处理的订单

    # ===== 停车点坐标 =====
    parX = 3
    parY = 1  # 都是停车点的横竖坐标

    parX_t = 5
    parY_t = 3  # 临时停车坐标

    STOP_POINT = []  # 停车点
    STOP_POINT_TEMP = []  # 临时停车点

    # ===== 载货/卸货点坐标 =====
    ROOT_LOCATION = []  # 机器人初始位置
    START_POINT = []  # 载货点（出发点）
    START_POINTcop = []  # 用于判断载货点有没有被占用
    END_POINT = []  # 卸货点
    END_POINTup = []  # 上方载货点
    END_POINTdown = []  # 下方载货点
    END_POINTfront = []  # 竖直载货点

    @classmethod
    def init(cls):
        """初始化所有列表型全局状态。在创建仿真引擎前调用一次。"""
        # 重置所有运行时状态
        cls.check = 0
        cls.pick = []
        cls.pick1 = []
        cls.cargo = cls.cargoMax
        cls.distriCenterCurr = 0
        cls.checkR = 0
        cls.checkR1 = 0
        cls.checkR2 = 0
        cls.relW1 = []
        cls.relW2 = []
        cls.relH = []
        cls.start = -1
        cls.orderProcessing = 0
        cls.orderCollect = 0
        cls.UpDistribute = 0
        cls.finish = "30"
        cls.MaxPickPoint = 0
        cls.startPos1 = []
        cls.endPos1 = []
        cls.checkPos = 0
        cls.STOP_POINT = []
        cls.STOP_POINT_TEMP = []
        cls.ROOT_LOCATION = []
        cls.START_POINT = []
        cls.START_POINTcop = []
        cls.END_POINT = []
        cls.END_POINTup = []
        cls.END_POINTdown = []
        cls.END_POINTfront = []

        # ===== 机器人初始位置（随机）=====
        for i in range(1, cls.MAX_ROBOT_COUNT + 1):
            cls.ROOT_LOCATION.append((random.randint(1, cls.HEIGHT - 2), random.randint(1, cls.WIDTH - 2)))

        # ===== 载货点（出发点）=====
        for i in range(1, cls.HEIGHT, 3):
            cls.START_POINT.append((i, 0))
            cls.pickPoint.append((i, 0))
            cls.START_POINTcop.append((i, 0, 0))

        # ===== 卸货点（接收点）=====
        for i in range(3, cls.WIDTH, 3):
            cls.END_POINT.append((cls.HEIGHT - 1, i))
            cls.END_POINTdown.append((cls.HEIGHT - 1, i))

        for i in range(3, cls.WIDTH, 3):
            cls.END_POINT.append((0, i))
            cls.END_POINTup.append((0, i))

        for i in range(2, cls.HEIGHT - 1, 3):
            cls.END_POINT.append((i, cls.WIDTH - 1))
            cls.END_POINTfront.append((i, cls.WIDTH - 1))

        # ===== 计算载货点数量并初始化货物 =====
        for i in range(cls.HEIGHT):
            if i == 1:
                cls.check += 1
                cls.pick.append(0)
                cls.pick1.append(0)
            elif (i - 1) % 3 == 0:
                cls.check += 1
                cls.pick.append(0)
                cls.pick1.append(0)

        # 初始填满载货点
        for i in range(len(cls.START_POINT)):
            if cls.cargo > cls.MaxloadP:
                cls.cargo -= cls.MaxloadP
                cls.pick[i] = cls.MaxloadP
                cls.pick1[i] = cls.MaxloadP
            else:
                cls.pick[i] = cls.cargo
                cls.pick1[i] = cls.cargo
                cls.cargo = 0

        # ===== 计算卸货点数量 =====
        for i in range(cls.WIDTH):
            if i == 0:
                continue
            elif i % 3 == 0:
                cls.checkR += 2
                cls.relW1.append(0)
                cls.relW2.append(0)
                cls.checkR1 += 1
        for i in range(cls.HEIGHT - 1):
            if i == 2:
                cls.checkR += 1
                cls.relH.append(0)
                cls.checkR2 += 1
            elif (i - 2) % 3 == 0:
                cls.checkR += 1
                cls.relH.append(0)
                cls.checkR2 += 1

        # ===== 临时停车点 =====
        for i in range((int)(cls.WIDTH / 3) - 1):
            for j in range((int)(cls.HEIGHT / 3)):
                cls.STOP_POINT_TEMP.append((cls.parY_t, cls.parX_t))
                cls.parY_t += 2
            cls.parX_t += 2
            cls.parY_t = 3

        # ===== 正式停车点 =====
        for i in range((int)(cls.WIDTH / 3) - 1):
            for j in range((int)(cls.HEIGHT / 3)):
                cls.STOP_POINT.append((cls.parY, cls.parX))
                cls.parY += 3
            cls.parX += 3
            cls.parY = 1
