# NJUST JWC TOOL 模块化工具包

本目录包含南京理工大学教务系统的功能模块，旨在通过模块化拆分提高代码的可读性、可维护性及复用性。

## 目录结构

```text
njust_tool/
├── __init__.py      # 包初始化文件
├── constants.py     # 配置信息与常量 (URL, HEADERS, 文件名)
├── utils.py         # 通用工具函数 (环境管理、密码遮罩输入)
├── auth.py          # 身份验证模块 (登录逻辑、Cookie 维护)
├── grades.py        # 成绩查询模块 (数据抓取与解析)
└── schedule.py      # 课表查询模块 (综合视图解析与学期切换)
```

## 模块说明

### [constants.py](./constants.py)
集中管理系统所需的硬编码信息。
- `LOGIN_URL`, `SCORE_URL`, `COURSE_URL`: 教务系统的接口地址。
- `HEADERS`: 模拟浏览器请求的 HTTP 头部。
- `ENV_FILE`: 本地配置存储文件名（默认为 `.env`）。

### [utils.py](./utils.py)
提供跨平台的通用支持功能。
- `get_password_with_mask()`: 在 Windows 控制台下实现类似 Unix 的星号遮罩密码输入。
- `save_env()`, `load_env()`: 简单的键值对存储，用于持久化 `JSESSIONID` 和登录凭据。

### [auth.py](./auth.py)
核心登录逻辑。
- `login(username, password)`: 执行登录流程，成功后返回 `requests.Session` 并自动保存 `JSESSIONID`。

### [grades.py](./grades.py)
成绩数据处理。
- `fetch_scores(session)`: 获取并以表格形式打印当前用户的成绩信息。

### [schedule.py](./schedule.py)
复杂的课表逻辑。
- `parse_courses(content, output_json=False)`: 结合了“格子视图”与“列表视图”的数据。支持控制台表格或 JSON 格式输出。
- `fetch_courses(session, output_json=False)`: 提供交互式的学期切换查询功能。支持在交互过程中选择不同学期并以 JSON 格式输出。

## 开发与扩展

如需添加新功能（例如：考试安排查询、自动选课等），请在 `njust_tool` 目录下新建对应的模块文件，并在主入口文件（如 `main_new.py`）中进行引用。
