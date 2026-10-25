"""EP07入口：定时运行与审批。代码在 scheduler/ 里。

    python run.py start                 定时器调用：生成本周周报并发送审批通知
    python run.py resume 2026-W43 yes   不用网页，直接在命令行审批
    python run.py serve                 启动审批网页
"""

import argparse

from scheduler import jobs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="周报助手：定时运行与审批")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_start = sub.add_parser("start", help="生成本周周报并发送审批通知")
    p_start.add_argument("--thread", help="任务编号，默认按年份和周数生成")
    p_start.add_argument("--force", action="store_true", help="本周已完成也重新生成")
    p_resume = sub.add_parser("resume", help="审批后继续")
    p_resume.add_argument("thread")
    p_resume.add_argument("decision", help="yes、no，或一句修改意见")
    p_serve = sub.add_parser("serve", help="启动审批网页")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.cmd == "start":
        jobs.start(thread=args.thread, force=args.force)
    elif args.cmd == "resume":
        jobs.resume(args.thread, args.decision)
    else:
        import uvicorn

        from scheduler.server import api

        uvicorn.run(api, host=args.host, port=args.port)
