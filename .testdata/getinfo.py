import pandas as pd
from bs4 import BeautifulSoup
import re

def parse_and_visualize(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # --- 1. 解析 dataList 建立精确小节映射 ---
    # 结果：{('课程名', '星期'): '01-03'}
    section_map = {}
    data_table = soup.find('table', id='dataList')
    if data_table:
        for row in data_table.find_all('tr')[1:]:
            tds = row.find_all('td')
            if len(tds) < 10: continue
            c_name = tds[3].get_text(strip=True)
            time_raw = tds[5].get_text('|', strip=True).split('|')
            for item in time_raw:
                match = re.search(r'(星期[一二三四五六日])\((.*?)\)', item)
                if match:
                    day, sec = match.groups()
                    sec = sec.replace('小节', '')
                    section_map[(c_name, day)] = sec

    # --- 2. 解析 kbtable 提取详细信息 ---
    results = []
    kb_table = soup.find('table', id='kbtable')
    days_list = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    
    if kb_table:
        rows = kb_table.find_all('tr')[1:]
        for row in rows:
            cells = row.find_all('td')
            for col_idx, cell in enumerate(cells):
                day = days_list[col_idx]
                # 抓取详细视图 div (kbcontent)
                content_div = cell.find('div', class_='kbcontent')
                if not content_div or not content_div.get_text(strip=True):
                    continue
                
                # 按照分隔线拆分
                parts = re.split(r'-{5,}', str(content_div))
                for p in parts:
                    p_soup = BeautifulSoup(p, 'html.parser')
                    text_parts = [t.strip() for t in p_soup.get_text("|", strip=True).split("|") if t.strip()]
                    if not text_parts: continue
                    
                    course_name = text_parts[0]
                    teacher = p_soup.find('font', title='老师').get_text(strip=True) if p_soup.find('font', title='老师') else ""
                    weeks = p_soup.find('font', title='周次(节次)').get_text(strip=True).replace('(周)', '[周]') if p_soup.find('font', title='周次(节次)') else ""
                    location = p_soup.find('font', title='教室').get_text(strip=True) if p_soup.find('font', title='教室') else ""
                    
                    # 匹配精确小节
                    precise_sec = section_map.get((course_name, day), "??")
                    
                    results.append({
                        "Name": course_name,
                        "Time": f"{day}[{precise_sec}节]",
                        "Weeks": weeks,
                        "Teacher": teacher,
                        "Loc": location
                    })

    # --- 3. 排序与格式化输出 ---
    # 先按课程名排序，再按时间排序
    df = pd.DataFrame(results).drop_duplicates()
    df = df.sort_values(by=['Name', 'Time'])

    print(f"\n{'='*100}")
    print(f"{'序号':<6} {'课程名称':<25} {'上课时间':<18} {'周次':<12} {'地点':<15} {'教师'}")
    print(f"{'-'*100}")

    current_course = ""
    course_idx = 0
    
    for _, row in df.iterrows():
        # 如果是新课程，序号增加
        if row['Name'] != current_course:
            course_idx += 1
            current_course = row['Name']
            idx_str = f"[{course_idx}]"
        else:
            idx_str = "" # 同一门课的不同时间段不重复显示序号

        # 格式化输出
        print(f"{idx_str:<6} {row['Name']:<25} {row['Time']:<18} {row['Weeks']:<12} {row['Loc']:<15} {row['Teacher']}")

    print(f"{'='*100}\n")

# 运行
parse_and_visualize('.testdata/ m,ki9
index.html')