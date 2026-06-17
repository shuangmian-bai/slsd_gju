#!/usr/bin/env python3
"""
湖南水利水电职业技术学院 - 自动化工具
统一入口：登录一次，所有功能复用会话
"""

import os
import sys

# ─── 功能模块注册 ─────────────────────────────────────────────
# 每个模块需要实现 run(sso, cookies) 函数
MODULES = {}


def register(name, desc):
    """装饰器：注册功能模块"""
    def decorator(func):
        MODULES[name] = {"desc": desc, "run": func}
        return func
    return decorator


# ─── 功能模块定义 ─────────────────────────────────────────────

@register("评教系统", "自动评教，查询待评课程，一键满分")
def run_pingjiao(sso, cookies):
    from pingjiao import PingJiao

    pj = PingJiao()
    pj.set_sso_cookie(cookies)

    print("\n查询待评教课程...")
    pj.show_assessments()

    print("\n操作:")
    print("  [1] 所有课程满分评教")
    print("  [2] 选择课程评教")
    print("  [0] 返回")

    choice = input("请选择: ").strip()
    if choice == "1":
        result = pj.score_all()
        print(result)
    elif choice == "2":
        course = input("课程名称: ").strip()
        teacher = input("老师姓名: ").strip()
        result = pj.score(course, teacher)
        print(result)


@register("选课系统", "交互式选课、抢课、退课")
def run_xuanke(sso, cookies):
    from xuanke import XuanKe

    print("\n正在获取教务系统 Cookie...")
    result = sso.get_cookie(domain="zfjw.hnslsdxy.com")
    if not result["success"]:
        print(f"获取教务系统 Cookie 失败: {result['message']}")
        return

    xk = XuanKe()
    if "cookie_jar" in result:
        xk.set_cookie_jar(result["cookie_jar"])
    else:
        xk.set_cookies(result["cookies"])

    while True:
        print("\n" + "=" * 40)
        print("  选课系统")
        print("=" * 40)
        print("  1. 查询全部课程")
        print("  2. 抢课")
        print("  3. 退课")
        print("  0. 返回主菜单")
        print("=" * 40)

        choice = input("请选择: ").strip()

        if choice == "1":
            xk.show_courses()
        elif choice == "2":
            _grab_course(xk)
        elif choice == "3":
            _drop_course(xk)
        elif choice == "0":
            break
        else:
            print("无效选择")


def _grab_course(xk):
    """抢课（支持多线程）"""
    import time
    import threading

    result = xk.get_courses()
    courses = result.get("tmpList", [])
    if not courses:
        print("没有可选课程")
        return

    selected_ids = xk.get_selected_jxb_ids()
    xk.print_courses(courses, selected_ids)

    choice = input("\n输入序号选择课程（0 取消）: ").strip()
    if choice == "0":
        return
    try:
        idx = int(choice) - 1
        if not (0 <= idx < len(courses)):
            print("序号无效")
            return
    except ValueError:
        print("请输入数字")
        return

    name = courses[idx].get("kcmc", "")

    threads_input = input("线程数（默认 3）: ").strip()
    num_threads = int(threads_input) if threads_input.isdigit() and int(threads_input) > 0 else 3

    interval_input = input("请求间隔秒数（默认 1）: ").strip()
    interval = float(interval_input) if interval_input else 1.0

    max_input = input("最大尝试次数（默认 0=不限）: ").strip()
    max_attempts = int(max_input) if max_input.isdigit() else 0

    print(f"\n开始抢课: {name} | 线程数: {num_threads} | 间隔: {interval}s")

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
                r = xk.grab(name)
                with lock:
                    if r["success"]:
                        counter["success"] += 1
                        print(f"\n  [线程{thread_id}] #{attempt} ✓ {r['message']}")
                        stop_event.set()
                        return
                    else:
                        counter["fail"] += 1
                        print(f"  [线程{thread_id}] #{attempt} ✗ {r['message']}")
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


def _drop_course(xk):
    """退课"""
    courses = xk.get_selected_courses()
    if not courses:
        print("没有已选课程")
        return

    print(f"\n{'序号':<4} {'课程名称':<30} {'课程号':<14} {'教学班'}")
    print("=" * 80)
    for i, c in enumerate(courses, 1):
        print(f"{i:<4} {c.get('kcmc',''):<30} {c.get('kch',''):<14} {c.get('jxbmc','')}")
    print("=" * 80)

    choice = input("\n输入序号选择课程（0 取消）: ").strip()
    if choice == "0":
        return
    try:
        idx = int(choice) - 1
        if not (0 <= idx < len(courses)):
            print("序号无效")
            return
    except ValueError:
        print("请输入数字")
        return

    name = courses[idx].get("kcmc", "")
    confirm = input(f"\n确认退课 \"{name}\"？(y/N): ").strip().lower()
    if confirm != "y":
        print("已取消")
        return

    r = xk.drop(name)
    print(f"{'✓' if r['success'] else '✗'} {r['message']}")


# ─── 主流程 ─────────────────────────────────────────────────

def show_menu():
    print()
    print("=" * 50)
    print("  湖南水利水电职业技术学院 - 自动化工具")
    print("=" * 50)
    print()
    keys = list(MODULES.keys())
    for i, name in enumerate(keys, 1):
        print(f"  [{i}] {name}")
        print(f"      {MODULES[name]['desc']}")
        print()
    print(f"  [0] 退出")
    print()
    return keys


def main():
    from sso import SSO

    # ── 登录 ──
    print("\n--- 登录统一身份认证 ---")
    username = input("学号: ").strip()
    password = input("密码: ").strip()

    if not username or not password:
        print("学号和密码不能为空")
        return

    sso = SSO()
    sso.set_account(username, password)

    print("正在登录...")
    result = sso.get_cookie()
    if not result["success"]:
        print(f"登录失败: {result['message']}")
        return

    cookies = result["cookies"]
    print("✓ 登录成功！")

    # ── 功能菜单 ──
    while True:
        keys = show_menu()
        choice = input("请选择功能: ").strip()

        if choice == "0":
            print("再见！")
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                name = keys[idx]
                try:
                    MODULES[name]["run"](sso, cookies)
                except KeyboardInterrupt:
                    print("\n已取消")
                except Exception as e:
                    print(f"执行失败: {e}")
            else:
                print("无效选择")
        except ValueError:
            print("请输入数字")


if __name__ == "__main__":
    main()
