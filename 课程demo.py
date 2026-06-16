from xuanke import XuanKe

# 初始化 + 设置 cookie
xk = XuanKe()
xk.set_cookie("JSESSIONID=D2B7F4C8E54B0DF9470FEEB6EC21E91D; __jsluid_s=62029d741e05da233b213238200b8282; insert_cookie=76657641")

# 查询课程状态（标记已选课程）
xk.show_courses()

# 抢课（只需课程名称，支持模糊匹配）
# result = xk.grab("电影赏析")
# print(result)

# 退课（只需课程名称）
# result = xk.drop("常用AI工具应用")
# print(result)
