#!/usr/bin/env python3
"""
SSO 登录模块使用示例
"""

from sso import SSO


def main():
    """交互式 SSO 登录"""
    print("\n--- SSO 登录 ---")
    username = input("学号: ").strip()
    password = input("密码: ").strip()

    if not username or not password:
        print("学号和密码不能为空")
        return

    sso = SSO()
    # sso = SSO(proxy="http://127.0.0.1:7890")  # 使用代理
    sso.set_account(username, password)

    result = sso.get_cookie()

    if result["success"]:
        print("\n✓ 登录成功！")
        print("Cookies:")
        for k, v in result["cookies"].items():
            print(f"  {k}={v}")
    else:
        print(f"\n✗ 登录失败: {result['message']}")


if __name__ == "__main__":
    main()
