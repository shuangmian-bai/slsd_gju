#!/usr/bin/env python3
"""
学习通模块 — 湖南水利水电职业技术学院超星网络教学平台

功能：获取用户信息

Cookie 通过 SSO 模块获取：
    from sso import SSO
    sso = SSO()
    sso.set_account("学号", "密码")
    result = sso.get_cookie(domain="study.hnslsdxy.com")

Usage:
    from xuexitong import XueXiTong

    xt = XueXiTong()
    xt.set_cookies(sso_result["cookies"])

    # 获取当前登录用户信息
    info = xt.get_user_info()
    # {"success": True, "uid": "361609524", "name": "黄孝文迪", "photo": "http://..."}
"""

import re
import requests

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)


class XueXiTong:
    """学习通操作封装"""

    BASE_URL = "http://study.hnslsdxy.com"

    def __init__(self, proxy: str = None):
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": _USER_AGENT})

        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}
        self._initialized = False

    def set_cookies(self, cookie_dict: dict):
        """
        通过字典设置 Cookie

        Args:
            cookie_dict: SSO.get_cookie(domain="study.hnslsdxy.com") 返回的 cookies
        """
        for name, value in cookie_dict.items():
            self._session.cookies.set(name, value, domain="study.hnslsdxy.com", path="/")
            self._session.cookies.set(name, value, domain=".hnslsdxy.com", path="/")
            self._session.cookies.set(name, value, domain=".chaoxing.com", path="/")
        self._initialized = False

    def _ensure_session(self):
        """确保会话已初始化（访问 portal 建立会话）"""
        if self._initialized:
            return
        resp = self._session.get(f"{self.BASE_URL}/portal", timeout=15)
        resp.encoding = "utf-8"
        self._initialized = resp.status_code == 200

    def get_user_info(self) -> dict:
        """
        获取当前登录用户信息

        Returns:
            {"success": bool, "uid": str, "name": str, "photo": str, "message": str}
        """
        try:
            self._ensure_session()

            # 调用 logininfojs 获取用户信息（登录后状态）
            resp = self._session.get(
                f"{self.BASE_URL}/logininfojs?index=1&portal=0",
                headers={"Referer": f"{self.BASE_URL}/portal"},
                timeout=15,
            )
            resp.encoding = "utf-8"
            text = resp.text

            # 提取 UID（从头像 URL）
            uid_match = re.search(r"photo\.chaoxing\.com/p/(\d+)", text)
            uid = uid_match.group(1) if uid_match else ""

            # 提取用户名
            name_match = re.search(r'zsi_a_userName\\">([^<]+)<', text)
            name = name_match.group(1) if name_match else ""

            if uid:
                return {
                    "success": True,
                    "uid": uid,
                    "name": name,
                    "photo": f"http://photo.chaoxing.com/p/{uid}_80",
                    "message": "获取用户信息成功",
                }
        except Exception as e:
            return {"success": False, "uid": "", "name": "", "photo": "", "message": f"请求失败: {e}"}

        return {"success": False, "uid": "", "name": "", "photo": "", "message": "未获取到用户信息，请检查 Cookie 是否有效"}


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from sso import SSO

    print("=" * 50)
    print("  学习通模块测试")
    print("=" * 50)

    # SSO 登录
    username = input("\n学号: ").strip()
    password = input("密码: ").strip()

    sso = SSO()
    sso.set_account(username, password)

    # 获取学习通 Cookie
    print("\n获取学习通 Cookie...")
    result = sso.get_cookie(domain="study.hnslsdxy.com")

    if not result["success"]:
        print(f"获取失败: {result['message']}")
        sys.exit(1)

    print(f"✓ 获取成功 ({len(result['cookies'])} 个 Cookie)")

    # 创建学习通实例
    xt = XueXiTong()
    xt.set_cookies(result["cookies"])

    # 测试: 获取用户信息
    print("\n--- 测试: 获取用户信息 ---")
    info = xt.get_user_info()

    if info["success"]:
        print(f"UID: {info['uid']}")
        print(f"姓名: {info['name']}")
        print(f"头像: {info['photo']}")
    else:
        print(f"获取失败: {info['message']}")
