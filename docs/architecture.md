# 项目架构

## 概述

Pomelo 是一个基于文档的学习平台：上传文档 → AI 生成学习资料/题库/试卷 → 安排学生学习 → 考试 → 结业。前后端分离。

## 系统架构图

```
┌─────────────┐     HTTP/JSON      ┌──────────────┐   SQLAlchemy   ┌──────────┐
│   Nuxt 3    │ ←───────────────→  │   FastAPI    │ ←────────────→ │  MySQL   │
│  (前端 SPA) │      /api/*        │   (后端)     │    (async)     │ (MySQL8/PXC)│
└─────────────┘                    └──────┬───────┘                └──────────┘
                                          │
                        ┌─────────┬───────┴────────┬──────────────┐
                        │         │                │              │
                  ┌─────┴───┐ ┌───┴────┐     ┌────┴────┐    ┌────┴────┐
                  │ DeepSeek│ │  Redis │     │ OSS     │    │ 文件系统│
                  │ (AI 服务)│ │(会话/JTI)│    │(视频/前端)│   │(NAS PV)│
                  └─────────┘ └────────┘     └─────────┘    └────────┘
```

- **前端**：Nuxt 3 静态 SSG，部署到阿里云 OSS 静态网站（Kong ingress + `200.html` SPA 回退）；运行时 `config.js` 注入 API 地址。
- **后端**：FastAPI（async）+ SQLAlchemy 2.0（async，`eager_defaults=True`）+ MySQL；DeepSeek（OpenAI 兼容 SDK）；Redis（JWT 会话、jti 校验）；edge-tts 配音；OSS（视频上传/签名播放，内网/外网分离）。
- **部署**：Kubernetes（ACK）+ Kong ingress + cert-manager；前端 OSS 静态托管。

## 后端架构

### 分层设计

```
routers/         ← 请求入口，参数验证，调用服务层（14 个：auth/users/tags/departments/libraries/
                    approvals/ai-prompts/question-banks/exams/study-materials/study-assignments/
                    drills/videos/dashboard）
    │
services/        ← 业务逻辑（ai_service, document_parser, exam_service, file_service,
                    oss_service, redis_store, tts_service, video_service）
    │
models/          ← SQLAlchemy ORM 模型（11 个）
schemas/         ← Pydantic 请求/响应模型
dependencies/    ← 认证、授权依赖注入（get_current_user / require_admin / require_teacher_or_admin / require_student）
```

### 关键设计

- **异步生成任务**：题库/学习资料 AI 生成采用「202 + job_id 轮询」；后台 `asyncio.create_task`，任务结果由 `_background_tasks` set 持有防止被 GC。
- **ORM**：`Base.__mapper_args__ = {"eager_defaults": True}` — `server_default`/`onupdate` 列（created_at/updated_at）在 flush 时取回，避免 MySQL 5.7（无 RETURNING）下的 async 懒加载 `MissingGreenlet`。
- **认证**：JWT（access/refresh）+ Redis 会话 + jti 防重放；角色 admin/teacher/student；`REGISTRATION_ENABLED` 注册开关。
- **文件存储**：本地 `storage/`（docs/stage/backup/material/qb/exam/drills），生产为 NAS PV（`/app/data/storage`）。

## 数据模型

```
User ─┬─ Department（部门）
      ├─ StudentTag（学员标签，多对多）
      └─ 上传 → Document ──< DocumentLibrary（文档库）
                                   │
DocumentLibrary ─┬─ StageDocument（审批：new → content_review → rewrite → preview → completed）
                 ├─ StudyMaterial（学习资料，AI 生成 + TTS 配音）
                 ├─ QuestionBank（题库，AI 生成，disabled 禁用）
                 ├─ Video（视频，OSS）
                 └─ Document（文档）

StudyMaterial ──< StudyAssignment（学生学习进度：total_study_seconds/read_count/complete_count）
QuestionBank ──< Exam（试卷）
Exam ──< ExamBatch（考试批次）──< ExamAssignment（学生分配）
Video ──< VideoViewRecord / VideoComment（观看记录/留言）
AIPrompt（AI 提示词：rewrite/study/exam 三类）
```

## 前端架构

```
app/
  pages/           ← 页面（admin/* 管理端、student/* 学生端、exam/take 考试）
  components/      ← ConfirmModal, MarkdownEditor, VideoPlayer 等
  stores/          ← Pinia（auth）
  plugins/         ← axios（JWT 拦截器、运行时 apiBase）、logger
  middleware/      ← auth / teacher / admin 路由守卫
  utils/           ← logger, markdownHighlight, sanitize（DOMPurify）
```

## 文档处理流程

```
上传文档（txt/md/pdf/docx/xlsx/xls/pptx）
    ↓ 存入 stage 暂存区
审批（StageDocument 状态机：new → content_review → rewrite → preview）
    ↓ 确认执行
格式转换为 .md → 存入文档库（/storage/docs/<库名>/）
    ↓
AI 生成学习资料 / 题库（异步 job）→ 供学生课程学习 / 模拟训练 / 组卷考试
```
