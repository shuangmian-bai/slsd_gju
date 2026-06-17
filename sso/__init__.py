#!/usr/bin/env python3
"""
SSO 登录模块 — 湖南水利水电职业技术学院

功能：SSO 登录获取 Cookie，通过 requests 跟踪 CAS 重定向链获取各子站点 Cookie

Usage:
    from sso import SSO

    sso = SSO()
    sso.set_account("学号", "密码")

    # 获取 SSO Cookie
    result = sso.get_cookie()

    # 获取指定域名的 Cookie（自动跟踪 CAS 重定向链）
    result = sso.get_cookie(domain="zfjw.hnslsdxy.com")   # 教务系统
    result = sso.get_cookie(domain="assess.hnslsdxy.com")  # 评教系统
"""

import re
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

    def get_cookie(self, domain: str = None, max_retries: int = 3) -> dict:
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

    def _login(self, max_retries: int = 3) -> dict:
        """
        执行 SSO 登录

        Returns:
            {"success": bool, "cookies": dict, "message": str}
        """
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Referer": self.LOGIN_URL,
            "Origin": self.BASE,
        })
        if self._proxy:
            session.proxies = {"http": self._proxy, "https": self._proxy}

        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                print(f"\n--- 重试 #{attempt - 1} ---")

            # 1. 获取登录页
            print("[1/4] 获取登录页...")
            resp = session.get(self.LOGIN_URL, timeout=15)
            resp.raise_for_status()
            fields = self._extract_page_fields(resp.text)
            croypto = fields["croypto"]
            execution = fields["execution"]

            if not croypto:
                return {"success": False, "cookies": {}, "message": "无法提取 login-croypto"}
            print(f"  croypto: {croypto}")

            # 2. 检查验证码
            print("[2/4] 检查验证码...")
            captcha_info = check_captcha(session, self._username)
            need_captcha = captcha_info.get("captchaInvisible", False)
            captcha_count = captcha_info.get("count", 0)
            print(f"  count={captcha_count}, invisible={need_captcha}")

            # 3. 验证码 OCR
            captcha_code = ""
            captcha_payload = ""
            if need_captcha or captcha_count > 0:
                print("[3/4] 需要验证码 → 获取并识别...")
                img = fetch_captcha(session)
                captcha_code = ocr_captcha(img)
                print(f"  OCR 结果: {captcha_code}")
                if not captcha_code:
                    return {"success": False, "cookies": {}, "message": "验证码 OCR 返回空"}
                captcha_payload = aes_encrypt(croypto, captcha_code)
            else:
                print("[3/4] 无需验证码")

            # 4. 加密密码并提交
            print("[4/4] 加密密码并提交表单...")
            encrypted_pw = aes_encrypt(croypto, self._password)

            # 使用列表支持重复字段（captcha_code 需要发送两次）
            form = [
                ("username", self._username),
                ("password", encrypted_pw),
                ("type", "UsernamePassword"),
                ("_eventId", "submit"),
                ("geolocation", ""),
                ("execution", execution),
                ("croypto", croypto),
            ]
            if captcha_code:
                form.append(("captcha_code", captcha_code))
                form.append(("captcha_code", captcha_code))
                form.append(("captcha_payload", captcha_payload))

            resp = session.post(
                self.LOGIN_URL,
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
                allow_redirects=True,
            )

            cookies = {c.name: c.value for c in session.cookies}
            final_url = resp.url

            if "/login" not in final_url:
                print(f"  ✓ 登录成功！重定向到: {final_url}")
                self._cookies = cookies
                return {"success": True, "cookies": cookies, "message": "OK", "redirect": final_url}

            if "error" in final_url or "code" in final_url:
                print(f"  ✗ 登录失败，URL: {final_url}")

            # 解析错误
            error_msg = self._parse_error(resp.text)
            print(f"  ✗ 登录失败: {error_msg}")

            if "验证码" in error_msg and attempt < max_retries:
                continue

            return {
                "success": False,
                "cookies": cookies,
                "message": error_msg or "登录失败，请检查账号密码",
            }

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
