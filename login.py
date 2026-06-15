#!/usr/bin/env python3
"""
SSO Login for https://sso.hnslsdxy.com/login

Login flow (reverse-engineered from Angular app):
  1. GET /login → extract login-croypto (AES key) and execution token
  2. GET /api/protected/user/findCaptchaCount/{username} → check if captcha needed
  3. If captcha: GET /api/captcha/generate/DEFAULT → OCR with ddddocr
  4. Encrypt password: AES-192-ECB(croypto, password + "," + timestamp)
  5. POST /login (form-urlencoded) with all fields

Usage:
    python3 login.py <username> <password> [--proxy http://127.0.0.1:7890]
"""

import sys
import time
import json
import argparse
import base64
import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import ddddocr

# ─── Constants ───────────────────────────────────────────────────────────────
BASE = "https://sso.hnslsdxy.com"
LOGIN_URL = f"{BASE}/login"
CAPTCHA_COUNT_API = f"{BASE}/api/protected/user/findCaptchaCount"
CAPTCHA_GEN_API = f"{BASE}/api/captcha/generate/DEFAULT"

# Static CSRF from the frontend JS
CSRF_KEY = "FzgxPikIetYDlXZM4lRG9taclVDa99lB"
CSRF_VALUE = "7964f321f00366a3a287a133dd307ed0"


# ─── AES-192-ECB Encryption ─────────────────────────────────────────────────
def aes_encrypt(key_str: str, plaintext: str) -> str:
    """AES-128-ECB + Pkcs7. Key is base64-decoded croypto (16 bytes)."""
    key = base64.b64decode(key_str)  # 16 bytes → AES-128
    pt = plaintext.encode("utf-8")
    cipher = AES.new(key, AES.MODE_ECB)
    ct = cipher.encrypt(pad(pt, AES.block_size))
    return base64.b64encode(ct).decode()


# ─── Page Parsing ────────────────────────────────────────────────────────────
def extract_page_fields(html: str) -> dict:
    """Extract croypto, execution (flowkey), and captchaId from login page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    def _text(pid):
        el = soup.find("p", id=pid)
        return el.get_text(strip=True) if el else ""

    return {
        "croypto": _text("login-croypto"),
        "execution": _text("login-page-flowkey"),
        "captcha_id": _text("captchaId"),
    }


# ─── Captcha ─────────────────────────────────────────────────────────────────
def check_captcha(session: requests.Session, username: str) -> dict:
    """GET /api/protected/user/findCaptchaCount/{username}."""
    resp = session.get(
        f"{CAPTCHA_COUNT_API}/{username}",
        headers={"Csrf-Key": CSRF_KEY, "Csrf-Value": CSRF_VALUE},
        timeout=15,
    )
    try:
        return resp.json().get("data", {})
    except Exception:
        return {}


def fetch_captcha(session: requests.Session) -> bytes:
    """GET /api/captcha/generate/DEFAULT → raw image bytes."""
    resp = session.get(CAPTCHA_GEN_API, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Captcha API returned {resp.status_code}")
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


def ocr_captcha(image_bytes: bytes) -> str:
    """Recognize captcha image using ddddocr."""
    ocr = ddddocr.DdddOcr(show_ad=False)
    result = ocr.classification(image_bytes)
    return result.strip()


# ─── Login ───────────────────────────────────────────────────────────────────
def login(username: str, password: str, proxy: str = None, max_retries: int = 3) -> dict:
    """
    Perform SSO login and return cookies.
    Retries up to max_retries times if captcha OCR is wrong.
    Returns: {"success": bool, "cookies": {name: value}, "message": str}
    """
    # ── Session ──────────────────────────────────────────────────────────────
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": LOGIN_URL,
        "Origin": BASE,
    })
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            print(f"\n--- Retry #{attempt - 1} ---")

        # ── 1. Fetch login page ──────────────────────────────────────────────
        print("[1/4] Fetching login page...")
        resp = session.get(LOGIN_URL, timeout=15)
        resp.raise_for_status()
        fields = extract_page_fields(resp.text)
        croypto = fields["croypto"]
        execution = fields["execution"]

        if not croypto:
            return {"success": False, "cookies": {}, "message": "Cannot extract login-croypto"}
        print(f"  croypto : {croypto}")

        # ── 2. Check captcha ─────────────────────────────────────────────────
        print("[2/4] Checking captcha...")
        captcha_info = check_captcha(session, username)
        need_captcha = captcha_info.get("captchaInvisible", False)
        captcha_count = captcha_info.get("count", 0)
        print(f"  count={captcha_count}, invisible={need_captcha}")

        # ── 3. Captcha OCR ───────────────────────────────────────────────────
        captcha_code = ""
        captcha_payload = ""
        if need_captcha or captcha_count > 0:
            print("[3/4] Captcha required → fetching & OCR...")
            img = fetch_captcha(session)
            captcha_code = ocr_captcha(img)
            print(f"  OCR result: {captcha_code}")
            if not captcha_code:
                return {"success": False, "cookies": {}, "message": "Captcha OCR returned empty"}
            captcha_payload = aes_encrypt(croypto, captcha_code)
        else:
            print("[3/4] No captcha needed.")

        # ── 4. Encrypt password & POST ───────────────────────────────────────
        print("[4/4] Encrypting password & submitting form...")
        encrypted_pw = aes_encrypt(croypto, password)

        form = {
            "username": username,
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
            LOGIN_URL,
            data=form,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Csrf-Key": CSRF_KEY,
                "Csrf-Value": CSRF_VALUE,
            },
            timeout=15,
            allow_redirects=True,
        )

        # ── Result ───────────────────────────────────────────────────────────
        cookies = {c.name: c.value for c in session.cookies}
        final_url = resp.url

        if "/login" not in final_url or resp.status_code == 302:
            print(f"  ✓ Login successful! Redirected to: {final_url}")
            return {"success": True, "cookies": cookies, "message": "OK", "redirect": final_url}

        # Parse error
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

        print(f"  ✗ Login failed: [{error_code}] {error_msg}")

        # If captcha error → retry; otherwise return immediately
        if "验证码" in error_msg and attempt < max_retries:
            continue

        return {
            "success": False,
            "cookies": cookies,
            "message": error_msg or "Unknown error",
            "error_code": error_code,
        }

    # All retries exhausted
    return {"success": False, "cookies": {}, "message": "Max retries exceeded"}


# ─── CLI ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="SSO Login for sso.hnslsdxy.com")
    parser.add_argument("username", help="Student/Staff ID")
    parser.add_argument("password", help="Password in plaintext")
    parser.add_argument(
        "--proxy", "-p",
        default=None,
        help="HTTP proxy, e.g. http://127.0.0.1:7890 (Clash)",
    )
    args = parser.parse_args()

    result = login(args.username, args.password, proxy=args.proxy)
    print("\n" + "=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["success"]:
        print("\nCookies:")
        for k, v in result["cookies"].items():
            print(f"  {k}={v}")


if __name__ == "__main__":
    main()
