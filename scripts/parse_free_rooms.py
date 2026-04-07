import requests
from bs4 import BeautifulSoup
import sys

def parse_free_classrooms(html_content):
    """
    解析教务系统空闲教室 HTML。
    逻辑：
    1. 找到 id 为 'dataList' 的 table。
    2. 第一行 th 定义了星期（每个星期占 6 列，因为一天有 5 大节 + 1 中午）。
    3. 第二行 td 定义了具体的节次。
    4. 之后的每一行 tr 代表一个教室。
    5. 教室行的第一个 td 是教室名，之后的 td 是该教室在对应星期和节次的状态。
    6. td 内容为空即为空闲。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', id='dataList')
    if not table:
        return []

    rows = table.find_all('tr')
    if len(rows) < 3:
        return []

    # 解析表头获取星期分布
    # 第一行：<th>星期</th>, <th colspan="6">星期一</th>, ...
    header_weeks = rows[0].find_all('th')[1:] # 跳过第一个 "星期"
    week_names = []
    for th in header_weeks:
        name = th.get_text(strip=True)
        colspan = int(th.get('colspan', 1))
        week_names.append((name, colspan))

    # 解析教室数据
    free_rooms = []
    for tr in rows[2:]: # 从第三行开始是教室数据
        tds = tr.find_all('td')
        if not tds:
            continue
        
        # 教室名称在第一个 td
        room_info = tds[0].get_text(strip=True)
        
        # 检查是否全周全节次空闲
        # 根据用户要求：找出指定周内全周的空闲教室
        # 这里的 "全周" 指的是返回的 HTML 中包含的所有星期和节次
        is_all_free = True
        status_tds = tds[1:]
        
        for td in status_tds:
            if td.get_text(strip=True): # 如果有内容（如 L, G, K, X, J, ◆），则不是空闲
                is_all_free = False
                break
        
        if is_all_free:
            free_rooms.append(room_info)
            
    return free_rooms

def query_free_classrooms(session_id, xnxqh, zc, xq_start=1, xq_end=7, xqbh="01"):
    """
    发送请求并解析全周空闲教室。
    """
    url = "http://202.119.81.112:9080/njlgdx/kbxx/jsjy_query2"
    headers = {
        "Cookie": f"JSESSIONID={session_id}",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 为了查询“全周”空闲，我们将 zc 和 zc2 设为同一周
    # 将 xq 和 xq2 设为 1 到 7
    data = {
        "typewhere": "jszq",
        "xnxqh": xnxqh,
        "xqbh": xqbh,
        "jszt": "",    # 留空以获取详细状态表
        "zc": zc,
        "zc2": zc,
        "xq": xq_start,
        "xq2": xq_end,
        "jxqbh": "",
        "jxlbh": "",
        "jsbh": "",
        "bjfh": "",
        "rnrs": "",
        "jc": "",
        "jc2": ""
    }

    print(f"正在查询 {xnxqh} 第 {zc} 周 (星期{xq_start}至{xq_end}) 的空闲教室...")
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        
        # 处理可能的编码问题
        response.encoding = response.apparent_encoding
        
        rooms = parse_free_classrooms(response.text)
        return rooms
    except Exception as e:
        print(f"请求失败: {e}")
        return []

if __name__ == "__main__":
    # 示例用法
    JSESSIONID = "YOUR_SESSION_ID" # 替换为实际 ID
    XNXQH = "2025-2026-2"
    WEEK = "1"
    
    # 如果有本地文件用于测试
    # with open("f:/Github/NJUST-JWC-COURSE/document/空闲教室.html", "r", encoding="utf-8") as f:
    #     rooms = parse_free_classrooms(f.read())
    #     print(f"解析到全周空闲教室 ({len(rooms)} 个):")
    #     for r in rooms: print(r)

    # 实际请求示例（需要有效的 JSESSIONID）
    if JSESSIONID == "YOUR_SESSION_ID":
        print("请先在脚本中设置有效的 JSESSIONID")
    else:
        free_rooms = query_free_classrooms(JSESSIONID, XNXQH, WEEK)
        if free_rooms:
            print(f"\n第 {WEEK} 周全周空闲的教室共有 {len(free_rooms)} 个:")
            for room in free_rooms:
                print(f"- {room}")
        else:
            print("未找到全周空闲的教室。")
