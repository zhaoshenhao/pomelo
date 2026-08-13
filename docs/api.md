# API 手册

Base URL: `http://localhost:8080/api`（本地）；`https://pomelo.dev.youbanban.com/api`（测试环境）

> 本手册为概述性参考。**完整、实时的接口清单请以运行中的 OpenAPI 文档为准**：`GET /docs`（Swagger UI）。

## 异步生成模式（题库 / 学习资料）

AI 生成耗时较长，以下接口采用「202 + job_id 轮询」异步模式：
- `POST /question-banks/generate` → `202 {"data": {"job_id": "..."}}`
- `GET /question-banks/generate/{job_id}` → `{"status": "running"|"done"|"failed", ...}`
- `POST /study-materials/generate` → `202 {"data": {"job_id": "..."}}`
- `GET /study-materials/generate/{job_id}` → 同上

前端每 3 秒轮询一次，`done` 后取回资源 id。

## 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "timestamp": "2026-01-23T10:30:00Z",
  "request_id": "req-abc123"
}
```

## 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|----------|------|
| 0 | 200 | 成功 |
| 1000 | 400 | 参数错误 |
| 1001 | 401 | 认证失败 |
| 1002 | 403 | 权限不足 |
| 2000 | 400 | 业务逻辑错误 |
| 4004 | 404 | 资源不存在 |
| 5000 | 500 | 系统内部错误 |

## Auth

### POST /auth/register

```json
// Request
{"username": "test", "email": "test@example.com", "phone": "13800138000", "department": "技术部", "password": "password123"}
// Response 201
{"code": 0, "message": "注册成功", "data": {"id": 1, "username": "test", "role": "admin"}}
```

### POST /auth/login

```json
// Request
{"username": "test", "password": "password123"}
// Response 200
{"code": 0, "data": {"access_token": "...", "refresh_token": "...", "user": {...}}}
```

### POST /auth/refresh

```json
// Request: query param refresh_token
// Response 200
{"code": 0, "data": {"access_token": "...", "refresh_token": "..."}}
```

### GET /auth/me

```
Header: Authorization: Bearer <access_token>
```

## Users (Admin only for CUD)

### GET /users?page=1&page_size=20

### GET /users/{id}

### PATCH /users/{id}/role

```json
{"role": "teacher"}
```

### DELETE /users/{id}

## Libraries

### POST /libraries (Admin)

```json
{"name": "课程文档库", "description": "2026年课程资料"}
```

### GET /libraries

### GET /libraries/{id}

### PUT /libraries/{id} (Admin)

### DELETE /libraries/{id} (Admin)

### POST /libraries/{id}/documents (Admin/Teacher)

```
FormData: file=<上传文件>
支持格式: .txt, .md, .pdf, .docx, .xlsx, .xls
```

### GET /libraries/{id}/documents

### DELETE /libraries/documents/{id}

## AI Prompts (Admin only)

### POST /ai-prompts

```json
{"name": "简洁风格", "prompt": "请将内容改写为简洁精炼的风格", "prompt_type": "rewrite"}
```

### GET /ai-prompts

可选 `?type=rewrite|study|exam` 过滤类型。

### PUT /ai-prompts/{id}

### DELETE /ai-prompts/{id}

## Study Materials (Teacher/Admin)

### GET /study-materials

分页列表 + 搜索：`?page=1&page_size=20&search=关键词`

### POST /study-materials/generate

```json
{
  "name": "学习资料标题",
  "description": "描述",
  "library_id": 1,
  "document_names": ["doc1.md", "doc2.md"],
  "prompt_id": 1
}
```
`document_names` 为空数组表示使用整个文档库。prompt 必须 type=study。
AI 生成结果包含 `style` 字段（一套 CSS），该样式自动注入到资料所有页面。

### GET /study-materials/{id}

元数据 + manifest（按序页面列表）。

### GET /study-materials/{id}/page/{page_file}

返回单页 `{"html": "...", "text": "..."}`

### PUT /study-materials/{id}

更新名称/描述。

### DELETE /study-materials/{id}

删除 DB 记录 + 磁盘文件。

### GET /study-materials/voices

返回可用配音角色列表：`{default: "zh-CN-...", voices: [...]}`

### POST /study-materials/{id}/voice

```json
{"voice": "zh-CN-YunxiNeural"}
```
为所有页面重新生成配音（覆盖旧 mp3 文件）。

### GET /study-materials/{id}/audio/{filename}

返回指定音频文件（MP3，`audio/mpeg`）。

## Exams (Teacher/Admin + Student)

### GET /exams
分页列表 + 搜索（Teacher/Admin）

### POST /exams/generate
```json
{"name":"试卷名称","library_id":1,"document_names":["doc.md"],"prompt_id":1,"duration_minutes":30,"pass_score":60}
```
prompt 必须 type=exam。名称不能重复。

### GET /exams/{id}
元数据。`GET /exams/{id}/paper` 返回含答案的完整试卷。

### PUT /exams/{id} | DELETE /exams/{id}

### POST /exams/{id}/assignments
安排学生考试：`{"student_ids":[2,3],"deadline":"2026-08-10T00:00:00"}`
`DELETE /exams/{id}/assignments/{sid}` 取消（已完成不可取消）

### GET /exams/{id}/results
成绩汇总。`POST /exams/{id}/results/regenerate` 重新汇总。

### GET /exams/my（Student）
未完成/已完成考试列表。

### GET /exams/{id}/take（Student）
获取考题（**不含答案**，仅题干+选项）。

### POST /exams/{id}/submit（Student）
交卷 `{"answers":[{"question_id":"q1","answer":"A"}]}` → 返回评分+AI评价。

## Approvals

### POST /approvals

```json
{"library_id": 1, "document_ids": [1, 2]}
```

### GET /approvals/{id}

### POST /approvals/{id}/semantic-check
### POST /approvals/{id}/selection
### POST /approvals/{id}/spell-check
### POST /approvals/{id}/rewrite
### POST /approvals/{id}/apply-edit
### GET /approvals/{id}/preview
### POST /approvals/{id}/confirm
### POST /approvals/{id}/cancel
### DELETE /approvals/{id}/lock (Admin)

## Health

### GET /health
### GET /ready
