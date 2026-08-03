# 文档库管理

## 数据模型

### DocumentLibrary
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int (PK) | 自增主键 |
| name | str (unique) | 文档库名称 |
| description | str | 描述 |
| local_path | str | 本地路径 /docs/<name>/ |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### Document
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int (PK) | 自增主键 |
| library_id | FK | 所属文档库 |
| filename | str | 原始文件名 |
| original_path | str | /docs/stage/ 中路径 |
| approved_path | str | /docs/<library>/ 中路径 |
| status | enum | stage / approved / rejected |
| uploaded_by | FK | 上传用户 |
| created_at | datetime | 上传时间 |

## API 端点

### 文档库 (Admin only for CUD)
- `POST /api/libraries` — 创建文档库
- `GET /api/libraries` — 列表
- `GET /api/libraries/{id}` — 详情
- `PUT /api/libraries/{id}` — 更新
- `DELETE /api/libraries/{id}` — 删除

### 文档上传 (Admin/Teacher)
- `POST /api/libraries/{id}/documents` — 上传文档（支持 .txt/.md/.pdf/.docx）
- `GET /api/libraries/{id}/documents` — 文档列表
- `DELETE /api/libraries/documents/{id}` — 删除暂存区文档

## 目录结构
```
docs/
  /stage/    — 上传暂存
  /<库名>/   — 已审批文档
  /temp/     — 审批中间步骤
  /backup/   — 压缩备份
```

## 文档解析
- .txt → 直接读取
- .md → 直接读取
- .pdf → PyMuPDF 文本提取
- .docx → python-docx 段落提取
- .xlsx → openpyxl 按 sheet 转 Markdown 表格
- .xls → xlrd 按 sheet 转 Markdown 表格
- 所有格式上� → 转为 .md
