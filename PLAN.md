# Pomelo 实现计划

> 最后更新：2026-08-02 · 测试通过 83/83

## 实施进度总览

| 模块 | 后端 | 前端 | 测试 | 文档 |
|------|------|------|------|------|
| 用户系统 | ✅ | ✅ | ✅ | ✅ |
| 部门管理 | ✅ | ✅ | ✅ | — |
| 文档库管理 | ✅ | ✅ | ✅ | ✅ |
| 审批流程 | ✅ | ✅ | ✅ | ✅ |
| AI 服务 + AI提示词 | ✅ | ✅ | ✅ | ✅ |
| 学习资料 | ✅ | ✅ | ✅ | — |
| 配音功能 | ✅ | ✅ | ✅ | — |
| 试卷功能 | ✅ | ✅ | ✅ | — |
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
- [x] `frontend/.env.example`：`NUXT_PUBLIC_API_BASE`（SSG 构建时注入）

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
| `AIPrompt` | `ai_prompts` | AI 提示词 (name + prompt + prompt_type: rewrite/study/exam) |
| `StudyMaterial` | `study_materials` | 学习资料 (name + description + library_id + document_names + prompt_id + created_by) |

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
│  │  ├─ ai_prompt.py
│  │  └─ study_material.py
│  ├─ routers/
│  │  ├─ auth.py              # /auth/*
│  │  ├─ users.py             # /users/*
│  │  ├─ libraries.py         # /libraries/* + 文档 CRUD
│  │  ├─ departments.py       # /departments/*
│  │  ├─ approvals.py         # /approvals/* (审批流转)
│  │  └─ ai_prompts.py      # /ai-prompts/*
│  │  └─ study_materials.py # /study-materials/*
│  ├─ schemas/
│  │  ├─ common.py            # success_response()
│  │  ├─ user.py
│  │  ├─ document.py
│  │  ├─ department.py
│  │  ├─ approval.py
│  │  ├─ ai_prompt.py
│  │  └─ study_material.py
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
│  │     ├─ ai-prompts.vue
│  │     ├─ study-materials/
│  │     │  ├─ index.vue     # 学习资料管理列表
│  │     │  ├─ generate.vue  # 生成向导
│  │     │  └─ [id].vue      # 查看/阅读页
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
- [x] `backend/requirements.txt`：fastapi, uvicorn, sqlalchemy 2.0, pymysql, aiomysql, cryptography, python-jose, passlib[bcrypt], bcrypt==4.2.1, python-multipart, PyMuPDF, python-docx, openpyxl, xlrd, python-pptx, alembic, pydantic-settings, email-validator, httpx, openai, redis, pyyaml
- [x] `backend/requirements-dev.txt`：pytest, pytest-asyncio, httpx, ruff, mypy
- [x] `frontend/package.json`：nuxt 4, vue 3, pinia, axios, @codemirror/*, @lezer/highlight, codemirror, marked, highlight.js, diff, tailwindcss 4

### 1.2 配置管理
- [x] `backend/app/config.py`：Pydantic Settings 加载 `.env`（`APP_PORT`, `DB_*`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `JWT_*`, `DOCS_ROOT`, `DEEPSEEK_*`, `AI_MAX_TOKENS`, `AI_DOC_MAX_CHARS`, `AI_TOTAL_MAX_CHARS`, `AI_TEMPERATURE`, `PROMPTS_FILE`）
- [x] `backend/.env`（本地，不入库）/ `.env.example`（模板，空/占位符）
- [x] `backend/config/prompts.yaml`：可外部化的提示词文件（改写 + 学习资料），`PROMPTS_FILE` env 可指向自定义路径
- [x] `backend/app/prompts_config.py`：提示词加载器（YAML 文件优先 → 内置默认值兜底）
- [x] `frontend/.env.example`（`NUXT_PUBLIC_API_BASE`）
- [x] 云端部署：K8s `pomelo-secrets` 注入所有 env；`docker-entrypoint.sh` 按 `APP_PORT` 启动
- [x] 部署脚本 `deploy.ps1 -CreateSecret` 从 `deploy/envs/*.env` 生成/更新 K8s Secret
- [x] `oss-upload.ps1` 按环境注入 `NUXT_PUBLIC_API_BASE` 构建前端

### 1.3 数据库
- [x] `app/database.py`：SQLAlchemy async engine + session，MySQL→aiomysql
- [x] Alembic 迁移配置 + 已执行 migration（`a1b2c3d4e5f6_*` + `b1e2f3d4e5f6_rename_rewrite_styles_to_ai_prompts`）

### 1.4 应用入口
- [x] `app/main.py`：FastAPI + CORS(`http://localhost:3000`) + lifespan + 全局异常 handler
- [x] 路由注册：auth, users, libraries, departments, approvals, ai-prompts（前缀 `/api`）
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

## Phase 4: AI 服务 + AI提示词（✅ 完成）

### 4.1 AI 服务（`ai_service.py`，DeepSeek AsyncOpenAI）
- [x] `get_ai_client()`：懒加载全局 AI client
- [x] `content_diff(new_text, library_texts)`：全文语义差异分析（新增/冲突/重复）
- [x] `grammar_rewrite(text)`：拼写语法修正
- [x] `style_rewrite(text, prompt)`：按提示词改写

### 4.2 AI提示词路由（`/api/ai-prompts/*`，Admin）
- [x] `POST/GET /ai-prompts`：创建 / 列表（支持 `?type=rewrite|study|exam` 过滤）
- [x] `PUT/DELETE /ai-prompts/{id}`：更新 / 删除
- [x] 模型 `AIPrompt`：id, name, prompt, prompt_type (rewrite/study/exam)
- [x] `prompt_type` 同类型下 name 唯一，不同类型可同名

### 4.3 前端页面
- [x] `admin/ai-prompts.vue`：提示词列表（类型筛选）+ 新建/编辑/删除

### 4.4 测试（`test_ai_prompts.py`）
- [x] AI提示词 CRUD（含类型过滤、同类型查重、不同类型同名、权限校验）

---

## Phase 4.5: 学习资料（✅ 完成）

### 4.5.1 模型（`StudyMaterial`，`study_materials`）
- [x] id, name, description, library_id(FK), document_names(逗号分隔), prompt_id(FK), created_by(FK), created_at, updated_at
- [x] 仅存储元数据，内容全在磁盘 `storage/material/<库目录>/<id>/`

### 4.5.2 学习资料路由（`/api/study-materials/*`，Teacher/Admin）
- [x] `GET /study-materials`：分页列表 + 搜索（name 模糊）
- [x] `GET /study-materials/{id}`：元数据 + manifest（页面顺序）
- [x] `GET /study-materials/{id}/page/{file}`：单页 HTML + 朗读 .txt
- [x] `POST /study-materials/generate`：单次 AI 调用生成完整结构化 JSON → 渲染 HTML/txt/manifest 落盘
- [x] `PUT /study-materials/{id}`：改名称/描述
- [x] `DELETE /study-materials/{id}`：删记录 + 磁盘目录

### 4.5.3 AI 生成（`ai_service.py`）
- [x] `generate_study_material(docs, style_prompt)`：默认结构提示词 + 风格提示词 + 文档内容 → AI 返回 cover/chapters/pages/end JSON → 后端渲染
- [x] `prompts_config.py`：提示词 yaml 文件加载器（内置默认值兜底）；`config.py` 新增 `AI_MAX_TOKENS`/`AI_DOC_MAX_CHARS`/`AI_TOTAL_MAX_CHARS`/`AI_TEMPERATURE` 外部可配
- [x] 图片链接原样保留；章节可有多页；封面/章节封面/内容页/结束页各含独立 HTML + .txt（口语化朗读）

### 4.5.4 前端页面
- [x] `admin/study-materials/index.vue`：管理列表（分页+搜索+编辑+删除）
- [x] `admin/study-materials/generate.vue`：生成向导（选库→选文档→选提示词→填信息→生成）
- [x] `admin/study-materials/[id].vue`：查看页（按序浏览，HTML 渲染 + 朗读文本切换）
- [x] 菜单 + admin / teacher 可访问

### 4.5.5 文件存储（`file_service.py`）
- [x] `get_material_root/get_material_library_dir/get_material_dir/delete_material_dir/save_material_file/read_material_file`

### 4.5.6 测试（`test_study_materials.py`，15 tests）
- [x] 生成：整库/部分文档、无效库/文档/提示词类型、空库 400、student 403、**CSS 样式注入 + 消毒**
- [x] 列表：分页、搜索、认证
- [x] 详情：元数据+manifest、单页内容（HTML+txt）
- [x] 变更：更新、删除（含磁盘清理）、404

---

## Phase 4.6: 配音功能（✅ 完成）

### 4.6.1 模型（`StudyMaterial` 加 `voice` 字段）
- [x] `voice`（VARCHAR 100），记录配音角色名

### 4.6.2 外部配置（`config.py`）
- [x] `TTS_DEFAULT_VOICE`、`TTS_AVAILABLE_VOICES`、`TTS_FALLBACK_CHARS_PER_SEC`（env 可覆盖）

### 4.6.3 TTS 服务（`app/services/tts_service.py`）
- [x] `synthesize(text, voice, path)`：Edge TTS 生成 MP3 → mutagen 读时长
- [x] `estimate_duration(text)`：无音频时按文字长度估算

### 4.6.4 路由（`/api/study-materials/*`）
- [x] 生成时自动配音（`TTS_DEFAULT_VOICE` 非空时，失败不阻断）
- [x] `GET /voices`：可用音色列表
- [x] `POST /{id}/voice`：重配音（覆盖旧文件）
- [x] `GET /{id}/audio/{file}`：FileResponse 返回 mp3

### 4.6.5 前端
- [x] 管理页：配音按钮 + 音色选择 modal + 二次确认
- [x] 查看页：自动翻页（默认开，时长=音频或估算+0.3s，末页循环）+ 朗读（默认关，播放 mp3）

### 4.6.6 部署
- [x] `deploy/envs/*.env`、`secret.txt`、K8s README 补全 TTS 配置
- [x] ⚠️ Edge TTS 需出站 `speech.platform.bing.com:443`（README 已注明）

### 4.6.7 测试（`test_study_materials.py`，6 tests）
- [x] 音色列表、配音（生成 + 重配）、非法音色 400、音频下载、音频 404、未授权 401

---

## Phase 4.7: 试卷功能（✅ 完成）

### 4.7.1 模型（`Exam` + `ExamAssignment`）
- [x] `Exam`：name(unique), description, library_id, document_names, prompt_id(FK, type=exam), duration_minutes, pass_score, created_by
- [x] `ExamAssignment`：exam_id + student_id(唯一约束), deadline, status, score, passed, completed_at
- [x] 磁盘：`storage/exam/<id>/exam.json`, `<student_id>.json`, `result.json`
- [x] **后端全齐**：generate/list/paper/edit/delete/assign/cancel/results/regenerate/student-result
- [x] 学生端点：`/my`, `/take`(不含答案), `/submit`, `/my-result`(查看自己答卷+评价)

### 4.7.2 试题类型 + 评分（`exam_service.py`）
- [x] fill(规范化精确匹配), true_false, single(选项), multiple(集合相等), match(映射相等)
- [x] 百分制 score = correct/total*100；passed = score>=pass_score

### 4.7.3 AI（`ai_service.py` + `prompts.yaml`）
- [x] `generate_exam`：(结构提示词+exam型AIPrompt+文档)→试题JSON
- [x] `evaluate_exam`：提交时同步AI评价
- [x] `summarize_exam`：重新汇总时AI知识覆盖率

### 4.7.4 路由（`/api/exams/*`）
- [x] 教师：generate/list/paper(含答案)/edit/delete/assign/cancel/results/regenerate/student-result
- [x] 学生：`/my`(两列表), `/take`(**不含答案**), `/submit`
- [x] 新增 `require_student` 依赖；已完成不可取消

### 4.7.5 前端
- [x] `admin/exams/index.vue`：管理列表 + 生成弹窗 + 编辑 + 删除 + 安排/成绩入口
- [x] `admin/exams/[id]/browse.vue`：只读浏览，正确答案高亮
- [x] `admin/exams/[id]/schedule.vue`：安排考试 Panel（左可选/右已选/已完成禁用）
- [x] `admin/exams/[id]/results.vue`：成绩汇总（总数/平均/每题正确率/及格率/AI覆盖率）+ 重新汇总 + 查看答卷
- [x] `student/exams/index.vue`：未完成/已完成列表（显示文档），开始考试→window.open，已完成→查看细节
- [x] `exam/take/[id].vue`：kiosk窗口(layout:false,禁右键/复制,倒计时),逐题作答,自动提交
- [x] `student/exams/[id]/view.vue`：已完成考试详情（答卷+评分+AI评价）

### 4.7.6 测试（`test_exams.py`，18 tests）
- [x] 生成/重名/非exam提示词/空库/student403, list, paper含答案, take不含答案
- [x] submit评分(满分+部分), 安排取消, 取消已完成被拒, delete级联, my学生列表

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
└── test_services.py                 # 文件/解析服务 + AI 跳过逻辑
└── test_ai_prompts.py               # AI提示词 CRUD + 类型过滤
└── test_study_materials.py          # 学习资料 CRUD + 生成（mock AI）
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
