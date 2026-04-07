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
    print(f"[登录] 正在尝试登录用户：{username}...")
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

def get_big_section(small_section):
    """将小节号映射为大节名称，用于跨表格匹配"""
    if not small_section: return ""
    # 提取起始小节数字
    match = re.search(r'(\d+)', small_section)
    if not match: return ""
    start_sec = int(match.group(1))
    
    if 1 <= start_sec <= 3: return "第一大节"
    if 4 <= start_sec <= 5: return "第二大节"
    if 6 <= start_sec <= 8: return "第三大节"
    if 9 <= start_sec <= 11: return "第四大节"
    if 12 <= start_sec <= 15: return "第五大节"
    return ""

def parse_courses(content):
    """解析并展示课表 (综合格子视图和列表视图，确保信息完整)"""
    soup = BeautifulSoup(content, 'html.parser')
    
    # 提取基本元数据
    student_tag = soup.find(class_="Nsb_top_menu_nc")
    student = student_tag.get_text(strip=True) if student_tag else "未知"
    semester_tag = soup.find('select', {'name': 'xnxq01id'})
    semester = "未知"
    if semester_tag:
        selected_option = semester_tag.find('option', selected="selected")
        if selected_option:
            semester = selected_option.get_text(strip=True)

    if student == "未知" and semester == "未知":
        return False

    print(f"\n{'='*25} 课程表信息 {'='*25}")
    print(f"学生: {student} | 学期: {semester}")
    print(f"{'='*60}")

    # 1. 预解析 kbtable：建立 (课程名, 星期, 大节) -> 详细安排列表
    kb_info = {} 
    kb_table = soup.find('table', {'id': 'kbtable'})
    if kb_table:
        weekdays = [th.get_text(strip=True) for th in kb_table.find_all('tr')[0].find_all('th')][1:]
        rows = kb_table.find_all('tr')[1:]
        for row in rows:
            section_th = row.find('th')
            if not section_th: continue
            big_section = section_th.get_text(strip=True).replace('\xa0', '').strip()
            
            tds = row.find_all('td')
            for col_idx, td in enumerate(tds):
                if col_idx >= len(weekdays): break
                day = weekdays[col_idx]
                kb_div = td.find('div', class_='kbcontent')
                if not kb_div: continue
                
                content_str = str(kb_div)
                content_str = re.sub(r'^<div.*?>|</div>$', '', content_str, flags=re.S)
                parts = re.split(r'---------------------|-{10,}', content_str)
                for part in parts:
                    part_soup = BeautifulSoup(part, 'html.parser')
                    lines = [s.strip() for s in part_soup.get_text(separator='\n').split('\n') if s.strip()]
                    if not lines: continue
                    name = lines[0]
                    
                    weeks = ""
                    classroom = ""
                    teacher = ""
                    
                    weeks_font = part_soup.find('font', title='周次(节次)')
                    if weeks_font: weeks = weeks_font.get_text(strip=True)
                    classroom_font = part_soup.find('font', title='教室')
                    if classroom_font: classroom = classroom_font.get_text(strip=True)
                    teacher_font = part_soup.find('font', title='老师')
                    if teacher_font: teacher = teacher_font.get_text(strip=True)
                    
                    key = (name, day, big_section)
                    if key not in kb_info: kb_info[key] = []
                    kb_info[key].append({
                        'weeks': weeks,
                        'classroom': classroom,
                        'teacher': teacher
                    })

    # 2. 解析 dataList：作为主数据源
    data_list_table = soup.find('table', {'id': 'dataList'})
    if not data_list_table:
        print("[课表] 未找到课程列表 (dataList)。")
        return False

    rows = data_list_table.find_all('tr')[1:]
    count = 0
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 9: continue
        name = cells[3].get_text(strip=True)
        if not name: continue
        count += 1
        
        teacher_summary = cells[4].get_text(strip=True)
        credit = cells[6].get_text(strip=True)
        prop = cells[8].get_text(strip=True)
        
        time_text = cells[5].get_text(separator='\n', strip=True)
        times = [t.strip() for t in time_text.split('\n') if t.strip()]
        
        # 构造排课项
        schedules = []
        for t in times:
            match = re.match(r'(星期[一二三四五六日])\((.*?)\)', t)
            if match:
                day, small_section = match.groups()
                big_section = get_big_section(small_section)
                
                # 优先匹配 (name, day, big_section)
                key = (name, day, big_section)
                matched_kb = kb_info.get(key, [])
                
                if matched_kb:
                    for kb in matched_kb:
                        schedules.append({
                            'time': t,
                            'weeks': kb['weeks'],
                            'classroom': kb['classroom'],
                            'teacher': kb['teacher']
                        })
                else:
                    # 如果大节匹配失败（如中午、晚上或不规则时间），尝试仅按 (name, day) 找
                    # 这种情况通常出现在 dataList 有记录但 kbtable 无法精准定位大节时
                    found_any = False
                    for k, v in kb_info.items():
                        if k[0] == name and k[1] == day:
                            for kb in v:
                                schedules.append({
                                    'time': t,
                                    'weeks': kb['weeks'],
                                    'classroom': kb['classroom'],
                                    'teacher': kb['teacher']
                                })
                                found_any = True
                    if not found_any:
                        schedules.append({
                            'time': t,
                            'weeks': "未知",
                            'classroom': "未知",
                            'teacher': teacher_summary
                        })

        # 去重合并
        unique_schedules = []
        seen = set()
        for s in schedules:
            k = (s['time'], s['weeks'], s['classroom'], s['teacher'])
            if k not in seen:
                unique_schedules.append(s)
                seen.add(k)
        schedules = unique_schedules

        # 输出
        print(f"[{count}] {name}")
        print(f"    教师: {teacher_summary} | 学分: {credit} | 属性: {prop}")
        if schedules:
            if len(schedules) > 1: print(f"    {'·' * 50}")
            for i, s in enumerate(schedules, 1):
                prefix = f"    {count}.{i} " if len(schedules) > 1 else "    "
                print(f"{prefix}时间: {s['time']} | 周次: {s['weeks']}")
                indent = " " * len(prefix) if len(schedules) > 1 else "    "
                teacher_info = f" | 教师: {s['teacher']}" if s['teacher'] and s['teacher'] != teacher_summary else ""
                print(f"{indent}地点: {s['classroom'] or '未知'}{teacher_info}")
                if len(schedules) > 1 and i < len(schedules): print(f"    {'·' * 30}")
        print("-" * 60)

    print(f"共找到 {count} 门课程。")
    print("="*60 + "\n")
    return True

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
    # 1. 尝试初始化 Session
    session = requests.Session()
    logged_in = False

    # 先检查本地是否有有效的 JSESSIONID
    jsid = load_env("JSESSIONID")
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
        # 如果未登录，尝试自动重试保存的账号密码
        if not logged_in:
            saved_user = load_env("SAVED_USER")
            saved_pass = load_env("SAVED_PASS")
            
            if saved_user and saved_pass:
                print(f"[系统] 正在尝试使用保存的账号 {saved_user} 自动登录...")
                session = login(saved_user, saved_pass)
                if session:
                    logged_in = True
                else:
                    print("[系统] 自动登录失败，保存的凭据可能已失效。")

        # 如果还是没登录（没保存或保存的失效了），手动输入
        if not logged_in:
            print("[系统] 请进行登录验证。")
            username = input("请输入学号: ").strip()
            password = get_password_with_mask("请输入密码: ")
            session = login(username, password)
            if not session:
                print("[系统] 登录失败，请重试。")
                continue
            
            # 登录成功后，询问是否保存
            save_choice = input("是否保存账号密码以便下次自动登录？(y/n): ").strip().lower()
            if save_choice == 'y':
                save_env("SAVED_USER", username)
                save_env("SAVED_PASS", password)
                print("[系统] 账号密码已保存到 .env。")
            
            logged_in = True

        # 主菜单逻辑
        print(f"\n{'='*20} 南理工教务系统工具 {'='*20}")
        print("1. 查询成绩")
        print("2. 查询课表")
        print("3. 切换账号 (并清除保存信息)")
        print("q. 退出程序")
        print("="*50)
        
        choice = input("请选择功能 (1/2/3/q): ").strip().lower()
        
        if choice == '1':
            if not fetch_scores(session):
                print("[系统] 获取成绩失败，Session 可能已失效，正在尝试重新连接...")
                logged_in = False
                save_env("JSESSIONID", "")
        elif choice == '2':
            if not fetch_courses(session):
                print("[系统] 获取课表失败，Session 可能已失效，正在尝试重新连接...")
                logged_in = False
                save_env("JSESSIONID", "")
        elif choice == '3':
            print("[系统] 正在注销并清除保存的信息...")
            save_env("JSESSIONID", "")
            save_env("SAVED_USER", "")
            save_env("SAVED_PASS", "")
            session = requests.Session() # 重置 session
            logged_in = False
            print("[系统] 已注销。")
        elif choice == 'q':
            print("[系统] 感谢使用，再见！")
            break
        else:
            print("[系统] 无效选择，请重新输入。")

if __name__ == "__main__":
    main()
