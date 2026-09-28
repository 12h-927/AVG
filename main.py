"""AGV 物流调度平台 - Web 入口

启动方式：
    python main.py
或（带热重载，用于命令行开发）：
    UVICORN_RELOAD=1 python main.py
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""
import os
import sys

import uvicorn

if __name__ == "__main__":
    # 启动标记：如果控制台连这行都没打印，说明 PyCharm 运行配置/解释器有问题
    print("正在启动 AGV 后端... Python:", sys.version.split()[0], "|", sys.executable)
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        # reload 的 reloader 进程树在 PyCharm 运行环境下会静默退出，默认关闭；
        # 需要热重载时设置环境变量 UVICORN_RELOAD=1
        reload=os.environ.get("UVICORN_RELOAD") == "1",
    )
