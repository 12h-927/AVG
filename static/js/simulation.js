/**
 * 仿真渲染引擎
 * 接收 WebSocket 推送的状态 JSON，用 Canvas 绘制地图/AGV/载货点/卸货点
 */

// ===== 全局状态 =====
let canvas, ctx;
let blockLength = 15;
let mapWidth = 41;
let mapHeight = 27;
let ws = null;
let lastState = null;

// ===== 初始化 Canvas =====
function initCanvas() {
    canvas = document.getElementById('map-canvas');
    ctx = canvas.getContext('2d');
    canvas.width = mapWidth * blockLength + 50;
    canvas.height = mapHeight * blockLength + 50;
}

// ===== 主渲染函数 =====
function renderMap(state) {
    lastState = state;
    if (!ctx) initCanvas();

    // 更新尺寸（首次或变化时）
    if (state.width !== mapWidth || state.height !== mapHeight) {
        mapWidth = state.width;
        mapHeight = state.height;
        blockLength = state.blockLength || 15;
        canvas.width = mapWidth * blockLength + 50;
        canvas.height = mapHeight * blockLength + 50;
    }

    // 清空画布
    ctx.fillStyle = '#2a2a2a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 偏移量
    const offsetX = 25;
    const offsetY = 25;

    // ===== 绘制格子 =====
    for (let i = 0; i < state.height; i++) {
        for (let j = 0; j < state.width; j++) {
            // 默认背景
            ctx.fillStyle = '#e6e6e6';
            ctx.fillRect(offsetX + j * blockLength, offsetY + i * blockLength, blockLength, blockLength);
        }
    }

    // ===== 绘制载货点 =====
    if (state.upPoints) {
        for (const up of state.upPoints) {
            const i = up.x, j = up.y;
            // 颜色浓度随货物量变化
            const intensity = Math.min(up.pick * 9, 250);
            ctx.fillStyle = `rgb(${intensity}, 75, 90)`;
            ctx.fillRect(offsetX + j * blockLength, offsetY + i * blockLength, blockLength, blockLength);
            // 显示货物量 "逻辑|物理"
            ctx.fillStyle = '#000';
            ctx.font = '8px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(
                `${up.pick}|${up.pick1}`,
                offsetX + j * blockLength + blockLength / 2,
                offsetY + i * blockLength + blockLength * 0.7
            );
        }
    }

    // ===== 绘制卸货点 =====
    if (state.downPoints) {
        for (const dp of state.downPoints) {
            const i = dp.x, j = dp.y;
            // 关闭状态用红色
            if (dp.status === 1) {
                ctx.fillStyle = '#ff0000';
            } else {
                const intensity = Math.min(dp.goods * 13, 250);
                ctx.fillStyle = `rgb(${intensity}, 200, 40)`;
            }
            ctx.fillRect(offsetX + j * blockLength, offsetY + i * blockLength, blockLength, blockLength);
            ctx.strokeStyle = '#000';
            ctx.strokeRect(offsetX + j * blockLength, offsetY + i * blockLength, blockLength, blockLength);

            // 显示货物堆积量
            ctx.fillStyle = '#000';
            ctx.font = '8px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(
                `${dp.goods}`,
                offsetX + j * blockLength + blockLength / 2,
                offsetY + i * blockLength + blockLength * 0.7
            );
        }
    }

    // ===== 绘制 AGV =====
    if (state.agvs) {
        for (const agv of state.agvs) {
            const i = agv.x, j = agv.y;
            if (i < 0 || j < 0) continue;

            const [r, g, b] = agv.color;
            ctx.fillStyle = `rgb(${r},${g},${b})`;
            ctx.beginPath();
            ctx.arc(
                offsetX + j * blockLength + blockLength / 2,
                offsetY + i * blockLength + blockLength / 2,
                blockLength / 2 - 1,
                0, Math.PI * 2
            );
            ctx.fill();

            // 画编号
            ctx.fillStyle = '#fff';
            ctx.font = 'bold 9px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(
                `${agv.id}`,
                offsetX + j * blockLength + blockLength / 2,
                offsetY + i * blockLength + blockLength * 0.65
            );
        }
    }

    // ===== 绘制停车点（仅显示空位）=====
    if (state.stopPoints) {
        for (const sp of state.stopPoints) {
            const [i, j] = sp;
            ctx.strokeStyle = '#444';
            ctx.lineWidth = 1;
            ctx.strokeRect(offsetX + j * blockLength, offsetY + i * blockLength, blockLength, blockLength);
        }
    }

    // ===== 更新统计面板 =====
    updateStats(state);
}

// ===== 更新右侧统计 =====
function updateStats(state) {
    document.getElementById('stat-count').textContent = state.count || 0;
    document.getElementById('stat-busy').textContent = state.busy || 0;
    document.getElementById('stat-total').textContent = (state.agvs || []).length;
    document.getElementById('stat-cargo').textContent = `${state.cargo || 0}/${state.cargoMax || 0}`;
    document.getElementById('stat-onroad').textContent = (state.cargoMax || 0) - (state.cargo || 0) - (state.count || 0);
    document.getElementById('stat-orders').textContent = state.orderProcessing || 0;
    document.getElementById('stat-distri').textContent = state.distriCenter || 300;

    const time = state.time || 0;
    const min = Math.floor(time / 60);
    const sec = Math.floor(time % 60);
    document.getElementById('stat-time').textContent = `${min}分${sec}秒`;

    // 完成提示
    if (state.finish) {
        document.getElementById('finish-banner').style.display = 'flex';
        document.getElementById('stat-finish').textContent = state.finish;
    } else {
        document.getElementById('finish-banner').style.display = 'none';
    }
}

// ===== WebSocket 连接管理 =====
function connectWebSocket() {
    const indicator = document.getElementById('ws-indicator');
    indicator.textContent = '连接中...';
    indicator.className = 'connecting';

    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${location.host}/ws/simulation`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        indicator.textContent = '已连接';
        indicator.className = 'connected';
        console.log('WebSocket 已连接');
    };

    ws.onmessage = (event) => {
        try {
            const state = JSON.parse(event.data);
            renderMap(state);
        } catch (e) {
            console.error('解析状态失败:', e);
        }
    };

    ws.onclose = () => {
        indicator.textContent = '已断开';
        indicator.className = 'disconnected';
        console.log('WebSocket 断开，3秒后重连...');
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
        console.error('WebSocket 错误:', err);
        indicator.textContent = '连接错误';
        indicator.className = 'disconnected';
    };
}

// ===== 页面加载时初始化 =====
window.addEventListener('load', () => {
    initCanvas();
    connectWebSocket();
});

// 暴露给外部使用
window.simulation = {
    getWS: () => ws,
    renderMap,
    getLastState: () => lastState,
};
