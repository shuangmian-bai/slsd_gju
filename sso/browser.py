"""通过 requests 跟踪 CAS 重定向链，获取子域名 Cookie

不同子域名的认证链路不同：
- 教务系统 (zfjw.hnslsdxy.com): CAS → /sso/jasiglogin → /jwglxt/ticketlogin
- 评教系统 (assess.hnslsdxy.com): CAS → /auth/login/
- 学习通 (study.hnslsdxy.com): 走 portal.py 超星 SSO 桥接，不经过此模块
- 通用: CAS 入口 → 重定向
"""

import requests
from urllib.parse import urlparse

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)


def get_domain_cookie(domain: str, cookies: dict, proxy: str = None) -> dict:
    """
    通过 requests 跟踪 CAS 重定向链获取指定域名的 cookies

    Args:
        domain: 目标域名
        cookies: SSO 登录后的 cookies 字典
        proxy: HTTP 代理

    Returns:
        {"success": bool, "cookies": dict, "cookie_jar": list, "message": str}
    """
    session = requests.Session()
    session.headers.update({"User-Agent": _USER_AGENT})
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    # 注入 SSO cookies
    for name, value in cookies.items():
        session.cookies.set(name, value, domain="sso.hnslsdxy.com", path="/")
        session.cookies.set(name, value, domain=".hnslsdxy.com", path="/")

    # 按域名选择 CAS 入口
    cas_urls = {
        "zfjw.hnslsdxy.com": "https://zfjw.hnslsdxy.com/sso/jasiglogin",
        "assess.hnslsdxy.com": "https://assess.hnslsdxy.com/auth/login/",
        "portal.hnslsdxy.com": "https://portal.hnslsdxy.com/cas/validate",
    }
    cas_url = cas_urls.get(domain, f"https://{domain}/sso/jasiglogin")

    print(f"[CAS] 访问 {cas_url}")
    url = cas_url

    # 跟踪重定向链
    max_redirects = 10
    for step in range(1, max_redirects + 1):
        resp = session.get(url, allow_redirects=False, timeout=15)
        location = resp.headers.get("Location")
        sc = resp.headers.get("Set-Cookie", "")
        if sc:
            cookie_name = sc.split("=")[0]
            print(f"[CAS] Step {step}: {resp.status_code} Set-Cookie: {cookie_name}")

        if not location or resp.status_code not in (301, 302, 303, 307, 308):
            break

        # 相对路径补全
        if location.startswith("/"):
            parsed = urlparse(url)
            location = f"{parsed.scheme}://{parsed.netloc}{location}"

        url = location

    print(f"[CAS] 最终 URL: {url}")

    # 提取目标域名 cookies（保留 domain/path）
    domain_cookies = {}
    cookie_jar = []
    for cookie in session.cookies:
        if cookie.domain == domain or cookie.domain.endswith(f".{domain}"):
            domain_cookies[cookie.name] = cookie.value
            cookie_jar.append(cookie)

    print(f"[CAS] cookies: {list(domain_cookies.keys())}")

    if not domain_cookies:
        return {"success": False, "cookies": {}, "message": f"未获取到 {domain} 的 cookies"}

    return {
        "success": True,
        "cookies": domain_cookies,
        "cookie_jar": cookie_jar,
        "message": f"成功获取 {domain} 的 cookies",
    }
