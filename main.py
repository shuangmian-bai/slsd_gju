#!/usr/bin/env python3
"""
湖南水利水电职业技术学院 - 自动化工具
主入口：交互式菜单，选择功能模块
"""

import sys
from sso import SSO

# ─── 功能模块注册 ─────────────────────────────────────────────
MODULES = {
    "1": {
        "name": "SSO 登录",
        "desc": "登录统一身份认证，获取 Cookie",
        "action": "login",
    },
    "2": {
        "name": "评教系统",
        "desc": "自动评教，查询待评课程，一键满分",
        "action": "pingjiao",
    },
    "3": {
        "name": "选课系统",
        "desc": "交互式选课",
        "action": "xuanke",
    },
}


def show_menu():
    """显示主菜单"""
    print()
    print("=" * 50)
    print("  湖南水利水电职业技术学院 - 自动化工具")
    print("=" * 50)
    print()
    for key, mod in MODULES.items():
        print(f"  [{key}] {mod['name']}")
        print(f"      {mod['desc']}")
        print()
    print("  [0] 退出")
    print()


def do_login():
    """SSO 登录模块"""
    from sso_login_demo import main as login_main
    login_main()


def do_pingjiao():
    """评教模块"""
    from pingjiao_main import main as pj_main
    pj_main()


def do_xuanke():
    """选课模块"""
    from xuanke_main import main as xk_main
    xk_main()


# ─── 动作分发 ─────────────────────────────────────────────────
ACTIONS = {
    "login": do_login,
    "pingjiao": do_pingjiao,
    "xuanke": do_xuanke,
}


def main():
    while True:
        show_menu()
        choice = input("请选择功能 [0-3]: ").strip()

        if choice == "0":
            print("再见！")
            break

        mod = MODULES.get(choice)
        if not mod:
            print("无效选择，请重试")
            continue

        action = ACTIONS.get(mod["action"])
        if action:
            try:
                action()
            except KeyboardInterrupt:
                print("\n已取消")
            except Exception as e:
                print(f"执行失败: {e}")
        else:
            print(f"模块 {mod['name']} 暂未实现")


if __name__ == "__main__":
    main()
