提示词主题：开发“巡游梦境”小程序原型（FastAPI + SQLite + HTML）

1. 项目概述
请帮我开发一个名为“巡游梦境”的小程序后端及前端演示页面。

核心功能：用户输入梦境描述，系统将其存入数据库，并预留“内容精炼”与“内容扩充”的 AI 处理接口。

设计原则：架构简洁（KISS原则），适合新手快速部署，代码结构清晰，方便后期扩展。

2. 数据库设计优化（SQLite）
请按以下结构设计数据库，并使用 SQLAlchemy (Python ORM) 实现：

User 表：id (PK), username, created_at。

DreamRecord 表：

id (PK), user_id (FK), record_date (记录日期)。

raw_content (原始记录)。

refined_content (精炼内容，初始为空)。

expanded_content (扩充内容，初始为空)。

status (处理状态：pending/processing/completed)。

3. 技术栈与架构要求
后端：使用 FastAPI。需要包含以下 API 接口：

POST /dreams：接收梦境文字并存入数据库。

GET /dreams/{user_id}：获取该用户所有的梦境记录。

AI 接口预留：编写两个函数 process_refine(text) 和 process_expand(text)。目前仅需返回占位符文字（例如 "Refining..."），并标注出我未来接入大模型的位置。

前端：提供一个单文件 index.html。

使用原生的 HTML5 和 JavaScript (Fetch API)。

UI 简洁，包含一个输入框、提交按钮以及一个展示历史记录的列表卡片。

数据库：使用异步 SQLAlchemy 驱动或标准的 SQLite 连接，确保代码可以直接运行生成 .db 文件。

4. 输出要求
项目目录结构：告诉我要创建哪些文件夹和文件。

后端代码：包含 main.py 和必要的模型定义。

前端代码：完整的 index.html 代码。

运行指南：详细说明如何安装依赖、如何启动后端以及如何访问前端。
