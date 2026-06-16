#!/usr/bin/env python3
"""
SSO 登录模块 — 湖南水利水电职业技术学院

功能：SSO 登录获取 Cookie
通过 set_account() 设置账号密码，get_cookie() 获取 Cookie

Usage:
    from sso import SSO

    sso = SSO()
    sso.set_account("学号", "密码")
    result = sso.get_cookie()
    # result = {"success": True, "cookies": {...}, "message": "OK"}
"""

import time
import base64
import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import ddddocr


class SSO:
    """SSO 登录封装"""

    BASE = "https://sso.hnslsdxy.com"
    LOGIN_URL = f"{BASE}/login"
    CAPTCHA_COUNT_API = f"{BASE}/api/protected/user/findCaptchaCount"
    CAPTCHA_GEN_API = f"{BASE}/api/captcha/generate/DEFAULT"

    # 静态 CSRF（从前端 JS 提取）
    CSRF_KEY = "FzgxPikIetYDlXZM4lRG9taclVDa99lB"
    CSRF_VALUE = "7964f321f00366a3a287a133dd307ed0"

    def __init__(self, proxy: str = None):
        """
        初始化 SSO 登录模块

        Args:
            proxy: HTTP 代理，如 'http://127.0.0.1:7890'
        """
        self._username = None
        self._password = None
        self._proxy = proxy
        self._cookies = None

    def set_account(self, username: str, password: str):
        """
        设置账号密码

        Args:
            username: 学号/工号
            password: 密码（明文）
        """
        self._username = username
        self._password = password

    def get_cookie(self, max_retries: int = 3) -> dict:
        """
        获取 SSO Cookie

        Args:
            max_retries: 验证码识别失败时的最大重试次数

        Returns:
            {"success": bool, "cookies": dict, "message": str}
        """
        if not self._username or not self._password:
            return {"success": False, "cookies": {}, "message": "请先调用 set_account() 设置账号密码"}

        return self._login(max_retries)

    def _aes_encrypt(self, key_str: str, plaintext: str) -> str:
        """AES-128-ECB + Pkcs7. Key 是 base64 解码的 croypto (16 字节)."""
        key = base64.b64decode(key_str)
        pt = plaintext.encode("utf-8")
        cipher = AES.new(key, AES.MODE_ECB)
        ct = cipher.encrypt(pad(pt, AES.block_size))
        return base64.b64encode(ct).decode()

    def _extract_page_fields(self, html: str) -> dict:
        """从登录页 HTML 提取 croypto、execution (flowkey)、captchaId."""
        soup = BeautifulSoup(html, "html.parser")

        def _text(pid):
            el = soup.find("p", id=pid)
            return el.get_text(strip=True) if el else ""

        return {
            "croypto": _text("login-croypto"),
            "execution": _text("login-page-flowkey"),
            "captcha_id": _text("captchaId"),
        }

    def _check_captcha(self, session: requests.Session, username: str) -> dict:
        """检查是否需要验证码"""
        resp = session.get(
            f"{self.CAPTCHA_COUNT_API}/{username}",
            headers={"Csrf-Key": self.CSRF_KEY, "Csrf-Value": self.CSRF_VALUE},
            timeout=15,
        )
        try:
            return resp.json().get("data", {})
        except Exception:
            return {}

    def _fetch_captcha(self, session: requests.Session) -> bytes:
        """获取验证码图片"""
        resp = session.get(self.CAPTCHA_GEN_API, timeout=15)
        if resp.status_code != 200:
            raise RuntimeError(f"验证码 API 返回 {resp.status_code}")
        ct = resp.headers.get("Content-Type", "")
        data = resp.content
        if "json" in ct:
            try:
                j = resp.json()
                b64 = j.get("data", {}).get("image", "") or j.get("image", "")
                if b64:
                    data = base64.b64decode(b64)
            except Exception:
                pass
        return data

    def _ocr_captcha(self, image_bytes: bytes) -> str:
        """识别验证码"""
        ocr = ddddocr.DdddOcr(show_ad=False)
        result = ocr.classification(image_bytes)
        return result.strip()

    def _login(self, max_retries: int = 3) -> dict:
        """
        执行 SSO 登录

        Returns:
            {"success": bool, "cookies": dict, "message": str}
        """
        # 创建会话
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
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
            captcha_info = self._check_captcha(session, self._username)
            need_captcha = captcha_info.get("captchaInvisible", False)
            captcha_count = captcha_info.get("count", 0)
            print(f"  count={captcha_count}, invisible={need_captcha}")

            # 3. 验证码 OCR
            captcha_code = ""
            captcha_payload = ""
            if need_captcha or captcha_count > 0:
                print("[3/4] 需要验证码 → 获取并识别...")
                img = self._fetch_captcha(session)
                captcha_code = self._ocr_captcha(img)
                print(f"  OCR 结果: {captcha_code}")
                if not captcha_code:
                    return {"success": False, "cookies": {}, "message": "验证码 OCR 返回空"}
                captcha_payload = self._aes_encrypt(croypto, captcha_code)
            else:
                print("[3/4] 无需验证码")

            # 4. 加密密码并提交
            print("[4/4] 加密密码并提交表单...")
            encrypted_pw = self._aes_encrypt(croypto, self._password)

            form = {
                "username": self._username,
                "password": encrypted_pw,
                "type": "UsernamePassword",
                "_eventId": "submit",
                "geolocation": "",
                "execution": execution,
                "croypto": croypto,
            }
            if captcha_code:
                form["captcha_code"] = captcha_code
                form["captcha_payload"] = captcha_payload

            resp = session.post(
                self.LOGIN_URL,
                data=form,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Csrf-Key": self.CSRF_KEY,
                    "Csrf-Value": self.CSRF_VALUE,
                },
                timeout=15,
                allow_redirects=True,
            )

            # 处理结果
            cookies = {c.name: c.value for c in session.cookies}
            final_url = resp.url

            if "/login" not in final_url or resp.status_code == 302:
                print(f"  ✓ 登录成功！重定向到: {final_url}")
                self._cookies = cookies
                return {"success": True, "cookies": cookies, "message": "OK", "redirect": final_url}

            # 解析错误
            soup = BeautifulSoup(resp.text, "html.parser")
            error_el = soup.find("p", id="login-error-code")
            error_code = error_el.get_text(strip=True) if error_el else ""

            error_msg = ""
            for sel in [".error-msg", ".error-toast", ".ant-message-error", ".wechat-note"]:
                el = soup.select_one(sel)
                if el:
                    txt = el.get_text(strip=True)
                    if txt and len(txt) < 200:
                        error_msg = txt
                        break

            body_text = soup.get_text()
            if not error_msg:
                for pattern in ["用户名或密码错误", "验证码有误", "验证码错误", "网络异常",
                                "账号已锁定", "密码错误", "账号不存在", "账号被禁用"]:
                    if pattern in body_text:
                        error_msg = pattern
                        break

            print(f"  ✗ 登录失败: [{error_code}] {error_msg}")

            # 验证码错误时重试
            if "验证码" in error_msg and attempt < max_retries:
                continue

            return {
                "success": False,
                "cookies": cookies,
                "message": error_msg or "未知错误",
                "error_code": error_code,
            }

        # 所有重试用完
        return {"success": False, "cookies": {}, "message": "超过最大重试次数"}
