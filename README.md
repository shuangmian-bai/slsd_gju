# 湖南水利水电职业技术学院 - 自动评教脚本

## 项目结构

```
├── login.py       # SSO 登录模块（加密、验证码 OCR、Cookie 获取）
├── pingjiao.py    # 自动评教主脚本
└── README.md      # 说明文档
```

## 环境要求

- Python 3.8+
- 依赖包：

```bash
pip install requests beautifulsoup4 pycryptodome ddddocr
```

## 使用方法

### 评教（一键满分）

```bash
# 使用 Clash 代理（默认 7890 端口）
python3 pingjiao.py <学工号> <密码> --proxy http://127.0.0.1:7890

# 不使用代理
python3 pingjiao.py <学工号> <密码>

# 示例
python3 pingjiao.py 202450350051 'MyPassword123@H' -p http://127.0.0.1:7890
```

### 单独登录（仅获取 Cookie）

```bash
python3 login.py <学工号> <密码> --proxy http://127.0.0.1:7890
```

返回 JSON 格式：

```json
{
  "success": true,
  "cookies": {
    "SESSION": "...",
    "SOURCEID_TGC": "...",
    "__jsluid_s": "...",
    "rg_objectid": "..."
  },
  "message": "OK",
  "redirect": "https://portal.hnslsdxy.com?ticket=ST-xxx"
}
```

### 在其他脚本中调用

```python
from login import login
from pingjiao import create_session, get_assessments, save_assessment, make_full_score

# 1. SSO 登录
result = login("202450350051", "MyPassword123@H", proxy="http://127.0.0.1:7890")
if not result["success"]:
    print(f"登录失败: {result['message']}")
    exit(1)

# 2. 获取评教会话
session = create_session(result["cookies"], proxy="http://127.0.0.1:7890")

# 3. 查询待评教
data = get_assessments(session)
items = data.get("result", [])
full_score = make_full_score(data.get("standard", {}))

# 4. 提交评教
for item in items:
    save_assessment(session, item["course"], item["teacher"], item["id"], full_score)
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
       │  带 SSO Cookie 访问评教系统
       │  CAS 自动跳转获取 sessionid
       ▼
┌─────────────┐   POST API          ┌─────────────┐
│   脚本       │ ──────────────────→ │  评教服务器   │
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
- 脚本自动调用 `ddddocr` OCR 识别，最多重试 3 次

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `登录失败: 用户名或密码错误` | 密码错误或加密方式不对 | 确认密码正确 |
| `验证码有误` | OCR 识别错误 | 脚本会自动重试，或重新运行 |
| `reCAPTCHA 验证失败` | 同一 IP 多次失败触发风控 | 换代理 IP 或等一段时间再试 |
| `no_login` | 评教系统 Cookie 未获取 | 检查 CAS 跳转是否正常 |
| 连接超时 | 网络问题或代理不通 | 检查 `--proxy` 参数 |

## 注意事项

- 密码包含特殊字符时请用单引号包裹：`'P@ssw0rd!#'`
- 代理地址格式：`http://127.0.0.1:7890`（Clash 默认端口）
- 评教结果为满分提交，无法自定义分数
