#!/usr/bin/env python3
"""
评教模块使用示例
"""

from sso import SSO
from pingjiao import PingJiao

# 方式1: 直接设置 Cookie
# pj = PingJiao()
# pj.set_cookie("SESSION=xxx; csrftoken=xxx")

# 方式2: 通过 SSO 登录获取 Cookie
sso = SSO()
sso.set_account("your_user", "your_password")
result = sso.get_cookie()

if not result["success"]:
    print(f"登录失败: {result['message']}")
    exit(1)

# 初始化评教模块
pj = PingJiao()

# 通过 SSO Cookie 建立评教会话
pj.set_sso_cookie(result["cookies"])

# 查询待评教课程
pj.show_assessments()

# 给所有课程满分评教
result = pj.score_all()
print(result)

# 给某个老师满分评教
# result = pj.score("课程名称", "老师姓名")
# print(result)

# 给某个老师指定分数评教
# result = pj.score("课程名称", "老师姓名", scores=[10, 10, 10, ...])
# print(result)
