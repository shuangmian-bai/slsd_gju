#!/usr/bin/env python3
"""
选课交互式脚本

功能：
1. 查询全部课程（标记已选状态）
2. 抢课（支持多线程持续抢）
3. 退课
"""

import sys
import time
import threading
from sso import SSO
from xuanke import XuanKe


def login():
    """SSO 登录并获取教务系统 Cookie"""
    username = input("学号: ").strip()
    password = input("密码: ").strip()
    if not username or not password:
        print("账号密码不能为空")
        sys.exit(1)

    sso = SSO()
    sso.set_account(username, password)

    print("正在 SSO 登录...")
    result = sso.get_cookie()
    if not result["success"]:
        print(f"登录失败: {result['message']}")
        sys.exit(1)
    print("SSO 登录成功")

    print("正在获取教务系统 Cookie...")
    result = sso.get_cookie(domain="zfjw.hnslsdxy.com")
    if not result["success"]:
        print(f"获取教务系统 Cookie 失败: {result['message']}")
        sys.exit(1)
    print("教务系统 Cookie 获取成功")

    xk = XuanKe()
    # 使用 cookie_jar 保留正确的 domain 和 path（如 JSESSIONID 的 path=/jwglxt）
    if "cookie_jar" in result:
        xk.set_cookie_jar(result["cookie_jar"])
    else:
        xk.set_cookies(result["cookies"])
    return xk


def show_courses(xk: XuanKe):
    """查询全部课程"""
    print()
    xk.show_courses()
    print()


def select_course(xk: XuanKe) -> str:
    """让用户选择一门课程，返回课程名称"""
    result = xk.get_courses()
    courses = result.get("tmpList", [])
    if not courses:
        print("没有可选课程")
        return None

    selected_ids = xk.get_selected_jxb_ids()
    xk.print_courses(courses, selected_ids)

    while True:
        choice = input("\n输入序号选择课程（0 取消）: ").strip()
        if choice == "0":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(courses):
                return courses[idx].get("kcmc", "")
            else:
                print(f"序号范围: 1-{len(courses)}")
        except ValueError:
            print("请输入数字")


def select_selected_course(xk: XuanKe) -> str:
    """让用户从已选课程中选择一门，返回课程名称"""
    courses = xk.get_selected_courses()
    if not courses:
        print("没有已选课程")
        return None

    print(f"\n{'序号':<4} {'课程名称':<30} {'课程号':<14} {'教学班'}")
    print("=" * 80)
    for i, c in enumerate(courses, 1):
        kcmc = c.get("kcmc", "")
        kch = c.get("kch", "")
        jxbmc = c.get("jxbmc", "")
        print(f"{i:<4} {kcmc:<30} {kch:<14} {jxbmc}")
    print("=" * 80)

    while True:
        choice = input("\n输入序号选择课程（0 取消）: ").strip()
        if choice == "0":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(courses):
                return courses[idx].get("kcmc", "")
            else:
                print(f"序号范围: 1-{len(courses)}")
        except ValueError:
            print("请输入数字")


def grab_course(xk: XuanKe):
    """抢课（支持多线程持续抢）"""
    name = select_course(xk)
    if not name:
        return

    # 线程数
    threads_input = input("线程数（默认 3）: ").strip()
    num_threads = int(threads_input) if threads_input.isdigit() and int(threads_input) > 0 else 3

    # 间隔
    interval_input = input("请求间隔秒数（默认 1）: ").strip()
    interval = float(interval_input) if interval_input else 1.0

    # 最大尝试次数
    max_input = input("最大尝试次数（默认 0=不限）: ").strip()
    max_attempts = int(max_input) if max_input.isdigit() else 0

    print(f"\n开始抢课: {name} | 线程数: {num_threads} | 间隔: {interval}s | 最大尝试: {'不限' if max_attempts == 0 else max_attempts}")

    stop_event = threading.Event()
    counter = {"attempt": 0, "success": 0, "fail": 0}
    lock = threading.Lock()

    def worker(thread_id):
        while not stop_event.is_set():
            with lock:
                if max_attempts > 0 and counter["attempt"] >= max_attempts:
                    stop_event.set()
                    break
                counter["attempt"] += 1
                attempt = counter["attempt"]

            try:
                result = xk.grab(name)
                with lock:
                    if result["success"]:
                        counter["success"] += 1
                        print(f"\n  [线程{thread_id}] #{attempt} ✓ {result['message']}")
                        stop_event.set()
                        return
                    else:
                        counter["fail"] += 1
                        print(f"  [线程{thread_id}] #{attempt} ✗ {result['message']}")
            except Exception as e:
                with lock:
                    counter["fail"] += 1
                    print(f"  [线程{thread_id}] #{attempt} 异常: {e}")

            time.sleep(interval)

    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i + 1,), daemon=True)
        t.start()
        threads.append(t)

    try:
        for t in threads:
            t.join(timeout=3600)
    except KeyboardInterrupt:
        print("\n用户中断，停止抢课...")
        stop_event.set()

    print(f"\n抢课结束: 尝试 {counter['attempt']} 次, 成功 {counter['success']} 次, 失败 {counter['fail']} 次")


def drop_course(xk: XuanKe):
    """退课"""
    name = select_selected_course(xk)
    if not name:
        return

    confirm = input(f"\n确认退课 \"{name}\"？(y/N): ").strip().lower()
    if confirm != "y":
        print("已取消")
        return

    result = xk.drop(name)
    if result["success"]:
        print(f"✓ {result['message']}")
    else:
        print(f"✗ {result['message']}")


def main():
    xk = login()

    while True:
        print("\n" + "=" * 40)
        print("  选课系统")
        print("=" * 40)
        print("  1. 查询全部课程")
        print("  2. 抢课")
        print("  3. 退课")
        print("  0. 退出")
        print("=" * 40)

        choice = input("请选择: ").strip()

        if choice == "1":
            show_courses(xk)
        elif choice == "2":
            grab_course(xk)
        elif choice == "3":
            drop_course(xk)
        elif choice == "0":
            print("退出")
            break
        else:
            print("无效选择")


if __name__ == "__main__":
    main()
