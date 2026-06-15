#!/usr/bin/env python3
"""
自动评教脚本 — 通过 SSO 登录获取 Cookie，查询待评教课程并提交满分评教。

Usage:
    python3 pingjiao.py <学工号> <密码> [--proxy http://127.0.0.1:7890]
"""

import json
import argparse
import requests
from login import login

ASSESS_BASE = "https://assess.hnslsdxy.com"


def create_session(sso_cookies: dict, proxy: str = None) -> requests.Session:
    """
    用 SSO Cookie 建立评教系统会话（CAS 自动跳转）。
    返回已携带 assess.hnslsdxy.com Cookie 的 Session。
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
    })
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    # 写入 SSO Cookie
    for name, value in sso_cookies.items():
        session.cookies.set(name, value, domain="hnslsdxy.com")

    # CAS 跳转链：assess → sso(已登录) → 回调 assess → 拿到 sessionid/csrftoken
    r1 = session.get(f"{ASSESS_BASE}/auth/login/", timeout=15, allow_redirects=False)
    r2 = session.get(r1.headers["Location"], timeout=15, allow_redirects=False)
    r3 = session.get(r2.headers["Location"], timeout=15, allow_redirects=False)
    final = r3.headers["Location"]
    if final.startswith("/"):
        final = f"{ASSESS_BASE}{final}"
    session.get(final, timeout=15, allow_redirects=True)

    # 设置 CSRF Token
    csrf = session.cookies.get("csrftoken", domain="assess.hnslsdxy.com")
    if csrf:
        session.headers["X-CSRFToken"] = csrf

    return session


def get_assessments(session: requests.Session) -> dict:
    """查询所有待评教课程"""
    resp = session.post(f"{ASSESS_BASE}/rest/teaching/get_assessment", timeout=15)
    resp.raise_for_status()
    return resp.json()


def save_assessment(session: requests.Session, course: str, teacher: str,
                    item_id: int, score: list) -> dict:
    """提交评教"""
    data = {
        "course": course,
        "id": item_id,
        "veto": 0,
        "score": score,
        "teacher": teacher,
        "name": "1",
    }
    resp = session.post(
        f"{ASSESS_BASE}/rest/teaching/save_assessment",
        json=data,
        headers={"Content-Type": "application/json;charset=UTF-8"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def make_full_score(standard: dict) -> list:
    """从评教标准中提取每项满分值"""
    full_score = []
    for category in standard.get("standard", []):
        for child in category.get("children", []):
            full_score.append(child["score"])
    return full_score


def main():
    parser = argparse.ArgumentParser(description="自动评教")
    parser.add_argument("username", help="学工号")
    parser.add_argument("password", help="密码")
    parser.add_argument("--proxy", "-p", default=None,
                        help="HTTP 代理, 如 http://127.0.0.1:7890")
    args = parser.parse_args()

    # 1. SSO 登录
    print("=" * 50)
    print("正在登录 SSO...")
    result = login(args.username, args.password, proxy=args.proxy)
    if not result["success"]:
        print(f"登录失败: {result['message']}")
        return
    print("登录成功！")

    # 2. 建立评教会话
    print("\n正在获取评教系统会话...")
    session = create_session(result["cookies"], proxy=args.proxy)

    # 3. 查询待评教列表
    print("\n正在查询评教列表...")
    data = get_assessments(session)
    items = data.get("result", [])
    standard = data.get("standard", {})
    full_score = make_full_score(standard)

    if not items:
        print("没有需要评教的课程！")
        return

    print(f"\n共 {len(items)} 门课程待评教，满分数组: {full_score}")
    print("-" * 50)

    # 4. 逐个评教（满分）
    for item in items:
        item_id = item.get("id")
        course = item.get("course", "未知课程")
        teacher = item.get("teacher", "未知老师")

        print(f"\n评教: {course} - {teacher} (ID: {item_id})")
        try:
            resp = save_assessment(session, course, teacher, item_id, full_score)
            print(f"  结果: {resp}")
        except Exception as e:
            print(f"  失败: {e}")

    print("\n" + "=" * 50)
    print("评教完成！")


if __name__ == "__main__":
    main()
