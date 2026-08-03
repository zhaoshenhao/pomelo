# Pomelo 实现计划

> 最后更新：2026-08-02 · 测试通过 83/83

## 实施进度总览

| 模块 | 后端 | 前端 | 测试 | 文档 |
|------|------|------|------|------|
| 用户系统 | ✅ | ✅ | ✅ | ✅ |
| 部门管理 | ✅ | ✅ | ✅ | — |
| 文档库管理 | ✅ | ✅ | ✅ | ✅ |
| 审批流程 | ✅ | ✅ | ✅ | ✅ |
| AI 服务 + 改写风格 | ✅ | ✅ | ✅ | ✅ |
| 错误处理 + 日志 | ✅ / ⏳ | — | ✅ | ✅ |
| 健康检查 | ✅ | — | — | ✅ |
| **云端部署** | ⏳ | ⏳ | ⏳ | ⏳ |

---

## 未完成项目清单

### 待实施（P0: 部署必需）

**后端：Redis 会话**
- [x] `backend/app/config.py`：新增 `REDIS_HOST/PORT/DB/PASSWORD/SESSION_TTL`、`CORS_ORIGINS`
- [x] `backend/app/services/redis_store.py`（新建）：异步 Redis 客户端 + session CRUD
- [x] `backend/app/dependencies/auth.py`：`create_access_token` 加 `jti`；`get_current_user` 校验 session
- [x] `backend/app/routers/auth.py`：`POST /auth/logout`；`refresh` 轮换 + 复用检测
- [x] `backend/.env.example`：补全 Redis/CORS 占位符
- [x] `backend/requirements.txt`：追加 `redis`

**后端：容器化 + k8s**
- [ ] `backend/Dockerfile`：`python:3.13-slim`，uvicorn 监听 0.0.0.0:8080
- [ ] `k8s/pomelo-backend.yaml`：Deployment + Service(443→8080) + PVC + Probe + Ingress

**前端：运行时配置**
- [ ] `frontend/nuxt.config.ts`：`runtimeConfig.public.apiBase`
- [ ] `frontend/app/plugins/axios.ts`：`baseURL` 读 runtime config（`useRuntimeConfig()`）
- [ ] `frontend/app/stores/auth.ts`：`logout` 调 `POST /auth/logout`
- [ ] `frontend/.env.local` + `frontend/.env.example`：`NUXT_PUBLIC_API_BASE`

**部署脚本**
- [ ] `deploy/oss-upload.sh`：`pnpm generate` + `ossutil cp` 同步 OSS

**测试**
- [x] `backend/tests/test_sessions.py`：登录→刷新轮换→登出→吊销→复用检测（7 passed）

**日志配置与结构化日志（P1）**
- **后端：**
  - [x] `backend/app/config.py`：`LOG_LEVEL`、`LOG_FORMAT`（json/text）
  - [x] `backend/app/main.py`：`logging.config.dictConfig` + 请求日志中间件 + Redis lifespan
  - [x] `backend/app/error_handler.py`：`logger.exception(...)` 记录堆栈跟踪
  - [x] `backend/app/services/*`：各服务接入 `logging.getLogger`
  - [x] `backend/.env.example`：`LOG_LEVEL`/`LOG_FORMAT` 占位
- **前端：**
  - [x] 新建 `frontend/app/utils/logger.js`：共享 logger 工具（结构化 JSON 输出）
  - [x] 新建 `frontend/app/plugins/logger.ts`：Nuxt 日志插件（`$logger` 注入）
  - [x] `frontend/app/plugins/axios.ts`：axios 拦截器记录请求/响应错误日志
  - [x] `ReadonlyMarkdown.vue` / `RewriteDiffEditor.vue`：`console.error` → `logger.error`

### 待确认参数（阻塞部署）

- [ ] OSS bucket 名称 + region
- [ ] OSS 访问模式（公有读 + CDN / 内网转发）
- [ ] Ingress 类型（阿里云 ALB 或 Nginx）
- [ ] ossutil 凭据方式（AK/SK 环境变量 / 配置文件）
- [ ] k8s 命名空间 + StorageClass

---

## 架构概要

### 技术栈
- **后端**：Python 3.11+, FastAPI + SQLAlchemy 2.0 (async) + MySQL
- **前端**：Vue 3 + Nuxt 3 (SSG), Pinia, Axios, CodeMirror 6
- **AI**：DeepSeek-v4-pro (OpenAI-compatible API, async client)
- **认证**：JWT (python-jose + passlib bcrypt 4.2.x)
- **文件存储**：本地 `storage/` 目录 (docs, stage, backup)

### 数据模型（6 个）

| 模型 | 表 | 用途 |
|------|-----|------|
| `User` | `users` | 用户 (admin/teacher/student) |
| `Department` | `departments` | 部门 |
| `DocumentLibrary` | `document_libraries` | 文档库 |
| `Document` | `documents` | 库内已入库文档 (path, filename) |
| `StageDocument` | `stage_documents` | 审批暂存文档 (单模型状态机) |
| `RewriteStyle` | `rewrite_styles` | AI 改写风格 (name + prompt) |

**StageDocument 状态机**：`new` → `content_review` → `rewrite` → `preview` → `completed` / `deleted`

### 目录结构

```
backend/
├─ app/
│  ├─ config.py              # Pydantic Settings (.env)
│  ├─ database.py             # SQLAlchemy async engine + session
│  ├─ error_handler.py        # 全局异常 → {code, message, request_id}
│  ├─ main.py                 # FastAPI + CORS + lifespan
│  ├─ dependencies/
│  │  └─ auth.py              # JWT, get_current_user, role guards
│  ├─ models/
│  │  ├─ __init__.py          # Base + 所有模型注册
│  │  ├─ user.py
│  │  ├─ department.py
│  │  ├─ document.py          # DocumentLibrary + Document
│  │  ├─ stage_document.py
│  │  └─ rewrite_style.py
│  ├─ routers/
│  │  ├─ auth.py              # /auth/*
│  │  ├─ users.py             # /users/*
│  │  ├─ libraries.py         # /libraries/* + 文档 CRUD
│  │  ├─ departments.py       # /departments/*
│  │  ├─ approvals.py         # /approvals/* (审批流转)
│  │  └─ rewrite_styles.py    # /rewrite-styles/*
│  ├─ schemas/
│  │  ├─ common.py            # success_response()
│  │  ├─ user.py
│  │  ├─ document.py
│  │  ├─ department.py
│  │  ├─ approval.py
│  │  └─ rewrite_style.py
│  └─ services/
│     ├─ ai_service.py        # content_diff, grammar_rewrite, style_rewrite
│     ├─ document_parser.py   # 多格式 → markdown (txt/md/pdf/docx/xlsx/xls/pptx)
│     └─ file_service.py      # stage/backup/library 文件读写
├─ tests/                     # 9 个测试文件, 76 passed
├─ alembic/                   # 数据库迁移
├─ requirements.txt
├─ requirements-dev.txt
└─ .env / .env.example

frontend/ (Nuxt 3 SSG, srcDir=app/)
├─ nuxt.config.ts
├─ app/
│  ├─ plugins/axios.ts        # Axios 实例 (JWT 拦截器)
│  ├─ stores/auth.ts          # Pinia auth store
│  ├─ middleware/
│  │  ├─ auth.ts              # 路由守卫: 需登录
│  │  ├─ admin.ts             # 仅 admin
│  │  ├─ teacher.ts           # teacher 或 admin
│  │  └─ expired.global.ts    # 全局: token 过期处理
│  ├─ components/
│  │  ├─ MarkdownEditor.vue   # 编辑/预览切换, CodeMirror markdown + syntaxHighlighting
│  │  ├─ ReadonlyMarkdown.vue # 只读对比 (diff: 绿=added/黄=modified/红=removed)
│  │  ├─ RewriteDiffEditor.vue# 改写编辑 (三色 diff)
│  │  └─ ConfirmModal.vue     # 通用确认弹窗
│  ├─ utils/
│  │  └─ markdownHighlight.js # 彩色 Markdown 高亮样式 (CodeMirror)
│  ├─ pages/
│  │  ├─ login.vue
│  │  ├─ register.vue
│  │  ├─ profile.vue
│  │  ├─ index.vue
│  │  └─ admin/
│  │     ├─ users.vue
│  │     ├─ departments.vue
│  │     ├─ styles.vue
│  │     ├─ libraries/
│  │     │  ├─ index.vue
│  │     │  └─ [id].vue        # 上传/文档列表/审批列表 + 编辑面板
│  │     └─ approvals/
│  │        ├─ index.vue
│  │        └─ [id].vue         # 4 步审批流转
│  └─ assets/css/main.css
└─ .env / .env.example

docs/
├─ architecture.md
├─ api.md
├─ local-env.md
├─ deployment.md
└─ modules/
   ├─ user-system.md
   ├─ document-library.md
   ├─ approval.md
   └─ ai-service.md

storage/ (不提交 Git)
├─ docs/<library_dir>/       # 已入库文档 (.md)
├─ stage/<approval_id>/       # 审批暂存: origin.md, preview.md, metadata.json
└─ backup/<lib>-<sha256>.zip  # 备份 (SHA256 去重)
```

---

## Phase 1: 项目脚手架（✅ 完成）

### 1.1 依赖声明
- [x] `backend/requirements.txt`：fastapi, uvicorn, sqlalchemy 2.0, pymysql, aiomysql, cryptography, python-jose, passlib[bcrypt], bcrypt==4.2.1, python-multipart, PyMuPDF, python-docx, openpyxl, xlrd, python-pptx, alembic, pydantic-settings, email-validator, httpx, openai
- [x] `backend/requirements-dev.txt`：pytest, pytest-asyncio, httpx, ruff, mypy
- [x] `frontend/package.json`：nuxt 4, vue 3, pinia, axios, @codemirror/*, @lezer/highlight, codemirror, marked, highlight.js, diff, tailwindcss 4

### 1.2 配置管理
- [x] `backend/app/config.py`：Pydantic Settings 加载 `.env` (`APP_PORT`, `DB_*`, `JWT_*`, `DOCS_ROOT`, `DEEPSEEK_*`, `GRAMMAR_REWRITE_PROMPT`)
- [x] `backend/.env`（本地，不入库）/ `.env.example`（模板，空/占位符）

### 1.3 数据库
- [x] `app/database.py`：SQLAlchemy async engine + session，MySQL→aiomysql
- [x] Alembic 迁移配置 + 已执行 migration（`a1b2c3d4e5f6_add_stage_documents_and_rewrite_styles`）

### 1.4 应用入口
- [x] `app/main.py`：FastAPI + CORS(`http://localhost:3000`) + lifespan + 全局异常 handler
- [x] 路由注册：auth, users, libraries, departments, approvals, rewrite-styles（前缀 `/api`）
- [x] `GET /health` + `GET /ready`（健康/就绪探针）

### 1.5 前端基础
- [x] Pinia auth store（localStorage 持久化）
- [x] Axios 插件（JWT Bearer 拦截器 + 401 自动登出）

---

## Phase 2: 用户系统（✅ 完成）

### 2.1 数据模型
- [x] `User`：id, username, display_name, email, phone, department_id(FK), hashed_password, role(admin/teacher/student), is_active, created_at, updated_at
- [x] `Department`：id, name, parent_id(self FK), sort_order, created_at

### 2.2 认证路由（`/api/auth/*`）
- [x] `POST /register`：注册（首个用户自动 admin，后为 student）
- [x] `POST /login`：返回 access_token(30min) + refresh_token(7d) + 用户信息
- [x] `POST /refresh`：刷新 access token（无状态验证）
- [x] `GET /me`：当前用户信息
- [x] `PATCH /profile`：修改个人资料
- [x] `POST /change-password`：修改密码（旧密码验证）

### 2.3 用户管理路由（`/api/users/*`，Admin + Teacher）
- [x] `GET /users`：列表（分页 + 搜索）
- [x] `POST /users`：创建用户（Admin）
- [x] `GET /users/{id}`：详情
- [x] `PATCH /users/{id}`：更新（禁删最后一个 admin）
- [x] `PATCH /users/{id}/role`：修改角色
- [x] `PATCH /users/{id}/password`：重置密码
- [x] `DELETE /users/{id}`：删除（禁删 admin）

### 2.4 部门管理路由（`/api/departments/*`）
- [x] `GET/POST /departments`：列表 + 新建
- [x] `PATCH/DELETE /departments/{id}`：更新 / 删除

### 2.5 前端页面
- [x] `login.vue` / `register.vue` / `profile.vue`
- [x] `admin/users.vue`：用户 CRUD + 角色管理 + 密码重置
- [x] `admin/departments.vue`：部门树管理

### 2.6 认证基础设施
- [x] `app/dependencies/auth.py`：JWT 签发/验证、密码哈希、`get_current_user`、`require_admin`、`require_teacher_or_admin`
- [x] 前端 middleware：`auth`, `admin`, `teacher`, `expired.global`

### 2.7 测试（`test_auth.py`, `test_users.py`, `test_departments_and_users.py`）
- [x] 注册（成功/重复/缺字段）
- [x] 登录（成功/密码错误/不存在/禁用）+ token 签发
- [x] 刷新 token（过期/篡改）
- [x] 用户 CRUD（权限：admin/teacher/student）
- [x] 部门 CRUD
- [x] 角色切换 + 最后一个 admin 保护

---

## Phase 3: 文档库管理（✅ 完成）

### 3.1 数据模型
- [x] `DocumentLibrary`：id, name, description, directory(本地路径), created_by, created_at, updated_at
- [x] `Document`：id, library_id(FK), filename, path(完整路径), created_at

### 3.2 文档库路由（`/api/libraries/*`）
- [x] `POST /libraries`：创建 (Admin)
- [x] `GET /libraries`：全部列表
- [x] `GET /libraries/{id}`：详情
- [x] `PUT /libraries/{id}`：更新 (Admin)
- [x] `DELETE /libraries/{id}`：删除 (Admin, 清理文件)

### 3.3 文档操作路由
- [x] `GET /libraries/{id}/documents`：库内文档列表
- [x] `DELETE /documents/{id}`：删除库内文档
- [x] `GET /documents/{id}/content`：读取文档内容（Markdown）
- [x] `PUT /documents/{id}/content`：编辑保存文档内容

### 3.4 文件服务（`file_service.py`）
- [x] `sanitize_directory_name` / `sanitize_filename`（路径安全）
- [x] `get_library_root/directory/path`（目录管理）
- [x] `save_library_file` / `delete_library_files` / `list_library_files`
- [x] `backup_library`（SHA256 去重 zip）
- [x] stage 文件：`save_stage_file` / `read_stage_file` / `delete_stage_dir`
- [x] approval metadata：`read_approval_json` / `write_approval_json`

### 3.5 文档解析器（`document_parser.py`）
- [x] `convert_to_markdown(filepath)` — 统一入口，支持：`.txt`, `.md`, `.pdf`(PyMuPDF), `.docx`(python-docx), `.xlsx`/`.xls`(openpyxl/xlrd), `.pptx`

### 3.6 前端页面
- [x] `admin/libraries/index.vue`：文档库列表 + 新建/编辑弹窗（Admin）
- [x] `admin/libraries/[id].vue`：详情页
  - 上传文档（→ 审批流程）
  - 文档列表（查看和编辑 MarkdownEditor 面板、删除）
  - 审批列表（状态 tag、跳转审批详情、删除审批记录）

### 3.7 测试（`test_libraries.py`, `test_documents.py`, `test_services.py`）
- [x] 文档库 CRUD（正常/冲突/不存在/非 Admin 拒绝）
- [x] 文档上传（格式支持/不支持拒绝）
- [x] 文档编辑（`PUT /content` 更新保存 + 读写验证）
- [x] 文件服务（保存/删除/备份）
- [x] 文档解析（各格式转换）

---

## Phase 4: AI 服务 + 改写风格（✅ 完成）

### 4.1 AI 服务（`ai_service.py`，DeepSeek AsyncOpenAI）
- [x] `get_ai_client()`：懒加载全局 AI client
- [x] `content_diff(new_text, library_texts)`：全文语义差异分析（新增/冲突/重复）
- [x] `grammar_rewrite(text)`：拼写语法修正
- [x] `style_rewrite(text, prompt)`：按风格改写

### 4.2 改写风格路由（`/api/rewrite-styles/*`，Admin）
- [x] `POST/GET /rewrite-styles`：创建 / 列表
- [x] `PUT/DELETE /rewrite-styles/{id}`：更新 / 删除
- [x] 模型 `RewriteStyle`：id, name, prompt, created_by, created_at, updated_at

### 4.3 前端页面
- [x] `admin/styles.vue`：改写风格列表 + 新建/编辑/删除

### 4.4 测试（`test_services.py`）
- [x] 改写风格 CRUD
- [x] AI 测试在有 `DEEPSEEK_API_KEY` 时运行，无则跳过

---

## Phase 5: 审批流程（✅ 完成）

### 5.1 审批模型（`StageDocument` 单模型状态机）
- [x] `StageDocument`：id, library_id(FK), original_filename, file_type, stage_dir, status, created_by, created_at, updated_at
- [x] 状态流转：`new` → `content_review` → `rewrite` → `preview` → `completed` / `deleted`

### 5.2 审批路由（`/api/approvals/*`）
- [x] `POST /approvals`：创建审批（上传文件 → 转 markdown → 生成 `origin.md`/`preview.md` → 存 stage）
- [x] `GET /approvals`：审批列表（可选 library_id + status 过滤；默认过滤 completed/deleted）
- [x] `GET /approvals/{id}`：审批详情 + origin/preview 内容 + 库内文档列表 + metadata.json
- [x] `PUT /approvals/{id}/meta`：保存入库名称 + 内容策略 (content_choice: 新增/替换整个文档库/替换部分文档)
- [x] `POST /approvals/{id}/content-diff`：AI 生成内容差异对比 → status→`content_review`
- [x] `POST /approvals/{id}/rewrite`：AI 改写（语法/风格/自定义）→ 更新 preview.md → status→`rewrite`
- [x] `PUT /approvals/{id}/preview`：保存最终预览内容 → status→`rewrite`
- [x] `POST /approvals/{id}/confirm`：确认入库 → 备份 → 按 content_choice 写入文档库 → status→`completed`
- [x] `DELETE /approvals/{id}`：软删除（status→`deleted` + 清理 stage 目录）

### 5.3 前端审批详情页（`admin/approvals/[id].vue`，4 步 Tab）
1. **内容差异比较**：调用 AI content-diff，展示新内容/冲突/重复；有差异时显示「确认，进入下一步」按钮 → Tab1
2. **内容选择**：入库名称 + 内容策略（新增/替换整个文档库/替换部分文档）；保存后「确认，进入下一步」→ Tab2
3. **文字改写**：语法修正/按风格改写/自定义风格 + 改写编辑器；预览确认后「确认，进入下一步」→ Tab3
4. **预览并完成**：最终预览（marked+hljs 渲染）+ 确认入库

- [x] `admin/approvals/index.vue`：审批列表（含过滤、链接跳转）
- [x] `typeLabel` / `typeBadge` / `statusLabel` / `statusBadge`（文件类型/状态展示）
- [x] 编辑器组件：`ReadonlyMarkdown`（只读 diff 三色对比）、`RewriteDiffEditor`（改写编辑 diff）
- [x] MarkdownEditor 中的 `ConfirmModal` + MarkdownEditor 文档对话框

### 5.4 测试（`test_approvals.py`）
- [x] 审批创建（上传各格式）
- [x] 审批推进（content-diff → rewrite → confirm）
- [x] 审批取消（软删除）
- [x] 权限控制

---

## Phase 6: 错误处理 + 日志 + 可观测性（✅ 完成）

### 6.1 错误处理
- [x] `app/error_handler.py`：全局异常 handler → `{code, message, data, timestamp, request_id}`
- [x] `app/schemas/common.py`：`success_response()` 统一格式

### 6.2 日志
- [x] AI 服务结构化日志（`logging.getLogger`, request_id 传递）

### 6.3 健康检查
- [x] `GET /health`：`{"status": "healthy"}`
- [x] `GET /ready`：`{"status": "ready"}`

### 6.4 CORS
- [x] `allow_origins=["http://localhost:3000"]`（开发模式直连）

### 6.5 前端收尾
- [x] 登录/注册/首页 + 路由守卫（auth middleware）
- [x] 全局 token 过期处理（`expired.global.ts`）
- [x] `ConfirmModal` 通用组件

---

## 测试覆盖

```
backend/tests/
├── conftest.py                      # pytest 配置 (SQLite 内存数据库 + fixture)
├── utils.py                         # 测试工具函数
├── test_auth.py                     # 认证
├── test_users.py                    # 用户管理
├── test_departments_and_users.py    # 部门 + 用户联动
├── test_libraries.py                # 文档库 CRUD
├── test_documents.py                # 文档上传/编辑/内容
├── test_approvals.py                # 审批流转
└── test_services.py                 # 文件/解析/改写风格 + AI 跳过逻辑

76 passed (无 DEEPSEEK_API_KEY 时 AI 相关自动跳过)
```

---

## 文档产出

```
docs/
├── architecture.md      # 项目架构和模块设计
├── api.md               # 完整 API 手册（请求/响应示例）
├── local-env.md         # 本地开发环境搭建
├── deployment.md        # 本地开发部署文档
└── modules/
   ├── user-system.md    # 用户系统设计文档
   ├── document-library.md # 文档库设计
   ├── approval.md       # 审批流程设计
   └── ai-service.md     # AI 服务设计
```
