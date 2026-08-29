# Mini Coding Agent

这是一个从零实现的命令行编程智能体。它不依赖 LangChain、OpenAI Agents SDK、AutoGen、CrewAI 等 Agent 框架，而是直接使用模型原生 tool calling，自行管理对话历史、工具执行和循环终止。

## 运行机制

1. 将用户任务、系统提示词和工具定义发送给模型。
2. 模型选择读取文件、修改文件或运行命令。
3. 本地程序验证并执行工具，把真实结果加入对话历史。
4. 模型根据结果继续决策，直到返回最终答案或达到最大轮数。

## 功能

- 递归列出工作区文件；
- 读取带行号的 UTF-8 文本；
- 创建、完整写入或局部替换文件；
- 经用户确认后运行本地命令；
- 路径越界保护、文件大小限制、命令超时和输出截断；
- 执行子进程时移除名称中含 KEY、TOKEN、SECRET、PASSWORD 的环境变量；
- 文件工具隐藏并拒绝访问 `.env`、私钥和常见凭据文件；
- 最大 Agent 轮数保护和工具错误反馈。

## 环境

- Python 3.10 或更高版本；
- 支持原生 tool calling 的 OpenAI-compatible 模型接口；
- Windows、macOS 或 Linux。

## 安装

```bash
python -m venv .venv
```

Windows：

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS/Linux：

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`：

```dotenv
MODEL_API_KEY=你的密钥
MODEL_BASE_URL=接口地址
MODEL_NAME=支持工具调用的模型名称
```

`.env` 已被 `.gitignore` 忽略。请勿将密钥放入仓库、README、截图或视频。

## 运行

交互输入任务：

```bash
python main.py --workspace ./demo_workspace
```

直接给出任务：

```bash
python main.py --workspace ./demo_workspace --task "运行测试，定位并修复错误，确保全部测试通过"
```

默认情况下，每条本地命令都需要人工确认。只应在完全可信的演示工作区中使用 `--yes`：

```bash
python main.py --workspace ./demo_workspace --yes --task "运行测试，定位并修复错误，确保全部测试通过"
```

## 测试

项目自身的离线测试不需要 API Key：

```bash
python -m unittest discover -s tests -v
```

演示项目初始包含一个故意设置的错误，可先验证失败：

```bash
cd demo_workspace
python -m unittest -v
```

Agent 修复演示项目后，可以通过 Git 恢复演示文件，再次录制演示。恢复前请确认其中没有需要保留的个人修改。

## 设计边界

本项目是教学和考核用途的最小实现，不是完整安全沙箱。路径检查能限制文件工具，但终端命令本身仍可能访问工作区外资源，因此默认要求人工确认。在生产环境中应把命令执行放入权限受限的容器或虚拟机。
