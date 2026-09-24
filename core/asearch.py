from copy import copy
import math

from core.config import config


class point:  # 点类（每一个唯一坐标只有对应的一个实例）
    _list = []  # 储存所有的point类实例
    _tag = True  # 标记最新创建的实例是否为_list中的已有的实例，True表示不是已有实例

    def __new__(cls, x, y):  # 重写new方法实现对于同样的坐标只有唯一的一个实例
        for i in point._list:
            if i.x == x and i.y == y:
                point._tag = False
                return i
        nt = super(point, cls).__new__(cls)
        point._list.append(nt)
        return nt

    def __init__(self, x, y):
        if point._tag:
            self.x = x
            self.y = y
            self.father = None
            self.F = 0  # 当前点的评分  F=G+H
            self.G = 0  # 起点到当前节点所花费的消耗
            self.cost = 0  # 父节点到此节点的消耗
        else:
            point._tag = True

    @classmethod
    def clear(cls):  # clear方法，每次搜索结束后，将所有点数据清除，以便进行下一次搜索的时候点数据不会冲突。
        point._list = []

    def __eq__(self, T):  # 重写==运算以便实现point类的in运算
        if type(self) == type(T):
            return (self.x, self.y) == (T.x, T.y)
        else:
            return False

    def __str__(self):
        return '(%d,%d)[F=%d,G=%d,cost=%d][father:(%s)]' % (self.x, self.y, self.F, self.G, self.cost, str((
            self.father.x,
            self.father.y)) if self.father != None else 'null')


class A_Search:  # 核心部分，寻路类
    def __init__(self, arg_start, arg_end, arg_map, no_hypotenuse=False):
        self.no_hypotenuse = no_hypotenuse  # no_hypotenuse为是否禁止走斜边，默认为否
        self.start = arg_start  # 储存此次搜索的开始点
        self.end = arg_end  # 储存此次搜索的目的点
        self.newStart = self.start
        self.Map = copy(arg_map)  # 一个二维数组，为此次搜索的地图引用
        self.Map[self.end.x][self.end.y] = 0
        self.Map[self.start.x][self.start.y] = 0
        self.open = []  # 开放列表：储存即将被搜索的节点
        self.close = []  # 关闭列表：储存已经搜索过的节点
        self.result = []  # 当计算完成后，将最终得到的路径写入到此属性中
        self.count = 0  # 记录此次搜索所搜索过的节点数
        self.useTime = 0  # 记录此次搜索花费的时间
        self.open.append(arg_start)

    def cal_F(self, loc):
        G = loc.father.G + loc.cost
        H = self.getEstimate(loc)
        F = G + H
        return {'G': G, 'H': H, 'F': F}

    def F_Min(self):  # 搜索open列表中F值最小的点并将其返回，同时判断open列表是否为空，为空则代表搜索失败
        if len(self.open) <= 0:
            return None
        
        t = self.open[0]
        for i in self.open:
            if i.F < t.F:
                t = i
        return t

    def getAroundPoint(self, loc):  # 获取指定点周围所有可通行的点，并将其对应的移动消耗进行赋值。
        if self.no_hypotenuse:  # 若禁止走斜线，则将走斜边的移动消耗设置地很高，走直线的移动消耗设置地很低。
            l = [(loc.x, loc.y + 1, 1), (loc.x + 1, loc.y + 1, 100), (loc.x + 1, loc.y, 1), (loc.x + 1, loc.y - 1, 100),
                 (loc.x, loc.y - 1, 1), (loc.x - 1, loc.y - 1, 100), (loc.x - 1, loc.y, 1), (loc.x - 1, loc.y + 1, 100)]
        else:
            l = [(loc.x, loc.y + 1, 10), (loc.x + 1, loc.y + 1, 14), (loc.x + 1, loc.y, 10), (loc.x + 1, loc.y - 1, 14),
                 (loc.x, loc.y - 1, 10), (loc.x - 1, loc.y - 1, 14), (loc.x - 1, loc.y, 10), (loc.x - 1, loc.y + 1, 14)]
        for i in l[::-1]:
            if i[0] < 0 or i[0] >= config.HEIGHT or i[1] < 0 or i[1] >= config.WIDTH:
                l.remove(i)
        nl = []
        for i in l:
            if self.Map[i[0]][i[1]] == 0:
                nt = point(i[0], i[1])
                nt.cost = i[2]
                nl.append(nt)
        return nl

    def addToOpen(self, l, father):
        for i in l:
            if i not in self.open:
                if i not in self.close:
                    i.father = father
                    self.open.append(i)
                    r = self.cal_F(i)
                    i.G = r['G']
                    i.F = r['F']
            else:
                tf = i.father
                i.father = father
                r = self.cal_F(i)
                if i.F > r['F']:
                    i.G = r['G']
                    i.F = r['F']
                else:
                    i.father = tf

    def getEstimate(self, loc):  # H :从点loc移动到终点的预估花费
        return (abs(loc.x - self.end.x) + abs(loc.y - self.end.y)) * 10

    def process(self):
        time = config.debug
        while time:
            time -= 1
            self.count += 1
            tar = self.F_Min()
            if tar == None:
                self.result = None
                self.count = -1
                break
            else:
                aroundP = self.getAroundPoint(tar)
                self.addToOpen(aroundP, tar)
                self.open.remove(tar)
                self.close.append(tar)
                if self.end in self.open:
                    e = self.end
                    self.result.append(e)
                    while True:
                        e = e.father
                        if e == None:
                            break
                        self.result.append(e)
                    break

        if not self.result:
            return None

        # 计算出完整的路径后，仅返回下一步路径，其它的路径忽略
        nextStep = (self.result[-2].x, self.result[-2].y)
        return nextStep

    def process1(self):
        while True:
            self.count += 1
            tar = self.F_Min()
            if tar == None:
                self.result = None
                self.count = -1
                break
            else:
                aroundP = self.getAroundPoint(tar)
                self.addToOpen(aroundP, tar)
                self.open.remove(tar)
                self.close.append(tar)
                if self.end in self.open:
                    e = self.end
                    self.result.append(e)
                    while True:
                        e = e.father
                        if e == None:
                            break
                        self.result.append(e)
                    break

        distance = self.result
        return distance
