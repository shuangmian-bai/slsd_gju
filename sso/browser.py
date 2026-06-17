"""无头浏览器 CAS 跳转，获取子域名 Cookie

不同子域名的认证链路不同：
- 教务系统 (zfjw.hnslsdxy.com): CAS ticket → /sso/jasiglogin → /jwglxt/ticketlogin → 最终页面
- 评教系统 (assess.hnslsdxy.com): 门户入口点击 → CAS 跳转
- 通用: 门户入口点击 → CAS 跳转
"""

from playwright.sync_api import sync_playwright


def get_domain_cookie(domain: str, cookies: dict, proxy: str = None) -> dict:
    """
    通过无头浏览器获取指定域名的 cookies

    根据域名选择不同的认证链路。

    Args:
        domain: 目标域名
        cookies: SSO 登录后的 cookies 字典（需包含 SESSION 等）
        proxy: HTTP 代理

    Returns:
        {"success": bool, "cookies": dict, "message": str}
    """
    # 按域名分发
    handlers = {
        "zfjw.hnslsdxy.com": _get_zfjw_cookie,
        "assess.hnslsdxy.com": _get_assess_cookie,
    }
    handler = handlers.get(domain)
    if handler:
        return handler(domain, cookies, proxy)

    # 默认：通过门户入口点击
    return _get_portal_cookie(domain, cookies, proxy)


def _get_zfjw_cookie(domain: str, cookies: dict, proxy: str = None) -> dict:
    """
    教务系统 Cookie 获取

    完整链路（基于 curl 分析）：
    1. 访问 CAS 入口 http://zfjw.hnslsdxy.com/sso/jasiglogin?ticket=...
    2. 302 → HTTPS，服务端设置 JSESSIONID
    3. 内部跳转 /jwglxt/ticketlogin?uid=...&timestamp=...&verify=...
    4. 最终到达 /jwglxt/xtgl/login_slogin.html
    5. cookies: JSESSIONID + __jsluid_s + insert_cookie
    """
    try:
        with _launch_browser(proxy) as (browser, context):
            _inject_sso_cookies(context, cookies)

            # 直接访问 CAS 入口，携带 SSO session
            page = context.new_page()

            # 从 SSO 获取 ticket
            print(f"[Browser] 访问教务系统 CAS 入口...")
            cas_url = "https://zfjw.hnslsdxy.com/sso/jasiglogin"
            page.goto(cas_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            print(f"[Browser] 当前 URL: {page.url}")

            # 如果被重定向到 SSO 登录页，说明 SSO cookies 未生效
            if "sso.hnslsdxy.com/login" in page.url:
                print(f"[Browser] SSO cookies 未生效，尝试从 URL 获取 ticket...")
                # 从当前 URL 提取 service 参数，带 SSO cookies 重新请求
                # 回退到门户方式
                return _get_portal_cookie(domain, cookies, proxy)

            # 等待完整重定向链完成
            print(f"[Browser] 等待认证链完成...")
            page.wait_for_timeout(5000)

            # 如果打开了新页面，切换过去
            if len(context.pages) > 1:
                page = context.pages[-1]
                page.wait_for_timeout(3000)

            final_url = page.url
            print(f"[Browser] 最终 URL: {final_url}")

            # 提取教务系统 cookies
            domain_cookies = _extract_cookies(context, domain)

            # 检查关键 cookies
            has_jsessionid = "JSESSIONID" in domain_cookies
            has_insert = "insert_cookie" in domain_cookies
            print(f"[Browser] JSESSIONID: {'✓' if has_jsessionid else '✗'}")
            print(f"[Browser] insert_cookie: {'✓' if has_insert else '✗'}")

            if not has_jsessionid:
                return {"success": False, "cookies": {}, "message": "未获取到 JSESSIONID"}

            return {
                "success": True,
                "cookies": domain_cookies,
                "message": f"成功获取 {domain} 的 cookies",
            }

    except Exception as e:
        return {"success": False, "cookies": {}, "message": f"获取 {domain} cookies 失败: {str(e)}"}


def _get_assess_cookie(domain: str, cookies: dict, proxy: str = None) -> dict:
    """
    评教系统 Cookie 获取

    直接访问 CAS 入口 https://assess.hnslsdxy.com/auth/login/
    浏览器自动完成 CAS 跳转。
    """
    try:
        with _launch_browser(proxy) as (browser, context):
            _inject_sso_cookies(context, cookies)

            page = context.new_page()
            cas_url = "https://assess.hnslsdxy.com/auth/login/"
            print(f"[Browser] 访问评教系统 CAS 入口: {cas_url}")
            page.goto(cas_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(5000)

            print(f"[Browser] 当前 URL: {page.url}")

            domain_cookies = _extract_cookies(context, domain)
            print(f"[Browser] 获取到 cookies: {list(domain_cookies.keys())}")

            if not domain_cookies:
                return {"success": False, "cookies": {}, "message": f"未获取到 {domain} 的 cookies"}

            return {
                "success": True,
                "cookies": domain_cookies,
                "message": f"成功获取 {domain} 的 cookies",
            }

    except Exception as e:
        return {"success": False, "cookies": {}, "message": f"获取 {domain} cookies 失败: {str(e)}"}


def _get_portal_cookie(domain: str, cookies: dict, proxy: str = None) -> dict:
    """
    通用 Cookie 获取：通过门户入口点击

    流程：
    1. 携带 SSO cookies 访问门户首页
    2. 点击子系统入口
    3. 等待 CAS 跳转完成
    4. 获取目标域名的 cookies
    """
    try:
        with _launch_browser(proxy) as (browser, context):
            _inject_sso_cookies(context, cookies)

            page = context.new_page()
            print(f"[Browser] 访问门户首页...")
            page.goto("https://portal.hnslsdxy.com/home", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            print(f"[Browser] 当前 URL: {page.url}")

            # 点击目标子系统入口
            print(f"[Browser] 点击子系统入口...")
            try:
                target = page.locator(
                    '//*[@id="root"]/div/div/div[2]/div[2]/div/div[1]/div[2]/div[2]/div/div[1]/div[5]/div/span[1]'
                )
                target.click(timeout=10000)
                print(f"[Browser] 已点击目标元素")
            except Exception as e:
                print(f"[Browser] 点击失败: {e}，尝试直接访问...")
                page.goto(f"https://{domain}/sso/jasiglogin", wait_until="networkidle", timeout=30000)

            print(f"[Browser] 等待跳转完成...")
            page.wait_for_timeout(5000)

            if len(context.pages) > 1:
                page = context.pages[-1]
                page.wait_for_timeout(3000)

            print(f"[Browser] 当前 URL: {page.url}")

            domain_cookies = _extract_cookies(context, domain)

            # 补充通用 cookies
            for name in ("__jsluid_s", "rg_objectid"):
                if name in cookies and name not in domain_cookies:
                    domain_cookies[name] = cookies[name]

            print(f"[Browser] 获取到 cookies: {list(domain_cookies.keys())}")

            if not domain_cookies:
                return {"success": False, "cookies": {}, "message": f"未获取到 {domain} 的 cookies"}

            return {
                "success": True,
                "cookies": domain_cookies,
                "message": f"成功获取 {domain} 的 cookies",
            }

    except Exception as e:
        return {"success": False, "cookies": {}, "message": f"获取 {domain} cookies 失败: {str(e)}"}


# ---- 工具函数 ----

def _launch_browser(proxy: str = None):
    """启动浏览器的上下文管理器"""
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        with sync_playwright() as p:
            browser_args = {}
            if proxy:
                browser_args["proxy"] = {"server": proxy}
            browser = p.chromium.launch(headless=True, **browser_args)
            context = browser.new_context()
            try:
                yield browser, context
            finally:
                browser.close()

    return _ctx()


def _inject_sso_cookies(context, cookies: dict):
    """将 SSO cookies 注入浏览器上下文"""
    cookies_to_set = []
    for name, value in cookies.items():
        for cookie_domain in ("sso.hnslsdxy.com", ".hnslsdxy.com"):
            cookies_to_set.append({
                "name": name,
                "value": value,
                "domain": cookie_domain,
                "path": "/",
            })
    context.add_cookies(cookies_to_set)


def _extract_cookies(context, domain: str) -> dict:
    """从浏览器上下文提取指定域名的 cookies"""
    all_cookies = context.cookies()
    domain_cookies = {}
    for cookie in all_cookies:
        if cookie["domain"] == domain or cookie["domain"].endswith(f".{domain}"):
            domain_cookies[cookie["name"]] = cookie["value"]
    return domain_cookies
