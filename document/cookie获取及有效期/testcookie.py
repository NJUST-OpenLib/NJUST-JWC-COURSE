import os
import sys
import time
from datetime import datetime, timedelta

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import requests
from njust_tool.utils import load_env
from njust_tool.constants import HEADERS

TEST_URL = "http://202.119.81.112:9080/njlgdx/xskb/xskb_list.do?Ves632DSdyV=NEW_XSD_PYGL"

CHECK_INTERVAL_SECONDS = 10
MAX_FAILURES = 3
TOTAL_CYCLES = 5

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_cookie_validity(session):
    """请求测试页面并检查是否包含指定标题"""
    try:
        response = session.get(TEST_URL, headers=HEADERS, timeout=30)
        response.encoding = "utf-8"

        if "<title>学期理论课表</title>" in response.text:
            return True, "有效"
        else:
            return False, "失效 (未找到指定标题)"

    except Exception as e:
        return False, f"请求异常: {str(e)}"


def build_session_from_env():
    """从 env 构建 session"""
    jsid = load_env("JSESSIONID")

    if not jsid:
        print("[提示] .env 中没有 JSESSIONID")
        return None, None

    session = requests.Session()
    session.cookies.set("JSESSIONID", jsid)

    return session, jsid


def run_test_cycle(cycle_num):

    print(f"\n{'='*20} 开始第 {cycle_num+1} 次测试周期 {'='*20}")

    session, jsid = build_session_from_env()

    if not session:
        print("[错误] 未找到可用 Cookie，本周期计为失败")
        return None

    start_time = datetime.now()

    print(f"[周期 {cycle_num+1}] 使用 Cookie: {jsid}")
    print(f"[周期 {cycle_num+1}] 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    consecutive_failures = 0
    last_valid_time = start_time

    # 先检测一次 cookie
    is_valid, msg = check_cookie_validity(session)

    if not is_valid:
        print(f"[周期 {cycle_num+1}] Cookie 初始检测失败: {msg}")
        return None

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Cookie 检查: 有效")

    while True:

        time.sleep(CHECK_INTERVAL_SECONDS)

        is_valid, msg = check_cookie_validity(session)

        current_time = datetime.now()

        if is_valid:

            consecutive_failures = 0
            last_valid_time = current_time

            print(f"[{current_time.strftime('%H:%M:%S')}] Cookie 检查: {msg}")

        else:

            consecutive_failures += 1

            print(
                f"[{current_time.strftime('%H:%M:%S')}] Cookie 检查: {msg} (连续失败 {consecutive_failures}/{MAX_FAILURES})"
            )

            if consecutive_failures >= MAX_FAILURES:

                print(
                    f"[周期 {cycle_num+1}] 确认失效。最后一次有效时间: {last_valid_time.strftime('%H:%M:%S')}"
                )
                break

    duration = last_valid_time - start_time
    end_time = datetime.now()

    report = {
        "cycle": cycle_num + 1,
        "jsessionid": jsid,
        "start": start_time,
        "end": end_time,
        "last_valid": last_valid_time,
        "duration": duration,
    }

    print(f"\n{'*'*10} 第 {cycle_num+1} 次周期报告 {'*'*10}")
    print(f"Cookie: {jsid}")
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"失效日期: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"有效时长: {duration}")
    print(f"{'*'*35}\n")

    return report


def main():

    print("=== 南理工教务系统 Cookie 有效期测试工具 ===")
    print(f"配置: 每 {CHECK_INTERVAL_SECONDS} 秒检查一次, 连续 {MAX_FAILURES} 次失败认为失效")

    all_reports = []

    for i in range(TOTAL_CYCLES):

        report = run_test_cycle(i)

        if report:
            all_reports.append(report)
            time.sleep(10)
        else:
            print("[系统] 本周期 Cookie 不可用，计为失败")
            time.sleep(5)

    if all_reports:

        print("\n" + "#" * 20 + " 最终汇总报告 " + "#" * 20)

        total_duration = timedelta()

        for r in all_reports:
            print(f"周期 {r['cycle']}: {r['duration']} (Cookie: {r['jsessionid']})")
            total_duration += r["duration"]

        avg_duration = total_duration / len(all_reports)

        print(f"\n平均有效时长: {avg_duration}")
        print("#" * 55)


if __name__ == "__main__":
    main()