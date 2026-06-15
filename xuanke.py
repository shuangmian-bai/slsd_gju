import pandas as pd
import requests

def get_course_df():
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "https://zfjw.hnslsdxy.com",
        "Referer": "https://zfjw.hnslsdxy.com/jwglxt/xsxk/zzxkyzb_cxZzxkYzbIndex.html?gnmkdm=N253512&layout=default",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"'
    }

    cookies = {
        "JSESSIONID": "91C4959D3C989031C4A966534C57F216",
        "__jsluid_s": "62029d741e05da233b213238200b8282",
        "insert_cookie": "76657641"
    }

    url = "https://zfjw.hnslsdxy.com/jwglxt/xsxk/zzxkyzb_cxZzxkYzbPartDisplay.html?gnmkdm=N253512"
    data = "rwlx=2&xklc=2&xkly=0&bklx_id=0&sfkkjyxdxnxq=0&kzkcgs=0&xqh_id=00001&jg_id=0434691CD0BF5AD2E065000000000001&njdm_id_1=2024&zyh_id_1=028E8F4FFA5CA042E065000000000001&gnjkxdnj=0&zyh_id=028E8F4FFA5CA042E065000000000001&zyfx_id=wfx&njdm_id=2024&bh_id=21D54EB85FBE132DE065000000000001&bjgkczxbbjwcx=0&xbm=1&xslbdm=wlb&mzm=01&xz=3&ccdm=4&xsbj=0&sfkknj=0&sfkkzy=0&kzybkxy=0&sfznkx=0&zdkxms=0&sfkxq=1&bhbcyxkjxb=0&sfkcfx=0&kkbk=0&kkbkdj=0&bklbkcj=0&sfkgbcx=0&sfrxtgkcxd=0&tykczgxdcs=0&xkxnm=2026&xkxqm=3&kklxdm=10&bbhzxjxb=0&xkkz_id=540755BBD0F5022FE065000000000001&rlkz=0&xkzgbj=0&kspage=1&jspage=10&jxbzb="

    resp = requests.post(url, headers=headers, cookies=cookies, data=data)
    resp.raise_for_status()
    json_data = resp.json()
    course_list = json_data.get("tmpList", [])
    df = pd.DataFrame(course_list)
    return df


if __name__ == "__main__":
    # 完整打印全部表格，无省略
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.expand_frame_repr', False)

    df = get_course_df()
    print("===== 选课课程完整列表 =====")
    print(df)