#!/usr/bin/env python3
"""
评教模块 — 湖南水利水电职业技术学院

功能：查询评教标准、提交评教
通过 set_cookie() 设置 Cookie，然后进行评教操作

Usage:
    from pingjiao import PingJiao

    pj = PingJiao()
    pj.set_cookie("SESSION=xxx; csrftoken=xxx")

    # 查询待评教课程
    result = pj.get_assessments()

    # 给某个老师满分评教
    result = pj.score("课程名称", "老师姓名")

    # 给某个老师指定分数评教
    result = pj.score("课程名称", "老师姓名", scores=[10, 10, 10, ...])
"""

import requests
from typing import List, Dict, Optional


class PingJiao:
    """评教操作封装"""

    BASE_URL = "https://assess.hnslsdxy.com"

    # 公共请求头
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
    }

    def __init__(self, cookie_str: str = None, proxy: str = None):
        """
        初始化评教模块

        Args:
            cookie_str: Cookie 字符串，格式 'SESSION=xxx; csrftoken=xxx; ...'
            proxy: HTTP 代理，如 'http://127.0.0.1:7890'
        """
        self._session = requests.Session()
        self._session.headers.update(self.HEADERS)

        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}

        self._standard = None
        self._full_score = None

        if cookie_str:
            self.set_cookie(cookie_str)

    def set_cookie(self, cookie_str: str):
        """
        通过字符串设置 Cookie

        Args:
            cookie_str: 格式 'SESSION=xxx; csrftoken=xxx; ...'
        """
        cookie_dict = {}
        for item in cookie_str.split("; "):
            if "=" in item:
                k, v = item.split("=", 1)
                cookie_dict[k.strip()] = v.strip()

        # 设置 Cookie 到正确的域名
        for name, value in cookie_dict.items():
            self._session.cookies.set(name, value, domain="hnslsdxy.com")

        # 设置 CSRF Token
        csrf = cookie_dict.get("csrftoken")
        if csrf:
            self._session.headers["X-CSRFToken"] = csrf

    def set_cookies(self, cookie_dict: dict):
        """
        通过字典设置 Cookie

        Args:
            cookie_dict: {"SESSION": "xxx", "csrftoken": "xxx", ...}
        """
        for name, value in cookie_dict.items():
            self._session.cookies.set(name, value, domain="hnslsdxy.com")

        csrf = cookie_dict.get("csrftoken")
        if csrf:
            self._session.headers["X-CSRFToken"] = csrf

    def set_sso_cookie(self, sso_cookies: dict):
        """
        通过 SSO Cookie 建立评教系统会话（CAS 自动跳转）

        Args:
            sso_cookies: SSO 登录返回的 cookies 字典
        """
        # 写入 SSO Cookie
        for name, value in sso_cookies.items():
            self._session.cookies.set(name, value, domain="hnslsdxy.com")

        # CAS 跳转链：assess → sso(已登录) → 回调 assess → 拿到 sessionid/csrftoken
        r1 = self._session.get(f"{self.BASE_URL}/auth/login/", timeout=15, allow_redirects=False)
        r2 = self._session.get(r1.headers["Location"], timeout=15, allow_redirects=False)
        r3 = self._session.get(r2.headers["Location"], timeout=15, allow_redirects=False)
        final = r3.headers["Location"]
        if final.startswith("/"):
            final = f"{self.BASE_URL}{final}"
        self._session.get(final, timeout=15, allow_redirects=True)

        # 设置 CSRF Token
        csrf = self._session.cookies.get("csrftoken", domain="assess.hnslsdxy.com")
        if csrf:
            self._session.headers["X-CSRFToken"] = csrf

    def get_assessments(self) -> dict:
        """
        查询所有待评教课程

        Returns:
            {"result": [...], "standard": {...}}
        """
        resp = self._session.post(f"{self.BASE_URL}/rest/teaching/get_assessment", timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # 缓存评教标准和满分数组
        self._standard = data.get("standard", {})
        self._full_score = self._make_full_score(self._standard)

        return data

    def get_full_score(self) -> list:
        """
        获取满分数组

        Returns:
            满分数组，如 [10, 10, 10, ...]
        """
        if self._full_score is None:
            # 如果还没有查询过评教标准，先查询一次
            self.get_assessments()
        return self._full_score or []

    def get_standard(self) -> dict:
        """
        获取评教标准

        Returns:
            评教标准字典
        """
        if self._standard is None:
            self.get_assessments()
        return self._standard or {}

    def _make_full_score(self, standard: dict) -> list:
        """从评教标准中提取每项满分值"""
        full_score = []
        for category in standard.get("standard", []):
            for child in category.get("children", []):
                full_score.append(child["score"])
        return full_score

    def save_assessment(self, course: str, teacher: str, item_id: int, scores: list) -> dict:
        """
        提交评教

        Args:
            course: 课程名称
            teacher: 老师姓名
            item_id: 评教项 ID
            scores: 分数数组

        Returns:
            API 响应
        """
        data = {
            "course": course,
            "id": item_id,
            "veto": 0,
            "score": scores,
            "teacher": teacher,
            "name": "1",
        }
        resp = self._session.post(
            f"{self.BASE_URL}/rest/teaching/save_assessment",
            json=data,
            headers={"Content-Type": "application/json;charset=UTF-8"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def score(self, course_name: str = None, teacher_name: str = None,
              scores: list = None, full_score: bool = True) -> dict:
        """
        给老师评教（简化接口）

        Args:
            course_name: 课程名称（支持模糊匹配），不指定则评教所有课程
            teacher_name: 老师姓名（支持模糊匹配），不指定则评教所有老师
            scores: 指定分数数组，不指定则使用满分
            full_score: 是否使用满分（默认 True）

        Returns:
            {"success": bool, "message": str, "results": [...]}
        """
        # 查询待评教列表
        data = self.get_assessments()
        items = data.get("result", [])

        if not items:
            return {"success": False, "message": "没有需要评教的课程", "results": []}

        # 确定使用的分数数组
        if scores is not None:
            use_scores = scores
        elif full_score:
            use_scores = self.get_full_score()
        else:
            return {"success": False, "message": "请指定分数数组或使用满分", "results": []}

        if not use_scores:
            return {"success": False, "message": "无法获取满分数组", "results": []}

        # 筛选要评教的课程
        target_items = []
        for item in items:
            course = item.get("course", "")
            teacher = item.get("teacher", "")

            # 匹配课程名称
            if course_name and course_name not in course:
                continue

            # 匹配老师姓名
            if teacher_name and teacher_name not in teacher:
                continue

            target_items.append(item)

        if not target_items:
            return {"success": False, "message": f"未找到匹配的课程", "results": []}

        # 逐个评教
        results = []
        success_count = 0
        for item in target_items:
            item_id = item.get("id")
            course = item.get("course", "未知课程")
            teacher = item.get("teacher", "未知老师")

            try:
                resp = self.save_assessment(course, teacher, item_id, use_scores)
                results.append({
                    "course": course,
                    "teacher": teacher,
                    "success": True,
                    "response": resp,
                })
                success_count += 1
            except Exception as e:
                results.append({
                    "course": course,
                    "teacher": teacher,
                    "success": False,
                    "error": str(e),
                })

        return {
            "success": success_count > 0,
            "message": f"评教完成: {success_count}/{len(target_items)} 成功",
            "results": results,
        }

    def score_all(self, full_score: bool = True) -> dict:
        """
        给所有待评教课程满分评教

        Args:
            full_score: 是否使用满分（默认 True）

        Returns:
            {"success": bool, "message": str, "results": [...]}
        """
        return self.score(full_score=full_score)

    def show_assessments(self) -> None:
        """查询并打印待评教课程列表"""
        data = self.get_assessments()
        items = data.get("result", [])
        standard = self.get_standard()

        if not items:
            print("没有需要评教的课程")
            return

        # 打印评教标准
        print("=" * 60)
        print("评教标准:")
        for category in standard.get("standard", []):
            print(f"  {category.get('name', '')}:")
            for child in category.get("children", []):
                print(f"    - {child.get('name', '')}: {child.get('score', '')} 分")

        # 打印待评教列表
        print("\n" + "=" * 60)
        print(f"待评教课程 ({len(items)} 门):")
        print("-" * 60)
        for i, item in enumerate(items, 1):
            course = item.get("course", "未知课程")
            teacher = item.get("teacher", "未知老师")
            print(f"  {i}. {course} - {teacher}")
        print("-" * 60)
        print(f"满分数组: {self.get_full_score()}")
