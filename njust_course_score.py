import requests
import re
import os
import getpass
from bs4 import BeautifulSoup

# 配置信息 (从 njust_get_score.py 继承)
LOGIN_URL = "http://202.119.81.112:9080/njlgdx/xk/LoginToXk"
SCORE_URL = "http://202.119.81.112:9080/njlgdx/kscj/cjcx_list"
COURSE_URL = "http://202.119.81.112:9080/njlgdx/xskb/xskb_list.do?Ves632DSdyV=NEW_XSD_PYGL"

ENV_FILE = ".env"

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Connection': 'keep-alive',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
}

def save_env(key, value):
    """保存配置到 .env 文件"""
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    updated = False
    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                updated = True
            else:
                f.write(line)
        if not updated:
            f.write(f"{key}={value}\n")

def load_env(key):
    """从 .env 文件读取配置"""
    if not os.path.exists(ENV_FILE):
        return None
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith(f"{key}="):
                return line.split('=', 1)[1].strip()
    return None

def login(username, password):
    """执行登录并保存 Cookie"""
    print(f"[登录] 正在尝试登录用户: {username}...")
    session = requests.Session()
    post_data = {
        'USERNAME': username,
        'PASSWORD': password
    }
    
    try:
        # allow_redirects=False 模拟之前的 urllib 行为，因为我们需要手动处理重定向并获取 Cookie
        response = session.post(LOGIN_URL, data=post_data, headers=HEADERS, allow_redirects=False)
        
        jsessionid = session.cookies.get('JSESSIONID')
        if jsessionid:
            save_env("JSESSIONID", jsessionid)
            print(f"[登录] 成功获取 JSESSIONID: {jsessionid}")
            return session
        else:
            print("[登录] 未能获取 JSESSIONID，登录可能失败。")
            return None
    except Exception as e:
        print(f"[登录] 发生错误: {e}")
        return None

def fetch_scores(session):
    """获取并展示成绩"""
    print(f"\n{'='*20} 正在获取成绩 {'='*20}")
    try:
        response = session.get(SCORE_URL, headers=HEADERS)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找成绩表格中的所有行
        table = soup.find('table', {'id': 'dataList'})
        if not table:
            print("[成绩] 未找到成绩表格。")
            return

        rows = table.find_all('tr')
        if len(rows) <= 1:
            print("[成绩] 没有成绩记录。")
            return

        # 打印表头
        header_cells = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
        print(f"{' | '.join(header_cells)}")
        print("-" * 100)

        # 打印数据
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all('td')]
            print(f"{' | '.join(cells)}")
        
        print(f"{'='*50}\n")
    except Exception as e:
        print(f"[成绩] 获取失败: {e}")

def parse_semesters(content):
    """从 HTML 中提取所有可选的学期"""
    select_match = re.search(r'<select name="xnxq01id".*?>(.*?)</select>', content, re.S)
    if not select_match:
        return []
    options = re.findall(r'<option value="(.*?)".*?>(.*?)</option>', select_match.group(1), re.S)
    return options

def parse_courses(content):
    """解析并展示课表"""
    # 复用 interactive_course_query.py 的解析逻辑
    student_match = re.search(r'class="Nsb_top_menu_nc".*?>(.*?)</div>', content, re.S)
    student = student_match.group(1).strip() if student_match else "未知"

    semester_match = re.search(r'学年学期：<select.*?>\s*<option.*?selected="selected">(.*?)</option>', content, re.S)
    semester = semester_match.group(1) if semester_match else "未知"

    print(f"\n{'='*25} 课程表信息 {'='*25}")
    print(f"学生: {student}")
    print(f"学期: {semester}")
    print(f"{'='*60}\n")

    table_match = re.search(r'<table id="dataList".*?>(.*?)</table>', content, re.S)
    if table_match:
        table_content = table_match.group(1)
        rows = re.findall(r'<tr>(.*?)</tr>', table_content, re.S)
        headers = ["序号", "课程号", "课序号", "课程名称", "教师", "时间", "学分", "地点", "课程属性", "选课阶段"]
        
        for row in rows[1:]:
            cells = re.findall(r'<td.*?>(.*?)</td>', row, re.S)
            if len(cells) >= len(headers):
                clean_cells = [re.sub(r'<.*?>', ' ', cell).strip() for cell in cells]
                print(f"[{clean_cells[0]}] {clean_cells[3]}")
                print(f"    教师: {clean_cells[4]} | 学分: {clean_cells[6]} | 属性: {clean_cells[8]}")
                print(f"    时间: {clean_cells[5].replace(' ', '')}")
                if clean_cells[7]:
                    print(f"    地点: {clean_cells[7]}")
                print("-" * 60)
    else:
        print("[课表] 未找到课程列表。")

def fetch_courses(session, semester_val=None):
    """获取课表并提供交互式学期选择"""
    print(f"\n{'='*20} 正在获取课表 {'='*20}")
    # 课表请求通常需要 Referer
    course_headers = HEADERS.copy()
    course_headers['Referer'] = COURSE_URL
    
    try:
        # 如果没有指定学期，先发一个 GET 获取最新学期和学期列表
        response = session.get(COURSE_URL, headers=course_headers)
        response.encoding = 'utf-8'
        
        # 优化判断逻辑：由于页面中包含 Logout 链接，里面会有 "Login" 字样导致误判
        # 只有在标题或页面主要区域出现 "请先登录" 或 "登录个人中心" 时才判断为未登录
        if "请先登录系统" in response.text or "登录个人中心" in response.text:
            print("[课表] Cookie 已过期，请重新登录。")
            return

        # 展示当前（最新）学期的课表
        print("[课表] 默认展示最新学期课表:")
        parse_courses(response.text)

        # 获取所有可用学期
        semesters = parse_semesters(response.text)
        if not semesters:
            print("[课表] 未能获取学期列表。")
            return

        # 询问是否查询其他学期
        want_other = input("\n是否需要查询其他学期的课表？(y/n): ").strip().lower()
        if want_other == 'y':
            print("\n可用学期列表:")
            for i, (val, name) in enumerate(semesters):
                print(f"{i+1}. {name.strip()}")

            while True:
                choice = input(f"\n请输入学期编号 (1-{len(semesters)}) 进行查询 (输入 q 退出): ").strip()
                if choice.lower() == 'q':
                    break
                if choice.isdigit() and 1 <= int(choice) <= len(semesters):
                    selected_val = semesters[int(choice)-1][0]
                    print(f"\n正在查询 {selected_val} 的课程信息...")
                    body_data = {
                        "cj0701id": "",
                        "zc": "",
                        "demo": "",
                        "xnxq01id": selected_val,
                        "pageIndex": "1"
                    }
                    post_response = session.post(COURSE_URL, headers=course_headers, data=body_data)
                    post_response.encoding = 'utf-8'
                    parse_courses(post_response.text)
                else:
                    print("无效输入，请重新输入。")
    except Exception as e:
        print(f"[课表] 发生错误: {e}")

def main():
    # 1. 尝试从 .env 读取 JSESSIONID
    jsid = load_env("JSESSIONID")
    session = requests.Session()
    
    logged_in = False
    if jsid:
        session.cookies.set('JSESSIONID', jsid, domain='202.119.81.112')
        print(f"[系统] 已从 .env 加载 JSESSIONID: {jsid}")
        # 验证 Cookie 是否有效
        test_res = session.get(SCORE_URL, headers=HEADERS)
        if "请先登录系统" not in test_res.text and "登录个人中心" not in test_res.text:
            logged_in = True
        else:
            print("[系统] 本地 Cookie 已过期。")

    if not logged_in:
        print("[系统] 请进行登录验证。")
        username = input("请输入学号: ").strip()
        password = getpass.getpass("请输入密码: ")
        session = login(username, password)
        if session:
            logged_in = True

    if not logged_in:
        print("[系统] 登录失败，程序退出。")
        return

    # 2. 获取并展示成绩
    fetch_scores(session)

    # 3. 获取并展示课表
    fetch_courses(session)

if __name__ == "__main__":
    main()
