import json
import os
from bs4 import BeautifulSoup
from .constants import HEADERS

CET_URL = "http://202.119.81.112:9080/njlgdx/kscj/djkscj_list"

def fetch_cet_scores(session):
    """
    从指定 URL 获取 CET4/CET6 成绩，计算最高分并保存。
    """
    print(f"\n{'='*20} 正在获取四六级成绩 {'='*20}")
    try:
        response = session.get(CET_URL, headers=HEADERS)
        response.encoding = 'utf-8'

        if "请先登录系统" in response.text or "登录个人中心" in response.text:
            print("[CET] 会话已过期，请重新登录。")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 定位表格：HTML 中 id 是 " dataList" (带空格)，同时 class 是 "Nsb_table"
        # 优先使用 class 定位更稳妥
        table = soup.find('table', class_='Nsb_table')
        
        if not table:
            print("[CET] 未找到成绩表格，尝试备选方案...")
            table = soup.find('table', id=lambda x: x and 'dataList' in x)

        if not table:
            print("[CET] 错误：无法定位成绩表格。")
            return None

        # 2. 解析行数据
        all_rows = table.find_all('tr')
        cet4_records = []
        cet6_records = []

        # 注意：HTML 结构中有 2 行表头 (rowspan="2")，所以数据从第 3 行开始
        # 但为了稳妥，我们遍历所有行，通过 td 的数量和内容来判断
        for row in all_rows:
            cols = row.find_all('td')
            # 数据行通常有 9 列，表头行通常是 th
            if len(cols) < 9:
                continue
            
            # 提取字段
            course_name = cols[1].get_text(strip=True)
            # 总成绩在第 5 列（索引为 4）
            score_text = cols[4].get_text(strip=True)
            # 日期在最后一列（索引为 8）
            exam_date = cols[8].get_text(strip=True)

            try:
                score = int(score_text)
            except ValueError:
                score = 0

            record = {
                "course": course_name,
                "score": score,
                "date": exam_date,
            }

            if "CET4" in course_name:
                cet4_records.append(record)
            elif "CET6" in course_name:
                cet6_records.append(record)

        # 3. 处理分数逻辑（过滤掉 0 分，因为 0 分通常代表未出分或缺考）
        c4_valid = [r['score'] for r in cet4_records if r['score'] > 0]
        c6_valid = [r['score'] for r in cet6_records if r['score'] > 0]

        best_cet4 = max(c4_valid, default=0)
        best_cet6 = max(c6_valid, default=0)
        best_overall = max(best_cet4, best_cet6)

        # 4. 打印汇总
        def print_table(name, records):
            if not records:
                print(f"\n[{name}] 无记录")
                return
            print(f"\n{name} 历次成绩：")
            print(f"  {'日期':<15} {'总成绩':>6}")
            print("  " + "-" * 23)
            # 按日期降序排列（最新的在前面）
            for r in sorted(records, key=lambda x: x['date'], reverse=True):
                print(f"  {r['date']:<15} {r['score']:>6}")

        print_table("CET4", cet4_records)
        print_table("CET6", cet6_records)

        print(f"\n{'='*50}")
        print(f"  CET4 最高分：{best_cet4 if best_cet4 > 0 else '无'}")
        print(f"  CET6 最高分：{best_cet6 if best_cet6 > 0 else '无'}")
        print(f"  综合最高分：{best_overall if best_overall > 0 else '无'}")
        print(f"{'='*50}\n")

        # 5. 保存结果
        result = {
            "CET4": best_cet4,
            "CET6": best_cet6,
            "best": best_overall,
            "CET4_records": cet4_records,
            "CET6_records": cet6_records,
        }

        output_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', 'CET_score.json')
        )
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
            
        print(f"[CET] 结果已更新至：{output_path}")
        return result

    except Exception as e:
        print(f"[CET] 获取失败: {e}")
        return None