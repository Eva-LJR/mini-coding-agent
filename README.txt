Mini Coding Agent

Git仓库地址：请在创建公开GitHub或Gitee仓库后填写

项目简介：本项目是一个从零实现的命令行编程智能体，不使用LangChain、OpenAI Agents SDK、AutoGen等Agent框架。程序直接使用模型原生tool calling，自行管理对话历史、工具调用、执行结果回传和循环终止。Agent可以列出和读取工作区文件、完整写入或局部修改文件，并在用户确认后运行本地命令。

环境与安装：需要Python 3.10或以上版本，以及支持tool calling的OpenAI-compatible模型接口。执行“pip install -r requirements.txt”，复制“.env.example”为“.env”，填写MODEL_API_KEY、MODEL_BASE_URL和MODEL_NAME。真实密钥不会进入Git仓库。

运行方法：执行“python main.py --workspace ./demo_workspace”，然后输入任务。也可通过“--task”直接传入任务。默认每条命令需要人工确认；只在可信演示目录中使用“--yes”自动批准。

特色与安全：实现了工作区路径越界保护、敏感文件拒绝、命令超时、最大循环轮数、文件及输出大小限制、错误结果回传、敏感环境变量移除。测试命令为“python -m unittest discover -s tests -v”。项目仅为最小教学实现，命令执行不是完整沙箱，实际使用仍应人工确认或放入隔离容器。
