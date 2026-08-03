# 用户系统

## 数据模型

### User
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int (PK) | 自增主键 |
| username | str (unique) | 用户名 |
| email | str (unique) | 邮箱 |
| phone | str | 手机号 |
| department | str | 部门 |
| hashed_password | str | bcrypt 哈希密码 |
| role | enum | admin / teacher / student |
| is_active | bool | 是否启用 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

## 角色权限

| 角色 | 权限说明 |
|------|---------|
| admin | 管理员 — 全部权限，包括用户管理 |
| teacher | 教师 — 可查看用户列表，文档模块完整权限 |
| student | 学生 — 仅注册/登录，无文档访问 |

## 认证流程

1. **注册**: `POST /api/auth/register` — 第一个注册用户自动成为 admin，后续注册默认 student
2. **登录**: `POST /api/auth/login` — 返回 access_token + refresh_token + user 信息
3. **刷新**: `POST /api/auth/refresh` — 使用 refresh_token 换取新 token
4. **当前用户**: `GET /api/auth/me` — 获取当前登录用户信息

## JWT

- access_token 有效期: 30 分钟
- refresh_token 有效期: 7 天
- 算法: HS256
- 需在 .env 中配置 JWT_SECRET

## 用户管理 (Admin only)

- `GET /api/users` — 用户列表 (分页)
- `PATCH /api/users/{id}/role` — 修改角色
- `DELETE /api/users/{id}` — 删除用户 (不能删除自己)
