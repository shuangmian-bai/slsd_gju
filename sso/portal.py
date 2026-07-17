"""通过超星 SSO 桥接获取学习通 Cookie

认证链路：
fysso.chaoxing.com/sso/hnslsdxy
  → sso.hnslsdxy.com/login?service=...  (CAS 认证)
  → hnslsdxy.fysso.chaoxing.com/sso/hnslsdxy?ticket=...
  → study.hnslsdxy.com/sso/logindsso
  → passport2.chaoxing.com/v2/loginfanya
  → study.hnslsdxy.com/login/auth
  → mobile.fanya.chaoxing.com/login/ssologin
  → study.hnslsdxy.com/login/tologin
  → study.hnslsdxy.com/portal  (最终到达)
"""

import requests
from urllib.parse import urlparse

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)

# 超星 SSO 桥接入口（来自门户 API /api/services/card）
FYSSO_URL = "https://fysso.chaoxing.com/sso/hnslsdxy"


def get_study_cookie(sso_cookies: dict, proxy: str = None) -> dict:
    """
    通过超星 SSO 桥接获取学习通 Cookie

    Args:
        sso_cookies: SSO 登录后的 cookies 字典
        proxy: HTTP 代理

    Returns:
        {"success": bool, "cookies": dict, "cookie_jar": list, "message": str}
    """
    session = requests.Session()
    session.headers.update({"User-Agent": _USER_AGENT})
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    # 注入 SSO cookies（CAS 认证需要）
    for name, value in sso_cookies.items():
        session.cookies.set(name, value, domain="sso.hnslsdxy.com", path="/")
        session.cookies.set(name, value, domain=".hnslsdxy.com", path="/")

    # 访问超星 SSO 桥接入口，跟踪完整重定向链
    print(f"[学习通] 访问 {FYSSO_URL}")
    url = FYSSO_URL

    max_redirects = 15
    for step in range(1, max_redirects + 1):
        resp = session.get(url, allow_redirects=False, timeout=15)
        location = resp.headers.get("Location")
        sc = resp.headers.get("Set-Cookie", "")
        if sc:
            cookie_name = sc.split("=")[0]
            print(f"[学习通] Step {step}: {resp.status_code} Set-Cookie: {cookie_name}")

        if not location or resp.status_code not in (301, 302, 303, 307, 308):
            break

        # 相对路径补全
        if location.startswith("/"):
            parsed = urlparse(url)
            location = f"{parsed.scheme}://{parsed.netloc}{location}"

        url = location
        print(f"[学习通] Step {step}: → {url[:80]}")

    print(f"[学习通] 最终 URL: {url}")

    # 提取学习通相关 cookies
    target_domains = (
        "study.hnslsdxy.com", ".study.hnslsdxy.com",
        "chaoxing.com", ".chaoxing.com",
        "hnslsdxy.com", ".hnslsdxy.com",
    )
    domain_cookies = {}
    cookie_jar = []
    for cookie in session.cookies:
        if any(cookie.domain == d or cookie.domain.endswith(f".{d.lstrip('.')}")
               for d in target_domains):
            domain_cookies[cookie.name] = cookie.value
            cookie_jar.append(cookie)

    print(f"[学习通] cookies: {list(domain_cookies.keys())}")

    if not domain_cookies:
        return {"success": False, "cookies": {}, "message": "未获取到学习通 cookies"}

    return {
        "success": True,
        "cookies": domain_cookies,
        "cookie_jar": cookie_jar,
        "message": "成功获取学习通 cookies",
    }
