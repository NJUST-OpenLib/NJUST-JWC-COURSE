import os
import sys
import time
import csv
from datetime import datetime, timedelta

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import requests
from njust_tool.auth import login
from njust_tool.utils import load_env, save_env
from njust_tool.constants import HEADERS

TEST_URL = "http://202.119.81.112:9080/njlgdx/xskb/xskb_list.do?Ves632DSdyV=NEW_XSD_PYGL"

CHECK_INTERVAL_SECONDS = 10
MAX_FAILURES = 3
TOTAL_CYCLES = 20

CSV_FILE = "cookie_lifecycle.csv"

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_cookie_validity(session):
    try:
        r = session.get(TEST_URL, headers=HEADERS, timeout=30)
        r.encoding = "utf-8"

        if "<title>学期理论课表</title>" in r.text:
            return True
        return False

    except Exception:
        return False


def build_session_from_env():
    jsid = load_env("JSESSIONID")

    if not jsid:
        return None, None

    session = requests.Session()
    session.cookies.set("JSESSIONID", jsid)

    return session, jsid


def refresh_cookie():
    username = load_env("SAVED_USER")
    password = load_env("SAVED_PASS")

    if not username or not password:
        print("env 中没有账号密码")
        return None, None

    session = login(username, password)

    if not session:
        return None, None

    jsid = session.cookies.get("JSESSIONID")

    if jsid:
        save_env("JSESSIONID", jsid)

    return session, jsid


def write_csv(report):

    file_exists = os.path.exists(CSV_FILE)

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "cycle",
                "cookie",
                "start_time",
                "end_time",
                "last_valid_time",
                "duration_seconds"
            ])

        writer.writerow([
            report["cycle"],
            report["cookie"],
            report["start"],
            report["end"],
            report["last_valid"],
            report["duration"].total_seconds()
        ])


def run_cycle(cycle):

    print(f"\n====== 周期 {cycle+1} ======")

    env_fail = 0

    while env_fail < MAX_FAILURES:

        session, jsid = build_session_from_env()

        if not session:
            env_fail += 1
            print("env cookie 不存在")
            continue

        print("使用 cookie:", jsid)

        if check_cookie_validity(session):
            print("cookie 有效，开始监控")

            start = datetime.now()
            last_valid = start
            fail = 0

            while True:

                time.sleep(CHECK_INTERVAL_SECONDS)

                if check_cookie_validity(session):

                    last_valid = datetime.now()
                    fail = 0

                    print(last_valid.strftime("%H:%M:%S"), "valid")

                else:

                    fail += 1
                    print(datetime.now().strftime("%H:%M:%S"), "fail", fail)

                    if fail >= MAX_FAILURES:
                        break

            end = datetime.now()
            duration = last_valid - start

            report = {
                "cycle": cycle + 1,
                "cookie": jsid,
                "start": start,
                "end": end,
                "last_valid": last_valid,
                "duration": duration
            }

            write_csv(report)

            print("生命周期:", duration)

            return report

        else:

            env_fail += 1
            print("cookie 无效", env_fail)

    print("env cookie 连续失败，重新登录")

    session, jsid = refresh_cookie()

    if session:
        print("刷新 cookie:", jsid)

    return None


def summary(reports):

    if not reports:
        return

    durations = [r["duration"].total_seconds() for r in reports]

    avg = sum(durations) / len(durations)
    mx = max(durations)
    mn = min(durations)

    print("\n====== 生命周期统计 ======")
    print("周期数:", len(durations))
    print("平均:", timedelta(seconds=avg))
    print("最长:", timedelta(seconds=mx))
    print("最短:", timedelta(seconds=mn))


def main():

    print("教务 Cookie 生命周期监控工具")

    reports = []

    for i in range(TOTAL_CYCLES):

        r = run_cycle(i)

        if r:
            reports.append(r)

        time.sleep(5)

    summary(reports)


if __name__ == "__main__":
    main()