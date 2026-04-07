import requests
from bs4 import BeautifulSoup
import sys

def parse_free_classrooms(html_content):
    """
    解析教务系统空闲教室 HTML。
    逻辑：找出指定查询范围内全周、全节次都为空闲的教室。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', id='dataList')
    if not table:
        return []

    rows = table.find_all('tr')
    if len(rows) < 3:
        return []

    # 解析教室数据
    free_rooms = []
    for tr in rows[2:]: # 从第三行开始是教室数据
        tds = tr.find_all('td')
        if not tds:
            continue
        
        # 教室名称在第一个 td
        room_info = tds[0].get_text(strip=True)
        
        # 检查该行所有状态列（tds[1:]）是否都为空
        # 在该系统中，空闲表示没有文字内容
        is_all_free = True
        for td in tds[1:]:
            if td.get_text(strip=True): # 如果有任何文字（如 L, G, K, X, J, ◆），说明该时段不空闲
                is_all_free = False
                break
        
        if is_all_free:
            free_rooms.append(room_info)
            
    return free_rooms

def get_input(prompt, default=None):
    if default:
        res = input(f"{prompt} [{default}]: ").strip()
        return res if res else default
    return input(f"{prompt}: ").strip()

def main():
    print("=== 南理工教务系统空闲教室查询工具 ===")
    print("提示：请确保已获取有效的 JSESSIONID")
    
    # 交互式输入
    jsessionid = get_input("请输入 JSESSIONID")
    if not jsessionid:
        print("错误：JSESSIONID 不能为空")
        return

    xnxqh = get_input("请输入学年学期号", "2025-2026-2")
    
    print("\n校区编号：01-孝陵卫校区, 4y-江阴校区")
    xqbh = get_input("请输入校区编号", "01")
    
    zc = get_input("请输入要查询的起始周次", "1")
    zc2 = get_input("请输入要查询的结束周次", zc)
    
    print("\n星期范围：1-周一, 7-周日")
    xq = get_input("请输入起始星期", "1")
    xq2 = get_input("请输入结束星期", "7")

    url = "http://202.119.81.112:9080/njlgdx/kbxx/jsjy_query2"
    headers = {
        "Cookie": f"JSESSIONID={jsessionid}",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    data = {
        "typewhere": "jszq",
        "xnxqh": xnxqh,
        "xqbh": xqbh,
        "jszt": "",    # 留空以获取详细状态表
        "zc": zc,
        "zc2": zc2,
        "xq": xq,
        "xq2": xq2,
        "jxqbh": "",
        "jxlbh": "",
        "jsbh": "",
        "bjfh": "",
        "rnrs": "",
        "jc": "",
        "jc2": ""
    }

    print(f"\n正在向服务器请求数据...")
    try:
        response = requests.post(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        print("正在解析结果...")
        free_rooms = parse_free_classrooms(response.text)
        
        if free_rooms:
            print(f"\n查询成功！在第 {zc}-{zc2} 周，星期 {xq}-{xq2} 范围内，全周空闲的教室共有 {len(free_rooms)} 个：")
            for room in free_rooms:
                print(f"- {room}")
        else:
            print(f"\n查询完成。在第 {zc}-{zc2} 周，星期 {xq}-{xq2} 范围内，未找到全周全时段空闲的教室。")
            
    except requests.exceptions.RequestException as e:
        print(f"\n请求失败：{e}")
    except Exception as e:
        print(f"\n发生错误：{e}")

if __name__ == "__main__":
    main()
