/**
 * 控制面板逻辑
 * 按钮事件 -> REST API 调用
 */

async function callAPI(method, path, body) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    try {
        const res = await fetch(path, opts);
        return await res.json();
    } catch (e) {
        console.error(`API ${method} ${path} 失败:`, e);
        return { ok: false, error: e.message };
    }
}

window.addEventListener('load', async () => {
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    const btnReset = document.getElementById('btn-reset');

    // 刷新页面时从后端同步当前运行状态，避免按钮状态错乱
    try {
        const status = await callAPI('GET', '/api/sim/status');
        if (status.running) {
            btnStart.disabled = true;
            btnStart.textContent = '运行中...';
            btnStop.disabled = false;
        } else {
            btnStart.disabled = false;
            btnStart.textContent = '开始仿真';
            btnStop.disabled = true;
        }
    } catch (e) {
        console.warn('获取初始状态失败，使用默认按钮状态:', e);
    }

    // 启动
    btnStart.addEventListener('click', async () => {
        btnStart.disabled = true;
        const result = await callAPI('POST', '/api/sim/start');
        if (result.ok) {
            btnStop.disabled = false;
            btnStart.textContent = '运行中...';
        } else {
            btnStart.disabled = false;
            alert('启动失败: ' + (result.error || '未知错误'));
        }
    });

    // 停止
    btnStop.addEventListener('click', async () => {
        await callAPI('POST', '/api/sim/stop');
        btnStart.disabled = false;
        btnStop.disabled = true;
        btnStart.textContent = '开始仿真';
    });

    // 重置
    btnReset.addEventListener('click', async () => {
        await callAPI('POST', '/api/sim/reset');
        btnStart.disabled = false;
        btnStop.disabled = true;
        btnStart.textContent = '开始仿真';
        // 重置后立即请求一次状态刷新
        const status = await callAPI('GET', '/api/sim/status');
        if (window.simulation) {
            window.simulation.renderMap(status);
        }
        console.log('仿真已重置');
    });
});
