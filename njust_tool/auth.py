import requests
from .constants import LOGIN_URL, HEADERS
from .utils import save_env

def login(username, password):
    """执行登录并保存 Cookie"""
    print(f"[登录] 正在尝试登录用户：{username}...")
    session = requests.Session()
    post_data = {
        'USERNAME': username,
        'PASSWORD': password
    }
    
    try:
        # allow_redirects=False 模拟之前的 urllib 行为，因为我们需要手动处理重定向并获取 Cookie
        response = session.post(LOGIN_URL, data=post_data, headers=HEADERS, allow_redirects=False)
        
        # 增加真实性校验：强智系统登录成功通常会返回 302 重定向
        if response.status_code != 302:
            if "密码错误" in response.text:
                print("[登录] 登录失败: 密码错误。")
            elif "验证码" in response.text:
                print("[登录] 登录失败: 需要验证码。")
            else:
                print(f"[登录] 登录失败: 服务器返回状态码 {response.status_code}")
            return None

        jsessionid = session.cookies.get('JSESSIONID')
        if jsessionid:
            save_env("JSESSIONID", jsessionid)
            print(f"[登录] 成功获取 JSESSIONID: {jsessionid}")
            return session
        else:
            print("[登录] 未能获取 JSESSIONID，登录可能失败。")
            return None
    except Exception as e:
        print(f"[登录] 发生错误: {e}")
        return None
