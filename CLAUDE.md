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

# 运行评教（使用 Clash 代理）
python3 pingjiao.py <学号> <密码> --proxy http://127.0.0.1:7890

# 仅 SSO 登录（返回 JSON 格式的 cookies）
python3 login.py <学号> <密码> --proxy http://127.0.0.1:7890
```

## 模块架构

**sso/** — SSO 登录模块包。通过 `set_account()` 设置账号密码，`get_cookie()` 获取 Cookie：
- `set_account(username, password)` — 设置账号密码
- `get_cookie(max_retries=3)` — 获取 SSO Cookie
- 返回 `{"success", "cookies", "message"}` 字典
- `cookies` 包含：`SESSION`、`SOURCEID_TGC`、`__jsluid_s`、`rg_objectid`

**login.py** — SSO 认证模块（旧版 CLI）。已被 `sso/` 模块取代。

**pingjiao.py** — 评教执行器。从 `sso/` 导入 `SSO`，然后：
1. 调用 `login()` 获取 SSO cookies
2. `create_session()` 执行 CAS 重定向链：`assess.hnslsdxy.com` → `sso.hnslsdxy.com`（带 ticket）→ 返回 assess，获得 `sessionid` + `csrftoken` cookies
3. `get_assessments()` / `save_assessment()` 调用 `assess.hnslsdxy.com` 的评教 API

**xuanke/** — 选课模块包。通过 `set_cookie()` 或 `set_cookies()` 传入 Cookie，支持：
- `show_courses()` — 查询课程并标记已选状态
- `grab(name)` — 抢课（只需课程名称，支持模糊匹配）
- `drop(name)` — 退课（只需课程名称）
- `get_courses()` — 查询可选课程（底层方法）
- `get_selected_courses()` — 获取已选课程列表
- `select_course()` — 抢课底层方法（需2次请求）
- `drop_course()` — 退课底层方法（需2次请求）

**main.py** — 旧版本（从 curl dump 文件读取 cookies）。已被 `pingjiao.py` 取代。

## 关键技术细节

- SSO 登录表单以 `application/x-www-form-urlencoded` 格式 POST 到 `/login`（不是 JSON）
- `login-croypto` 值是 base64 字符串，解码后为 16 字节 — 直接用作 AES 密钥（不是 UTF-8 字节）
- CSRF 头（`Csrf-Key` / `Csrf-Value`）是从前端 JS 提取的静态值
- 评教服务需要 CAS ticket 验证 — 仅 SSO cookies 不够
- 评教 API 需要 `csrftoken` cookie 的 `X-CSRFToken` 头
- 选课系统域名：`zfjw.hnslsdxy.com`，使用 `JSESSIONID` + `__jsluid_s` + `insert_cookie` 鉴权

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
