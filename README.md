# next-api

下一代 AI API 聚合网关，作为 [new-api](https://github.com/Calcium-Ion/new-api) 的下游适配层。

## 设计原则

- **OpenAI 兼容**：所有端点暴露标准 OpenAI 格式接口，可直接被 new-api 调用
- **不做计费**：用户管理、计费、限流由 new-api 完成，本项目只做厂商聚合
- **不依赖 meutils**：完全独立的代码库，仅依赖 fastapi/httpx 等标准库
- **多人协作友好**：每个厂商一个文件，新增厂商无需改动主架构
- **可插拔**：通过注册表管理"模型→厂商"映射

## 目录结构

```
next-api/
├── main.py                      # 入口
├── pyproject.toml               # 依赖
├── .env.example                 # 配置模板
│
├── app/
│   ├── core/                    # 框架基础设施
│   │   ├── app.py               # FastAPI 工厂
│   │   ├── registry.py          # 模型→厂商 注册表
│   │   ├── auth.py              # API Key 认证
│   │   ├── errors.py            # 错误转 OpenAI 格式
│   │   ├── streaming.py         # SSE 流式响应工具
│   │   └── http.py              # HTTP 客户端封装
│   │
│   ├── schemas/                 # 请求/响应 schema
│   │   ├── chat.py              # ChatRequest / ChatResponse
│   │   ├── image.py             # ImageRequest
│   │   ├── video.py             # VideoRequest / VideoTaskResponse
│   │   └── common.py            # 通用类型
│   │
│   ├── routes/                  # 路由层（极薄）
│   │   ├── chat.py              # POST /v1/chat/completions
│   │   ├── images.py            # POST /v1/images/generations
│   │   └── videos.py            # POST /v1/videos + GET /v1/videos/{id}
│   │
│   └── vendors/                 # 厂商实现（每厂商一个文件）
│       ├── base.py              # BaseVendor 抽象类
│       └── seedance.py          # 火山方舟 Seedance（视频）
│
└── tests/
    └── vendors/
        └── test_seedance.py
```

## 新增厂商流程

1. 在 `app/vendors/xxx.py` 写一个继承 `BaseVendor` 的类
2. 在 `app/core/registry.py` 加一行 `registry.register(...)`
3. 完成

## 启动

```bash
# 本地开发
uvicorn main:app --reload --port 8000

# 生产部署
gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 2
```

## 配置

复制 `.env.example` 为 `.env` 并填入：

```bash
# new-api 注册的下游 API Key（new-api 调用本服务时使用）
DOWNSTREAM_API_KEY=sk-xxx

# 各厂商上游 Key（也可以在 new-api 中配置后通过 Authorization 头传入）
SEEDANCE_API_KEY=ark-xxx
```
# 更新日志
1. gpt-image-2 端口
- 文生/图生 统一到 文生端口上，并且添加对象存储，支持返回url
