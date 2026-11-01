# 周报助手：用 LangGraph 写一个真正能干活的 AI Agent

「Rocky 的第二引擎」· **AI Agent 实战系列配套示例**。

以周报助手为贯穿案例，从读取笔记、调用工具和人工确认开始，逐步加入长期记忆、可观测性、评估、安全护栏、定时审批与多步骤流水线。通过一个持续演进的项目，理解如何把 AI Agent 做成能解决实际问题的工具。

Agent 读取工作笔记、整理并保存周报，在发送前暂停，等待人工确认。基础版本模拟发送；EP07 起提供真实群机器人接入。

## 系列与代码版本

`main` 保存最新的系列代码，各期标签保留对应视频的代码快照。可以从 EP01 入门，也可以按主题查看后续版本。

| 标签 | 主题 | 主要内容 |
| --- | --- | --- |
| `ep01` | 基础 Agent | 工具调用、思考与执行循环、人工确认 |
| `ep02` | 能力全景 | 三层能力全景图，代码与 EP01 相同 |
| `ep03` | 长期记忆 | 写作偏好与遗留问题 |
| `ep04` | 可观测性 | Langfuse 追踪、耗时与 token 用量 |
| `ep05` | 评估集 | 对比提示词与模型表现 |
| `ep06` | 安全护栏与容错 | 资料隔离、输出检查、错误处理与重试 |
| `ep07` | 定时运行与手机审批 | 持久化进度、审批网页、群机器人接入 |
| `ep08` | 多步骤流水线 | 规划、并行小结、撰写、审核、确认与发送 |

```bash
git switch --detach ep01   # 查看第一期录制代码；换成 ep03 等可查看其他期
git diff ep02 ep03         # 比较相邻两期的改动
git switch main            # 回到系列最新版
```

切换版本后，重新安装该版本的依赖，并参考该版本的 `.env.example`。旧标签保留录制时的代码与说明，可能与后续整理版存在差异。

## 项目结构

基础代码按功能拆分如下，后续各期在此基础上增加模块。检出不同标签时，实际文件和可用命令会有所不同。

```
weekly-report-agent/
├── agent.py              入口：python agent.py
├── show_graph.py         把 Agent 的流程图画出来
├── weekly_agent/
│   ├── config.py         配置：路径和 .env
│   ├── llm.py            模型：Agent 的「大脑」
│   ├── prompts.py        提示词：Agent 的「工作说明书」
│   ├── tools.py          工具：Agent 的「手」（读笔记、存周报、发群消息）
│   ├── graph.py          图：两个工作节点，用条件路由连接大脑和手
│   ├── runner.py         运行：执行图，遇到暂停就问人
│   ├── display.py        显示：用颜色和边框展示每一步（rich）
│   └── cli.py            命令行入口
├── workspace/notes/      5 篇虚构的工作笔记
└── tests/                不需要 API Key 的离线测试
```

读代码建议按这个顺序：`tools.py` → `prompts.py` → `llm.py` → `graph.py` → `runner.py`。

后续模块包括：`memory.py`（EP03）、`tracing.py`（EP04）、`evals/`（EP05）、`guardrails.py`（EP06）、`notify.py` 与 `scheduler/`（EP07）、`pipeline.py`（EP08）。请在对应标签或 `main` 中查看。

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
# 默认获取系列最新版；跟随视频学习时，可先执行 git switch --detach ep01
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env    # 然后在 .env 里填入你的 API Key
python agent.py
```

运行后输入任务，或直接回车使用默认任务。终端会显示工具调用和待确认的周报；输入 `yes` 确认，输入 `no` 取消，EP03 起还支持输入修改意见。基础版本只模拟发送；EP07 起的真实发送需要配置群机器人。

样例笔记均为虚构数据。你可以替换 `workspace/notes/` 下的 Markdown 文件；读取目录内全部笔记的基础流程不会自动筛选日期。基础循环版在确认前保存 `workspace/output/weekly.md`；EP08 流水线版在确认发送后保存。基础运行的暂停进度仅保存在内存中，EP07 的定时审批入口使用数据库保存进度。

## 换成其他模型

只需修改 `.env`，代码不用动。默认使用 MiniMax-M3.1-Flash：

| 模型 | MODEL_PROTOCOL | MODEL_NAME | MODEL_BASE_URL |
| --- | --- | --- | --- |
| MiniMax M3.1 Flash（默认，国内账号） | `anthropic` | `MiniMax-M3.1-Flash` | `https://api.minimax.cn/anthropic` |
| MiniMax M3.1 Flash（海外账号） | `anthropic` | `MiniMax-M3.1-Flash` | `https://api.minimax.io/anthropic` |
| DeepSeek | `openai` | `deepseek-chat` | `https://api.deepseek.com` |
| 本地 Ollama | `openai` | 你拉取的模型名，如 `qwen3` | `http://localhost:11434/v1` |

默认配置使用 Anthropic 兼容接口，以保留多轮工具调用中的 thinking 内容。接入其他模型时，请同时设置协议、模型名、地址和密钥。

> 模型名和地址会随服务商更新而变化，请以各家官方文档为准。工具调用能力较弱的模型可能出现漏调、错调工具的情况。

## 把 Agent 的流程图画出来

LangGraph 可以直接导出图的结构，不需要 API Key：

```bash
python show_graph.py
```

默认仅生成终端字符图和 `graph.mmd`，不访问在线绘图服务。需要 PNG 时运行 `python show_graph.py --png`，会通过 mermaid.ink 在线渲染。Mermaid 源码也可粘贴到 [mermaid.live](https://mermaid.live) 查看。实线是固定边，虚线是条件边。

## 不用 API Key 先跑测试

`tests/` 里用一个按剧本出牌的假模型（`tests/fake_model.py`），验证图结构和人工确认流程：

```bash
pip install -r requirements-dev.txt  # 若所选旧版本没有此文件，执行 pip install pytest
python -m pytest -q
```

当前整理版的测试输出写入临时目录；旧标签的测试行为以对应代码为准。

## 常见问题

**提示填写 `MODEL_API_KEY`**：没有创建 `.env`，或 Key 没填。

**Agent 没调用 send_to_group 就结束了**：模型的工具调用能力不够稳定，换一个模型，或把 `weekly_agent/prompts.py` 里的提示词写得更明确。

**恢复后 save_report 又执行了一次**：这是 LangGraph 的正常行为，恢复时会重新执行暂停所在的节点。这里覆盖写同一个文件，没有副作用；扣款、下单这类不可重复的动作，应把确认单独做成一个节点。

**切换版本提示本地有改动**：先提交自己的改动，或用 `git stash` 暂存，再切换分支或标签。

## 提交范围

保留源码、离线测试、虚构笔记和 `.env.example`。本地密钥、IDE / AI 工具配置、数据库、生成周报、系统文件及 `assets/branding/` 品牌素材已加入 `.gitignore`，不随教学代码发布。

## 版本

录制时使用 LangGraph 1.2.17、模型 MiniMax-M3.1-Flash（2026年10月）。运行依赖以所选版本的 `requirements.txt` 为准；当前整理版将测试依赖单独放在 `requirements-dev.txt`。
