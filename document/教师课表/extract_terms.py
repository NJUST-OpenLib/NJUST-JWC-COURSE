import os
import json
import requests
from bs4 import BeautifulSoup

import sys

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
    """获取一个包含有效登录状态的 Session"""
    session = requests.Session()
    logged_in = False

    print("请输入 JSESSIONID (直接回车则尝试自动登录或手动输入账号密码):")
    manual_jsid = input("JSESSIONID=").strip()
    
    if manual_jsid:
        session.cookies.set('JSESSIONID', manual_jsid, domain='202.119.81.112')
        save_env("JSESSIONID", manual_jsid)
        # 验证手动输入的 JSESSIONID
        try:
            test_res = session.get('http://202.119.81.112:9080/njlgdx/kbcx/kbxx_teacher', headers=HEADERS, timeout=5)
            if "请先登录" not in test_res.text and "登录个人中心" not in test_res.text:
                logged_in = True
                print("[系统] 通过手动输入的 Cookie 登录成功。")
            else:
                print("[系统] 您输入的 Cookie 无效，将尝试其他登录方式...")
        except Exception as e:
            print(f"[系统] 验证 Cookie 失败: {e}")

    if not logged_in:
        jsid = load_env("JSESSIONID")
        if jsid:
            session.cookies.set('JSESSIONID', jsid, domain='202.119.81.112')
            try:
                test_res = session.get('http://202.119.81.112:9080/njlgdx/kbcx/kbxx_teacher_ifr', headers=HEADERS, timeout=5)
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
            save_choice = input("是否保存账号密码以便下次自动登录？(y/n): ").strip().lower()
            if save_choice == 'y':
                save_env("SAVED_USER", username)
                save_env("SAVED_PASS", password)
                print("[系统] 账号密码已保存。")
            logged_in = True
        else:
            print("[系统] 登录失败，程序退出。")
            return None

    return session

def extract_select_options(soup, select_id):
    select_element = soup.find('select', id=select_id)
    if select_element:
        options = select_element.find_all('option')
        result = []
        for option in options:
            val = option.get('value', '').strip()
            text = option.text.strip()
            # 忽略没有 value 的默认项
            if val:
                result.append({'value': val, 'text': text})
        return result
    return []

def main():
    session = get_session()
    if not session:
        return

    # 获取列表数据的来源为 kbxx_teacher
    url_main = 'http://202.119.81.112:9080/njlgdx/kbcx/kbxx_teacher'
    
    print(f"\n[系统] 正在请求主页面 {url_main} 抽取参数选项...")
    response = session.get(url_main, headers=HEADERS)
    response.encoding = 'utf-8'
    html_content = response.text
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 获取学年学期
    terms = extract_select_options(soup, 'xnxqh')

    departments = extract_select_options(soup, 'skyx')
    teachers = extract_select_options(soup, 'jg0101id')

    print(f"[结果] 提取到 {len(terms)} 个学年学期。")
    print(f"[结果] 提取到 {len(departments)} 个开课院系。")
    print(f"[结果] 提取到 {len(teachers)} 个教师。")

    # 根据要求存放于脚本所在同级目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    term_file = os.path.join(base_dir, 'extracted_terms.json')
    dept_file = os.path.join(base_dir, 'extracted_departments.json')
    teacher_file = os.path.join(base_dir, 'extracted_teachers.json')

    print(f"\n[系统] 正在按要求分别保存至文件...")
    
    with open(term_file, 'w', encoding='utf-8') as f:
        json.dump(terms, f, ensure_ascii=False, indent=4)
        
    with open(dept_file, 'w', encoding='utf-8') as f:
        json.dump(departments, f, ensure_ascii=False, indent=4)
        
    with open(teacher_file, 'w', encoding='utf-8') as f:
        json.dump(teachers, f, ensure_ascii=False, indent=4)
        
    print(f"✔️ 学年学期已保存到: {term_file}")
    print(f"✔️ 开课院系已保存到: {dept_file}")
    print(f"✔️ 教师ID已保存到:   {teacher_file}")

if __name__ == '__main__':
    main()
