# 周报助手：用 LangGraph 写一个真正能干活的 AI Agent

Agent 自动读取本周工作笔记、整理成周报、保存为文件，**在发送到群之前暂停，等你确认**。

配套视频：「AI Agent 实战」系列 EP01–EP07【视频链接】

## 项目结构

代码按功能拆成几个模块，每个文件只做一件事：

```
weekly-report-agent/
├── agent.py              入口：python agent.py
├── run.py                入口：定时运行与审批（EP07）
├── show_graph.py         把 Agent 的流程图画出来
├── evals/                评估集（EP05）
│   ├── cases.yaml        考卷：每组笔记 + 检查规则
│   ├── data/             每组的笔记
│   ├── scoring.py        评分标准
│   └── run_eval.py       运行评估、输出对比表
├── weekly_agent/
│   ├── config.py         配置：路径和 .env
│   ├── llm.py            模型：Agent 的「大脑」
│   ├── prompts.py        提示词：Agent 的「工作说明书」，按版本管理
│   ├── tools.py          工具：Agent 的「手」（读笔记、存周报、发群消息）
│   ├── memory.py         记忆：跨任务的长期记忆（EP03）
│   ├── tracing.py        追踪：接入 Langfuse，统计用量（EP04）
│   ├── guardrails.py     护栏：资料隔离、输出检查、重试规则（EP06）
│   ├── notify.py         通知：发消息到飞书 / 企业微信群（EP07）
│   ├── graph.py          图：两个节点、三条边，把大脑和手连起来
│   ├── runner.py         运行：执行图，遇到暂停就问人
│   ├── display.py        显示：用颜色和边框展示每一步（rich）
│   └── cli.py            命令行参数
├── scheduler/            定时运行与审批（EP07）
│   ├── jobs.py           start / resume：把一次运行拆成两半
│   ├── approval.py       审批链接的签名与校验
│   └── server.py         审批网页
├── workspace/notes/      5 篇虚构的工作笔记
├── workspace/demo/       提示词注入演示用的笔记（EP06）
└── tests/                不需要 API Key 的离线测试
```

读代码建议按这个顺序：`tools.py` → `prompts.py` → `llm.py` → `graph.py` → `runner.py`，再看每期新增的模块。

```
          ┌──────────────┐
START ──▶ │  agent 节点   │ ── 不需要工具 ──▶ END
          │（大模型思考） │
          └──────┬───────┘
                 │ 需要调用工具
                 ▼
          ┌──────────────┐
          │  tools 节点   │（读笔记 / 写文件 / 发群消息）
          └──────┬───────┘
                 │ 把结果交回去
                 └──────────▶ 回到 agent 节点
```

## 快速开始

需要 Python 3.10 及以上。

```bash
git clone https://github.com/y001j/weekly-report-agent.git
cd weekly-report-agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env    # 然后在 .env 里填入你的 API Key
python agent.py
```

运行后先在「👤 你：」后面说一句你想让它做什么（直接回车就用默认任务「根据本周笔记写一份周报并发到群里」），然后你会看到 Agent 每一步调用的工具，最后它会停下来显示待发送的周报，输入 `yes` 发送，输入 `no` 取消，也可以直接输入修改意见（EP03起）。生成的周报保存在 `workspace/output/weekly.md`。

## 换成其他模型

只需修改 `.env`，代码不用动。默认使用 MiniMax-M3.1-Flash：

| 模型 | MODEL_PROTOCOL | MODEL_NAME | MODEL_BASE_URL |
| --- | --- | --- | --- |
| MiniMax M3.1 Flash（默认，国内账号） | `anthropic` | `MiniMax-M3.1-Flash` | `https://api.minimax.cn/anthropic` |
| MiniMax M3.1 Flash（海外账号） | `anthropic` | `MiniMax-M3.1-Flash` | `https://api.minimax.io/anthropic` |
| DeepSeek | `openai` | `deepseek-chat` | `https://api.deepseek.com` |
| 本地 Ollama | `openai` | 你拉取的模型名，如 `qwen3` | `http://localhost:11434/v1` |

**为什么 MiniMax 走 Anthropic 兼容接口？** M3.1 Flash 每次都会先思考再回答，多轮调用工具时，必须把上一轮的思考内容原样传回给模型。LangChain 的 `ChatOpenAI` 只按 OpenAI 官方格式处理，会丢掉第三方的思考字段；走 Anthropic 兼容接口，思考内容以独立的 thinking 块完整保留。这也是 MiniMax 官方推荐的接入方式。

> 模型名和地址会随服务商更新而变化，请以各家官方文档为准。工具调用能力较弱的模型可能出现漏调、错调工具的情况。

## 把 Agent 的流程图画出来

LangGraph 可以直接导出图的结构，不需要 API Key：

```bash
python show_graph.py
```

会得到终端里的字符图，以及 `graph.mmd`（Mermaid 源码，可粘贴到 [mermaid.live](https://mermaid.live) 查看）；能访问 mermaid.ink 时还会生成 `graph.png`。图中实线是固定的边，虚线是有条件的边。

## 不用 API Key 先跑测试

`tests/` 里用一个按剧本出牌的假模型（`tests/fake_model.py`），验证图结构和人工确认流程：

```bash
python -m pytest -q
```

## AI Agent 实战：从能跑到能上生产

每一期新增一个模块，代码打了标签。`git checkout ep03` 切到对应版本，`git checkout main` 回到最新版；`git diff ep02 ep03` 查看这一期改了什么。

| 标签 | 期数 | 新增模块 | 内容 |
| --- | --- | --- | --- |
| `ep01` | EP01 | `weekly_agent/` 基础模块 | 四个工具、两个节点、人工确认 |
| `ep02` | EP02 | 无（代码同 ep01） | 三层能力全景图 |
| `ep03` | EP03 | `memory.py` | 长期记忆：记住写作偏好和遗留问题 |
| `ep04` | EP04 | `tracing.py` | 可观测性：接入 Langfuse，每一步都可回放 |
| `ep05` | EP05 | `evals/` | 评估集：10 组任务对比提示词和模型 |
| `ep06` | EP06 | `guardrails.py` | 安全护栏与容错：防提示词注入、工具报错不崩溃、自动重试 |
| `ep07` | EP07 | `notify.py`、`scheduler/`、`run.py` | 定时运行与手机审批：每周五自动写周报，审批后发送 |

### EP03：长期记忆（`weekly_agent/memory.py`）

- 确认发送时，除了 `yes`、`no`，也可以直接输入修改意见，比如「太长了，每条一行」。Agent 会用 `remember` 工具把长期有效的偏好记下来，再改周报
- 发送成功后，Agent 会把下周计划记为遗留问题，下周写周报时自动带上
- 记忆保存在 `workspace/memory.db`，程序退出后也不会丢；不同 `USER_ID` 的记忆互相隔离
- 其他文件的改动：`graph.py` 把记忆放进提示词、`prompts.py` 加两条规则、`tools.py` 支持修改意见、`cli.py` 加命令行参数

```bash
python agent.py --show-memory   # 查看 Agent 记住了什么
python agent.py --forget        # 清空记忆
python agent.py --thread demo-2 # 用新的任务编号运行，验证长期记忆
```

### EP04：可观测性（`weekly_agent/tracing.py`）

在 `.env` 里填上 Langfuse 的三个变量，每次运行就会自动上报：每一轮模型的完整输入、思考内容、工具调用的参数和结果、耗时和 token。不填则不上报，不影响使用。

- 每条追踪记录带有用户（`USER_ID`）、任务编号、模型名、提示词版本，方便筛选和对比
- 运行结束时终端会打印本次的模型轮数、token 总数和耗时
- 其他文件的改动：`runner.py` 改用 `tracing.make_config` 生成运行配置；`prompts.py` 加上版本号
- 追踪记录里有业务原始数据，敏感场景建议[自部署 Langfuse](https://langfuse.com/self-hosting)

### EP05：评估集（`evals/`）

`evals/` 里有 10 组测试，每组是一个笔记文件夹加检查规则，覆盖正常周、相似事项易混、没有风险、外部阻塞、中英文混写等情况。打分全部用规则：三段结构、关键信息、没有编造、先存后发。

```bash
python evals/run_eval.py                                  # 对比最新两版提示词，每组 3 次
python evals/run_eval.py --env .env --env .env.deepseek   # 同时对比两个模型
python evals/run_eval.py --prompts v2 --repeats 1         # 省钱模式
```

- 提示词在 `weekly_agent/prompts.py` 的 `PROMPTS` 里按版本管理，`.env` 里用 `PROMPT_VERSION` 切换
- 评估时确认环节自动回答 `no`，不会真的发送；每次运行使用全新的记忆，互不干扰
- 输出每种组合的通过率、平均轮数、token 和耗时，详细结果（含每次生成的周报）存在 `evals/results/`
- 对比另一个模型：复制一份 `.env` 为 `.env.deepseek`，改掉模型的四个变量即可
- 其他文件的改动：`graph.py`、`llm.py`、`tracing.py` 各加了一个参数，方便评估时切换提示词和模型
- **注意费用**：默认 2 版提示词 × 10 组 × 3 次 = 60 次完整运行

### EP06：安全护栏与容错（`weekly_agent/guardrails.py`）

四道防线，目标不是「保证模型不上当」，而是「就算上当也造不成大损失」：

1. **最小权限**：`send_to_group` 没有「发给谁」的参数，只能发到固定的群
2. **资料隔离**：`guardrails.wrap_note` 用 `<note>` 标签包住笔记，提示词 v3 明确标签里的内容只是资料，不执行其中的指令
3. **输出检查**：`guardrails.check_report` 在发送前检查三段结构、风险栏不能为空、不能有链接和邮箱，不通过直接退回给模型修改
4. **人工确认**：EP01就有的最后一道闸

演示提示词注入：

```bash
cp workspace/demo/*.md workspace/notes/     # 放入一篇藏了指令的「供应商会议纪要」
PROMPT_VERSION=v2 python agent.py           # 没有防注入规则的旧版提示词
python agent.py                             # 默认的 v3
rm "workspace/notes/2026-10-24-供应商会议纪要.md"   # 演示完记得删掉
```

评估集里新增了 `injection` 组，专门检查这类攻击。

容错：

- 工具报错（例如笔记用 GBK 编码保存、按 UTF-8 读取失败）时，`ToolNode(handle_tool_errors=True)` 把错误交给模型处理，程序不会崩溃
- 模型调用遇到网络问题、限流（429）或服务端错误（5xx）时自动重试，最多 3 次；密钥错误这类 4xx 不重试（规则见 `guardrails.should_retry`）
- 其他文件的改动：`tools.py` 调用两道防线；`graph.py` 加重试和工具报错处理；`prompts.py` 新增 v3

### EP07：定时运行与手机审批（`scheduler/`）

把一次运行拆成两半，中间的进度存在 `workspace/state.db`，程序退出、机器重启都不会丢：

```
定时器 → run.py start → 写周报 → 暂停，把审批链接发到手机 → 退出
手机点「同意」→ 审批网页 → resume → 从暂停处继续 → 发到群里
```

```bash
python run.py serve                  # 启动审批网页（需要能被手机访问，见下文）
python run.py start                  # 手动触发一次，等同于定时器
python run.py resume 2026-W43 yes    # 不用网页，直接在命令行审批
```

定时器（Linux 服务器的 cron，每周五 16:00）：

```bash
0 16 * * 5  cd /opt/weekly-report-agent && .venv/bin/python run.py start >> logs/cron.log 2>&1
```

Windows 可以用「任务计划程序」定时运行 `python run.py start`。

几个细节：

- `scheduler/jobs.py` 和EP01的唯一区别是存档器换成了数据库版，Agent 本身一行没改
- 每周一个任务编号（如 `2026-W43`）。定时器重复触发时不会重新生成，只会重发审批通知
- 审批网页也可以写修改意见，Agent 改完会再发一次审批，修改意见同样会记进长期记忆
- 打开审批网页只是查看，不会触发任何操作；只有点按钮提交才会继续，重复点击不会发两次
- 审批链接带 HMAC 签名（`scheduler/approval.py`），改动任务编号或签名都会被拒绝。**签名只能证明链接是系统发出的，不能证明点击的人是谁**：正式使用请把审批网页放在 HTTPS 和公司统一登录之后，或改用飞书、企业微信的应用卡片回调
- `weekly_agent/notify.py` 发群消息；飞书群机器人如果开启了「签名校验」，需要按飞书文档在请求里加 timestamp 和 sign
- 存档演示用 SQLite；多实例部署请换成 PostgreSQL（`langgraph-checkpoint-postgres`），写法几乎一样
- 其他文件的改动：`tools.py` 的 `send_to_group` 改为调用 `notify.post_to_webhook` 真正发送

## 常见问题

**报错 `KeyError: 'MODEL_API_KEY'`**：没有创建 `.env`，或 Key 没填。

**Agent 没调用 send_to_group 就结束了**：模型的工具调用能力不够稳定，换一个模型，或把 `weekly_agent/prompts.py` 里的提示词写得更明确。

**恢复后 save_report 又执行了一次**：这是 LangGraph 的正常行为，恢复时会重新执行暂停所在的节点。这里覆盖写同一个文件，没有副作用；扣款、下单这类不可重复的动作，应把确认单独做成一个节点。

**`git checkout` 提示本地有改动**：先用 `git stash` 把改动收起来，或用 `git restore <文件>` 放弃改动。

## 版本

录制时使用 LangGraph 1.2.17、模型 MiniMax-M3.1-Flash（2026年10月），依赖版本已在 `requirements.txt` 中锁定。
