#!/usr/bin/env python3
"""
SSO 登录模块 — 湖南水利水电职业技术学院

功能：SSO 登录获取 Cookie，通过 requests 跟踪 CAS 重定向链获取各子站点 Cookie

Usage:
    from sso import SSO

    sso = SSO()
    sso.set_account("学号", "密码")

    # 获取 SSO Cookie（优先 Python 直接登录，失败则自动回退到浏览器登录）
    result = sso.get_cookie()

    # 强制使用浏览器登录
    result = sso.get_cookie(browser=True)

    # 获取指定域名的 Cookie（自动跟踪 CAS 重定向链）
    result = sso.get_cookie(domain="zfjw.hnslsdxy.com")   # 教务系统
    result = sso.get_cookie(domain="assess.hnslsdxy.com")  # 评教系统
"""

import re
import json
import time
import requests
from bs4 import BeautifulSoup

from .crypto import aes_encrypt
from .captcha import check_captcha, fetch_captcha, ocr_captcha
from .browser import get_domain_cookie


class SSO:
    """SSO 登录封装"""

    BASE = "https://sso.hnslsdxy.com"
    LOGIN_URL = f"{BASE}/login"

    # 子站点入口 URL
    SITE_URLS = {
        "portal.hnslsdxy.com": "https://portal.hnslsdxy.com/home",
        "assess.hnslsdxy.com": "https://assess.hnslsdxy.com/auth/login/",
        "zfjw.hnslsdxy.com": "https://zfjw.hnslsdxy.com/jwglxt/xtgl/index_initMenu.html?jsdm=xs",
    }

    def __init__(self, proxy: str = None):
        self._username = None
        self._password = None
        self._proxy = proxy
        self._cookies = None

    def set_account(self, username: str, password: str):
        """设置账号密码"""
        self._username = username
        self._password = password

    def get_cookie(self, domain: str = None, max_retries: int = 2) -> dict:
        """
        获取 Cookie

        Args:
            domain: 目标域名，如 'assess.hnslsdxy.com'。为 None 时返回 SSO 原始 cookies
            max_retries: 验证码识别失败时的最大重试次数

        Returns:
            {"success": bool, "cookies": dict, "message": str}
        """
        if not self._username or not self._password:
            return {"success": False, "cookies": {}, "message": "请先调用 set_account() 设置账号密码"}

        if not self._cookies:
            result = self._login(max_retries)
            if not result["success"]:
                return result
            self._cookies = result["cookies"]

        if domain is None:
            return {"success": True, "cookies": self._cookies, "message": "OK"}

        return get_domain_cookie(domain, self._cookies, self._proxy)

    def _extract_page_fields(self, html: str) -> dict:
        """从登录页 HTML 提取 croypto、execution"""
        soup = BeautifulSoup(html, "html.parser")

        def _text(pid):
            el = soup.find("p", id=pid)
            return el.get_text(strip=True) if el else ""

        return {
            "croypto": _text("login-croypto"),
            "execution": _text("login-page-flowkey"),
        }

    def _create_session(self) -> requests.Session:
        """创建匹配浏览器特征的 requests Session"""
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "Referer": self.LOGIN_URL,
            "Origin": self.BASE,
        })
        if self._proxy:
            session.proxies = {"http": self._proxy, "https": self._proxy}
        return session

    def _do_login(self, session: requests.Session, captcha_payload: str = "",
                  croypto: str = None, execution: str = None) -> dict:
        """
        执行一次登录请求

        Args:
            session: requests.Session
            captcha_payload: 验证码加密后的值，空字符串表示不带验证码
            croypto: 已获取的 croypto，为 None 时重新获取登录页
            execution: 已获取的 execution，为 None 时重新获取登录页

        Returns:
            {"success": bool, "cookies": dict, "message": str}
        """
        # 获取登录页（如果未提供 croypto/execution）
        if not croypto or not execution:
            resp = session.get(self.LOGIN_URL, timeout=15)
            resp.raise_for_status()
            fields = self._extract_page_fields(resp.text)
            croypto = fields["croypto"]
            execution = fields["execution"]

        if not croypto:
            return {"success": False, "cookies": {}, "message": "无法提取 login-croypto"}

        encrypted_pw = aes_encrypt(croypto, self._password)

        form = [
            ("username", self._username),
            ("type", "UsernamePassword"),
            ("_eventId", "submit"),
            ("geolocation", ""),
            ("execution", execution),
            ("captcha_code", captcha_payload),
            ("croypto", croypto),
            ("password", encrypted_pw),
            ("captcha_payload", captcha_payload),
        ]

        resp = session.post(
            self.LOGIN_URL,
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
            allow_redirects=True,
        )

        cookies = {c.name: c.value for c in session.cookies}
        if "/login" not in resp.url:
            return {"success": True, "cookies": cookies, "message": "OK", "redirect": resp.url}

        error_msg = self._parse_error(resp.text)
        return {"success": False, "cookies": cookies, "message": error_msg or "登录失败"}

    def _login_with_captcha(self, session: requests.Session) -> dict:
        """
        带验证码登录：获取登录页 → 获取验证码 → OCR → 加密 → 提交
        """
        try:
            # 1. 获取登录页
            resp = session.get(self.LOGIN_URL, timeout=15)
            resp.raise_for_status()
            fields = self._extract_page_fields(resp.text)
            croypto = fields["croypto"]
            execution = fields["execution"]

            # 2. 获取并识别验证码
            img = fetch_captcha(session)
            captcha_code = ocr_captcha(img)
            if not captcha_code:
                return {"success": False, "cookies": {}, "message": "验证码 OCR 返回空"}

            captcha_payload = aes_encrypt(croypto, captcha_code)
            print(f"  OCR: {captcha_code}")

            # 3. 用同一个 croypto/execution 提交
            return self._do_login(session, captcha_payload=captcha_payload,
                                  croypto=croypto, execution=execution)
        except Exception as e:
            return {"success": False, "cookies": {}, "message": f"验证码异常: {e}"}

    # 不需要重试的错误关键词
    _FATAL_ERRORS = ("用户名或密码错误", "账号已锁定", "账号不存在", "账号被禁用", "认证失败")

    def _login(self, max_retries: int = 2) -> dict:
        """
        智能顺序登录：
        - 先空验证码尝试
        - 如果失败且需要验证码，再带验证码尝试

        Returns:
            {"success": bool, "cookies": dict, "message": str}
        """
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                print(f"\n--- 重试 #{attempt - 1} ---")

            print(f"[尝试 {attempt}/{max_retries}]")

            # 1. 创建 session，获取登录页
            session = self._create_session()
            try:
                resp = session.get(self.LOGIN_URL, timeout=15)
                resp.raise_for_status()
            except Exception as e:
                print(f"  获取登录页失败: {e}")
                continue

            fields = self._extract_page_fields(resp.text)
            croypto = fields["croypto"]
            execution = fields["execution"]

            if not croypto:
                print("  无法提取 login-croypto")
                continue

            # 2. 先尝试空验证码（覆盖大部分场景）
            print("  → 尝试空验证码登录...")
            r = self._do_login(session, captcha_payload="",
                               croypto=croypto, execution=execution)

            if r["success"]:
                print(f"  ✓ 登录成功！")
                self._cookies = r["cookies"]
                return r

            # 3. 检查是否是致命错误
            for keyword in self._FATAL_ERRORS:
                if keyword in r["message"]:
                    print(f"  ✗ {r['message']}（不重试）")
                    return r

            # 4. 空验证码失败，检查是否需要验证码，尝试带验证码
            captcha_info = check_captcha(session, self._username)
            need_captcha = captcha_info.get("count", 0) > 0

            if need_captcha:
                print(f"  ✗ 空验证码失败，尝试带验证码...")
                session2 = self._create_session()
                r2 = self._login_with_captcha(session2)
                if r2["success"]:
                    print(f"  ✓ 带验证码登录成功！")
                    self._cookies = r2["cookies"]
                    return r2
                print(f"  ✗ 带验证码也失败: {r2['message']}")
            else:
                print(f"  ✗ {r['message']}")

        return {"success": False, "cookies": {}, "message": "超过最大重试次数"}

    def _parse_error(self, resp_text: str) -> str:
        """从响应中提取错误信息"""
        # 尝试 JSON
        try:
            import json
            resp_json = json.loads(resp_text)
            msg = resp_json.get("message") or resp_json.get("msg") or resp_json.get("error", "")
            if msg:
                return str(msg)
        except Exception:
            pass

        soup = BeautifulSoup(resp_text, "html.parser")

        # 常见错误选择器
        for sel in (".error-msg", ".error-toast", ".ant-message-error", ".login-error", "#error-msg"):
            el = soup.select_one(sel)
            if el:
                txt = el.get_text(strip=True)
                if txt and len(txt) < 200:
                    return txt

        # 页面文本匹配
        body_text = soup.get_text()
        for pattern in ("用户名或密码错误", "验证码有误", "验证码错误", "账号已锁定",
                        "密码错误", "账号不存在", "账号被禁用", "登录失败", "认证失败"):
            if pattern in body_text:
                return pattern

        # script 标签提取
        for script in soup.find_all("script"):
            if script.string and ("error" in script.string.lower() or "msg" in script.string.lower()):
                match = re.search(r'["\']([^"\']*(?:错误|失败|不正确|锁定|禁用)[^"\']*)["\']', script.string)
                if match:
                    return match.group(1)

        return ""
