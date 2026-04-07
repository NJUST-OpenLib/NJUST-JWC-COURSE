import requests
from njust_tool.constants import SCORE_URL, HEADERS
from njust_tool.utils import load_env, save_env, get_password_with_mask
from njust_tool.auth import login
from njust_tool.grades import fetch_scores
from njust_tool.schedule import fetch_courses

def main():
    # 1. 尝试初始化 Session
    session = requests.Session()
    logged_in = False

    # 先检查本地是否有有效的 JSESSIONID
    jsid = load_env("JSESSIONID")
    if jsid:
        # 注意：这里需要根据实际情况设置 domain，或者直接在请求时带上
        session.cookies.set('JSESSIONID', jsid, domain='202.119.81.112')
        print(f"[系统] 已从 .env 加载 JSESSIONID: {jsid}")
        # 验证 Cookie 是否有效
        try:
            test_res = session.get(SCORE_URL, headers=HEADERS)
            if "请先登录系统" not in test_res.text and "登录个人中心" not in test_res.text:
                logged_in = True
            else:
                print("[系统] 本地 Cookie 已过期。")
        except Exception as e:
            print(f"[系统] 验证 Cookie 时发生错误: {e}")

    while True:
        # 如果未登录，尝试自动重试保存的账号密码
        if not logged_in:
            saved_user = load_env("SAVED_USER")
            saved_pass = load_env("SAVED_PASS")
            
            if saved_user and saved_pass:
                print(f"[系统] 正在尝试使用保存的账号 {saved_user} 自动登录...")
                new_session = login(saved_user, saved_pass)
                if new_session:
                    session = new_session
                    logged_in = True
                else:
                    print("[系统] 自动登录失败，保存的凭据可能已失效。")

        # 如果还是没登录（没保存或保存的失效了），手动输入
        if not logged_in:
            print("[系统] 请进行登录验证。")
            username = input("请输入学号: ").strip()
            password = get_password_with_mask("请输入密码: ")
            new_session = login(username, password)
            if not new_session:
                print("[系统] 登录失败，请重试。")
                continue
            
            session = new_session
            # 登录成功后，询问是否保存
            save_choice = input("是否保存账号密码以便下次自动登录？(y/n): ").strip().lower()
            if save_choice == 'y':
                save_env("SAVED_USER", username)
                save_env("SAVED_PASS", password)
                print("[系统] 账号密码已保存到 .env。")
            
            logged_in = True

        # 主菜单逻辑
        print(f"\n{'='*20} 南理工教务系统工具 {'='*20}")
        print("1. 查询成绩")
        print("2. 查询课表")
        print("3. 切换账号 (并清除保存信息)")
        print("q. 退出程序")
        print("="*50)
        
        choice = input("请选择功能 (1/2/3/q): ").strip().lower()
        
        if choice == '1':
            if not fetch_scores(session):
                print("[系统] 获取成绩失败，Session 可能已失效，正在尝试重新连接...")
                logged_in = False
                save_env("JSESSIONID", "")
        elif choice == '2':
            json_choice = input("是否以 JSON 格式输出？(y/n, 默认 n): ").strip().lower()
            output_json = (json_choice == 'y')
            if not fetch_courses(session, output_json=output_json):
                print("[系统] 获取课表失败，Session 可能已失效，正在尝试重新连接...")
                logged_in = False
                save_env("JSESSIONID", "")
        elif choice == '3':
            print("[系统] 正在注销并清除保存的信息...")
            save_env("JSESSIONID", "")
            save_env("SAVED_USER", "")
            save_env("SAVED_PASS", "")
            session = requests.Session() # 重置 session
            logged_in = False
            print("[系统] 已注销。")
        elif choice == 'q':
            print("[系统] 感谢使用，再见！")
            break
        else:
            print("[系统] 无效选择，请重新输入。")

if __name__ == "__main__":
    main()
