from bs4 import BeautifulSoup
from .constants import SCORE_URL, HEADERS

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

