# 湖南水利水电职业技术学院 - 自动评教脚本

## 项目结构

```
├── sso/                # SSO 登录模块（AES 加密、验证码 OCR、Cookie 获取）
│   └── __init__.py
├── pingjiao/           # 评教模块
│   └── __init__.py
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

### SSO 登录

```python
from sso import SSO

sso = SSO()
sso.set_account("学号", "密码")

# 获取 SSO Cookie
result = sso.get_cookie()

# 获取评教系统 Cookie（自动完成 CAS 跳转）
result = sso.get_cookie(domain="assess.hnslsdxy.com")
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
       │  访问门户 → 点击评教系统入口
       │  自动完成 CAS 跳转
       ▼
┌─────────────┐   评教 API           ┌─────────────┐
│   浏览器     │ ──────────────────→ │  评教系统    │
│             │ ←────────────────── │             │
│             │     评教结果         │             │
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

### 验证码处理

- 当多次登录失败后，服务器会要求输入图形验证码
- 脚本自动调用 `ddddocr` OCR 识别（双模式 default+old 投票），最多重试 3 次
- 验证码图片自动保存到 `captcha/` 目录，文件名格式 `{时间戳}_{OCR结果}.png`，方便人工确认

### 关键注意事项

- `captcha_code` 字段需要**重复发送两次**（服务端特殊要求）
- 登录 POST 请求**不要**发送 `Csrf-Key`/`Csrf-Value` 头

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `登录失败: 用户名或密码错误` | 密码错误或加密方式不对 | 确认密码正确 |
| `验证码有误` | OCR 识别错误 | 脚本会自动重试，或查看 `captcha/` 目录确认 |
| `no_login` | 评教系统 Cookie 未获取 | 检查 CAS 跳转是否正常 |
| 连接超时 | 网络问题或代理不通 | 检查 `--proxy` 参数 |

## 注意事项

- 密码包含特殊字符时请用单引号包裹：`'P@ssw0rd!#'`
- 代理地址格式：`http://127.0.0.1:7890`（Clash 默认端口）
- 评教结果为满分提交，无法自定义分数
