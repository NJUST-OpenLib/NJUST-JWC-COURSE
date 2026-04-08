import os
import sys
import time
import csv
import threading
import logging

from datetime import datetime, timedelta
from collections import deque
from flask import Flask, render_template_string

# --- 原有逻辑导入 ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import requests
from njust_tool.auth import login
from njust_tool.utils import load_env, save_env
from njust_tool.constants import HEADERS

# --- 配置 ---
TEST_URL = "http://202.119.81.112:9080/njlgdx/xskb/xskb_list.do?Ves632DSdyV=NEW_XSD_PYGL"
CHECK_INTERVAL_SECONDS = 10
MAX_FAILURES = 3
TOTAL_CYCLES = 100
CSV_FILE = "cookie_lifecycle.csv"
LOG_FILE = "cookie_monitor.log" 
WEB_PORT = 5000

# --- 屏蔽 Flask 控制台访问日志 ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) 

# --- 全局状态 ---
monitor_data = {
    "current_cookie": "None",
    "status": "Initializing",
    "cycle": 0,
    "total_checks": 0,
    "cycle_checks": 0,
    "start_time": "N/A",
    "last_valid_time": "N/A",
    "failures": 0,
    "logs": deque(maxlen=20) 
}

app = Flask(__name__)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def write_log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [#{monitor_data['total_checks']}/{monitor_data['cycle_checks']}] {msg}"
    print(log_entry)
    monitor_data["logs"].appendleft(log_entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

# --- 账号密码检查与请求 ---
def ensure_credentials():
    """检查账号密码，如果没有则提示用户在控制台输入"""
    username = load_env("SAVED_USER")
    password = load_env("SAVED_PASS")
    
    if not username or not password:
        print("\n" + "="*40)
        print("首次运行或未检测到配置，请输入教务系统凭据：")
        while not username:
            username = input("请输入学号: ").strip()
        while not password:
            password = input("请输入密码: ").strip()
        
        save_env("SAVED_USER", username)
        save_env("SAVED_PASS", password)
        print("[+] 账号密码已保存。")
        print("="*40 + "\n")
    
    return username, password

# --- 核心逻辑 ---
def check_cookie_validity(session):
    monitor_data["total_checks"] += 1
    monitor_data["cycle_checks"] += 1
    try:
        r = session.get(TEST_URL, headers=HEADERS, timeout=15)
        r.encoding = "utf-8"
        is_valid = "<title>学期理论课表</title>" in r.text
        
        # 记录每一次检测
        status_str = "Valid (Success)" if is_valid else "Invalid (Failed)"
        write_log(f"Check: {status_str}")
        return is_valid
    except Exception as e:
        write_log(f"Check: Error ({type(e).__name__})")
        return False

def refresh_cookie():
    username, password = ensure_credentials()
    
    session = login(username, password)
    if not session:
        write_log("CRITICAL: 登录尝试失败，请检查账号密码或网络")
        return None, None
    
    jsid = session.cookies.get("JSESSIONID")
    if jsid:
        save_env("JSESSIONID", jsid)
        write_log(f"New Cookie Obtained: {jsid}")
    return session, jsid

def run_monitor_loop():
    for i in range(TOTAL_CYCLES):
        monitor_data["cycle"] = i + 1
        monitor_data["cycle_checks"] = 0
        monitor_data["status"] = "Checking"
        
        env_fail = 0
        while env_fail < MAX_FAILURES:
            jsid = load_env("JSESSIONID")
            
            # 如果没有 JSID，直接尝试登录
            if not jsid:
                session, jsid = refresh_cookie()
            else:
                session = requests.Session()
                session.cookies.set("JSESSIONID", jsid)

            monitor_data["current_cookie"] = jsid or "None"

            # 验证 Cookie 是否真的能用
            if jsid and check_cookie_validity(session):
                write_log(f"Cycle {i+1} started.")
                start = datetime.now()
                monitor_data["start_time"] = start.strftime("%Y-%m-%d %H:%M:%S")
                monitor_data["status"] = "Running"
                last_valid = start
                fail = 0

                while True:
                    time.sleep(CHECK_INTERVAL_SECONDS)
                    if check_cookie_validity(session):
                        last_valid = datetime.now()
                        monitor_data["last_valid_time"] = last_valid.strftime("%H:%M:%S")
                        fail = 0
                        monitor_data["failures"] = 0
                    else:
                        fail += 1
                        monitor_data["failures"] = fail
                        if fail >= MAX_FAILURES:
                            write_log(f"Cycle {i+1} terminated due to {fail} failures.")
                            break

                end = datetime.now()
                duration = last_valid - start
                with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([i+1, jsid, start, end, last_valid, duration.total_seconds()])
                break
            else:
                env_fail += 1
                write_log(f"Session invalid, attempting login/refresh ({env_fail}/{MAX_FAILURES})...")
                session, jsid = refresh_cookie()
                time.sleep(5)
        
        time.sleep(5)

# --- Web 界面 (同上) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Cookie Monitor Console</title>
    <meta http-equiv="refresh" content="10">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background: #f0f2f5; color: #1c1e21; }
        .card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; color: #65676b; font-size: 0.9em; padding: 8px 0; }
        td { font-weight: 600; padding: 8px 0; border-bottom: 1px solid #f0f2f5; }
        .status-tag { background: #e7f3ff; color: #1877f2; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; }
        .log-box { background: #1c1e21; color: #31d2f2; padding: 15px; border-radius: 8px; font-family: 'Consolas', monospace; height: 400px; overflow-y: auto; font-size: 0.9em; line-height: 1.5; }
        .fail { color: #fa3e3e; }
    </style>
</head>
<body>
    <h2 style="margin-bottom: 30px;">🛡️ 教务 Cookie 生命周期监控</h2>
    <div class="grid">
        <div class="card">
            <h3>实时状态</h3>
            <table>
                <tr><th>当前周期</th><td># {{ data.cycle }}</td></tr>
                <tr><th>运行状态</th><td><span class="status-tag">{{ data.status }}</span></td></tr>
                <tr><th>累计/本周检测</th><td>{{ data.total_checks }} / {{ data.cycle_checks }} 次</td></tr>
                <tr><th>当前 Cookie</th><td><code style="font-size: 0.8em; color: #e4405f;">{{ data.current_cookie }}</code></td></tr>
                <tr><th>本次开始</th><td>{{ data.start_time }}</td></tr>
                <tr><th>最后有效</th><td>{{ data.last_valid_time }}</td></tr>
                <tr><th>连续失败</th><td><span class="fail">{{ data.failures }}</span> / 3</td></tr>
            </table>
        </div>
        <div class="card">
            <h3>重要日志 (Recent 20)</h3>
            <div class="log-box">
                {% for log in data.logs %}
                    <div style="margin-bottom: 4px; border-bottom: 1px solid #333;">{{ log }}</div>
                {% endfor %}
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, data=monitor_data)

if __name__ == "__main__":
    # 启动前先确保有账号密码
    ensure_credentials()

    # 启动后台线程
    monitor_thread = threading.Thread(target=run_monitor_loop, daemon=True)
    monitor_thread.start()
    
    print(f"[*] 监控日志: {os.path.abspath(LOG_FILE)}")
    print(f"[*] Web 控制台: http://localhost:{WEB_PORT}")
    
    # 启动 Web 服务
    app.run(host='0.0.0.0', port=WEB_PORT, debug=False, use_reloader=False)