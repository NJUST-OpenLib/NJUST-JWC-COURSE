from bs4 import BeautifulSoup

def test_local_html_parsing():
    """
    测试本地空闲教室 HTML 解析逻辑。
    """
    file_path = "f:/Github/NJUST-JWC-COURSE/document/空闲教室.html"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        soup = BeautifulSoup(html_content, 'html.parser')
        table = soup.find('table', id='dataList')
        if not table:
            print("未找到 id 为 'dataList' 的 table。")
            return

        rows = table.find_all('tr')
        if len(rows) < 3:
            print(f"表格行数不足 (仅 {len(rows)} 行)。")
            return

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

        # 3. 解析教室数据并生成详细报告
        report_lines = []
        for tr in rows[2:]:
            tds = tr.find_all('td')
            if not tds: continue
            
            room_name = tds[0].get_text(strip=True)
            status_cells = tds[1:]
            
            room_status_parts = [f"{room_name}:"]
            
            current_week = ""
            for i, td in enumerate(status_cells):
                if i >= len(col_info): break
                
                week_name, slot_name = col_info[i]
                
                # 如果换了星期，添加星期标识
                if week_name != current_week:
                    room_status_parts.append(f"\n  [{week_name}]")
                    current_week = week_name
                
                # 判定状态：有内容即占用，无内容即空闲
                status_text = td.get_text(strip=True)
                status_label = "占用" if status_text else "空闲"
                
                room_status_parts.append(f"    {slot_name}: {status_label}")
            
            report_lines.append(" ".join(room_status_parts))

        # 4. 汇总输出
        final_report = "\n" + "="*50 + "\n"
        final_report += "教室详细占用状态报告\n"
        final_report += "="*50 + "\n"
        final_report += "\n\n".join(report_lines)
        
        # 同时保存到文件，防止控制台输出过多被截断
        output_file = "f:/Github/NJUST-JWC-COURSE/document/classroom_detailed_report.txt"
        with open(output_file, "w", encoding="utf-8") as f_out:
            f_out.write(final_report)
            
        print(f"解析完成！详细报告已生成并保存至: {output_file}")
        print(f"报告共包含 {len(report_lines)} 个教室。")
        
        # 在控制台展示前 3 个作为示例
        print("\n--- 报告内容示例 (前3个教室) ---")
        print("\n\n".join(report_lines[:3]))
        print("\n... 其余部分请查看生成的文本文件。")

    except Exception as e:
        print(f"测试过程中出错: {e}")

if __name__ == "__main__":
    test_local_html_parsing()
