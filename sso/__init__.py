#!/usr/bin/env python3
"""
SSO 登录模块 — 湖南水利水电职业技术学院

功能：SSO 登录获取 Cookie，支持获取各子站点的 Cookie
通过无头浏览器自动完成 CAS 跳转

Usage:
    from sso import SSO

    sso = SSO()
    sso.set_account("学号", "密码")

    # 获取 SSO Cookie
    result = sso.get_cookie()

    # 获取指定域名的 Cookie（自动完成 CAS 跳转）
    result = sso.get_cookie(domain="zfjw.hnslsdxy.com")
    result = sso.get_cookie(domain="assess.hnslsdxy.com")
"""

import time
import base64
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import ddddocr
from playwright.sync_api import sync_playwright


class SSO:
    """SSO 登录封装"""

    BASE = "https://sso.hnslsdxy.com"
    LOGIN_URL = f"{BASE}/login"
    CAPTCHA_COUNT_API = f"{BASE}/api/protected/user/findCaptchaCount"
    CAPTCHA_GEN_API = f"{BASE}/api/captcha/generate/DEFAULT"

    # 静态 CSRF（从前端 JS 提取）
    CSRF_KEY = "FzgxPikIetYDlXZM4lRG9taclVDa99lB"
    CSRF_VALUE = "7964f321f00366a3a287a133dd307ed0"

    # 子站点入口 URL
    SITE_URLS = {
        "portal.hnslsdxy.com": "https://portal.hnslsdxy.com/home",
        "assess.hnslsdxy.com": "https://assess.hnslsdxy.com/auth/login/",
        "zfjw.hnslsdxy.com": "https://zfjw.hnslsdxy.com/jwglxt/xtgl/index_initMenu.html?jsdm=xs",
    }

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

    def get_cookie(self, domain: str = None, max_retries: int = 3) -> dict:
        """
        获取 Cookie

        Args:
            domain: 目标域名，如 'zfjw.hnslsdxy.com'、'assess.hnslsdxy.com'
                    为 None 时返回 SSO 原始 cookies
            max_retries: 验证码识别失败时的最大重试次数

        Returns:
            {"success": bool, "cookies": dict, "message": str}
        """
        if not self._username or not self._password:
            return {"success": False, "cookies": {}, "message": "请先调用 set_account() 设置账号密码"}

        # 如果没有 SSO cookies，先登录
        if not self._cookies:
            result = self._login(max_retries)
            if not result["success"]:
                return result
            self._cookies = result["cookies"]

        # 如果没有指定域名，返回 SSO cookies
        if domain is None:
            return {"success": True, "cookies": self._cookies, "message": "OK"}

        # 获取指定域名的 cookies
        return self._get_domain_cookie(domain)

    def _get_domain_cookie(self, domain: str) -> dict:
        """
        通过无头浏览器获取指定域名的 cookies

        流程：
        1. 访问门户首页
        2. 点击教务系统入口
        3. 等待跳转完成
        4. 获取目标域名的 cookies

        Args:
            domain: 目标域名

        Returns:
            {"success": bool, "cookies": dict, "message": str}
        """
        try:
            print(f"[Browser] 启动无头浏览器...")
            with sync_playwright() as p:
                # 启动浏览器
                browser_args = {}
                if self._proxy:
                    browser_args["proxy"] = {"server": self._proxy}

                browser = p.chromium.launch(headless=True, **browser_args)
                context = browser.new_context()

                # 设置 SSO cookies
                cookies_to_set = []
                for name, value in self._cookies.items():
                    cookies_to_set.append({
                        "name": name,
                        "value": value,
                        "domain": "sso.hnslsdxy.com",
                        "path": "/",
                    })
                    cookies_to_set.append({
                        "name": name,
                        "value": value,
                        "domain": ".hnslsdxy.com",
                        "path": "/",
                    })

                context.add_cookies(cookies_to_set)

                # 步骤1: 访问门户首页
                page = context.new_page()
                print(f"[Browser] 步骤1: 访问门户首页...")
                page.goto("https://portal.hnslsdxy.com/home", wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(3000)
                print(f"[Browser] 当前 URL: {page.url}")

                # 步骤2: 点击教务系统入口
                print(f"[Browser] 步骤2: 点击教务系统入口...")
                try:
                    # XPath: //*[@id="root"]/div/div/div[2]/div[2]/div/div[1]/div[2]/div[2]/div/div[1]/div[5]/div/span[1]
                    target = page.locator('//*[@id="root"]/div/div/div[2]/div[2]/div/div[1]/div[2]/div[2]/div/div[1]/div[5]/div/span[1]')
                    target.click(timeout=10000)
                    print(f"[Browser] 已点击目标元素")
                except Exception as e:
                    print(f"[Browser] 点击失败: {e}")
                    # 尝试直接访问教务系统
                    print(f"[Browser] 尝试直接访问教务系统...")
                    page.goto("https://zfjw.hnslsdxy.com/sso/jasiglogin", wait_until="networkidle", timeout=30000)

                # 步骤3: 等待跳转完成
                print(f"[Browser] 步骤3: 等待跳转完成...")
                page.wait_for_timeout(5000)

                # 如果点击后打开了新页面，切换到新页面
                if len(context.pages) > 1:
                    page = context.pages[-1]
                    page.wait_for_timeout(3000)

                current_url = page.url
                print(f"[Browser] 当前 URL: {current_url}")

                # 步骤4: 获取目标域名的 cookies
                all_cookies = context.cookies()
                domain_cookies = {}
                for cookie in all_cookies:
                    if cookie["domain"] == domain or cookie["domain"].endswith(f".{domain}"):
                        domain_cookies[cookie["name"]] = cookie["value"]

                # 添加通用 cookies
                for name in ["__jsluid_s", "rg_objectid"]:
                    if name in self._cookies and name not in domain_cookies:
                        domain_cookies[name] = self._cookies[name]

                print(f"[Browser] 获取到 cookies: {list(domain_cookies.keys())}")

                browser.close()

                if not domain_cookies:
                    return {"success": False, "cookies": {}, "message": f"未获取到 {domain} 的 cookies"}

                return {
                    "success": True,
                    "cookies": domain_cookies,
                    "message": f"成功获取 {domain} 的 cookies",
                }

        except Exception as e:
            return {"success": False, "cookies": {}, "message": f"获取 {domain} cookies 失败: {str(e)}"}

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

    def _ocr_captcha(self, image_bytes: bytes, save_dir: str = "captcha") -> str:
        """
        识别验证码 — 多次识别取众数，提高准确率

        ddddocr 单次识别可能不稳定，对同一张图多次识别并投票，
        取出现频率最高的结果。
        图片会保存到 save_dir 目录，文件名包含时间戳和 OCR 结果。

        Args:
            image_bytes: 验证码图片字节
            save_dir: 图片保存目录，默认 'captcha'

        Returns:
            识别出的验证码文本
        """
        import re
        from collections import Counter

        # 使用两种模式：default + old，各识别 5 次，共 10 次投票
        ocr_default = ddddocr.DdddOcr(show_ad=False)
        ocr_old = ddddocr.DdddOcr(show_ad=False, old=True)

        results = []
        for _ in range(5):
            for ocr in (ocr_default, ocr_old):
                try:
                    r = ocr.classification(image_bytes).strip()
                    # 后处理：只保留字母和数字
                    r = re.sub(r'[^a-zA-Z0-9]', '', r)
                    if r:
                        results.append(r.lower())
                except Exception:
                    pass

        if not results:
            return ""

        # 取众数（出现最多的结果）
        counter = Counter(results)
        best, count = counter.most_common(1)[0]
        print(f"  OCR 多次结果: {dict(counter)} → 选择: {best} (出现{count}次)")

        # 保存验证码图片到本地，方便人工确认
        try:
            os.makedirs(save_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{best}.png"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            print(f"  验证码图片已保存: {filepath}")
        except Exception as e:
            print(f"  保存验证码图片失败: {e}")

        return best

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

            # 使用列表而非字典，支持重复字段（curl 中 captcha_code 出现两次）
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
                form.append(("captcha_code", captcha_code))  # 服务端可能需要重复字段
                form.append(("captcha_payload", captcha_payload))


            resp = session.post(
                self.LOGIN_URL,
                data=form,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=15,
                allow_redirects=True,
            )

            # 处理结果
            cookies = {c.name: c.value for c in session.cookies}
            final_url = resp.url

            # 检查是否登录成功
            # 成功条件：不在登录页面，或者有特定的成功标识
            if "/login" not in final_url:
                print(f"  ✓ 登录成功！重定向到: {final_url}")
                self._cookies = cookies
                return {"success": True, "cookies": cookies, "message": "OK", "redirect": final_url}

            # 检查是否有错误参数在 URL 中
            if "error" in final_url or "code" in final_url:
                print(f"  ✗ 登录失败，URL: {final_url}")

            # 解析错误
            resp_text = resp.text

            # 检查响应是否是 JSON（某些 SSO 登录失败会返回 JSON）
            import json as _json
            try:
                resp_json = resp.json()
                # 尝试从 JSON 提取错误
                error_msg = resp_json.get("message") or resp_json.get("msg") or resp_json.get("error", "")
                error_code = str(resp_json.get("code", ""))
                if error_msg:
                    print(f"  ✗ 登录失败: [{error_code}] {error_msg}")
                    if "验证码" in str(error_msg) and attempt < max_retries:
                        continue
                    return {
                        "success": False,
                        "cookies": cookies,
                        "message": str(error_msg),
                        "error_code": error_code,
                    }
            except Exception:
                pass

            # HTML 解析错误（SPA 页面可能无法提取，但还是尝试）
            soup = BeautifulSoup(resp_text, "html.parser")
            error_el = soup.find("p", id="login-error-code")
            error_code = error_el.get_text(strip=True) if error_el else ""

            error_msg = ""
            # 尝试多种错误选择器
            for sel in [".error-msg", ".error-toast", ".ant-message-error", ".wechat-note",
                        ".login-error", ".error-message", "#error-msg", "#error-message"]:
                el = soup.select_one(sel)
                if el:
                    txt = el.get_text(strip=True)
                    if txt and len(txt) < 200:
                        error_msg = txt
                        break

            # 如果没有找到错误消息，尝试从页面文本中提取
            body_text = soup.get_text()
            if not error_msg:
                for pattern in ["用户名或密码错误", "验证码有误", "验证码错误", "网络异常",
                                "账号已锁定", "密码错误", "账号不存在", "账号被禁用",
                                "登录失败", "认证失败", "用户名或密码不正确"]:
                    if pattern in body_text:
                        error_msg = pattern
                        break

            # 如果还是没有找到错误消息，尝试从 script 标签中提取
            if not error_msg:
                scripts = soup.find_all("script")
                for script in scripts:
                    if script.string and ("error" in script.string.lower() or "msg" in script.string.lower()):
                        # 尝试提取错误消息
                        import re
                        match = re.search(r'["\']([^"\']*(?:错误|失败|不正确|锁定|禁用)[^"\']*)["\']', script.string)
                        if match:
                            error_msg = match.group(1)
                            break

            print(f"  ✗ 登录失败: [{error_code}] {error_msg}")

            # 验证码错误时重试
            if "验证码" in error_msg and attempt < max_retries:
                continue

            return {
                "success": False,
                "cookies": cookies,
                "message": error_msg or "登录失败，请检查账号密码",
                "error_code": error_code,
            }

        # 所有重试用完
        return {"success": False, "cookies": {}, "message": "超过最大重试次数"}
