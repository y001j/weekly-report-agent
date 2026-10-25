"""审批网页：手机上点开链接，看周报，点「同意」或「拒绝」，也可以写修改意见。

    GET  /review  只展示，不做任何改动（聊天软件预览链接时不会误触发审批）
    POST /decide  提交审批结果，后台从暂停处继续运行 Agent
"""

from html import escape

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse

from . import jobs
from .approval import verify

api = FastAPI(title="周报审批")

PAGE = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>周报审批</title>
<style>body{{font-family:system-ui,sans-serif;max-width:640px;margin:24px auto;padding:0 16px;line-height:1.6}}
pre{{white-space:pre-wrap;background:#f5f5f5;padding:12px;border-radius:8px}}
textarea{{width:100%;box-sizing:border-box;min-height:72px}}button{{padding:10px 20px;margin:8px 8px 0 0;font-size:16px}}</style>
</head><body>{body}</body></html>"""


def _check(thread: str, sig: str) -> None:
    if not verify(thread, sig):
        raise HTTPException(status_code=403, detail="链接无效或已被篡改")


@api.get("/review", response_class=HTMLResponse)
def review(thread: str, sig: str):
    _check(thread, sig)
    text = jobs.pending_text(jobs.get_app(), thread)
    if text is None:
        return PAGE.format(body=f"<h2>{escape(thread)}</h2><p>这份周报已经处理过了。</p>")
    form = f"""<h2>周报待审批：{escape(thread)}</h2><pre>{escape(text)}</pre>
<form method="post" action="decide">
<input type="hidden" name="thread" value="{escape(thread)}"><input type="hidden" name="sig" value="{escape(sig)}">
<button name="decision" value="yes">同意发送</button><button name="decision" value="no">拒绝</button>
<p>或者写修改意见，Agent 会改完再发给你审批：</p><textarea name="feedback"></textarea>
<button name="decision" value="feedback">提交修改意见</button></form>"""
    return PAGE.format(body=form)


@api.post("/decide", response_class=HTMLResponse)
def decide(background: BackgroundTasks, thread: str = Form(), sig: str = Form(),
           decision: str = Form(), feedback: str = Form("")):
    _check(thread, sig)
    if jobs.pending_text(jobs.get_app(), thread) is None:
        return PAGE.format(body="<p>这份周报已经处理过了。</p>")
    if decision == "feedback":
        if not feedback.strip():
            return PAGE.format(body="<p>修改意见不能为空，请返回重新填写。</p>")
        value, tip = feedback.strip(), "已提交修改意见，改好后会再次发给你审批。"
    elif decision in ("yes", "no"):
        value, tip = decision, "已同意，正在发送到群。" if decision == "yes" else "已拒绝，本周周报不会发送。"
    else:
        raise HTTPException(status_code=400, detail="未知的审批结果")
    background.add_task(jobs.resume, thread, value)  # 恢复运行可能要几十秒，放到后台，页面立即返回
    return PAGE.format(body=f"<h2>{escape(thread)}</h2><p>{tip}</p>")
