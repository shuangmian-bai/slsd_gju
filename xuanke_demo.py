#!/usr/bin/env python3
"""
选课模块交互式演示 — 湖南水利水电职业技术学院

功能：SSO 登录 → 无头浏览器 → 交互式选课/退课/抢课（支持多线程）
"""

import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from sso import SSO
from xuanke_browser import XuanKeBrowser
from playwright.sync_api import sync_playwright


class XuanKeDemo:
    """交互式选课演示"""

    def __init__(self, proxy: str = None):
        self.proxy = proxy
        self.sso = None
        self.xk = None
        self.browser = None
        self.context = None
        self.page = None
        self._grab_stop_event = threading.Event()
        self._grab_stats = {"success": 0, "fail": 0, "total": 0}

    def login(self, username: str, password: str) -> bool:
        """SSO 登录并通过浏览器获取教务系统会话"""
        print(f"\n{'='*50}")
        print(f"正在登录 SSO...")
        print(f"{'='*50}")

        self.sso = SSO(proxy=self.proxy)
        self.sso.set_account(username, password)

        # 获取 SSO cookies
        result = self.sso.get_cookie()
        if not result["success"]:
            print(f"SSO 登录失败: {result['message']}")
            return False

        print(f"SSO 登录成功！")

        # 启动浏览器
        print(f"\n启动无头浏览器...")
        self._playwright = sync_playwright().start()

        browser_args = {}
        if self.proxy:
            browser_args["proxy"] = {"server": self.proxy}

        self.browser = self._playwright.chromium.launch(headless=True, **browser_args)
        self.context = self.browser.new_context()

        # 设置 SSO cookies
        cookies_to_set = []
        for name, value in result['cookies'].items():
            cookies_to_set.append({'name': name, 'value': value, 'domain': 'sso.hnslsdxy.com', 'path': '/'})
            cookies_to_set.append({'name': name, 'value': value, 'domain': '.hnslsdxy.com', 'path': '/'})

        self.context.add_cookies(cookies_to_set)

        # 访问门户首页
        self.page = self.context.new_page()
        print(f"访问门户首页...")
        self.page.goto("https://portal.hnslsdxy.com/home", wait_until="networkidle", timeout=30000)
        self.page.wait_for_timeout(3000)

        # 点击教务系统入口
        print(f"点击教务系统入口...")
        try:
            target = self.page.locator('//*[@id="root"]/div/div/div[2]/div[2]/div/div[1]/div[2]/div[2]/div/div[1]/div[5]/div/span[1]')
            target.click(timeout=10000)
            self.page.wait_for_timeout(5000)

            # 切换到新页面
            if len(self.context.pages) > 1:
                self.page = self.context.pages[-1]
                self.page.wait_for_timeout(3000)
        except Exception as e:
            print(f"点击失败: {e}")
            return False

        print(f"教务系统 URL: {self.page.url}")

        # 初始化选课模块
        self.xk = XuanKeBrowser(self.page)

        # 测试查询
        print(f"\n测试查询可选课程...")
        test_result = self.xk.get_courses(kspage=1, jspage=1)
        if "error" in test_result:
            print(f"查询失败: {test_result['error']}")
            return False
        else:
            print(f"查询成功！")

        return True

    def show_menu(self):
        print(f"\n{'='*50}")
        print(f"选课系统 - 交互式操作")
        print(f"{'='*50}")
        print(f"1. 查看可选课程")
        print(f"2. 查看已选课程")
        print(f"3. 抢课（单次）")
        print(f"4. 抢课（多线程持续抢）")
        print(f"5. 退课")
        print(f"6. 退出")
        print(f"{'='*50}")

    def show_courses(self):
        print(f"\n正在查询可选课程...")
        self.xk.show_courses()

    def show_selected_courses(self):
        print(f"\n正在查询已选课程...")
        courses = self.xk.get_selected_courses()
        if not courses:
            print("暂无已选课程")
            return
        print(f"\n已选课程 ({len(courses)} 门):")
        print("-" * 80)
        for i, c in enumerate(courses, 1):
            kcmc = c.get("kcmc", "未知课程")
            kch = c.get("kch", "")
            jxbmc = c.get("jxbmc", "")
            xf = c.get("xf", "")
            print(f"{i}. {kcmc} ({kch}) - {jxbmc} - {xf}学分")
        print("-" * 80)

    def grab_single(self):
        name = input("\n请输入课程名称（支持模糊匹配）: ").strip()
        if not name:
            print("课程名称不能为空")
            return
        print(f"\n正在抢课: {name}...")
        result = self.xk.grab(name)
        print(f"{'✓' if result['success'] else '✗'} {result['message']}")

    def grab_multi_thread(self):
        name = input("\n请输入课程名称（支持模糊匹配）: ").strip()
        if not name:
            print("课程名称不能为空")
            return

        try:
            threads = int(input("请输入线程数（默认3，最大10）: ").strip() or "3")
            threads = max(1, min(threads, 10))
        except ValueError:
            threads = 3

        try:
            interval = float(input("请输入每次抢课间隔秒数（默认1.0）: ").strip() or "1.0")
            interval = max(0.1, interval)
        except ValueError:
            interval = 1.0

        try:
            max_tries = int(input("请输入最大尝试次数（默认0表示无限）: ").strip() or "0")
        except ValueError:
            max_tries = 0

        print(f"\n{'='*50}")
        print(f"开始多线程抢课")
        print(f"课程: {name}")
        print(f"线程数: {threads}")
        print(f"间隔: {interval}秒")
        print(f"最大尝试: {'无限' if max_tries == 0 else max_tries}")
        print(f"按 Ctrl+C 停止")
        print(f"{'='*50}\n")

        self._grab_stop_event.clear()
        self._grab_stats = {"success": 0, "fail": 0, "total": 0}

        def grab_worker(worker_id: int):
            while not self._grab_stop_event.is_set():
                try:
                    result = self.xk.grab(name)
                    self._grab_stats["total"] += 1

                    if result["success"]:
                        self._grab_stats["success"] += 1
                        print(f"\n✓ [线程{worker_id}] {result['message']}")
                        print(f"  统计: 成功={self._grab_stats['success']}, "
                              f"失败={self._grab_stats['fail']}, "
                              f"总计={self._grab_stats['total']}")
                        self._grab_stop_event.set()
                        return
                    else:
                        self._grab_stats["fail"] += 1
                        if self._grab_stats["total"] % 10 == 0:
                            print(f"  [状态] 尝试 {self._grab_stats['total']} 次, "
                                  f"失败 {self._grab_stats['fail']} 次")
                        if max_tries > 0 and self._grab_stats["total"] >= max_tries:
                            print(f"\n已达到最大尝试次数 ({max_tries})，停止抢课")
                            self._grab_stop_event.set()
                            return
                except Exception as e:
                    self._grab_stats["fail"] += 1
                    print(f"  [线程{worker_id}] 异常: {e}")

                self._grab_stop_event.wait(interval)

        try:
            with ThreadPoolExecutor(max_workers=threads) as executor:
                futures = [executor.submit(grab_worker, i + 1) for i in range(threads)]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"线程异常: {e}")
        except KeyboardInterrupt:
            print(f"\n\n用户中断，正在停止...")
            self._grab_stop_event.set()

        print(f"\n{'='*50}")
        print(f"抢课结束")
        print(f"总尝试: {self._grab_stats['total']}")
        print(f"成功: {self._grab_stats['success']}")
        print(f"失败: {self._grab_stats['fail']}")
        print(f"{'='*50}")

    def drop_course(self):
        print(f"\n当前已选课程:")
        courses = self.xk.get_selected_courses()
        if not courses:
            print("暂无已选课程")
            return
        for i, c in enumerate(courses, 1):
            print(f"  {i}. {c.get('kcmc', '未知课程')}")

        name = input("\n请输入要退的课程名称（支持模糊匹配）: ").strip()
        if not name:
            print("课程名称不能为空")
            return

        confirm = input(f"确认退课 '{name}'？(y/N): ").strip().lower()
        if confirm != 'y':
            print("已取消退课")
            return

        print(f"\n正在退课: {name}...")
        result = self.xk.drop(name)
        print(f"{'✓' if result['success'] else '✗'} {result['message']}")

    def run(self):
        print(f"\n{'='*50}")
        print(f"湖南水利水电职业技术学院 - 选课系统")
        print(f"{'='*50}")

        username = input("请输入学号: ").strip()
        password = input("请输入密码: ").strip()

        if not username or not password:
            print("学号和密码不能为空")
            return

        if not self.login(username, password):
            return

        while True:
            try:
                self.show_menu()
                choice = input("\n请选择操作 (1-6): ").strip()

                if choice == "1":
                    self.show_courses()
                elif choice == "2":
                    self.show_selected_courses()
                elif choice == "3":
                    self.grab_single()
                elif choice == "4":
                    self.grab_multi_thread()
                elif choice == "5":
                    self.drop_course()
                elif choice == "6":
                    print("\n再见！")
                    break
                else:
                    print("\n无效选择，请重新输入")

            except KeyboardInterrupt:
                print(f"\n\n用户中断，退出...")
                break
            except Exception as e:
                print(f"\n操作异常: {e}")

        # 清理
        if self.browser:
            self.browser.close()
        if self._playwright:
            self._playwright.stop()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="选课系统交互式演示")
    parser.add_argument("-p", "--proxy", help="HTTP 代理，如 http://127.0.0.1:7890")
    args = parser.parse_args()

    demo = XuanKeDemo(proxy=args.proxy)
    demo.run()


if __name__ == "__main__":
    main()
