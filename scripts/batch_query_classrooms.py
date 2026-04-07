import requests
from bs4 import BeautifulSoup
import time
import os
import json

def parse_classroom_details(html_content):
    """
    解析 HTML 并返回结构化的教室数据列表和格式化的文本报告。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', id='dataList')
    if not table:
        return [], "未找到数据表格。"

    rows = table.find_all('tr')
    if len(rows) < 3:
        return [], "表格行数不足。"

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

    # 建立列索引到 (星期, 节次) 的映射
    col_info = []
    current_slot_idx = 0
    for week_name, span in week_mappings:
        for _ in range(span):
            if current_slot_idx < len(slot_names):
                col_info.append((week_name, slot_names[current_slot_idx]))
                current_slot_idx += 1

    # 3. 解析教室数据
    classroom_data = []
    report_lines = []
    
    for tr in rows[2:]:
        tds = tr.find_all('td')
        if not tds: continue
        
        room_name = tds[0].get_text(strip=True)
        status_cells = tds[1:]
        
        room_entry = {
            "room_name": room_name,
            "schedule": []
        }
        
        room_status_parts = [f"{room_name}:"]
        current_week = ""
        
        for i, td in enumerate(status_cells):
            if i >= len(col_info): break
            
            week_name, slot_name = col_info[i]
            status_text = td.get_text(strip=True)
            is_free = not bool(status_text)
            
            # 添加到结构化数据
            room_entry["schedule"].append({
                "week_day": week_name,
                "slot": slot_name,
                "is_free": is_free,
                "occupancy_type": status_text if status_text else None
            })
            
            # 添加到文本报告
            if week_name != current_week:
                room_status_parts.append(f"\n  [{week_name}]")
                current_week = week_name
            
            status_label = "占用" if status_text else "空闲"
            room_status_parts.append(f"    {slot_name}: {status_label}")
        
        classroom_data.append(room_entry)
        report_lines.append(" ".join(room_status_parts))

    return classroom_data, "\n\n".join(report_lines)

def query_and_save_day(session_id, week, day, xnxqh="2025-2026-2", xqbh="01"):
    """
    查询指定周次和星期并保存报告和 JSON 数据。
    """
    url = "http://202.119.81.112:9080/njlgdx/kbxx/jsjy_query2"
    headers = {
        "Cookie": f"JSESSIONID={session_id}",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    data = {
        "typewhere": "jszq",
        "xnxqh": xnxqh,
        "xqbh": xqbh,
        "jszt": "",    
        "zc": week,
        "zc2": week,
        "xq": day,     
        "xq2": day,    
        "jxqbh": "",
        "jxlbh": "",
        "jsbh": "",
        "bjfh": "",
        "rnrs": "",
        "jc": "",
        "jc2": ""
    }

    print(f"正在查询: 第 {week} 周 - 星期 {day}...")
    try:
        response = requests.post(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        data_list, report_text = parse_classroom_details(response.text)
        
        # 确保保存路径存在
        output_dir = "f:/Github/NJUST-JWC-COURSE/document/空闲教室/output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        base_name = f"{output_dir}/第{week}周-星期{day}-classroom"
        
        # 保存文本报告
        with open(f"{base_name}.txt", "w", encoding="utf-8") as f:
            f.write(f"第 {week} 周 星期 {day} 教室详细占用状态报告\n")
            f.write("="*50 + "\n\n")
            f.write(report_text)
            
        # 保存 JSON 数据
        with open(f"{base_name}.json", "w", encoding="utf-8") as f_json:
            json.dump({
                "week": week,
                "day": day,
                "xnxqh": xnxqh,
                "data": data_list
            }, f_json, ensure_ascii=False, indent=2)
            
        print(f"已保存: {base_name}.txt 和 .json")
        return True
    except Exception as e:
        print(f"第 {week} 周 星期 {day} 查询失败: {e}")
        return False

def main():
    print("=== 南理工教务系统空闲教室批量查询工具 (按天分割) ===")
    session_id = input("请输入 JSESSIONID: ").strip()
    if not session_id:
        print("错误：JSESSIONID 不能为空")
        return

    xnxqh = input("请输入学年学期号 [2025-2026-2]: ").strip() or "2025-2026-2"
    
    start_week = 1
    end_week = 19
    
    total_requests = end_week * 7
    success_count = 0
    
    for week in range(start_week, end_week + 1):
        for day in range(1, 8): # 星期一到星期日
            if query_and_save_day(session_id, week, day, xnxqh):
                success_count += 1
            
            # 延时，避免请求过快
            time.sleep(0.5) 

    print(f"\n批量查询完成！成功获取 {success_count}/{total_requests} 个数据文件。")
    print(f"结果已保存至: f:/Github/NJUST-JWC-COURSE/document/空闲教室/output")

if __name__ == "__main__":
    main()
