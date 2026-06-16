# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指导。

## 语言要求

**所有输出必须使用中文**，包括：日志、询问、代码输出、代码注释、提交信息等。

## 项目功能

自动化湖南水利水电职业技术学院的评教和选课系统。通过 SSO 登录获取会话 Cookie，然后进行评教提交和选课操作。

## 命令

```bash
# 安装依赖
pip install requests beautifulsoup4 pycryptodome ddddocr
```

项目没有 CLI 入口脚本，通过 Python 模块方式使用（参见 `sso_demo.py` 和 `pingjiao_demo.py`）。

## 模块架构

**sso/** — SSO 登录模块包（`sso.SSO` 类）。
```python
from sso import SSO
sso = SSO(proxy="http://127.0.0.1:7890")  # proxy 可选
sso.set_account("学号", "密码")
result = sso.get_cookie()  # {"success", "cookies", "message"}
```
- `cookies` 包含：`SESSION`、`SOURCEID_TGC`、`__jsluid_s`、`rg_objectid`

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

**xuanke/** — 选课模块包（`xuanke.XuanKe` 类）。
```python
from xuanke import XuanKe
xk = XuanKe(proxy="http://127.0.0.1:7890")
xk.set_cookie("JSESSIONID=xxx; __jsluid_s=xxx; insert_cookie=xxx")
xk.show_courses()          # 查询课程并标记已选状态
xk.grab("电影赏析")         # 抢课（模糊匹配）
xk.drop("电影赏析")         # 退课
```

**main.py** — 旧版本（从 curl dump 文件读取 cookies），已被模块化架构取代。

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
- CSRF 头（`Csrf-Key` / `Csrf-Value`）是从前端 JS 提取的静态值
- 评教服务需要 CAS ticket 验证 — 仅 SSO cookies 不够，必须通过 `set_sso_cookie()` 完成跳转
- 评教 API 需要 `csrftoken` cookie 的 `X-CSRFToken` 头
- 选课系统域名：`zfjw.hnslsdxy.com`，使用 `JSESSIONID` + `__jsluid_s` + `insert_cookie` 鉴权
- 验证码：多次登录失败后触发，使用 `ddddocr` OCR 自动识别，最多重试 3 次

## 编码约定

- 每个功能模块封装为一个类（`SSO`、`PingJiao`、`XuanKe`），通过构造函数接受 `proxy` 参数
- Cookie 设置方式：`set_cookie(字符串)` / `set_cookies(字典)` / `set_sso_cookie(SSO cookies 字典)`
- 课程匹配使用子字符串包含（`name in kcmc`），支持模糊匹配
- 中文对齐使用 `cn_ljust()` 辅助函数（中文字符占 2 个宽度）
- `get_courses()` 等底层方法返回原始 API 响应，`show_courses()` / `grab()` / `drop()` 等高层方法返回格式化的 `{"success", "message"}` 字典

## 选课系统 API 端点

| 操作 | API | 说明 |
|------|-----|------|
| 查询可选课程 | `POST /jwglxt/xsxk/zzxkyzb_cxZzxkYzbPartDisplay.html` | 返回 `tmpList` |
| 查询已选课程 | `POST /jwglxt/xsxk/zzxkyzb_cxZzxkYzbChoosedDisplay.html` | 返回已选课程列表 |
| 查询教学班详情 | `POST /jwglxt/xsxk/zzxkyzbjk_cxJxbWithKchZzxkYzb.html` | 获取 `do_jxb_id` |
| 选课（第1步） | `POST /jwglxt/xsxk/zzxkyzb_cxXkTitleMsg.html` | 预检查 |
| 选课（第2步） | `POST /jwglxt/xsxk/zzxkyzbjk_xkBcZyZzxkYzb.html` | 实际选课 |
| 退课（第1步） | `POST /jwglxt/xsxk/zzxkyzb_tuikBcZzxkYzb.html` | 退课请求 |
| 退课（第2步） | `POST /jwglxt/xsxk/zzxkyzb_xkBcZypxZzxkYzb.html` | 确认退课 |

## 选课系统关键参数

- `jxb_id` — 教学班 ID（简单格式，如 `536DA562F3294164E065000000000001`）
- `do_jxb_id` — 教学班加密 ID（长格式，用于实际选课/退课请求）
- `kch_id` — 课程 ID
- `xkkz_id` — 选课课程组 ID（默认 `540755BBD0F5022FE065000000000001`）
- `kcmc` — 课程名称参数，格式为 `(课程号)课程名称+-+学分+学分`
- `flag` — 选课返回状态：`1/3/6` = 成功，`0` = 失败
- 退课返回值：`"1"` = 成功，`"3"` = 失败

## 外部服务

| 域名 | 用途 |
|------|------|
| `sso.hnslsdxy.com` | SSO 认证（CAS 服务器） |
| `portal.hnslsdxy.com` | 门户（ticket 验证重定向） |
| `assess.hnslsdxy.com` | 评教 API |
| `zfjw.hnslsdxy.com` | 正方教务系统（选课） |
