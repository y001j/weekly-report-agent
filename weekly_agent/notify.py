"""EP07：发消息到飞书或企业微信的群机器人。没配置地址时只打印，方便本地演示。"""


def post_to_webhook(url: str | None, text: str) -> None:
    if not url:
        print(f"\n[模拟发送] 未配置 webhook 地址，以下内容不会真的发出：\n{text}\n")
        return
    import httpx

    if "qyapi.weixin.qq.com" in url:  # 企业微信群机器人
        body = {"msgtype": "text", "text": {"content": text}}
    else:  # 飞书群机器人
        body = {"msg_type": "text", "content": {"text": text}}
    resp = httpx.post(url, json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code", data.get("errcode", 0)) != 0:  # 两家都是 HTTP 200 + 错误码
        raise RuntimeError(f"webhook 返回错误：{data}")
