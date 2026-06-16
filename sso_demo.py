#!/usr/bin/env python3
"""
SSO 登录模块使用示例
"""

from sso import SSO

# 初始化
sso = SSO()
# sso = SSO(proxy="http://127.0.0.1:7890")  # 使用代理

# 设置账号密码
sso.set_account("202450350051", "yuangejiayou123@H")

# 获取 Cookie
result = sso.get_cookie()
print(result)

if result["success"]:
    print("\nCookies:")
    for k, v in result["cookies"].items():
        print(f"  {k}={v}")
