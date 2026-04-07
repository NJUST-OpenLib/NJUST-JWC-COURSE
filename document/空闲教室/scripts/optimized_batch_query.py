import requests
from bs4 import BeautifulSoup
import time
import os
import json

def parse_classroom_week_data(html_content):
    """
    解析一周的 HTML 表格并返回结构化数据。
    返回格式：{星期名: [ {room_name: ..., slots: [...]}, ... ]}
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', id='dataList')
    if not table:
        return None

    rows = table.find_all('tr')
    if len(rows) < 3:
        return None

    # 1. 解析第一行：获取星期及其跨度 (colspan)
    header_weeks_ths = rows[0].find_all('th')[1:] # 跳过第一个 "星期"
    week_mappings = []
    for th in header_weeks_ths:
        name = th.get_text(strip=True)
        span = int(th.get('colspan', 1))
        week_mappings.append((name, span))
    
    # 2. 解析第二行：获取具体节次
    header_slots_tds = rows[1].find_all('td')[1:] # 跳过第一个空 td
    slot_names = [td.get_text(strip=True) for td in header_slots_tds]

    # 建立列索引到 (星期名, 节次名) 的映射
    col_info = []
    current_slot_idx = 0
    for week_name, span in week_mappings:
        for _ in range(span):
            if current_slot_idx < len(slot_names):
                col_info.append((week_name, slot_names[current_slot_idx]))
                current_slot_idx += 1

    # 3. 解析教室数据并按星期分组
    # result = { "星期一": [ {room: ..., schedule: [...]}, ... ], ... }
    result_by_day = {}
    for week_name, _ in week_mappings:
        result_by_day[week_name] = []

    for tr in rows[2:]:
        tds = tr.find_all('td')
        if not tds: continue
        
        room_name = tds[0].get_text(strip=True)
        status_cells = tds[1:]
        
        # 预先为该教室在各个星期创建条目
        temp_room_schedules = {week_name: [] for week_name, _ in week_mappings}
        
        for i, td in enumerate(status_cells):
            if i >= len(col_info): break
            
            week_name, slot_name = col_info[i]
            status_text = td.get_text(strip=True)
            is_free = not bool(status_text)
            
            temp_room_schedules[week_name].append({
                "slot": slot_name,
                "is_free": is_free,
                "occupancy_type": status_text if status_text else None
            })
        
        # 将解析好的数据放入最终结果
        for week_name in result_by_day:
            result_by_day[week_name].append({
                "room_name": room_name,
                "schedule": temp_room_schedules[week_name]
            })

    return result_by_day

def save_day_files(week_num, day_name, day_data, output_dir, xnxqh):
    """
    保存单天的 JSON 和 TXT 文件。
    """
    # 提取星期数字 (例如 "星期一" -> 1)
    day_map = {"星期一": 1, "星期二": 2, "星期三": 3, "星期四": 4, "星期五": 5, "星期六": 6, "星期日": 7}
    day_num = day_map.get(day_name, 0)
    
    base_file_name = f"第{week_num}周-星期{day_num}-classroom"
    
    # 1. 保存 JSON
    json_path = f"{output_dir}/{base_file_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "week": week_num,
            "day": day_num,
            "day_name": day_name,
            "xnxqh": xnxqh,
            "data": day_data
        }, f, ensure_ascii=False, indent=2)
        
    # 2. 保存 TXT
    txt_path = f"{output_dir}/{base_file_name}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"第 {week_num} 周 {day_name} 教室详细占用状态报告\n")
        f.write("="*50 + "\n\n")
        for entry in day_data:
            f.write(f"{entry['room_name']}:\n")
            for s in entry['schedule']:
                status = "空闲" if s['is_free'] else "占用"
                f.write(f"    {s['slot']}: {status}")
            f.write("\n\n")
            
    print(f"  已保存: {base_file_name}.txt 和 .json")

def query_week_and_split(session_id, week, xnxqh="2025-2026-2", xqbh="01"):
    """
    通过一次请求获取整周数据，并在本地拆分。
    """
    url = "http://202.119.81.112:9080/njlgdx/kbxx/jsjy_query2"
    headers = {
        "Cookie": f"JSESSIONID={session_id}",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 一次请求 7 天 (xq=1 到 xq2=7)
    data = {
        "typewhere": "jszq",
        "xnxqh": xnxqh,
        "xqbh": xqbh,
        "jszt": "",    
        "zc": week,
        "zc2": week,
        "xq": "1",     
        "xq2": "7",    
        "jxqbh": "",
        "jxlbh": "",
        "jsbh": "",
        "bjfh": "",
        "rnrs": "",
        "jc": "",
        "jc2": ""
    }

    print(f"正在请求第 {week} 周数据 (包含 7 天)...")
    try:
        response = requests.post(url, headers=headers, data=data, timeout=45)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        print(f"正在本地拆分第 {week} 周数据...")
        result_by_day = parse_classroom_week_data(response.text)
        
        if not result_by_day:
            print(f"第 {week} 周未解析到有效数据。")
            return False
            
        output_dir = "f:/Github/NJUST-JWC-COURSE/document/空闲教室/output"
        os.makedirs(output_dir, exist_ok=True)
        
        for day_name, day_data in result_by_day.items():
            save_day_files(week, day_name, day_data, output_dir, xnxqh)
            
        return True
    except Exception as e:
        print(f"第 {week} 周请求或解析失败: {e}")
        return False

def main():
    print("=== 南理工教务系统空闲教室优化查询工具 (请求一次拆分七天) ===")
    session_id = input("请输入 JSESSIONID: ").strip()
    if not session_id:
        print("错误：JSESSIONID 不能为空")
        return

    xnxqh = input("请输入学年学期号 [2025-2026-2]: ").strip() or "2025-2026-2"
    
    # 只需要循环 19 次周请求，而不是 133 次天请求
    start_week = 1
    end_week = 19
    
    success_weeks = 0
    for week in range(start_week, end_week + 1):
        if query_week_and_split(session_id, week, xnxqh):
            success_weeks += 1
        
        # 延时，周请求间隔可以稍微长一点点，保护服务器
        if week < end_week:
            time.sleep(2) 

    print(f"\n批量查询完成！成功获取并拆分了 {success_weeks}/{end_week} 周的数据。")
    print(f"所有细分文件已保存至: f:/Github/NJUST-JWC-COURSE/document/空闲教室/output")
    
    print("\n[可视化预览示例]:")
    print("你可以启动本地服务器（如 python -m http.server 3000）后，通过以下链接预览数据：")
    print("http://127.0.0.1:3000/document/%E7%A9%BA%E9%97%B2%E6%95%99%E5%AE%A4/index.html?data=/document/%E7%A9%BA%E9%97%B2%E6%95%99%E5%AE%A4/output/%E7%AC%AC1%E5%91%A8-%E6%98%9F%E6%9C%9F1-classroom.json")

if __name__ == "__main__":
    main()
