# 周报助手：用 LangGraph 写一个真正能干活的 AI Agent

Agent 自动读取本周工作笔记、整理成周报、保存为文件，**在发送到群之前暂停，等你确认**。

配套视频：【视频链接】

## 项目结构

代码按功能拆成几个模块，每个文件只做一件事：

```
weekly-report-agent/
├── agent.py              入口：python agent.py
├── show_graph.py         把 Agent 的流程图画出来
├── weekly_agent/
│   ├── config.py         配置：路径和 .env
│   ├── llm.py            模型：Agent 的「大脑」
│   ├── prompts.py        提示词：Agent 的「工作说明书」
│   ├── tools.py          工具：Agent 的「手」（读笔记、存周报、发群消息）
│   ├── memory.py         记忆：跨任务的长期记忆（EP03）
│   ├── tracing.py        追踪：接入 Langfuse，统计用量（EP04）
│   ├── graph.py          图：两个节点、三条边，把大脑和手连起来
│   ├── runner.py         运行：执行图，遇到暂停就问人
│   ├── display.py        显示：用颜色和边框展示每一步（rich）
│   └── cli.py            命令行参数
├── workspace/notes/      5 篇虚构的工作笔记
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

运行后你会看到 Agent 每一步调用的工具，最后它会停下来显示待发送的周报，输入 `yes` 发送，输入 `no` 取消。生成的周报保存在 `workspace/output/weekly.md`。

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

## 进阶系列：从能跑到能上生产

每一期新增一个模块，代码打了标签。`git checkout ep03` 切到对应版本，`git checkout main` 回到最新版；`git diff ep02 ep03` 查看这一期改了什么。

| 标签 | 期数 | 新增模块 | 内容 |
| --- | --- | --- | --- |
| `ep01` | EP01 | `weekly_agent/` 基础模块 | 四个工具、两个节点、人工确认 |
| `ep02` | EP02 | 无（代码同 ep01） | 三层能力全景图 |
| `ep03` | EP03 | `memory.py` | 长期记忆：记住写作偏好和遗留问题 |
| `ep04` | EP04 | `tracing.py` | 可观测性：接入 Langfuse，每一步都可回放 |

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

## 常见问题

**报错 `KeyError: 'MODEL_API_KEY'`**：没有创建 `.env`，或 Key 没填。

**Agent 没调用 send_to_group 就结束了**：模型的工具调用能力不够稳定，换一个模型，或把 `weekly_agent/prompts.py` 里的提示词写得更明确。

**恢复后 save_report 又执行了一次**：这是 LangGraph 的正常行为，恢复时会重新执行暂停所在的节点。这里覆盖写同一个文件，没有副作用；扣款、下单这类不可重复的动作，应把确认单独做成一个节点。

**`git checkout` 提示本地有改动**：先用 `git stash` 把改动收起来，或用 `git restore <文件>` 放弃改动。

## 版本

录制时使用 LangGraph 1.2.17、模型 MiniMax-M3.1-Flash（2026年10月），依赖版本已在 `requirements.txt` 中锁定。
