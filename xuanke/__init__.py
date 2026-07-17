#!/usr/bin/env python3
"""
选课模块 — 湖南水利水电职业技术学院正方教务系统

功能：查询课程、抢课、退课
Cookie 通过 set_cookie() 或 set_cookies() 传入

Usage:
    from xuanke import XuanKe

    xk = XuanKe()
    xk.set_cookie("JSESSIONID=xxx; __jsluid_s=xxx; insert_cookie=xxx")

    # 查询课程并打印表格
    xk.show_courses()

    # 抢课（只需课程名称）
    result = xk.grab("电影赏析")

    # 退课（只需课程名称）
    result = xk.drop("电影赏析")
"""

import json
import requests
from typing import List, Dict


class XuanKe:
    """选课操作封装"""

    BASE_URL = "https://zfjw.hnslsdxy.com"
    GNMKDM = "N253512"

    # 公共请求头
    HEADERS = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": BASE_URL,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        ),
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
    }

    REFERER = (
        f"{BASE_URL}/jwglxt/xsxk/zzxkyzb_cxZzxkYzbIndex.html"
        f"?gnmkdm={GNMKDM}&layout=default"
    )

    def __init__(self, cookie_str: str = None, proxy: str = None):
        """
        初始化选课模块

        Args:
            cookie_str: Cookie 字符串，格式 'JSESSIONID=xxx; __jsluid_s=xxx; ...'
            proxy: HTTP 代理，如 'http://127.0.0.1:7890'
        """
        self._session = requests.Session()
        self._session.headers.update(self.HEADERS)
        self._session.headers["Referer"] = self.REFERER

        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}

        if cookie_str:
            self.set_cookie(cookie_str)

    def set_cookie(self, cookie_str: str):
        """
        通过字符串设置 Cookie

        Args:
            cookie_str: 格式 'JSESSIONID=xxx; __jsluid_s=xxx; insert_cookie=xxx'
        """
        cookie_dict = {}
        for item in cookie_str.split("; "):
            if "=" in item:
                k, v = item.split("=", 1)
                cookie_dict[k.strip()] = v.strip()
        self.set_cookies(cookie_dict)

    def set_cookies(self, cookie_dict: dict):
        """
        通过字典设置 Cookie

        Args:
            cookie_dict: {"JSESSIONID": "xxx", "__jsluid_s": "xxx", ...}
        """
        for name, value in cookie_dict.items():
            self._session.cookies.set(
                name, value,
                domain="zfjw.hnslsdxy.com",
                path="/",
            )

    def set_cookie_jar(self, cookies: list):
        """
        通过 cookie 对象列表设置 Cookie（保留 domain 和 path）

        Args:
            cookies: http.cookiejar.Cookie 对象列表，来自 sso.get_cookie() 的 cookie_jar 字段
        """
        for c in cookies:
            self._session.cookies.set(
                c.name, c.value,
                domain=c.domain,
                path=c.path,
            )

    # 默认选课课程 ID（从 curl 提取）
    DEFAULT_XKKZ_ID = "540755BBD0F5022FE065000000000001"

    def get_courses(self, xkxnm: str = "2026", xkxqm: str = "3",
                    kspage: int = 1, jspage: int = 10) -> dict:
        """
        查询全部可选课程

        Args:
            xkxnm: 学年，默认 2026
            xkxqm: 学期，3=秋季，12=春季，默认 3
            kspage: 起始页码，默认 1
            jspage: 结束页码，默认 10

        Returns:
            JSON 响应 dict，课程列表在 tmpList 字段中
        """
        url = f"{self.BASE_URL}/jwglxt/xsxk/zzxkyzb_cxZzxkYzbPartDisplay.html"
        params = {"gnmkdm": self.GNMKDM}
        data = (
            f"rwlx=2&xklc=2&xkly=0&bklx_id=0&sfkkjyxdxnxq=0&kzkcgs=0"
            f"&xqh_id=00001&njdm_id_1=2024"
            f"&zyh_id_1=028E8F4FFA5CA042E065000000000001"
            f"&gnjkxdnj=0&zyh_id=028E8F4FFA5CA042E065000000000001"
            f"&zyfx_id=wfx&njdm_id=2024"
            f"&bh_id=21D54EB85FBE132DE065000000000001"
            f"&bhbcyxkjxb=0&xbm=1&xslbdm=wlb&mzm=01&xz=3&ccdm=4&xsbj=0"
            f"&sfkknj=0&sfkkzy=0&kzybkxy=0&sfznkx=0&zdkxms=0&sfkxq=1"
            f"&sfkcfx=0&kkbk=0&kkbkdj=0&bklbkcj=0&sfkgbcx=0&sfrxtgkcxd=0"
            f"&tykczgxdcs=0&xkxnm={xkxnm}&xkxqm={xkxqm}&kklxdm=10"
            f"&bbhzxjxb=0&xkkz_id={self.DEFAULT_XKKZ_ID}&rlkz=0&xkzgbj=0"
            f"&kspage={kspage}&jspage={jspage}&jxbzb="
        )
        resp = self._session.post(url, params=params, data=data, timeout=15)
        resp.raise_for_status()

        # 检查响应内容是否为 JSON
        content_type = resp.headers.get("Content-Type", "")
        if "json" not in content_type and not resp.text.strip().startswith("{"):
            return {"tmpList": [], "error": "Cookie 已过期或未登录，请重新设置 Cookie"}

        try:
            return resp.json()
        except Exception:
            return {"tmpList": [], "error": f"响应内容: {resp.text[:200]}"}

    def print_courses(self, courses: List[Dict], selected_ids: set = None) -> None:
        """
        格式化打印课程列表

        Args:
            courses: get_courses 返回的 tmpList 列表
            selected_ids: 已选课程的 jxb_id 集合
        """
        if not courses:
            print("未找到可选课程")
            return

        if selected_ids is None:
            selected_ids = set()

        def cn_ljust(s: str, width: int) -> str:
            """中文对齐：中文字符占2个宽度"""
            display_width = sum(2 if ord(c) > 127 else 1 for c in s)
            return s + " " * (width - display_width)

        # 表头
        print(f"{'序号':<4} {'状态':<6} {cn_ljust('课程名称', 20)} {'课程号':<14} {cn_ljust('教学班', 32)} {'学分':<6} {'已选/容量':<10} {'课程类型'}")
        print("=" * 120)

        for i, c in enumerate(courses, 1):
            kcmc = c.get("kcmc", "")
            kch = c.get("kch", "")
            jxbmc = c.get("jxbmc", "")
            xf = c.get("xf", "")
            yxzrs = c.get("yxzrs", "0")
            rwzxs = c.get("rwzxs", "0")
            kzmc = c.get("kzmc", "")
            jxb_id = c.get("jxb_id", "")

            # 判断是否已选
            status = "✓ 已选" if jxb_id in selected_ids else ""

            # 截断过长的名称
            if len(kcmc) > 18:
                kcmc = kcmc[:16] + ".."
            if len(jxbmc) > 30:
                jxbmc = jxbmc[:28] + ".."

            print(f"{i:<4} {status:<6} {cn_ljust(kcmc, 20)} {kch:<14} {cn_ljust(jxbmc, 32)} {xf:<6} {yxzrs}/{rwzxs:<8} {kzmc}")

        print("=" * 120)
        print(f"共 {len(courses)} 门课程，已选 {len(selected_ids)} 门")

    def select_course(self, kch_id: str, jxb_ids: str,
                      kcmc: str = "", njdm_id: str = "2024",
                      zyh_id: str = "028E8F4FFA5CA042E065000000000001",
                      kklxdm: str = "10", xklc: str = "2",
                      xkxnm: str = "2026", xkxqm: str = "3") -> dict:
        """
        抢课（选课）— 需要发送2次请求

        Args:
            kch_id: 课程 ID
            jxb_ids: 教学班 ID（多个用逗号分隔）
            kcmc: 课程名称（可选）
            njdm_id: 年级代码，默认 2024
            zyh_id: 专业 ID
            kklxdm: 课程类型代码，默认 10
            xklc: 选课轮次，默认 2
            xkxnm: 学年，默认 2026
            xkxqm: 学期，默认 3

        Returns:
            JSON 响应 dict
        """
        params = {"gnmkdm": self.GNMKDM}

        # 第1次请求：获取选课标题信息
        url1 = f"{self.BASE_URL}/jwglxt/xsxk/zzxkyzb_cxXkTitleMsg.html"
        data1 = {
            "jxb_ids": jxb_ids,
            "xkxnm": xkxnm,
            "xkxqm": xkxqm,
            "bj": "7",
            "kch_id": kch_id,
            "njdm_id": njdm_id,
            "zyh_id": zyh_id,
            "kklxdm": kklxdm,
        }
        resp1 = self._session.post(url1, params=params, data=data1, timeout=15)
        resp1.raise_for_status()

        # 第2次请求：实际选课
        url2 = f"{self.BASE_URL}/jwglxt/xsxk/zzxkyzbjk_xkBcZyZzxkYzb.html"
        data2 = {
            "jxb_ids": jxb_ids,
            "kch_id": kch_id,
            "kcmc": kcmc,
            "rwlx": "2",
            "rlkz": "0",
            "cdrlkz": "0",
            "rlzlkz": "1",
            "sxbj": "1",
            "xxkbj": "0",
            "qz": "0",
            "cxbj": "0",
            "xkkz_id": self.DEFAULT_XKKZ_ID,
            "njdm_id": njdm_id,
            "zyh_id": zyh_id,
            "kklxdm": kklxdm,
            "xklc": xklc,
            "xkxnm": xkxnm,
            "xkxqm": xkxqm,
            "jcxx_id": "",
        }
        resp2 = self._session.post(url2, params=params, data=data2, timeout=15)
        resp2.raise_for_status()

        # 尝试解析 JSON
        try:
            return resp2.json()
        except Exception:
            return resp2.text

    def drop_course(self, kch_id: str, jxb_ids: str,
                    xkxnm: str = "2026", xkxqm: str = "3") -> dict:
        """
        退课（底层方法）— 需要发送2次请求

        Args:
            kch_id: 课程 ID
            jxb_ids: 教学班 ID
            xkxnm: 学年，默认 2026
            xkxqm: 学期，默认 3

        Returns:
            JSON 响应 dict
        """
        params = {"gnmkdm": self.GNMKDM}

        # 第1次请求：退课
        url1 = f"{self.BASE_URL}/jwglxt/xsxk/zzxkyzb_tuikBcZzxkYzb.html"
        data1 = {
            "kch_id": kch_id,
            "jxb_ids": jxb_ids,
            "xkxnm": xkxnm,
            "xkxqm": xkxqm,
            "txbsfrl": "0",
        }
        resp1 = self._session.post(url1, params=params, data=data1, timeout=15)
        resp1.raise_for_status()

        # 第2次请求：确认退课（参数为空）
        url2 = f"{self.BASE_URL}/jwglxt/xsxk/zzxkyzb_xkBcZypxZzxkYzb.html"
        data2 = {
            "zypxs": "",
            "jxb_ids": "",
        }
        resp2 = self._session.post(url2, params=params, data=data2, timeout=15)
        resp2.raise_for_status()

        # 尝试解析 JSON
        try:
            return resp1.json()
        except Exception:
            return resp1.text

    def _find_course(self, name: str) -> dict:
        """
        根据课程名称查找课程信息

        Args:
            name: 课程名称（支持模糊匹配）

        Returns:
            {"success": bool, "course": dict, "message": str}
        """
        result = self.get_courses()
        courses = result.get("tmpList", [])

        if not courses:
            return {"success": False, "course": None, "message": "没有可选课程"}

        # 精确匹配
        for c in courses:
            if c.get("kcmc") == name:
                return {"success": True, "course": c, "message": "找到课程"}

        # 模糊匹配
        matches = [c for c in courses if name in c.get("kcmc", "")]
        if len(matches) == 1:
            return {"success": True, "course": matches[0], "message": f"模糊匹配到: {matches[0].get('kcmc')}"}
        elif len(matches) > 1:
            names = [c.get("kcmc") for c in matches]
            return {"success": False, "course": None, "message": f"匹配到多门课程: {names}，请输入更精确的名称"}

        return {"success": False, "course": None, "message": f"未找到课程: {name}"}

    def get_course_jxb_list(self, kch_id: str, xkxnm: str = "2026",
                            xkxqm: str = "3") -> dict:
        """
        获取某门课程的教学班列表（用于判断是否已选）

        Args:
            kch_id: 课程 ID
            xkxnm: 学年，默认 2026
            xkxqm: 学期，默认 3

        Returns:
            JSON 响应 dict
        """
        url = f"{self.BASE_URL}/jwglxt/xsxk/zzxkyzbjk_cxJxbWithKchZzxkYzb.html"
        params = {"gnmkdm": self.GNMKDM}
        data = (
            f"rwlx=2&xkly=0&bklx_id=0&sfkkjyxdxnxq=0&kzkcgs=0"
            f"&xqh_id=00001&jg_id=0434691CD0BF5AD2E065000000000001"
            f"&zyh_id=028E8F4FFA5CA042E065000000000001"
            f"&zyfx_id=wfx&txbsfrl=0&njdm_id=2024"
            f"&bh_id=21D54EB85FBE132DE065000000000001"
            f"&xbm=1&xslbdm=wlb&mzm=01&xz=3&ccdm=4&xsbj=0"
            f"&sfkknj=0&gnjkxdnj=0&sfkkzy=0&kzybkxy=0&sfznkx=0&zdkxms=0"
            f"&sfkxq=1&bhbcyxkjxb=0&sfkcfx=0&bbhzxjxb=0"
            f"&kkbk=0&kkbkdj=0&bklbkcj=0&xkxnm={xkxnm}&xkxqm={xkxqm}"
            f"&xkxskcgskg=1&rlkz=0&cdrlkz=0&rlzlkz=1&kklxdm=10"
            f"&kch_id={kch_id}&jxbzcxskg=0&xklc=2"
            f"&xkkz_id={self.DEFAULT_XKKZ_ID}&cxbj=0&fxbj=0"
        )
        resp = self._session.post(url, params=params, data=data, timeout=15)
        resp.raise_for_status()

        try:
            return resp.json()
        except Exception:
            return {"tmpList": []}

    def get_selected_courses(self, xkxnm: str = "2026", xkxqm: str = "3") -> list:
        """
        获取已选课程列表

        Args:
            xkxnm: 学年，默认 2026
            xkxqm: 学期，默认 3

        Returns:
            已选课程列表
        """
        url = f"{self.BASE_URL}/jwglxt/xsxk/zzxkyzb_cxZzxkYzbChoosedDisplay.html"
        params = {"gnmkdm": self.GNMKDM}
        data = f"xkkz_id={self.DEFAULT_XKKZ_ID}&xkxnm={xkxnm}&xkxqm={xkxqm}"

        resp = self._session.post(url, params=params, data=data, timeout=15)
        resp.raise_for_status()

        try:
            return resp.json()
        except Exception:
            return []

    def get_selected_jxb_ids(self) -> set:
        """
        获取所有已选课程的教学班 ID 集合

        Returns:
            set: 已选课程的 jxb_id 集合
        """
        selected_courses = self.get_selected_courses()
        return {c.get("jxb_id") for c in selected_courses if c.get("jxb_id")}

    def show_courses(self) -> None:
        """查询并打印课程表格（标记已选课程）"""
        result = self.get_courses()
        # 检查是否有错误
        if "error" in result:
            print(f"错误: {result['error']}")
            return

        courses = result.get("tmpList", [])
        if not courses:
            print("未找到可选课程")
            return

        # 获取已选课程的 jxb_id 集合
        selected_ids = self.get_selected_jxb_ids()

        # 打印课程表格
        self.print_courses(courses, selected_ids)

    def get_do_jxb_id(self, kch_id: str, jxb_id: str) -> str:
        """
        获取教学班的 do_jxb_id（用于选课请求）

        Args:
            kch_id: 课程 ID
            jxb_id: 教学班 ID

        Returns:
            do_jxb_id 字符串，获取失败返回 None
        """
        try:
            jxb_result = self.get_course_jxb_list(kch_id)
            jxb_list = jxb_result if isinstance(jxb_result, list) else jxb_result.get("tmpList", [])

            for jxb in jxb_list:
                if jxb.get("jxb_id") == jxb_id:
                    return jxb.get("do_jxb_id")
        except Exception:
            pass
        return None

    def grab(self, name: str) -> dict:
        """
        抢课（简化接口）

        Args:
            name: 课程名称

        Returns:
            {"success": bool, "message": str}
        """
        find_result = self._find_course(name)
        if not find_result["success"]:
            return {"success": False, "message": find_result["message"]}

        course = find_result["course"]
        kch_id = course.get("kch_id")
        jxb_id = course.get("jxb_id")
        kcmc = course.get("kcmc")
        kch = course.get("kch", "")
        xf = course.get("xf", "")

        # 获取 do_jxb_id（选课请求需要的长加密ID）
        do_jxb_id = self.get_do_jxb_id(kch_id, jxb_id)
        if not do_jxb_id:
            return {"success": False, "message": f"获取教学班信息失败: {kcmc}"}

        # 构造 kcmc 参数：(课程号)课程名称+-+学分+学分
        kcmc_param = f"({kch}){kcmc}+-+{xf}+学分"

        try:
            resp = self.select_course(kch_id=kch_id, jxb_ids=do_jxb_id, kcmc=kcmc_param)
            # 返回值格式: {"msg": "...", "flag": "0/1"}
            if isinstance(resp, dict):
                flag = resp.get("flag", "0")
                msg = resp.get("msg", "")
                if flag in ["1", "3", "6"]:
                    return {"success": True, "message": f"抢课成功: {kcmc}"}
                else:
                    return {"success": False, "message": f"抢课失败: {msg}"}
            elif isinstance(resp, str):
                if resp.lower() in ["success", "1"]:
                    return {"success": True, "message": f"抢课成功: {kcmc}"}
                else:
                    return {"success": False, "message": f"抢课失败: {resp}"}
            else:
                return {"success": False, "message": f"抢课失败: 未知响应格式"}
        except Exception as e:
            return {"success": False, "message": f"抢课异常: {str(e)}"}

    def drop(self, name: str) -> dict:
        """
        退课（简化接口）

        Args:
            name: 课程名称

        Returns:
            {"success": bool, "message": str}
        """
        # 从已选课程列表中查找
        selected_courses = self.get_selected_courses()
        course = None
        for c in selected_courses:
            if c.get("kcmc") == name or name in c.get("kcmc", ""):
                course = c
                break

        if not course:
            return {"success": False, "message": f"未找到已选课程: {name}"}

        kch_id = course.get("kch_id")
        do_jxb_id = course.get("do_jxb_id")
        kcmc = course.get("kcmc")

        if not do_jxb_id:
            return {"success": False, "message": f"获取教学班信息失败: {kcmc}"}

        try:
            resp = self.drop_course(kch_id=kch_id, jxb_ids=do_jxb_id)
            # 返回值格式: "1" = 成功, "3" = 失败
            if isinstance(resp, str):
                if resp == "1":
                    return {"success": True, "message": f"退课成功: {kcmc}"}
                else:
                    error_msgs = {
                        "2": "不在退课时间",
                        "3": "退课失败（可能未选该课或不可退）",
                        "4": "超过退课截止时间",
                    }
                    error_msg = error_msgs.get(resp, f"错误码: {resp}")
                    return {"success": False, "message": f"退课失败: {error_msg}"}
            elif isinstance(resp, dict):
                flag = resp.get("flag", "0")
                msg = resp.get("msg", "")
                if flag == "1":
                    return {"success": True, "message": f"退课成功: {kcmc}"}
                else:
                    return {"success": False, "message": f"退课失败: {msg}"}
            else:
                return {"success": False, "message": f"退课失败: 未知响应格式"}
        except Exception as e:
            return {"success": False, "message": f"退课异常: {str(e)}"}


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from sso import SSO

    print("=" * 50)
    print("  选课模块测试")
    print("=" * 50)

    # SSO 登录
    username = input("\n学号: ").strip()
    password = input("密码: ").strip()

    sso = SSO()
    sso.set_account(username, password)
    sso_result = sso.get_cookie()

    if not sso_result["success"]:
        print(f"登录失败: {sso_result['message']}")
        sys.exit(1)

    print("✓ SSO 登录成功")

    # 获取教务系统 Cookie
    print("\n获取教务系统 Cookie...")
    jw_result = sso.get_cookie(domain="zfjw.hnslsdxy.com")
    if not jw_result["success"]:
        print(f"获取教务 Cookie 失败: {jw_result['message']}")
        sys.exit(1)

    print("✓ 教务 Cookie 获取成功")

    # 创建选课实例
    xk = XuanKe()
    if "cookie_jar" in jw_result:
        xk.set_cookie_jar(jw_result["cookie_jar"])
    else:
        xk.set_cookies(jw_result["cookies"])

    # 测试1: 查询课程
    print("\n--- 测试1: 查询可选课程 ---")
    xk.show_courses()

    # 测试2: 查询已选课程
    print("\n--- 测试2: 查询已选课程 ---")
    selected = xk.get_selected_courses()
    if selected:
        print(f"已选 {len(selected)} 门课程:")
        for c in selected:
            print(f"  - {c.get('kcmc', '')} ({c.get('kch', '')})")
    else:
        print("暂无已选课程")
