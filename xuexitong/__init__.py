#!/usr/bin/env python3
"""
学习通模块 — 湖南水利水电职业技术学院超星网络教学平台

功能：获取用户信息、查询课程列表

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

    # 查询课程列表
    courses = xt.get_courses()
    # {"success": True, "total": 30, "courses": [{"courseName": "...", "teacher": "...", ...}]}
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

    def get_courses(self, course_type: int = 1, page: int = 1, page_size: int = 50) -> dict:
        """
        查询当前用户的课程列表

        Args:
            course_type: 课程类型，1=学习课程，2=我 teaching 的课程
            page: 页码，从 1 开始
            page_size: 每页数量

        Returns:
            {
                "success": bool,
                "total": int,
                "courses": [
                    {
                        "courseName": str,      # 课程名称
                        "teacher": str,         # 教师姓名
                        "courseId": str,        # 课程 ID
                        "clazzId": str,         # 班级 ID
                        "cpi": str,             # 用户 ID
                        "info": str,            # "{clazzId}_{cpi}"
                        "cover": str,           # 封面图片 URL
                        "url": str,             # 课程详情页链接
                        "ended": bool           # 是否已结束（Course has closed）
                    },
                    ...
                ],
                "message": str
            }
        """
        try:
            self._ensure_session()

            url = "https://mooc2-ans.chaoxing.com/mooc2-ans/visit/courselistdata"
            data = {
                "courseType": str(course_type),
                "courseFolderId": "0",
                "query": "",
                "page": str(page),
                "pageSize": str(page_size),
            }

            resp = self._session.post(
                url,
                data=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://mooc2-ans.chaoxing.com/visit/interaction",
                },
                timeout=30,
            )
            resp.encoding = "utf-8"
            html = resp.text

            # 用正则解析 HTML（避免依赖 bs4 的 DOMParser）
            courses = []
            # 匹配每个课程块
            for m in re.finditer(
                r'<div\s+class="course\s+clearfix[^"]*"\s+info="(\d+_\d+)"[^>]*>',
                html,
            ):
                info = m.group(1)
                start = m.start()
                # 找到这个课程块的结束位置（下一个课程块开头或结尾）
                next_m = re.search(
                    r'<div\s+class="course\s+clearfix', html[start + len(m.group(0)):]
                )
                end = start + len(m.group(0)) + next_m.start() if next_m else len(html)
                block = html[start:end]

                # 提取字段
                clazz_id = re.search(r'class="clazzId"[^>]*value="(\d+)"', block)
                course_id = re.search(r'class="courseId"[^>]*value="(\d+)"', block)
                cpi = re.search(r'class="curPersonId"[^>]*value="(\d+)"', block)
                course_name = re.search(
                    r'class="course-name[^"]*"[^>]*title="([^"]*)"', block
                )
                teacher = re.search(
                    r'class="[^"]*\bcolor3\b[^"]*"[^>]*>([^<]+)<', block
                )
                cover = re.search(r'class="course-cover"\s*>.*?<img\s+src="([^"]*)"', block, re.DOTALL)
                link = re.search(
                    r'class="color1"\s+href="([^"]*)"', block
                )
                # 检测是否已结束（存在 class="not-open-tip" 元素）
                ended = bool(re.search(r'class="not-open-tip"', block))

                courses.append({
                    "courseName": course_name.group(1) if course_name else "",
                    "teacher": teacher.group(1).strip() if teacher else "",
                    "courseId": course_id.group(1) if course_id else "",
                    "clazzId": clazz_id.group(1) if clazz_id else "",
                    "cpi": cpi.group(1) if cpi else "",
                    "info": info,
                    "cover": cover.group(1) if cover else "",
                    "url": link.group(1) if link else "",
                    "ended": ended,
                })

            return {
                "success": True,
                "total": len(courses),
                "courses": courses,
                "message": f"获取课程列表成功，共 {len(courses)} 门课程",
            }
        except Exception as e:
            return {"success": False, "total": 0, "courses": [], "message": f"请求失败: {e}"}


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

    # 测试: 查询课程列表
    print("\n--- 测试: 查询课程列表 ---")
    result = xt.get_courses()

    if result["success"]:
        print(f"共 {result['total']} 门课程:\n")
        for i, c in enumerate(result["courses"], 1):
            status = "已结束" if c["ended"] else "进行中"
            print(f"  {i:2d}. [{status}] {c['courseName']}")
            print(f"      教师: {c['teacher']}")
            print(f"      课程ID: {c['courseId']}  班级ID: {c['clazzId']}")
            print()
    else:
        print(f"获取失败: {result['message']}")
