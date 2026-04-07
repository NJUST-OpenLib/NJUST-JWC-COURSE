import os
import sys
import msvcrt
from .constants import ENV_FILE

def get_password_with_mask(prompt="请输入密码: "):
    """
    密码输入：输入时显示最后一位，前面的显示为 *
    仅适用于 Windows (msvcrt)
    """
    print(prompt, end='', flush=True)
    password = []
    while True:
        ch = msvcrt.getch()
        # 处理回车
        if ch in (b'\r', b'\n'):
            print()
            return "".join(password)
        # 处理退格
        elif ch == b'\x08':
            if password:
                password.pop()
                # 抹掉之前显示的所有内容并重绘
                # 简单处理：退格后，显示全 * 的前 len-1 位
                sys.stdout.write('\r' + prompt + '*' * len(password) + ' ' + '\b')
                sys.stdout.flush()
        # 处理普通字符
        else:
            try:
                char = ch.decode('utf-8')
                if char.isprintable():
                    password.append(char)
                    # 重新显示：前面的位显示 *，最后一位显示原字符
                    mask = '*' * (len(password) - 1)
                    sys.stdout.write('\r' + prompt + mask + char)
                    sys.stdout.flush()
            except UnicodeDecodeError:
                continue

def save_env(key, value):
    """保存配置到 .env 文件"""
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    updated = False
    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                updated = True
            else:
                f.write(line)
        if not updated:
            f.write(f"{key}={value}\n")

def load_env(key):
    """从 .env 文件读取配置"""
    if not os.path.exists(ENV_FILE):
        return None
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith(f"{key}="):
                return line.split('=', 1)[1].strip()
    return None
