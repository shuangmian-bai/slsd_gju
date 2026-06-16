# 湖南水利水电职业技术学院 - 自动评教选课脚本

## 项目结构

```
├── sso/                # SSO 登录模块（AES 加密、验证码 OCR、Cookie 获取）
│   └── __init__.py
├── pingjiao/           # 评教模块
│   └── __init__.py
├── xuanke/             # 选课模块（requests 版，旧版）
│   └── __init__.py
├── xuanke_browser.py   # 选课模块（浏览器版，推荐）
├── xuanke_demo.py      # 交互式选课演示
├── sso_demo.py         # SSO 登录演示
├── pingjiao_demo.py    # 评教演示
├── main.py             # 旧版本（已弃用）
└── README.md
```

## 环境要求

- Python 3.8+
- 依赖包：

```bash
pip install requests beautifulsoup4 pycryptodome ddddocr playwright
playwright install chromium
```

## 使用方法

### 交互式选课（推荐）

```bash
# 直接运行
python3 xuanke_demo.py

# 使用代理
python3 xuanke_demo.py --proxy http://127.0.0.1:7890
```

功能菜单：
1. 查看可选课程
2. 查看已选课程
3. 抢课（单次）
4. 抢课（多线程持续抢，支持自定义线程数、间隔、最大尝试次数）
5. 退课
6. 退出

### SSO 登录

```python
from sso import SSO

sso = SSO()
sso.set_account("学号", "密码")

# 获取 SSO Cookie
result = sso.get_cookie()

# 获取教务系统 Cookie（自动完成 CAS 跳转）
result = sso.get_cookie(domain="zfjw.hnslsdxy.com")
```

### 评教

```python
from sso import SSO
from pingjiao import PingJiao

# SSO 登录
sso = SSO()
sso.set_account("学号", "密码")
result = sso.get_cookie()

# 评教
pj = PingJiao()
pj.set_sso_cookie(result["cookies"])
pj.show_assessments()  # 查看待评教课程
pj.score_all()         # 一键满分评教
```

### 选课（浏览器版）

```python
from sso import SSO
from xuanke_browser import XuanKeBrowser
from playwright.sync_api import sync_playwright

# SSO 登录
sso = SSO()
sso.set_account("学号", "密码")
sso_result = sso.get_cookie()

# 启动浏览器并访问教务系统
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    # 设置 SSO cookies
    cookies = [{'name': k, 'value': v, 'domain': '.hnslsdxy.com', 'path': '/'}
               for k, v in sso_result['cookies'].items()]
    context.add_cookies(cookies)

    # 访问门户并点击教务系统入口
    page = context.new_page()
    page.goto("https://portal.hnslsdxy.com/home")
    # ... 点击入口 ...

    # 选课操作
    xk = XuanKeBrowser(page)
    xk.show_courses()
    xk.grab("电影赏析")
```

## 登录流程说明

```
┌─────────────┐     GET /login      ┌─────────────┐
│   脚本       │ ──────────────────→ │  SSO 服务器  │
│             │ ←────────────────── │             │
│  拿到 croypto │    返回 AES 密钥    │             │
└──────┬──────┘                     └─────────────┘
       │
       │  AES-128-ECB 加密密码
       │
       ▼
┌─────────────┐   POST /login       ┌─────────────┐
│   脚本       │ ──────────────────→ │  SSO 服务器  │
│  (form 表单)  │ ←────────────────── │             │
│             │   302 重定向 + Cookie │             │
└──────┬──────┘                     └─────────────┘
       │
       │  无头浏览器携带 SSO Cookie
       │  访问门户 → 点击教务系统入口
       │  自动完成 CAS 跳转
       ▼
┌─────────────┐   选课 API           ┌─────────────┐
│   浏览器     │ ──────────────────→ │  教务系统    │
│             │ ←────────────────── │             │
│             │     选课结果         │             │
└─────────────┘                     └─────────────┘
```

### 密码加密方式

- 算法：**AES-128-ECB + PKCS7**
- 密钥：登录页 `login-croypto` 字段经 Base64 解码（16 字节）
- 明文：密码原文（不加时间戳）

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

key = base64.b64decode(croypto)        # 16 字节
ct  = AES.new(key, AES.MODE_ECB).encrypt(pad(password.encode(), 16))
encrypted = base64.b64encode(ct).decode()
```

### CAS 跳转流程

教务系统 CAS 入口：`https://zfjw.hnslsdxy.com/sso/jasiglogin`

1. 访问门户首页 `https://portal.hnslsdxy.com/home`
2. 点击教务系统入口（XPath: `//*[@id="root"]/div/div/div[2]/div[2]/div/div[1]/div[2]/div[2]/div/div[1]/div[5]/div/span[1]`）
3. 浏览器自动完成 CAS 跳转，获取 `JSESSIONID`

### 验证码处理

- 当多次登录失败后，服务器会要求输入图形验证码
- 脚本自动调用 `ddddocr` OCR 识别，最多重试 3 次

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `登录失败: 用户名或密码错误` | 密码错误或加密方式不对 | 确认密码正确 |
| `验证码有误` | OCR 识别错误 | 脚本会自动重试，或重新运行 |
| `reCAPTCHA 验证失败` | 同一 IP 多次失败触发风控 | 换代理 IP 或等一段时间再试 |
| `no_login` | 评教系统 Cookie 未获取 | 检查 CAS 跳转是否正常 |
| 连接超时 | 网络问题或代理不通 | 检查 `--proxy` 参数 |
| `Cookie 已过期或未登录` | JSESSIONID 无效 | 使用浏览器版（xuanke_demo.py） |

## 注意事项

- 密码包含特殊字符时请用单引号包裹：`'P@ssw0rd!#'`
- 代理地址格式：`http://127.0.0.1:7890`（Clash 默认端口）
- 评教结果为满分提交，无法自定义分数
- 选课推荐使用浏览器版（xuanke_demo.py），可以正确处理 CAS 跳转
