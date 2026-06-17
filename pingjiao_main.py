#!/usr/bin/env python3
"""
评教模块使用示例
"""

from sso import SSO
from pingjiao import PingJiao


def main():
    """交互式评教"""
    print("\n--- 评教系统 ---")
    username = input("学号: ").strip()
    password = input("密码: ").strip()

    if not username or not password:
        print("学号和密码不能为空")
        return

    # SSO 登录
    sso = SSO()
    sso.set_account(username, password)
    result = sso.get_cookie()

    if not result["success"]:
        print(f"登录失败: {result['message']}")
        return

    print("✓ SSO 登录成功")

    # 初始化评教模块
    pj = PingJiao()
    pj.set_sso_cookie(result["cookies"])

    # 查询待评教课程
    print("\n查询待评教课程...")
    pj.show_assessments()

    # 选择操作
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


if __name__ == "__main__":
    main()
