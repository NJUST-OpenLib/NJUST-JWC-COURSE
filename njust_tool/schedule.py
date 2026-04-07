import re
from bs4 import BeautifulSoup
from .constants import COURSE_URL, HEADERS

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
