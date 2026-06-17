"""验证码获取与 OCR 识别"""

import re
import os
import base64
from datetime import datetime
from collections import Counter

import requests
import ddddocr

# 验证码 API
_CAPTCHA_COUNT_API = "https://sso.hnslsdxy.com/api/protected/user/findCaptchaCount"
_CAPTCHA_GEN_API = "https://sso.hnslsdxy.com/api/captcha/generate/DEFAULT"

# 静态 CSRF（从前端 JS 提取）
_CSRF_KEY = "FzgxPikIetYDlXZM4lRG9taclVDa99lB"
_CSRF_VALUE = "7964f321f00366a3a287a133dd307ed0"


def check_captcha(session: requests.Session, username: str) -> dict:
    """
    检查是否需要验证码

    Returns:
        {"count": int, "captchaInvisible": bool}
    """
    resp = session.get(
        f"{_CAPTCHA_COUNT_API}/{username}",
        headers={"Csrf-Key": _CSRF_KEY, "Csrf-Value": _CSRF_VALUE},
        timeout=15,
    )
    try:
        return resp.json().get("data", {})
    except Exception:
        return {}


def fetch_captcha(session: requests.Session) -> bytes:
    """获取验证码图片"""
    resp = session.get(_CAPTCHA_GEN_API, timeout=15)
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


def ocr_captcha(image_bytes: bytes, save_dir: str = "captcha") -> str:
    """
    识别验证码 — 双模式（default + old）各 5 次，共 10 次投票取众数

    图片会保存到 save_dir 目录，文件名格式 {时间戳}_{OCR结果}.png

    Args:
        image_bytes: 验证码图片字节
        save_dir: 图片保存目录

    Returns:
        识别出的验证码文本
    """
    ocr_default = ddddocr.DdddOcr(show_ad=False)
    ocr_old = ddddocr.DdddOcr(show_ad=False, old=True)

    results = []
    for _ in range(5):
        for ocr in (ocr_default, ocr_old):
            try:
                r = ocr.classification(image_bytes).strip()
                r = re.sub(r'[^a-zA-Z0-9]', '', r)
                if r:
                    results.append(r.lower())
            except Exception:
                pass

    if not results:
        return ""

    counter = Counter(results)
    best, count = counter.most_common(1)[0]
    print(f"  OCR 多次结果: {dict(counter)} → 选择: {best} (出现{count}次)")

    # 保存验证码图片
    try:
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(save_dir, f"{timestamp}_{best}.png")
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        print(f"  验证码图片已保存: {filepath}")
    except Exception as e:
        print(f"  保存验证码图片失败: {e}")

    return best
