import requests
import re
import os
import sys
import msvcrt
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

def get_password_with_mask(prompt="请输入密码: "):
    """
    密码输入：输入时显示最后一位，前面的显示为 *
    仅适用于 Windows (msvcrt)
    """
    print(prompt, end='', flush=True)
    password = []
    while True:
        ch = msvcrt.getch()
        # 处理回车
        if ch in (b'\r', b'\n'):
            print()
            return "".join(password)
        # 处理退格
        elif ch == b'\x08':
            if password:
                password.pop()
                # 抹掉之前显示的所有内容并重绘
                # 简单处理：退格后，显示全 * 的前 len-1 位
                sys.stdout.write('\r' + prompt + '*' * len(password) + ' ' + '\b')
                sys.stdout.flush()
        # 处理普通字符
        else:
            try:
                char = ch.decode('utf-8')
                if char.isprintable():
                    password.append(char)
                    # 重新显示：前面的位显示 *，最后一位显示原字符
                    mask = '*' * (len(password) - 1)
                    sys.stdout.write('\r' + prompt + mask + char)
                    sys.stdout.flush()
            except UnicodeDecodeError:
                continue

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
        
        # 增加真实性校验：强智系统登录成功通常会返回 302 重定向
        if response.status_code != 302:
            if "密码错误" in response.text:
                print("[登录] 登录失败: 密码错误。")
            elif "验证码" in response.text:
                print("[登录] 登录失败: 需要验证码。")
            else:
                print(f"[登录] 登录失败: 服务器返回状态码 {response.status_code}")
            return None

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
        
        if "请先登录系统" in response.text or "登录个人中心" in response.text:
            print("[成绩] 会话已过期。")
            return False

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找成绩表格中的所有行
        table = soup.find('table', {'id': 'dataList'})
        if not table:
            print("[成绩] 未找到成绩表格。")
            return False

        rows = table.find_all('tr')
        if len(rows) <= 1:
            print("[成绩] 没有成绩记录。")
            return True

        # 打印表头
        header_cells = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
        print(f"{' | '.join(header_cells)}")
        print("-" * 100)

        # 打印数据
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all('td')]
            print(f"{' | '.join(cells)}")
        
        print(f"{'='*50}\n")
        return True
    except Exception as e:
        print(f"[成绩] 获取失败: {e}")
        return False

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

    if student == "未知" and semester == "未知":
        return False

    print(f"\n{'='*25} 课程表信息 {'='*25}")
    print(f"学生: {student} | 学期: {semester}")
    print(f"{'='*60}")

    table_match = re.search(r'<table id="dataList".*?>(.*?)</table>', content, re.S)
    if table_match:
        table_content = table_match.group(1)
        rows = re.findall(r'<tr>(.*?)</tr>', table_content, re.S)
        
        # rows[0] 是表头，rows[1:] 是数据
        if len(rows) <= 1:
            print("[课表] 该学期没有任何课程记录。")
            print("="*60 + "\n")
            return True

        headers = ["序号", "课程号", "课序号", "课程名称", "教师", "时间", "学分", "地点", "课程属性", "选课阶段"]
        count = 0
        for row in rows[1:]:
            cells = re.findall(r'<td.*?>(.*?)</td>', row, re.S)
            if len(cells) >= len(headers):
                clean_cells = [re.sub(r'<.*?>', ' ', cell).strip() for cell in cells]
                if not clean_cells[3]: continue # 跳过空行
                count += 1
                print(f"[{clean_cells[0]}] {clean_cells[3]}")
                print(f"    教师: {clean_cells[4]} | 学分: {clean_cells[6]} | 属性: {clean_cells[8]}")
                print(f"    时间: {clean_cells[5].replace(' ', '')}")
                if clean_cells[7]:
                    print(f"    地点: {clean_cells[7]}")
                print("-" * 60)
        
        if count == 0:
            print("[课表] 未能解析到有效课程。")
        else:
            print(f"共找到 {count} 门课程。")
        print("="*60 + "\n")
        return True
    else:
        print("[课表] 未找到课程列表表格。")
        print("="*60 + "\n")
        return False

def display_semesters(semesters):
    """分栏展示学期列表"""
    print(f"\n{'='*20} 可用学期列表 {'='*20}")
    cols = 2  # 设置为 2 栏显示，兼顾手机/窄窗口
    total = len(semesters)
    rows = (total + cols - 1) // cols
    
    for r in range(rows):
        line = ""
        for c in range(cols):
            idx = r + c * rows
            if idx < total:
                val, name = semesters[idx]
                # 编号左对齐，名称固定宽度
                item = f"{idx+1:2d}. {name.strip():<15}"
                line += f"{item}    "
        print(line.rstrip())
    print("="*54)

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
        
        # 优化判断逻辑
        if "请先登录系统" in response.text or "登录个人中心" in response.text:
            print("[课表] 会话已过期。")
            return False

        # 展示当前（最新）学期的课表
        print("[课表] 默认展示最新学期课表:")
        if not parse_courses(response.text):
            return False

        # 获取所有可用学期
        semesters = parse_semesters(response.text)
        if not semesters:
            print("[课表] 未能获取学期列表。")
            return True

        # 进入交互式查询循环
        while True:
            choice = input(f"是否需要查询其他学期？(输入编号 1-{len(semesters)}, 'l' 列出学期, 'q' 退出): ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == 'l':
                display_semesters(semesters)
                continue
            elif choice == 'y':
                display_semesters(semesters)
                continue
            elif choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(semesters):
                    selected_val, selected_name = semesters[idx-1]
                    print(f"\n[系统] 正在查询 {selected_name} 的课程信息...")
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
                    print(f"错误: 编号超出范围 (1-{len(semesters)})。")
            else:
                print("无效输入。输入编号查询，'l' 查看列表，'q' 退出。")
        
        return True
    except Exception as e:
        print(f"[课表] 发生错误: {e}")
        return False

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

    while True:
        if not logged_in:
            print("[系统] 请进行登录验证。")
            username = input("请输入学号: ").strip()
            # 使用带掩码的密码输入
            password = get_password_with_mask("请输入密码: ")
            session = login(username, password)
            if not session:
                print("[系统] 登录失败，请重试。")
                continue
            logged_in = True

        # 2. 获取并展示成绩
        success_score = fetch_scores(session)

        # 3. 获取并展示课表
        success_course = fetch_courses(session)

        # 如果两者都获取失败（可能是假登录成功），则要求重试
        if not success_score and not success_course:
            print("[系统] 无法获取到有效信息，可能登录失效，请重新登录。")
            logged_in = False
            # 清除失效的 JSESSIONID
            save_env("JSESSIONID", "")
            continue
        
        # 只要有一个成功，就可以认为成功了
        break

if __name__ == "__main__":
    main()
