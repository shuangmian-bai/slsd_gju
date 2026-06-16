#!/usr/bin/env python3
"""
选课模块（浏览器版） — 湖南水利水电职业技术学院正方教务系统

功能：通过无头浏览器执行查询课程、选课、退课等操作
"""

import json
from typing import List, Dict
from playwright.sync_api import sync_playwright, Page, BrowserContext


class XuanKeBrowser:
    """选课操作封装（浏览器版）"""

    BASE_URL = "https://zfjw.hnslsdxy.com"
    GNMKDM = "N253512"
    DEFAULT_XKKZ_ID = "540755BBD0F5022FE065000000000001"

    def __init__(self, page: Page):
        """
        初始化

        Args:
            page: Playwright Page 对象（已登录教务系统）
        """
        self._page = page

    def _post(self, url: str, data: str) -> dict:
        """
        发送 POST 请求

        Args:
            url: 请求 URL
            data: 表单数据

        Returns:
            JSON 响应
        """
        result = self._page.evaluate(f'''
            async () => {{
                const response = await fetch("{url}", {{
                    method: "POST",
                    headers: {{
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                        "X-Requested-With": "XMLHttpRequest",
                    }},
                    body: "{data}",
                }});
                const text = await response.text();
                try {{
                    return JSON.parse(text);
                }} catch (e) {{
                    return {{error: text.substring(0, 200)}};
                }}
            }}
        ''')
        return result

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
        return self._post(url, data)

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
        data = f"xkkz_id={self.DEFAULT_XKKZ_ID}&xkxnm={xkxnm}&xkxqm={xkxqm}"
        result = self._post(url, data)
        return result if isinstance(result, list) else []

    def get_course_jxb_list(self, kch_id: str, xkxnm: str = "2026",
                            xkxqm: str = "3") -> list:
        """
        获取某门课程的教学班列表

        Args:
            kch_id: 课程 ID
            xkxnm: 学年，默认 2026
            xkxqm: 学期，默认 3

        Returns:
            教学班列表
        """
        url = f"{self.BASE_URL}/jwglxt/xsxk/zzxkyzbjk_cxJxbWithKchZzxkYzb.html"
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
        result = self._post(url, data)
        return result if isinstance(result, list) else []

    def select_course(self, kch_id: str, jxb_ids: str,
                      kcmc: str = "", njdm_id: str = "2024",
                      zyh_id: str = "028E8F4FFA5CA042E065000000000001",
                      kklxdm: str = "10", xklc: str = "2",
                      xkxnm: str = "2026", xkxqm: str = "3") -> dict:
        """
        选课（需要发送2次请求）

        Args:
            kch_id: 课程 ID
            jxb_ids: 教学班 ID（do_jxb_id）
            kcmc: 课程名称参数

        Returns:
            JSON 响应 dict
        """
        # 第1次请求：预检查
        url1 = f"{self.BASE_URL}/jwglxt/xsxk/zzxkyzb_cxXkTitleMsg.html"
        data1 = (
            f"jxb_ids={jxb_ids}&xkxnm={xkxnm}&xkxqm={xkxqm}&bj=7"
            f"&kch_id={kch_id}&njdm_id={njdm_id}&zyh_id={zyh_id}&kklxdm={kklxdm}"
        )
        self._post(url1, data1)

        # 第2次请求：实际选课
        url2 = f"{self.BASE_URL}/jwglxt/xsxk/zzxkyzbjk_xkBcZyZzxkYzb.html"
        data2 = (
            f"jxb_ids={jxb_ids}&kch_id={kch_id}&kcmc={kcmc}"
            f"&rwlx=2&rlkz=0&cdrlkz=0&rlzlkz=1&sxbj=1&xxkbj=0&qz=0&cxbj=0"
            f"&xkkz_id={self.DEFAULT_XKKZ_ID}&njdm_id={njdm_id}&zyh_id={zyh_id}"
            f"&kklxdm={kklxdm}&xklc={xklc}&xkxnm={xkxnm}&xkxqm={xkxqm}&jcxx_id="
        )
        return self._post(url2, data2)

    def drop_course(self, kch_id: str, jxb_ids: str,
                    xkxnm: str = "2026", xkxqm: str = "3") -> dict:
        """
        退课（需要发送2次请求）

        Args:
            kch_id: 课程 ID
            jxb_ids: 教学班 ID（do_jxb_id）

        Returns:
            JSON 响应 dict
        """
        # 第1次请求：退课
        url1 = f"{self.BASE_URL}/jwglxt/xsxk/zzxkyzb_tuikBcZzxkYzb.html"
        data1 = (
            f"kch_id={kch_id}&jxb_ids={jxb_ids}"
            f"&xkxnm={xkxnm}&xkxqm={xkxqm}&txbsfrl=0"
        )
        result = self._post(url1, data1)

        # 第2次请求：确认退课
        url2 = f"{self.BASE_URL}/jwglxt/xsxk/zzxkyzb_xkBcZypxZzxkYzb.html"
        data2 = "zypxs=&jxb_ids="
        self._post(url2, data2)

        return result

    def get_do_jxb_id(self, kch_id: str, jxb_id: str) -> str:
        """
        获取教学班的 do_jxb_id

        Args:
            kch_id: 课程 ID
            jxb_id: 教学班 ID

        Returns:
            do_jxb_id 字符串
        """
        jxb_list = self.get_course_jxb_list(kch_id)
        for jxb in jxb_list:
            if jxb.get("jxb_id") == jxb_id:
                return jxb.get("do_jxb_id")
        return None

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

        # 获取 do_jxb_id
        do_jxb_id = self.get_do_jxb_id(kch_id, jxb_id)
        if not do_jxb_id:
            return {"success": False, "message": f"获取教学班信息失败: {kcmc}"}

        # 构造 kcmc 参数
        kcmc_param = f"({kch}){kcmc}+-+{xf}+学分"

        try:
            resp = self.select_course(kch_id=kch_id, jxb_ids=do_jxb_id, kcmc=kcmc_param)
            if isinstance(resp, dict):
                flag = resp.get("flag", "0")
                msg = resp.get("msg", "")
                if flag in ["1", "3", "6"]:
                    return {"success": True, "message": f"抢课成功: {kcmc}"}
                else:
                    return {"success": False, "message": f"抢课失败: {msg}"}
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
            return {"success": False, "message": f"退课失败: 未知响应格式"}
        except Exception as e:
            return {"success": False, "message": f"退课异常: {str(e)}"}

    def show_courses(self) -> None:
        """查询并打印课程表格（标记已选课程）"""
        result = self.get_courses()
        if "error" in result:
            print(f"错误: {result['error']}")
            return

        courses = result.get("tmpList", [])
        if not courses:
            print("未找到可选课程")
            return

        # 获取已选课程
        selected_courses = self.get_selected_courses()
        selected_ids = {c.get("jxb_id") for c in selected_courses if c.get("jxb_id")}

        # 打印课程表格
        def cn_ljust(s: str, width: int) -> str:
            display_width = sum(2 if ord(c) > 127 else 1 for c in s)
            return s + " " * (width - display_width)

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

            status = "✓ 已选" if jxb_id in selected_ids else ""

            if len(kcmc) > 18:
                kcmc = kcmc[:16] + ".."
            if len(jxbmc) > 30:
                jxbmc = jxbmc[:28] + ".."

            print(f"{i:<4} {status:<6} {cn_ljust(kcmc, 20)} {kch:<14} {cn_ljust(jxbmc, 32)} {xf:<6} {yxzrs}/{rwzxs:<8} {kzmc}")

        print("=" * 120)
        print(f"共 {len(courses)} 门课程，已选 {len(selected_ids)} 门")
