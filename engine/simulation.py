"""异步仿真引擎。

从原 map_board.py 的 start_Search 生成器和 timerEvent 中提取仿真逻辑，
改为异步函数。每 tick 计算所有 AGV 下一步、处理冲突/装卸货/补货，
然后通过回调推送状态给 WebSocket 客户端。
"""
import asyncio
from core.config import config
from core.asearch import A_Search, point
from core import task_generator
from engine.state import SimulationState


class SimulationEngine:
    """仿真引擎：管理仿真循环。"""

    _instance = None

    def __init__(self):
        self.state = SimulationState.get_instance()
        self._task = None  # asyncio.Task 引用

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self, broadcast_callback):
        """启动仿真循环。"""
        if self._task is not None and not self._task.done():
            return False
        self.state.running = True
        config.start = -config.start
        self._broadcast = broadcast_callback
        self._task = asyncio.create_task(self._loop())
        return True

    def stop(self):
        """停止仿真循环。"""
        self.state.running = False
        if self._task is not None and not self._task.done():
            self._task.cancel()
            self._task = None
        return True

    def reset(self):
        """重置仿真。"""
        was_running = self.state.running
        self.stop()
        self.state.reset()
        return True

    async def _loop(self):
        """主仿真循环：每 100ms 跑一帧。"""
        try:
            while self.state.running:
                # CPU 密集的 _tick 放到线程池执行，避免阻塞 asyncio 事件循环
                await asyncio.to_thread(self._tick)
                # 推送状态
                if self._broadcast is not None:
                    snapshot = self.state.get_status()
                    await self._broadcast(snapshot)
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"仿真循环异常: {e}")
            import traceback
            traceback.print_exc()
            self.state.running = False

    def _tick(self):
        """单帧逻辑：对应原 start_Search 一轮 + timerEvent 的装卸货处理。"""
        state = self.state

        # ===== 1. 卸货点货物堆积处理 =====
        for i in range(len(state.downPointList)):
            if state.downPointList[i].goodsCount >= config.MaxloadR:
                state.downPointList[i].removeGoods()

        # ===== 2. 为所有 AGV 计算下一步 =====
        nextStepList = []

        for i in range(len(state.agvList)):
            state.colorList[i] = (90, 193, 250)  # 默认浅蓝色
            agv = state.agvList[i]

            if agv.endPos in config.END_POINT:
                state.colorList[i] = (180, 40, 210)  # 有任务变粉色

            # 如果机器人的出发点和终点不一样，执行 A* 算法
            if agv.currentPos != agv.endPos and agv.endPos != (-1, -1):
                # 判断终点是否被其它 AGV 占据
                destinationOccupied = False
                for k in range(len(state.agvList)):
                    if agv.endPos == state.agvList[k].currentPos:
                        destinationOccupied = True
                        break

                # 判断卸货点是否被关闭
                downPointClosed = False
                downPointNumber = -1
                for k in range(len(state.downPointList)):
                    if agv.endPos == state.downPointList[k].pos:
                        downPointNumber = k
                        break

                if downPointNumber != -1 and downPointNumber < len(state.downPointList):
                    if state.downPointList[downPointNumber].status == 1:
                        downPointClosed = True

                if destinationOccupied or downPointClosed:
                    if destinationOccupied:
                        nextStep = self._handle_occupied_destination(i, agv, state)
                    else:
                        nextStep = self._handle_closed_downpoint(i, agv, state, downPointNumber)
                else:
                    nextStep = self._a_star_step(i, agv, state)

                # 减速进站判断
                if nextStep == agv.endPos:
                    state.colorList[i] = (122, 156, 184)
                    agv.lowSpeedFlags = True

                # 方向变化判断减速
                t = nextStep[0] - agv.currentPos[0]
                k = nextStep[1] - agv.currentPos[1]
                if (t, k) != agv.direction:
                    if agv.direction != (0, 0):
                        agv.lowSpeedFlags = True
                    agv.direction = (t, k)

                # 加速/减速等待
                if agv.lowSpeedFlags:
                    if agv.lowSpeedWait == 0:
                        agv.lowSpeedWait = config.ROBOT_ACCELERATION_TIME
                        nextStep = agv.currentPos
                    elif agv.lowSpeedWait > 1:
                        nextStep = agv.currentPos
                        agv.lowSpeedWait -= 1
                    elif agv.lowSpeedWait == 1:
                        agv.lowSpeedWait = 0
                        agv.lowSpeedFlags = False

                if agv.currentPos == agv.previousStart:
                    agv.lowSpeedFlags = True

                # 让行减速进站的机器人
                for j in range(len(nextStepList)):
                    if nextStep == state.agvList[j].prevPos and state.agvList[j].lowSpeedFlags:
                        nextStep = agv.currentPos

                # 堵车超时处理
                if agv.noMoveCount > 25:
                    agv.noMoveCount = 0
                    print(str(i) + "号小车堵车，坐标->" + str(agv.currentPos))

                point.clear()

                # 冲突处理
                for j in range(len(nextStepList)):
                    if nextStep == nextStepList[j]:
                        nextStep = agv.currentPos
                        if not destinationOccupied:
                            state.colorList[j] = (210, 40, 40)
                            state.colorList[i] = (210, 40, 40)
                        agv.noMoveCount += 1
                        state.agvList[j].noMoveCount += 1
                        break

                agv.prevPos = agv.currentPos
                nextStepList.append(nextStep)
            else:
                nextStepList.append(agv.currentPos)

        # 再次检查冲突
        for i in range(len(state.agvList)):
            for j in range(len(state.agvList)):
                if i != j and nextStepList[i] == nextStepList[j]:
                    nextStepList[i] = state.agvList[i].currentPos
                    break

        if nextStep == state.agvList[i].currentPos:
            state.agvList[i].noMoveCount += 1

        # ===== 3. 更新地图和位置 =====
        for i in range(len(state.agvList)):
            agv = state.agvList[i]
            if agv.currentPos != agv.endPos and agv.endPos != (-1, -1) and not agv.lowSpeedFlags:
                state.Map[agv.currentPos[0]][agv.currentPos[1]] = 0
                agv.currentPos = nextStepList[i]
            else:
                state.Map[agv.currentPos[0]][agv.currentPos[1]] = 1
                agv.currentPos = nextStepList[i]
        for i in range(len(state.agvList)):
            agv = state.agvList[i]
            state.Map[agv.currentPos[0]][agv.currentPos[1]] = 1

        # ===== 4. 补货逻辑 =====
        sec = state.time_count
        if sec % config.timeDis == 0 and sec > 0:
            self._handle_replenishment(state)

        # ===== 5. 装卸货处理（原 timerEvent）=====
        for i in range(len(state.agvList)):
            agv = state.agvList[i]
            if agv.currentPos == agv.endPos or agv.endPos == (-1, -1):
                self._handle_pickup_dropoff(i, agv, state)

        # ===== 6. 统计繁忙机器人 =====
        state.busy = 0
        for j in range(config.MAX_ROBOT_COUNT):
            a = state.agvList[j]
            if a.endPos[1] != 0 and a.endPos[0] != -1 and (a.endPos != config.STOP_POINT[j] and a.endPos != config.STOP_POINT_TEMP[j]):
                state.busy += 1

        # ===== 7. 卸货点货物搬移 =====
        for j in range(len(state.downPointList)):
            if state.downPointList[j].goodsCount >= config.MaxloadR:
                state.downPointList[j].removeGoods()

        # ===== 8. 时间推进和完成判定 =====
        if config.cargo == 0 and state.busy == 0:
            for i in range(config.MAX_ROBOT_COUNT):
                state.agvList[i].endPos = config.STOP_POINT[i]
            minute = int(state.time_count / 60)
            second = int(state.time_count % 60)
            config.finish = "完成用时" + str(minute) + "分" + str(second) + "秒"
        else:
            state.time_count += 1 / config.ROBOT_SPEED

    def _a_star_step(self, i, agv, state):
        """标准 A* 寻路。"""
        search = A_Search(
            point(agv.currentPos[0], agv.currentPos[1]),
            point(agv.endPos[0], agv.endPos[1]),
            state.Map,
            state.no_hypotenuse,
        )
        nextStep = search.process()
        if nextStep is None:
            print(str(i) + "号小车触发空坐标保护" + str(agv.currentPos))
            nextStep = agv.currentPos
        if not nextStep:
            nextStep = agv.currentPos
        agv.noMoveCount = 0
        return nextStep

    def _handle_occupied_destination(self, i, agv, state):
        """终点被占用时的处理逻辑（原 start_Search 中 destinationOccupied 分支）。"""
        for k in range(len(state.agvList)):
            if agv.endPos == state.agvList[k].currentPos:
                if agv.fast == 1:
                    agv.fast = 0
                if agv.endPos[1] == 0 and ((agv.endPos[0] - 1) % 3 == 0 or agv.endPos[0] == 0):
                    # 载货点被占，让其对齐
                    if agv.currentPos[0] != agv.endPos[0]:
                        if agv.endPos[0] > agv.currentPos[0]:
                            return (agv.currentPos[0] + 1, agv.currentPos[1])
                        elif agv.endPos[0] < agv.currentPos[0]:
                            return (agv.currentPos[0] - 1, agv.currentPos[1])
                    elif (int)(agv.currentPos[1]) >= config.saftyPos:
                        return (agv.currentPos[0], agv.currentPos[1] - 1)
                    return agv.currentPos
                else:
                    # 卸货点被占，计算距离
                    A1, A2 = agv.currentPos[0], agv.currentPos[1]
                    B1, B2 = agv.endPos[0], agv.endPos[1]
                    L1 = (int)(pow((pow((A1 - B1), 2) + pow((A2 - B2), 2)), 0.5))
                    if L1 >= config.saftyPos:
                        nextStep = self._a_star_step(i, agv, state)
                        if nextStep is None:
                            nextStep = agv.currentPos
                        return nextStep
                    elif L1 <= config.saftyPos:
                        if (agv.currentPos[1] == 0 and agv.endPos[1] < config.WIDTH / 4):
                            nextStep = self._a_star_step(i, agv, state)
                            if nextStep is None:
                                nextStep = agv.currentPos
                            return nextStep
                        else:
                            return agv.currentPos
                    return agv.currentPos
        return agv.currentPos

    def _handle_closed_downpoint(self, i, agv, state, downPointNumber):
        """卸货点关闭时的处理逻辑。"""
        if downPointNumber != -1 and downPointNumber < len(state.downPointList):
            if state.downPointList[downPointNumber].status != 1:
                # down点没被占
                if ((agv.currentPos[1] % 3 == 0) and (agv.currentPos[0] == 0 or agv.currentPos[1] == config.HEIGHT - 1)):
                    nextStep = self._a_star_step(i, agv, state)
                    if nextStep is None:
                        nextStep = agv.currentPos
                    return nextStep
                elif ((agv.currentPos[1] % 3 == 0) and ((agv.currentPos[0] + 1) % 3 == 0)):
                    nextStep = self._a_star_step(i, agv, state)
                    if nextStep is None:
                        nextStep = agv.currentPos
                    return nextStep
                else:
                    return self._a_star_step(i, agv, state)
            else:
                # down点被占
                search = A_Search(
                    point(agv.currentPos[0], agv.currentPos[1]),
                    point(agv.endPos[0], agv.endPos[1]),
                    state.Map,
                    state.no_hypotenuse,
                )
                nextStep = search.process()
                if nextStep is None:
                    nextStep = agv.currentPos
                if nextStep == agv.endPos:
                    nextStep = agv.currentPos
                return nextStep
        return agv.currentPos

    def _handle_replenishment(self, state):
        """补货逻辑（原 start_Search 中 timeDis 分支）。"""
        task_generator.reflush()
        if config.cargo >= config.distriCenter:
            print("正在补满载货点货物")
            config.orderProcessing += 1
            config.distriCenterCurr = config.distriCenter
        elif config.cargo > 0 and config.distriCenter > config.cargo:
            print("已经全部补满载货点货物")
            config.orderProcessing += 1
            config.distriCenterCurr = config.cargo
            config.cargo = 0

        if config.cargo >= 0 and config.distriCenterCurr > 0:
            cur = config.distriCenterCurr
            config.checkPos = (int)(config.check / 3)
            while True:
                if (config.pick1[config.checkPos] < config.MaxloadP) and config.distriCenterCurr > 0:
                    if config.distriCenterCurr > (config.MaxloadP - config.pick1[config.checkPos]):
                        temp = config.MaxloadP - config.pick1[config.checkPos]
                        config.distriCenterCurr -= temp
                        config.pick1[config.checkPos] += temp
                        config.pick[config.checkPos] += temp
                        config.cargo -= temp
                        if config.checkPos + 1 < config.check:
                            config.checkPos += 1
                        else:
                            config.checkPos = 0
                    elif (config.distriCenterCurr <= (config.MaxloadP - config.pick1[config.checkPos])):
                        temp = config.distriCenterCurr
                        config.distriCenterCurr = 0
                        config.pick1[config.checkPos] += temp
                        config.pick[config.checkPos] += temp
                        config.cargo -= temp
                        if config.checkPos + 1 < config.check:
                            config.checkPos += 1
                        else:
                            config.checkPos = 0
                        break
                else:
                    if config.distriCenterCurr == 0 and config.cargo == 0:
                        print("已经补满全部货物")
                    else:
                        print("已经补满" + str(cur - config.distriCenterCurr))
                        config.distriCenterCurr = 0
                    break

        config.loadPs = 1
        config.loadPM = 1
        task_generator.reflush()
        if config.loadPM > 0:
            for i in range(config.MAX_ROBOT_COUNT):
                if i + 1 > config.loadPs:
                    break
                if (state.agvList[i].endPos == config.STOP_POINT[i] or state.agvList[i].endPos == config.STOP_POINT_TEMP[i]) and config.loadPs > 0:
                    state.agvList[i].task = task_generator.generate_task()
                    state.agvList[i].stationR = config.endPos1
                    state.agvList[i].endPos = config.startPos1
                    task_generator.reflush()

    def _handle_pickup_dropoff(self, i, agv, state):
        """装卸货处理（原 timerEvent 中载货点/卸货点逻辑）。"""
        # 载货点处理
        for j in range(len(config.START_POINT)):
            if agv.currentPos == config.START_POINT[j]:
                config.START_POINTcop[j] = (config.START_POINTcop[j][0], config.START_POINTcop[j][1], 1)
                agv.previousStart = config.START_POINT[j]

                if agv.load_or_unload_wait_countdown == 0:
                    agv.endPos = agv.stationR[0]
                    agv.taskFinish = 0
                    if agv.stationR[1] != (-1, -1):
                        config.pick1[(int)(agv.currentPos[0] / 3)] -= 2
                    else:
                        config.pick1[(int)(agv.currentPos[0] / 3)] -= 1

                if agv.load_or_unload_wait_countdown >= 0:
                    state.colorList[i] = (180, 40, 210)
                    agv.load_or_unload_wait_countdown -= (1 / config.ROBOT_SPEED)
                else:
                    nextDestination = agv.task.getNextDestination()
                    agv.endPos = agv.stationR[0]
                    if nextDestination == (-1, -1):
                        task_generator.reflush()
                        if config.loadPs != 0:
                            nextDestination = agv.stationR[0]
                        elif config.loadPs == 0:
                            if state.busy != 0:
                                nextDestination = config.STOP_POINT_TEMP[i]
                            else:
                                nextDestination = config.STOP_POINT[i]
                    elif nextDestination != (-1, -1):
                        if agv.stationR[1] != (-1, -1):
                            config.pick1[(int)(agv.currentPos[0] / 3)] -= 2
                        elif agv.stationR[1] == (-1, -1):
                            config.pick1[(int)(agv.currentPos[0] / 3)] -= 1
                    agv.endPos = agv.stationR[0]
                    agv.taskFinish = 0
                    agv.load_or_unload_wait_countdown = config.ROBOT_WAIT_TIME
                break
            else:
                config.START_POINTcop[j] = (config.START_POINTcop[j][0], config.START_POINTcop[j][1], 0)

        # 卸货点处理
        for j in range(len(config.END_POINT)):
            if agv.currentPos == config.END_POINT[j]:
                agv.previousStart = config.END_POINT[j]
                tig = 0

                if agv.load_or_unload_wait_countdown == 0:
                    agv.fast = 1
                    task_generator.reflush()
                    agv.taskFinish += 1
                    state.count += 1

                    if agv.stationR[1] == (-1, -1):  # 送一次的
                        if config.loadPs != 0:
                            agv.task = task_generator.generate_task()
                        if config.loadPs != 0:
                            nextDestination = agv.task.getNextDestination()
                            agv.endPos = ((config.MaxPickPoint, 0))
                            agv.stationR = config.endPos1
                        elif config.loadPs == 0:
                            if state.busy != 0:
                                nextDestination = config.STOP_POINT_TEMP[i]
                            else:
                                nextDestination = config.STOP_POINT[i]
                            agv.endPos = nextDestination
                        state.downPointList[j].goodsCount += agv.task.quantity
                        tig = 1

                    elif agv.taskFinish == 2:  # 送两次的送完了
                        if config.loadPs != 0:
                            agv.task = task_generator.generate_task()
                        if config.loadPs != 0:
                            nextDestination = agv.task.getNextDestination()
                            agv.endPos = ((config.MaxPickPoint, 0))
                            agv.stationR = config.endPos1
                        elif config.loadPs == 0:
                            if state.busy != 0:
                                nextDestination = config.STOP_POINT_TEMP[i]
                            else:
                                nextDestination = config.STOP_POINT[i]
                            agv.endPos = nextDestination
                        state.downPointList[j].goodsCount += agv.task.quantity
                        tig = 1
                    else:  # 送两次没送完的
                        agv.load_or_unload_wait_countdown = config.ROBOT_WAIT_TIME
                        nextDestination = agv.task.getNextDestination()
                        agv.endPos = agv.stationR[1]
                        state.downPointList[j].goodsCount += agv.task.quantity
                        tig = 1

                if agv.load_or_unload_wait_countdown >= 0:
                    state.colorList[i] = (210, 140, 40)  # 变橙
                    agv.load_or_unload_wait_countdown -= (1 / config.ROBOT_SPEED)
                else:
                    if tig == 0:
                        state.downPointList[j].goodsCount += agv.task.quantity
                    nextDestination = agv.task.getNextDestination()
                    if nextDestination == (-1, -1) and tig == 0:
                        if config.loadPs != 0:
                            agv.task = task_generator.generate_task()
                        if config.loadPs != 0:
                            nextDestination = agv.task.getNextDestination()
                            agv.endPos = ((config.MaxPickPoint, 0))
                            agv.stationR = config.endPos1
                        elif config.loadPs == 0:
                            if state.busy != 0:
                                nextDestination = config.STOP_POINT_TEMP[i]
                            else:
                                nextDestination = config.STOP_POINT[i]
                            agv.endPos = nextDestination
                    agv.load_or_unload_wait_countdown = config.ROBOT_WAIT_TIME
                    state.task1 += 1
                break
