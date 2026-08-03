# API 手册

Base URL: `http://localhost:8000/api`

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

## Rewrite Styles (Admin only)

### POST /rewrite-styles

```json
{"name": "简洁风格", "prompt": "请将内容改写为简洁精炼的风格"}
```

### GET /rewrite-styles

### PUT /rewrite-styles/{id}

### DELETE /rewrite-styles/{id}

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
