import requests
import time
from datetime import datetime, timedelta
from njust_tool.auth import login
from njust_tool.utils import load_env
from njust_tool.constants import HEADERS

# --- 配置区 ---
TEST_URL = "http://202.119.81.112:9080/njlgdx/xskb/xskb_list.do?Ves632DSdyV=NEW_XSD_PYGL"
CHECK_INTERVAL_SECONDS = 300  # 每 5 分钟检查一次
MAX_FAILURES = 3              # 连续失败 3 次认为失效
TOTAL_CYCLES = 5              # 总测试周期次数 (可配置)
# --------------

def check_cookie_validity(session):
    """请求测试页面并检查是否包含指定标题"""
    try:
        # 显式设置 Cookie，确保请求中携带了 JSESSIONID
        response = session.get(TEST_URL, headers=HEADERS, timeout=30)
        response.encoding = 'utf-8' # 强智系统通常使用 utf-8 或 gbk
        if "<title>学期理论课表</title>" in response.text:
            return True, "有效"
        else:
            return False, "失效 (未找到指定标题)"
    except Exception as e:
        return False, f"请求异常: {str(e)}"

def run_test_cycle(cycle_num):
    print(f"\n{'='*20} 开始第 {cycle_num + 1} 次测试周期 {'='*20}")
    
    # 1. 自动从 .env 加载凭据并登录
    username = load_env("SAVED_USER")
    password = load_env("SAVED_PASS")
    
    if not username or not password:
        print("[错误] 未在 .env 中找到 SAVED_USER 或 SAVED_PASS，请先运行 main_new.py 登录一次。")
        return None

    session = login(username, password)
    if not session:
        print("[错误] 登录获取 Cookie 失败。")
        return None

    start_time = datetime.now()
    jsid = session.cookies.get('JSESSIONID')
    print(f"[周期 {cycle_num + 1}] 获取到 Cookie: {jsid}")
    print(f"[周期 {cycle_num + 1}] 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    consecutive_failures = 0
    last_valid_time = start_time

    # 2. 持续检查直到失效
    while True:
        is_valid, msg = check_cookie_validity(session)
        current_time = datetime.now()
        
        if is_valid:
            consecutive_failures = 0
            last_valid_time = current_time
            print(f"[{current_time.strftime('%H:%M:%S')}] Cookie 检查: {msg}")
        else:
            consecutive_failures += 1
            print(f"[{current_time.strftime('%H:%M:%S')}] Cookie 检查: {msg} (连续失败 {consecutive_failures}/{MAX_FAILURES})")
            
            if consecutive_failures >= MAX_FAILURES:
                print(f"[周期 {cycle_num + 1}] 确认失效。最后一次有效时间: {last_valid_time.strftime('%H:%M:%S')}")
                break
        
        # 等待下一次检查
        time.sleep(CHECK_INTERVAL_SECONDS)

    # 3. 计算结果
    duration = last_valid_time - start_time
    end_time = datetime.now()
    
    report = {
        "cycle": cycle_num + 1,
        "jsessionid": jsid,
        "start": start_time,
        "end": end_time,
        "last_valid": last_valid_time,
        "duration": duration
    }
    
    print(f"\n{'*'*10} 第 {cycle_num + 1} 次周期报告 {'*'*10}")
    print(f"Cookie: {jsid}")
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"失效日期: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"有效时长: {duration}")
    print(f"{'*'*35}\n")
    
    return report

def main():
    print("=== 南理工教务系统 Cookie 有效期压力测试工具 ===")
    print(f"配置: 每 {CHECK_INTERVAL_SECONDS} 秒检查一次, 连续 {MAX_FAILURES} 次失败认为失效, 总共测试 {TOTAL_CYCLES} 个周期。")
    
    all_reports = []
    
    for i in range(TOTAL_CYCLES):
        report = run_test_cycle(i)
        if report:
            all_reports.append(report)
            # 休息 10 秒再开始下一个周期，避免请求过于频繁
            time.sleep(10)
        else:
            print("[系统] 无法完成本周期，终止程序。")
            break

    # 最终汇总报告
    if all_reports:
        print("\n" + "#"*20 + " 最终汇总报告 " + "#"*20)
        total_duration = timedelta()
        for r in all_reports:
            print(f"周期 {r['cycle']}: {r['duration']} (Cookie: {r['jsessionid']})")
            total_duration += r['duration']
        
        avg_duration = total_duration / len(all_reports)
        print(f"\n平均有效时长: {avg_duration}")
        print("#"*55)

if __name__ == "__main__":
    main()
