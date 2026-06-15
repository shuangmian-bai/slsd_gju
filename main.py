import json
import requests

# 从查询curl文件中提取cookie
def get_cookie_from_file(path="查询curl"):
    with open(path, "r") as f:
        content = f.read()
    # 提取 -b '...' 中的cookie
    start = content.index("-b '") + 4
    end = content.index("'", start)
    return content[start:end]

BASE_URL = "https://assess.hnslsdxy.com"

# 公共请求头
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Origin": BASE_URL,
    "Pragma": "no-cache",
    "Referer": "https://assess.hnslsdxy.com/comment/webvision/AssessmentTeachingEdit/list",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
}


def get_assessments(session):
    """查询所有待评教课程"""
    resp = session.post(f"{BASE_URL}/rest/teaching/get_assessment")
    resp.raise_for_status()
    return resp.json()


def save_assessment(session, course, teacher, item_id, score):
    """提交评教（满分）"""
    data = {
        "course": course,
        "id": item_id,
        "veto": 0,
        "score": score,
        "teacher": teacher,
        "name": "1",
    }
    resp = session.post(
        f"{BASE_URL}/rest/teaching/save_assessment",
        json=data,
        headers={"Content-Type": "application/json;charset=UTF-8"},
    )
    resp.raise_for_status()
    return resp.json()


def make_full_score(standard):
    """从评教标准中提取每项满分值"""
    full_score = []
    for category in standard.get("standard", []):
        for child in category.get("children", []):
            full_score.append(child["score"])
    return full_score


def main():
    cookie = get_cookie_from_file("查询curl")
    cookie_dict = dict(item.split("=", 1) for item in cookie.split("; "))

    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers["X-CSRFToken"] = cookie_dict.get("csrftoken", "")
    session.cookies.update(cookie_dict)

    # 1. 查询待评教列表
    print("正在查询评教列表...")
    result = get_assessments(session)
    print(f"查询结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # 解析列表
    items = result.get("result", [])
    standard = result.get("standard", {})
    full_score = make_full_score(standard)

    if not items:
        print("没有需要评教的课程！")
        return

    print(f"\n共找到 {len(items)} 门课程待评教，满分数组: {full_score}\n")

    # 2. 逐个评教（满分）
    for item in items:
        item_id = item.get("id")
        course = item.get("course", "未知课程")
        teacher = item.get("teacher", "未知老师")

        print(f"正在评教: {course} - {teacher} (ID: {item_id})")

        try:
            resp = save_assessment(session, course, teacher, item_id, full_score)
            print(f"  结果: {resp}")
        except Exception as e:
            print(f"  失败: {e}")


if __name__ == "__main__":
    main()
