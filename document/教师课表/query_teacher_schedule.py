import os
import sys
import json
import requests
from bs4 import BeautifulSoup

# 将项目根目录（上两级目录）添加到 sys.path 中
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 尝试引用您现有的 auth.py 和 utils.py
try:
    from njust_tool.utils import load_env, save_env, get_password_with_mask
    from njust_tool.auth import login
    from njust_tool.constants import HEADERS
except ImportError:
    print(f"[错误] 找不到 njust_tool 包，当前项目根目录识别为: {project_root}")
    exit(1)

def get_session():
    """复用登录逻辑片段获取 Session"""
    session = requests.Session()
    logged_in = False

    print("请输入 JSESSIONID (直接回车则尝试自动登录或手动输入账号密码):")
    manual_jsid = input("JSESSIONID=").strip()
    
    if manual_jsid:
        session.cookies.set('JSESSIONID', manual_jsid, domain='202.119.81.112')
        save_env("JSESSIONID", manual_jsid)
        try:
            test_res = session.get('http://202.119.81.112:9080/njlgdx/kbcx/kbxx_teacher', headers=HEADERS, timeout=5)
            if "请先登录" not in test_res.text and "登录个人中心" not in test_res.text:
                logged_in = True
                print("[系统] 通过手动输入的 Cookie 登录成功。")
        except Exception:
            pass

    if not logged_in:
        jsid = load_env("JSESSIONID")
        if jsid:
            session.cookies.set('JSESSIONID', jsid, domain='202.119.81.112')
            try:
                test_res = session.get('http://202.119.81.112:9080/njlgdx/kbcx/kbxx_teacher', headers=HEADERS, timeout=5)
                if "请先登录" not in test_res.text and "登录个人中心" not in test_res.text:
                    logged_in = True
                    print(f"[系统] 已沿用 .env 中的 JSESSIONID 自动登录成功。")
            except Exception:
                pass

    if not logged_in:
        saved_user = load_env("SAVED_USER")
        saved_pass = load_env("SAVED_PASS")
        if saved_user and saved_pass:
            print(f"[系统] 正在尝试使用保存的账号 {saved_user} 自动登录...")
            new_session = login(saved_user, saved_pass)
            if new_session:
                session = new_session
                logged_in = True

    if not logged_in:
        print("[系统] 暂无有效登录信息，请进行账号验证。")
        username = input("请输入学号: ").strip()
        password = get_password_with_mask("请输入密码: ")
        new_session = login(username, password)
        if new_session:
            session = new_session
            logged_in = True
        else:
            print("[系统] 登录失败，程序退出。")
            return None

    return session

def get_display_width(s):
    """计算字符串显示宽度，中文字符处理为宽度 2"""
    width = 0
    for c in str(s):
        if '\u4e00' <= c <= '\u9fa5' or '\uFF00' <= c <= '\uFFEF' or '\u3000' <= c <= '\u303F':
            width += 2
        else:
            width += 1
    return width

def pad_string(s, width):
    """使用空格补齐字符串，使终端能够平齐显示"""
    s = str(s).strip()
    dw = get_display_width(s)
    if dw < width:
        return s + ' ' * (width - dw)
    return s

def search_in_json(filepath, query):
    """简单的辅助工具：从 Json 里的 text 字段进行模糊匹配"""
    if not os.path.exists(filepath):
        print(f"[错误] 尚未提取参数文件: {filepath}，请先运行 extract_terms.py")
        return []
        
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    results = [item for item in data if query in item.get('text', '') or query in item.get('value', '')]
    return results

def main():
    session = get_session()
    if not session:
        return

    term_file = os.path.join(current_dir, 'extracted_terms.json')
    teacher_file = os.path.join(current_dir, 'extracted_teachers.json')

    while True:
        print("\n" + "="*30)
        print("         主菜单")
        print("="*30)
        print("--- 1. 选择学年学期 ---")
        term_query = input("请输入查询的学期关键字 (如 '2025' 或 '2025-2026-2'。直接输入 'q' 退出): ").strip()
        
        if term_query.lower() == 'q':
            print("[系统] 已退出程序。")
            break
            
        term_matches = search_in_json(term_file, term_query)
        
        if not term_matches:
            print("[错误] 未找到匹配的学年学期。")
            continue
            
        if len(term_matches) > 1:
            print("[系统] 找到多个匹配的学期：")
            for i, t in enumerate(term_matches):
                print(f"  {i+1}. {t['text']} ({t['value']})")
            idx = input("请选择准确序号 (直接回车取消重新搜索): ").strip()
            if not idx:
                continue
            try:
                term_value = term_matches[int(idx)-1]['value']
            except ValueError:
                print("[错误] 序号格式错误，请重新搜索。")
                continue
            except IndexError:
                print("[错误] 序号超出范围，请重新搜索。")
                continue
        else:
            term_value = term_matches[0]['value']
            
        print(f"[系统] 确定查询学期为: {term_value}")

        print("\n--- 2. 选择教师 ---")
        teacher_query = input("请输入目标查询教师姓名 (支持模糊搜索，输入 'q' 退出，'b' 回到学期选择): ").strip()
        
        if teacher_query.lower() == 'q':
            print("[系统] 已退出程序。")
            break
        elif teacher_query.lower() == 'b':
            continue
            
        teacher_matches = search_in_json(teacher_file, teacher_query)
            
        if not teacher_matches:
            print("[错误] 在已提取的教师字典里未发现名字带有此字眼的教师。")
            continue
        
        if len(teacher_matches) > 1:
            print(f"[系统] 共找到 {len(teacher_matches)} 位相关的教师：")
            
            page_size = 20
            total_pages = (len(teacher_matches) + page_size - 1) // page_size
            current_page = 1
            
            selected_idx = None
            
            while True:
                start_idx = (current_page - 1) * page_size
                end_idx = min(start_idx + page_size, len(teacher_matches))
                
                print(f"\n--- 第 {current_page}/{total_pages} 页 ---")
                for i in range(start_idx, end_idx):
                    idx_str = f"{i+1}."
                    name_str = teacher_matches[i]['text']
                    # 使用包含中文对齐考虑的 pad_string 替代占位，使输出整齐
                    print(f"  {idx_str:<4} {pad_string(name_str, 14)} ---> 数据库ID: {teacher_matches[i]['value']}")
                
                print(f"-"*22)
                prompt_text = "请输入准确数字序号 ("
                if current_page < total_pages:
                    prompt_text += "输入 'n' 下一页, "
                if current_page > 1:
                    prompt_text += "输入 'p' 上一页, "
                prompt_text += "直接回车取消): "
                
                user_input = input(prompt_text).strip()
                
                if not user_input:
                    break
                elif user_input.lower() == 'n' and current_page < total_pages:
                    current_page += 1
                elif user_input.lower() == 'p' and current_page > 1:
                    current_page -= 1
                else:
                    try:
                        selected_idx = int(user_input) - 1
                        if 0 <= selected_idx < len(teacher_matches):
                            teacher_value = teacher_matches[selected_idx]['value']
                            teacher_text = teacher_matches[selected_idx]['text']
                            break
                        else:
                            print("[错误] 序号超出规范，请重新输入。")
                            selected_idx = None
                    except ValueError:
                        print("[错误] 格式不支持，请输入有效指令名。")
            
            if selected_idx is None:
                continue
        else:
            teacher_value = teacher_matches[0]['value']
            teacher_text = teacher_matches[0]['text']
            
        print(f"[系统] 确定查询教师为: {teacher_text}，对应的系统唯一检索 ID 是: {teacher_value}")

        # 第 3 步：正式向目标 _ifr 接口提交核心参数 POST 查询
        url = "http://202.119.81.112:9080/njlgdx/kbcx/kbxx_teacher_ifr"
        
        data = {
            "xnxqh": term_value,
            "skyx": "",  # 留空
            "jszc": "",  # 留空
            "jg0101id": teacher_value
        }

        headers = HEADERS.copy()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        print(f"\n[请求中] 正在获取并解析课表数据...")
        response = session.post(url, headers=headers, data=data)
        response.encoding = 'utf-8'

        if response.status_code == 200:
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            tables = soup.find_all('table')
            if not tables:
                print("\n[⚠ 系统] 请求虽然成功 200，但是在页面内未检索到表格 <table>，可能该学期此教师并未排课。")
            else:
                print(f"\n 【{teacher_text}】 的 {term_value} 课表:")
                print("="*60)
                
                course_count = 0
                for table in tables:
                    for row in table.find_all('tr'):
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 11:
                            # 使用 separator 处理 br 留下的空隙，使排版更整洁
                            texts = [c.get_text(separator=' ', strip=True) for c in cols]
                            
                            if "序号" in texts[0] or (len(texts) > 3 and "开课编号" in texts[3]):
                                continue
                            
                            course_count += 1
                            course_name = texts[4] if len(texts) > 4 else "-"
                            course_num = texts[3] if len(texts) > 3 else "-"
                            print(f"第 {course_count} 门课: 【{course_name}】 (编号: {course_num})")
                            
                            classes = texts[1] if len(texts) > 1 else "-"
                            students = texts[2] if len(texts) > 2 else "0"
                            print(f" ├─  上课班级: {classes} (人数: {students}人)")
                            
                            time_info = texts[7] if len(texts) > 7 else "-"
                            
                            # 在此挂载一层时间文本清洗逻辑
                            readable_time = time_info
                            if len(time_info) >= 3 and time_info[0] in '1234567' and time_info[1:].isdigit() and len(time_info[1:]) % 2 == 0:
                                day_map = {'1':'星期一','2':'星期二','3':'星期三','4':'星期四','5':'星期五','6':'星期六','7':'星期日'}
                                day_name = day_map[time_info[0]]
                                p_str = time_info[1:]
                                periods = [str(int(p_str[i:i+2])) for i in range(0, len(p_str), 2)]
                                
                                # 尝试折叠连续节次 (如: 第1,2,3,4,5节 -> 第1-5节)
                                if len(periods) > 2 and all(int(periods[k]) - int(periods[k-1]) == 1 for k in range(1, len(periods))):
                                    readable_time = f"{day_name} 第{periods[0]}-{periods[-1]}节"
                                else:
                                    readable_time = f"{day_name} 第{','.join(periods)}节"

                            weeks = texts[9] if len(texts) > 9 else "-"
                            odd_even = texts[10] if len(texts) > 10 else "-"
                            print(f" ├─  上课时间: {readable_time}  [ {weeks}周 {odd_even} ]")
                            
                            location = texts[8] if len(texts) > 8 else ""
                            if not location or location == "-":
                                print(f" ├─  上课地点: 暂无安排 (提醒: 系统中当前未指定教室)")
                            else:
                                print(f" ├─  上课地点: {location}")
                            
                            group = texts[11] if len(texts) > 11 else ""
                            if group:
                                print(f" └─  分组名称: {group}")
                            else:
                                print(" └─  暂无分组")
                                
                            print("-" * 60)
                
                if course_count == 0:
                    print("[系统] 未能在表格中解析到有效的课程数据行，可能没有查询到此周期的教学安排。")
        else:
            print(f"\n[❌ 错误] 通信失败，教务处服务器返回异常错误码: {response.status_code}")

        # 当单次查询结束后，给用户一点缓冲时间
        next_step = input("\n[操作] 课表查询完毕。按回车键回到主菜单继续查询，或输入 'q' 退出程序: ").strip().lower()
        if next_step == 'q':
            print("[系统] 已退出程序，感谢使用。")
            break

if __name__ == '__main__':
    main()
