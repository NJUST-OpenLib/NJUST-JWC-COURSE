# 教师课表查询工具 —— 开发文档

> 本工具用于查询南京理工大学教务系统中指定教师的课表信息，由两个脚本协同完成：`extract_terms.py` 负责抓取并缓存参数数据，`query_teacher_schedule.py` 负责查询和展示课表。

---

## 目录

- [依赖项](#依赖项)
- [项目结构](#项目结构)
- [接口说明](#接口说明)
  - [认证说明](#认证说明)
  - [接口一：获取参数列表（GET）](#接口一获取参数列表get)
  - [接口二：查询教师课表（POST）](#接口二查询教师课表post)
  - [响应数据解析](#响应数据解析)
- [手动请求示例（curl）](#手动请求示例curl)
  - [获取学期与教师列表](#获取学期与教师列表)
  - [查询教师课表](#查询教师课表)
- [脚本使用方法](#脚本使用方法)
  - [第一步：extract_terms.py](#第一步extracttermspy)
  - [第二步：query_teacher_schedule.py](#第二步queryteacherschedulepy)
- [登录认证机制](#登录认证机制)
- [缓存文件说明](#缓存文件说明)
- [核心模块依赖](#核心模块依赖)
- [常见问题](#常见问题)

---

## 依赖项

```bash
pip install requests beautifulsoup4
```

同时需要项目根目录下的 `njust_tool` 包（包含 `auth.py`、`utils.py`、`constants.py`）。

---

## 项目结构

```
project_root/
├── njust_tool/
│   ├── auth.py
│   ├── utils.py
│   └── constants.py
└── some/sub/dir/                    ← 脚本所在目录（可任意两级子目录）
    ├── extract_terms.py
    ├── query_teacher_schedule.py
    ├── extracted_terms.json         ← 运行后自动生成
    ├── extracted_departments.json   ← 运行后自动生成
    └── extracted_teachers.json      ← 运行后自动生成
```

> 脚本通过 `os.path` 自动向上两级定位 `project_root` 并将其加入 `sys.path`，无需手动配置路径。

---

## 接口说明

### 认证说明

教务系统使用基于 Session 的认证机制，**所有接口均需在请求中携带有效的 `JSESSIONID` Cookie**，否则响应内容会包含「请先登录」或跳转到登录页。

**获取 JSESSIONID 的方法：**

1. 在浏览器访问 `http://202.119.81.112:9080/njlgdx/` 并完成登录
2. 打开开发者工具（F12）→ Application → Cookies
3. 找到 `JSESSIONID` 字段，复制其值

> Session 有效期较短，失效后需重新登录获取。

**所有请求需携带以下 Header（实际上只有Cookie必填）：**

| Header 字段 | 示例值 | 必须 | 说明 |
|---|---|---|---|
| `User-Agent` | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36` | ✅ | 模拟浏览器，缺失可能被服务器拒绝 |
| `Cookie` | `JSESSIONID=ABCDEF1234567890ABCDEF1234567890` | ✅ | 认证凭据 |
| `Referer` | `http://202.119.81.112:9080/njlgdx/kbcx/kbxx_teacher` | ✅（POST） | POST 请求必须携带，缺失可能返回 403 |
| `Content-Type` | `application/x-www-form-urlencoded` | ✅（POST） | POST 请求声明 Body 编码方式 |
| `Accept` | `text/html,application/xhtml+xml,*/*;q=0.8` | 建议 | 声明接受 HTML 响应 |
| `Accept-Language` | `zh-CN,zh;q=0.9` | 建议 | 语言偏好 |

---

### 接口一：获取参数列表（GET）

```
GET http://202.119.81.112:9080/njlgdx/kbcx/kbxx_teacher
```

返回值：HTML

**用途：** 获取课表查询所需的三类下拉参数——学年学期、开课院系、教师列表。返回完整 HTML 页面，需解析其中的 `<select>` 元素。


**响应中需解析的 `<select>` 元素：**

| `select` id | 含义 | 对应 POST 参数 |
|---|---|---|
| `xnxqh` | 学年学期 | `xnxqh` |
| `skyx` | 开课院系 | `skyx` |
| `jg0101id` | 教师 | `jg0101id` |

**响应片段示例：**

```html
<select id="xnxqh" name="xnxqh">
  <option value="">--请选择--</option>
  <option value="2025-2026-1">2025-2026学年第1学期</option>
  <option value="2024-2025-2">2024-2025学年第2学期</option>
</select>

<select id="jg0101id" name="jg0101id">
  <option value="">--请选择--</option>
  <option value="A0F3B2">宗士增</option>
  <option value="C1D4E5">张三</option>
</select>
```

> `value` 属性为提交 POST 请求时使用的实际参数值。忽略 `value` 为空的默认占位项。

---

### 接口二：查询教师课表（POST）

```
POST http://202.119.81.112:9080/njlgdx/kbcx/kbxx_teacher_ifr
Content-Type: application/x-www-form-urlencoded
```

**用途：** 提交学期和教师 ID，返回该教师的完整课表 HTML 页面。

**Body 参数（form-urlencoded 格式）：**

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|---|---|---|---|---|
| `xnxqh` | string | 是 | 学年学期标识符，来自接口一 | `2025-2026-1` |
| `jg0101id` | string | 否 | 教师唯一ID | `A0F3B2` |
| `skyx` | string | 否 | 开课院系筛选，留空不限制 | `""` |
| `jszc` | string | 否 | 职称筛选，留空不限制 | `""` |

**响应：** 返回 HTML 页面，内含 `<table>` 标签，每个 `<tr>` 为一条课程安排记录。

---

### 响应数据解析

#### 表格结构

响应 HTML 中课表表格的表头与各列含义如下：

| 列索引（0-based） | 表头字段 | 说明 |
|---|---|---|
| 0 | 序号 | 行序号，可忽略 |
| 1 | 上课班级 | 上课班级名称 |
| 2 | 排课人数 | 选课学生人数 |
| 3 | 开课编号 | 课程唯一编号 |
| 4 | 开课课程 | 课程名称 |
| 5 | 授课教师 | 教师姓名 |
| 6 | 教师所在院系 | 教师院系代码 |
| 7 | 开课时间 | 紧凑编码格式，见下方说明 |
| 8 | 上课地点 | 教室名称 |
| 9 | 上课周次 | 如 `1-13`、`1-18` |
| 10 | 单双周 | `全周` / `单周` / `双周` |
| 11 | 分组名 | 分组名称，无则为空 |

**原始 HTML 行示例：**

```html
<tr>
  <td align="left"></td>
  <td align="left">40</td>
  <td align="left">05021702-3</td>
  <td align="left">工程制图</td>
  <td align="left">宗士增</td>
  <td align="left">000</td>
  <td align="left" style="width:150px;word-wrap:break-word; overflow:hidden;">40203</td>
  <td align="left" style="width:150px;word-wrap:break-word; overflow:hidden;">江阴致新B208</td>
  <td align="left">1-13</td>
  <td align="left">全周</td>
  <td align="left"></td>
</tr>
```

对应解析结果：课程「工程制图」，编号 `05021702-3`，40人，星期四第2、3节（时间编码 `40203`，见下方），地点江阴致新B208，第1-13周全周。

---

#### 上课时间编码格式

`开课时间`（列索引 7）字段使用紧凑数字编码，格式规则如下：

```
[星期位, 1位] + [节次位, 每节2位, 可重复]
```

- **首位（1位）**：星期，`1`=周一，`2`=周二，……`7`=周日
- **后续（每2位一组）**：节次编号，按从小到大排列，不足2位时前补零（如第2节为 `02`）

**示例解析：**

| 原始编码 | 星期位 | 节次原始段 | 节次解析 | 最终结果 |
|---|---|---|---|---|
| `414` | `4` | `14` | 第14节 | 星期四 第14节 |
| `214` | `2` | `14` | 第14节 | 星期二 第14节 |
| `40203` | `4` | `02` `03` | 第2、3节 | 星期四 第2-3节 |
| `301020304050607080910` | `3` | `01`..`10` | 第1至10节 | 星期三 第1-10节 |

**连续节次折叠规则（脚本显示逻辑）：**

若解析出的节次列表全部连续（相邻差值均为1），脚本自动折叠显示为「第N-M节」；若存在不连续节次，则逐一列出，如「第2、5、8节」。

---

## 手动请求示例（curl）

以下示例无需运行脚本，可直接在终端中执行。将 `JSESSIONID` 替换为你自己的有效值。

### 获取学期与教师列表

```bash
curl -X GET \
  'http://202.119.81.112:9080/njlgdx/kbcx/kbxx_teacher' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' \
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
  -H 'Accept-Language: zh-CN,zh;q=0.9' \
  -H 'Cookie: JSESSIONID=ABCDEF1234567890ABCDEF1234567890' \
  --compressed \
  -o teacher_page.html
```

获取到 `teacher_page.html` 后，从中提取 `<select id="xnxqh">` 和 `<select id="jg0101id">` 各 `<option>` 的 `value`，供下一步使用。

**用 Python 快速提取教师列表：**

```python
from bs4 import BeautifulSoup

with open('teacher_page.html', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')

for opt in soup.find('select', id='jg0101id').find_all('option'):
    if opt['value']:
        print(opt['value'], opt.text.strip())
```

---

### 查询教师课表

将上一步获取到的学期 `value` 和教师 `value` 填入 Body：

```bash
curl -X POST \
  'http://202.119.81.112:9080/njlgdx/kbcx/kbxx_teacher_ifr' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' \
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
  -H 'Accept-Language: zh-CN,zh;q=0.9' \
  -H 'Referer: http://202.119.81.112:9080/njlgdx/kbcx/kbxx_teacher' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'Cookie: JSESSIONID=ABCDEF1234567890ABCDEF1234567890' \
  --data-urlencode 'xnxqh=2025-2026-1' \
  --data-urlencode 'jg0101id=A0F3B2' \
  --data-urlencode 'skyx=' \
  --data-urlencode 'jszc=' \
  --compressed \
  -o schedule.html
```

**Body 参数说明：**

| 参数 | 来源 | 说明 |
|---|---|---|
| `xnxqh=2025-2026-1` | 接口一 `xnxqh` 下拉的 `value` | 学年学期 |
| `jg0101id=A0F3B2` | 接口一 `jg0101id` 下拉的 `value` | 教师唯一 ID |
| `skyx=` | 留空 | 不按院系筛选 |
| `jszc=` | 留空 | 不按职称筛选 |

> **注意：** `Referer` 头为 POST 请求的必须字段，值固定为接口一的 GET 地址。缺失时部分服务器配置会拒绝请求（返回 403）。

**快速验证响应是否包含课表数据：**

```bash
# 返回数字 > 1 说明有课表行；输出 0 或含"请先登录"则 Session 已失效
grep -c '<tr>' schedule.html
```

---

## 脚本使用方法

### 第一步：`extract_terms.py` —— 提取参数数据

**首次使用前必须运行一次**，将教务系统中的学期、院系、教师信息缓存到本地 JSON 文件。

```bash
python extract_terms.py
```

**交互流程：**

1. 提示输入 `JSESSIONID`（直接回车可跳过，尝试其他登录方式）
2. 登录成功后自动请求主页面并解析三个下拉列表
3. 将结果写入同目录下的三个 JSON 文件

**输出示例：**

```
[结果] 提取到 12 个学年学期。
[结果] 提取到 25 个开课院系。
[结果] 提取到 1842 个教师。
✔️ 学年学期已保存到: /path/to/extracted_terms.json
✔️ 开课院系已保存到: /path/to/extracted_departments.json
✔️ 教师ID已保存到:   /path/to/extracted_teachers.json
```

> 每学期开始时建议重新运行本脚本，以获取最新的教师和学期列表。

---

### 第二步：`query_teacher_schedule.py` —— 查询课表

```bash
python query_teacher_schedule.py
```

**交互流程：**

```
主菜单
  │
  ├─ 1. 输入学期关键字（如 "2025" 或 "2025-2026-2"）
  │       └─ 若多个匹配 → 显示列表，输入序号确认
  │
  ├─ 2. 输入教师姓名（支持模糊搜索）
  │       └─ 若多个匹配 → 分页展示（每页20条），输入序号确认
  │
  └─ 3. 自动发起 POST 请求，解析并展示课表
```

**课表展示示例：**

```
【宗士增】 的 2025-2026-1 课表:
============================================================
第 1 门课: 【工程制图】 (编号: 05021702-3)
 ├─  上课班级: 40 (人数: 40人)
 ├─  上课时间: 星期四 第2-3节  [ 1-13周 全周 ]
 ├─  上课地点: 江阴致新B208
 └─  暂无分组
------------------------------------------------------------
```

**分页导航（教师列表过多时）：**

| 输入 | 操作 |
|---|---|
| 数字序号 | 选择对应教师 |
| `n` | 下一页 |
| `p` | 上一页 |
| 回车 | 取消，重新搜索 |

**全局控制命令：**

| 输入 | 位置 | 操作 |
|---|---|---|
| `q` | 任意输入处 | 退出程序 |
| `b` | 教师搜索处 | 返回学期选择 |
| 回车 | 课表展示后 | 返回主菜单继续查询 |

---

## 登录认证机制

两个脚本均采用相同的四级登录回退策略（按优先级依次尝试）：

```
1. 手动输入 JSESSIONID
        ↓ 失败或跳过
2. 读取 .env 中缓存的 JSESSIONID
        ↓ 失败或不存在
3. 读取 .env 中保存的账号密码，自动调用 login()
        ↓ 失败或不存在
4. 提示手动输入学号和密码
```

成功登录的 `JSESSIONID` 会通过 `save_env()` 自动写入 `.env`，下次启动可免登录。`extract_terms.py` 额外提供了保存账号密码的选项（写入 `SAVED_USER` / `SAVED_PASS`）。

---

## 缓存文件说明

三个 JSON 缓存文件结构相同，每项为含 `value`（系统 ID）和 `text`（显示名称）的对象：

```json
[
    {
        "value": "2025-2026-1",
        "text": "2025-2026学年第1学期"
    }
]
```

`search_in_json()` 函数对 `text` 和 `value` 字段同时进行**子字符串模糊匹配**，输入部分关键字即可查找。

---

## 核心模块依赖

| 模块 | 作用 |
|---|---|
| `njust_tool.auth.login` | 账号密码登录，返回已认证的 Session |
| `njust_tool.utils.load_env` | 从 `.env` 文件读取保存的环境变量 |
| `njust_tool.utils.save_env` | 向 `.env` 文件写入键值对 |
| `njust_tool.utils.get_password_with_mask` | 带掩码的密码输入 |
| `njust_tool.constants.HEADERS` | 统一的 HTTP 请求头（含 User-Agent 等） |

---

## 常见问题

**Q: 运行 `query_teacher_schedule.py` 时提示"尚未提取参数文件"**

需先运行 `extract_terms.py` 生成缓存文件。

**Q: 查询成功（HTTP 200）但提示未找到表格**

该教师在所选学期内没有排课记录，属于正常情况。

**Q: curl 请求返回"请先登录"或被重定向**

JSESSIONID 已失效，需在浏览器重新登录后获取新的 Cookie 值。

**Q: POST 请求返回 403**

检查是否携带了 `Referer` 头，其值必须为接口一的 GET 地址。

**Q: 提示找不到 `njust_tool` 包**

检查脚本相对于项目根目录的层级是否为**两级子目录**（即 `project_root/a/b/script.py`）。若层级不同，需修改脚本中 `project_root` 的计算逻辑。