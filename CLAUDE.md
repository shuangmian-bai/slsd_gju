# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言要求

**所有输出必须使用中文**，包括：日志、询问、代码输出、代码注释、提交信息等。

## 项目功能

自动化湖南水利水电职业技术学院的学生系统：SSO 登录、评教、选课/抢课/退课。

## 命令

```bash
# 安装依赖
pip install -r requirements.txt

# 主入口（交互式菜单，选择功能模块）
python3 main.py

# 也可以单独运行各模块
python3 sso_login_demo.py    # SSO 登录
python3 pingjiao_main.py     # 评教
python3 xuanke_main.py       # 选课
```

## 模块架构

**sso/** — SSO 登录模块包（`sso.SSO` 类）。

```
sso/
├── __init__.py   # SSO 主类（登录、get_cookie 调度）
├── crypto.py     # AES-128-ECB 加密
├── captcha.py    # 验证码获取 + OCR 识别
├── browser.py    # CAS 重定向链跟踪（requests 协议，按域名分发）
└── portal.py     # 超星 SSO 桥接（学习通认证链路）
```

```python
from sso import SSO
sso = SSO(proxy="http://127.0.0.1:7890")  # proxy 可选
sso.set_account("学号", "密码")

# 获取 SSO Cookie（统一门户）
result = sso.get_cookie()  # {"success", "cookies", "message"}
# cookies: SESSION, SOURCEID_TGC, __jsluid_s, rg_objectid

# 获取教务系统 Cookie（完整认证链：CAS → ticketlogin → JSESSIONID）
result = sso.get_cookie(domain="zfjw.hnslsdxy.com")
# cookies: JSESSIONID, insert_cookie, __jsluid_h

# 获取评教系统 Cookie（CAS 跳转）
result = sso.get_cookie(domain="assess.hnslsdxy.com")
# cookies: sessionid, csrftoken, __jsluid_h, messages

# 获取学习通 Cookie（超星 SSO 桥接）
result = sso.get_cookie(domain="study.hnslsdxy.com")
# cookies: JSESSIONID, UID, uname, vc3, p_auth_token, fanyamoocs 等
```

- `get_cookie(domain=None)` — 返回 SSO 原始 cookies
- `get_cookie(domain=...)` — 通过 requests 跟踪 CAS 重定向链，返回域名专属 cookies
- 不同域名有不同的认证链路，由 `browser.py` 中的 handler 分发

**pingjiao/** — 评教模块包（`pingjiao.PingJiao` 类）。
```python
from pingjiao import PingJiao
pj = PingJiao(proxy="http://127.0.0.1:7890")
pj.set_sso_cookie(sso_cookies)  # 通过 SSO Cookie 建立评教会话（CAS 自动跳转）
pj.show_assessments()            # 查询待评教课程列表
pj.score_all()                   # 给所有课程满分评教
pj.score("课程名称", "老师姓名")  # 给某个老师评教（模糊匹配）
```
- `set_sso_cookie()` 会自动完成 CAS 跳转获取 `sessionid` 和 `csrftoken`
- `score()` 的 `course_name` 和 `teacher_name` 参数支持模糊匹配（子字符串包含）

**xuanke/** — 选课模块包（`xuanke.XuanKe` 类），对接正方教务系统。
```python
from xuanke import XuanKe
xk = XuanKe(proxy="http://127.0.0.1:7890")
xk.set_cookies(jw_cookies)       # 通过教务系统 Cookie 建立选课会话
xk.show_courses()                # 查询并打印全部可选课程
xk.grab("课程名称")              # 抢课（按课程名称模糊匹配）
xk.drop("课程名称")              # 退课
xk.get_selected_courses()        # 查询已选课程
xk.get_selected_jxb_ids()        # 获取已选课程的 jxb_id 集合
```
- 需要教务系统 Cookie（`JSESSIONID + insert_cookie`），通过 `sso.get_cookie(domain="zfjw.hnslsdxy.com")` 获取
- Cookie 设置支持：`set_cookie(字符串)` / `set_cookies(字典)` / `set_cookie_jar(cookie对象列表)`
- `grab()` / `drop()` 内部自动调用 `get_courses()` 获取最新课程列表再匹配
- 课程查询参数 `xkxnm`（学年）、`xkxqm`（学期：3=秋季，12=春季）需按实际情况调整

**xuexitong/** — 学习通模块包（`xuexitong.XueXiTong` 类），对接超星网络教学平台。
```python
from xuexitong import XueXiTong
xt = XueXiTong(proxy="http://127.0.0.1:7890")
xt.set_cookies(sso_study_cookies)   # 通过学习通 Cookie 建立会话
info = xt.get_user_info()           # 获取当前登录用户信息
# {"success": True, "uid": "361609524", "name": "黄孝文迪", "photo": "http://..."}
```
- 需要学习通 Cookie，通过 `sso.get_cookie(domain="study.hnslsdxy.com")` 获取
- `get_user_info()` 内部先访问 portal 建立会话，再调用 logininfojs 解析用户信息

**main.py** — 统一交互式入口（约 278 行）。
- 使用 `@register(name, description)` 装饰器将功能模块注册到 `MODULES` 字典
- 每个注册函数签名为 `run(sso, cookies)`，接收 SSO 实例和登录后的 cookies
- 模块内部按需延迟 import（如 `from pingjiao import PingJiao`）
- 选课模块集成多线程抢课：可配置线程数、请求间隔、最大尝试次数，使用 `threading.Event` 做停止信号

## 返回值约定

所有模块方法统一返回字典，包含 `success`（bool）和 `message`（str）字段：
```python
{"success": True, "message": "...", ...}   # 成功
{"success": False, "message": "错误信息"}   # 失败
```

## 关键技术细节

- SSO 登录表单以 `application/x-www-form-urlencoded` 格式 POST 到 `/login`（不是 JSON）
- `login-croypto` 值是 base64 字符串，解码后为 16 字节 — 直接用作 AES 密钥（不是 UTF-8 字节）
- AES 加密：`AES-128-ECB + PKCS7`，密钥为 base64 解码后的 croypto 字段
- 登录 POST 请求**不要**发送 `Csrf-Key`/`Csrf-Value` 头（匹配真实浏览器行为）
- **`captcha_code` 字段需要重复发送两次**（服务端特殊要求，使用元组列表而非字典构建表单）
- 验证码：多次登录失败后触发，使用 `ddddocr` OCR 自动识别（双模式 default+old 投票），最多重试 3 次
- 验证码图片自动保存到 `captcha/` 目录，文件名格式 `{时间戳}_{OCR结果}.png`，方便人工确认
- 评教服务需要 CAS ticket 验证 — 仅 SSO cookies 不够，必须通过 `set_sso_cookie()` 完成跳转
- 评教 API 需要 `csrftoken` cookie 的 `X-CSRFToken` 头

### 子域名认证链路

**教务系统 (zfjw.hnslsdxy.com)**：
```
1. 访问 CAS 入口 /sso/jasiglogin?ticket=...
2. 302 → HTTPS，服务端设置 JSESSIONID
3. 内部跳转 /jwglxt/ticketlogin?uid=...&timestamp=...&verify=...
4. 最终到达 /jwglxt/xtgl/index_initMenu.html
5. cookies: JSESSIONID + insert_cookie + __jsluid_h
```

**评教系统 (assess.hnslsdxy.com)**：
```
1. 访问 CAS 入口 /auth/login/
2. 自动完成 CAS 跳转
3. cookies: sessionid + csrftoken + __jsluid_h + messages
```

**学习通 (study.hnslsdxy.com)**：
```
1. 访问超星 SSO 桥接 fysso.chaoxing.com/sso/hnslsdxy
2. 302 → sso.hnslsdxy.com/login?service=...（CAS 认证）
3. 302 → hnslsdxy.fysso.chaoxing.com/sso/hnslsdxy?ticket=...
4. 302 → study.hnslsdxy.com/sso/logindsso
5. 302 → passport2.chaoxing.com/v2/loginfanya（超星通行证）
6. 302 → study.hnslsdxy.com/login/auth
7. 302 → mobile.fanya.chaoxing.com/login/ssologin
8. 302 → study.hnslsdxy.com/portal（最终到达）
9. cookies: JSESSIONID + UID + uname + vc3 + p_auth_token + fanyamoocs
```

### 门户入口

- 评教系统：`https://assess.hnslsdxy.com/auth/login/`
- 教务系统：`https://zfjw.hnslsdxy.com/sso/jasiglogin`
- 学习通：`https://fysso.chaoxing.com/sso/hnslsdxy`（超星 SSO 桥接）

## 编码约定

- 每个功能模块封装为一个类（`SSO`、`PingJiao`、`XuanKe`、`XueXiTong`），通过构造函数接受 `proxy` 参数
- Cookie 设置方式：`set_cookie(字符串)` / `set_cookies(字典)` / `set_sso_cookie(SSO cookies 字典)`
- 课程匹配使用子字符串包含（`name in kcmc`），支持模糊匹配
- 中文对齐使用 `cn_ljust()` 辅助函数（中文字符占 2 个宽度）
- `browser.py` 中按域名分发 handler，新增域名只需添加对应的 `_get_xxx_cookie` 函数
- **每个模块的 `__init__.py` 必须包含 `if __name__ == "__main__"` 测试代码**，提供完整的使用案例和测试流程，方便独立运行验证

## 项目约束

- **无测试**：没有测试文件、测试目录或测试框架配置
- **无 lint/format**：没有 flake8、pylint、black、ruff 等配置
- **无 CI/CD**：没有 GitHub Actions 或其他持续集成配置

## 外部服务

| 域名 | 用途 |
|------|------|
| `sso.hnslsdxy.com` | SSO 认证（CAS 服务器） |
| `portal.hnslsdxy.com` | 门户（ticket 验证重定向） |
| `assess.hnslsdxy.com` | 评教系统 |
| `zfjw.hnslsdxy.com` | 正方教务系统 |
| `study.hnslsdxy.com` | 学习通（超星网络教学平台） |
| `fysso.chaoxing.com` | 超星 SSO 桥接 |
| `passport2.chaoxing.com` | 超星通行证 |
