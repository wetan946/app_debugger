"""
【生产工单看板系统 - 后端API】
任务：此系统供车间主任查看当日生产工单状态，并支持更新工单进度。
请找出并修复所有 bug，使系统能正常运行。
"""

from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3
import json

app = Flask(__name__)
DB_PATH = "workshop.db"


# ===================== 数据库初始化 =====================

def init_db():
    """初始化数据库，创建工单表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS work_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT NOT NULL UNIQUE,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            completed INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    # 插入测试数据
    test_orders = [
        ('WO-2026-001', '铸铁法兰盘', 500, 120, 'in_progress'),
        ('WO-2026-002', '阀门壳体', 200, 200, 'completed'),
        ('WO-2026-003', '齿轮箱盖板', 150, 0, 'pending'),
    ]
    for order in test_orders:
        try:
            c.execute(
                "INSERT INTO work_orders (order_no, product_name, quantity, completed, status, created_at) VALUES (?,?,?,?,?,?)",
                (*order, datetime.now().isoformat())
            )
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()


# ===================== 工具函数 =====================

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def calculate_progress(completed, quantity):
    """计算完成进度百分比"""
    if quantity == 0:
        return 0  # 如果计划数量为0，返回进度为0
    return round(completed / quantity * 100, 1)


def format_order(row):
    """将数据库行转换为字典"""
    return {
        "id": row["id"],
        "order_no": row["order_no"],
        "product_name": row["product_name"],
        "quantity": row["quantity"],
        "completed": row["completed"],
        "progress": calculate_progress(row["quantity"], row["completed"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# ===================== API 路由 =====================

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """
    获取所有工单列表
    支持按状态筛选：GET /api/orders?status=in_progress
    """
    status_filter = request.args.get('status')
    conn = get_db_connection()
    try:
        if status_filter:
            # rows = conn.execute(
            #     f"SELECT * FROM work_orders WHERE status = {status_filter}"
            # ).fetchall()
            rows = conn.execute("SELECT * FROM work_orders WHERE status = ?", (status_filter,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM work_orders").fetchall()

        orders = [format_order(r) for r in rows]
        return jsonify({"success": True, "data": orders, "count": len(orders)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """获取单个工单详情"""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM work_orders WHERE id = ?", (order_id,)
        ).fetchone()
        if not row:
            return jsonify({"success": False, "error": "工单不存在"}), 404
        return jsonify({"success": True, "data": format_order(row)})
    finally:
        conn.close()


@app.route('/api/orders/<int:order_id>/progress', methods=['PUT'])
def update_progress(order_id):
    """
    更新工单完成数量
    请求体: {"completed": 150}
    规则：
      - completed 不能超过 quantity
      - completed 达到 quantity 时自动将 status 改为 'completed'
      - completed 大于 0 且小于 quantity 时 status 为 'in_progress'
    """
    data = request.get_json()

    new_completed = data['completed']

    if not isinstance(new_completed, int) or new_completed < 0:
        return jsonify({"success": False, "error": "completed 必须为非负整数"}), 400

    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM work_orders WHERE id = ?", (order_id,)
        ).fetchone()
        if not row:
            return jsonify({"success": False, "error": "工单不存在"}), 404

        if new_completed > row['quantity']:
            return jsonify({"success": False, "error": "完成数量不能超过计划数量"}), 400

        # 自动推断状态
        if new_completed == row['quantity']:
            new_status = 'completed'
        elif new_completed > 0:
            new_status = 'in_progress'
        else:
            new_status = 'pending'

        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE work_orders SET completed=?, status=?, updated_at=? WHERE id=?",
            (new_completed, new_status, now, order_id)
        )

        # 返回更新后的数据
        updated_row = conn.execute(
            "SELECT * FROM work_orders WHERE id = ?", (order_id,)
        ).fetchone()
        return jsonify({"success": True, "data": format_order(updated_row)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@app.route('/api/summary', methods=['GET'])
def get_summary():
    """
    获取今日生产汇总数据
    返回：各状态工单数量、总计划产量、总完成产量、整体完成率
    """
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM work_orders").fetchall()

        summary = {
            "total_orders": len(rows),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "total_quantity": 0,
            "total_completed": 0,
            "overall_progress": 0.0
        }

        for row in rows:
            summary[row['status']] += 1
            summary['total_quantity'] += row['quantity']
            summary['total_completed'] += row['completed']

        if summary['total_orders'] > 0:
            summary['overall_progress'] = round(
                summary['total_completed'] / summary['total_orders'] * 100, 1
            )

        return jsonify({"success": True, "data": summary})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


# ===================== 前端页面路由 =====================

@app.route('/')
def index():
    """返回看板主页 HTML"""
    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>车间生产看板</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f0f2f5; }
        .header { background: #1a3a5c; color: white; padding: 16px 32px; }
        .container { max-width: 1100px; margin: 24px auto; padding: 0 16px; }
        .summary-cards { display: flex; gap: 16px; margin-bottom: 24px; }
        .card { background: white; border-radius: 8px; padding: 20px; flex: 1; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .card h3 { margin: 0 0 8px; color: #666; font-size: 14px; }
        .card .value { font-size: 32px; font-weight: bold; color: #1a3a5c; }
        .card .sub { font-size: 13px; color: #999; margin-top: 4px; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        th { background: #1a3a5c; color: white; padding: 12px 16px; text-align: left; font-size: 14px; }
        td { padding: 12px 16px; border-bottom: 1px solid #f0f0f0; font-size: 14px; }
        tr:hover td { background: #f9f9f9; }
        .status-badge { padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }
        .status-pending { background: #fff3cd; color: #856404; }
        .status-in_progress { background: #cce5ff; color: #004085; }
        .status-completed { background: #d4edda; color: #155724; }
        .progress-bar-wrap { background: #e9ecef; border-radius: 4px; height: 8px; width: 120px; display: inline-block; vertical-align: middle; }
        .progress-bar { background: #28a745; height: 8px; border-radius: 4px; }
        .btn { padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
        .btn-primary { background: #1a3a5c; color: white; }
        .btn-primary:hover { background: #245080; }
        input[type=number] { width: 80px; padding: 5px 8px; border: 1px solid #ccc; border-radius: 4px; }
        .msg { padding: 10px 16px; border-radius: 6px; margin: 12px 0; display: none; }
        .msg-success { background: #d4edda; color: #155724; }
        .msg-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
<div class="header"><h2 style="margin:0">车间生产看板 · 浙江时代铸造</h2></div>
<div class="container">
    <div class="summary-cards" id="summaryCards">加载中...</div>
    <div id="msg" class="msg"></div>
    <table id="ordersTable">
        <thead>
            <tr>
                <th>工单号</th><th>产品名称</th><th>计划数量</th>
                <th>已完成</th><th>进度</th><th>状态</th><th>更新进度</th>
            </tr>
        </thead>
        <tbody id="ordersBody">
            <tr><td colspan="7" style="text-align:center;color:#999">加载中...</td></tr>
        </tbody>
    </table>
</div>
<script>
    const statusMap = { pending: '待生产', in_progress: '生产中', completed: '已完成' };
    const statusClass = { pending: 'status-pending', in_progress: 'status-in_progress', completed: 'status-completed' };

    function showMsg(text, isError) {
        const el = document.getElementById('msg');
        el.textContent = text;
        el.className = 'msg ' + (isError ? 'msg-error' : 'msg-success');
        el.style.display = 'block';
        setTimeout(() => el.style.display = 'none', 3000);
    }

    async function loadSummary() {
        const res = await fetch('/api/summary');
        const json = await res.json();
        if (!json.success) return;
        const d = json.data;
        document.getElementById('summaryCards').innerHTML = `
            <div class="card"><h3>工单总数</h3><div class="value">${d.total_orders}</div>
                <div class="sub">待生产 ${d.pending} · 生产中 ${d.in_progress} · 已完成 ${d.completed}</div></div>
            <div class="card"><h3>总计划产量</h3><div class="value">${d.total_quantity}</div><div class="sub">件</div></div>
            <div class="card"><h3>总完成产量</h3><div class="value">${d.total_completed}</div><div class="sub">件</div></div>
            <div class="card"><h3>整体完成率</h3><div class="value">${d.overall_progress}%</div><div class="sub">基于计划总量</div></div>
        `;
    }

    async function loadOrders() {
        const res = await fetch('/api/orders');
        const json = await res.json();
        if (!json.success) return;
        const tbody = document.getElementById('ordersBody');

        tbody.innerHTML = json.data.map(o => `
            <tr>
                <td><b>${o.order_no}</b></td>
                <td>${o.product_name}</td>
                <td>${o.quantity}</td>
                <td>${o.completed}</td>
                <td>
                    <div class="progress-bar-wrap">
                        # <div class="progress-bar" style="width: " + o.progress + "%"></div>
                        <div class="progress-bar" style="width: ${o.progress}%"></div>
                    </div>
                    <span style="margin-left:6px">${o.progress}%</span>
                </td>
                <td><span class="status-badge ${statusClass[o.status]}">${statusMap[o.status]}</span></td>
                <td>
                    <input type="number" id="inp_${o.id}" value="${o.completed}" min="0" max="${o.quantity}">
                    <button class="btn btn-primary" onclick="updateProgress(${o.id})">更新</button>
                </td>
            </tr>
        `).join('');
    }

    async function updateProgress(orderId) {
        const input = document.getElementById('inp_' + orderId);
        const completed = parseInt(input.value);

        const res = await fetch('/api/orders/' + orderId + '/progress', {
            method: 'PUT',
            body: JSON.stringify({ completed })
        });
        const json = await res.json();
        if (json.success) {
            showMsg('更新成功！工单状态已同步', false);
            loadOrders();
            loadSummary();
        } else {
            showMsg('更新失败：' + json.error, true);
        }
    }

    // 初始化加载
    
    loadOrders();
    loadSummary();
</script>
</body>
</html>'''
    return html


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
