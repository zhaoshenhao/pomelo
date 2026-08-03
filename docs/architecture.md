# 项目架构

## 概述

Pomelo 是一个基于文档的学习平台，采用前后端分离架构。

## 系统架构图

```
┌─────────────┐     HTTP/JSON     ┌──────────────┐     MySQL     ┌─────────┐
│   Nuxt 3    │ ←──────────────→ │   FastAPI     │ ←──────────→ │  MySQL  │
│  (前端)     │   /api/*         │   (后端)      │   SQLAlchemy │  (数据库)│
└─────────────┘                   └──────┬───────┘              └─────────┘
                                         │
                               ┌─────────┴─────────┐
                     ┌─────────┴──────┐  ┌─────────┴──────┐
                     │ DeepSeek API   │  │  文件系统      │
                     │ (AI 服务)     │  │  /docs/        │
                     └────────────────┘  └────────────────┘
```

## 后端架构

### 分层设计

```
routers/         ← 请求入口，参数验证，调用服务层
    │
services/        ← 业务逻辑 (AI, 文档解析, 文件管理)
    │
models/          ← SQLAlchemy ORM 模型
schemas/         ← Pydantic 请求/响应模型
dependencies/    ← 认证、授权依赖注入
```

### 数据模型关系

```
User ─────┐                     RewriteStyle (改写风格)
          │
          │ uploads
          ▼
Document ◄────────────────── DocumentLibrary (文档库)
  │
  │ approval process
  ▼
ApprovalProcess ──────< ApprovalStep (审批步骤)
  │
  ▼
BackupRecord (备份记录)
```

## 前端架构

```
pages/           ← 页面组件 (路由)
  │
stores/          ← Pinia 状态管理
  │
plugins/axios.ts ← HTTP 客户端 (JWT 拦截器)
```

## 文档管理流程

```
上传 → /docs/stage/          暂存区
    ↓
创建审批流程 (锁定)
    ↓
Step 1: 语义检查 (AI 全文对比)
    ↓
Step 2: 内容审核 (拼写检查 / AI改写)
    ↓
Step 3: 最终预览
    ↓
Step 4: 确认执行
    ├── ZIP 备份 → /docs/backup/
    └── 格式转换 → /docs/<库名>/
```
