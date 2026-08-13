# 部署手册

## 本地开发

### 后端

```bash
cd backend
cp .env.example .env     # 编辑 .env 填入真实配置
python -m venv venv
venv\Scripts\activate    # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

### 数据库

创建 MySQL 数据库:

```sql
CREATE DATABASE pomelo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 环境变量配置

| 变量 | 必填 | 说明 |
|------|------|------|
| DB_HOST | 是 | MySQL 主机地址 |
| DB_PORT | 否 | MySQL 端口，默认 3306 |
| DB_NAME | 否 | 数据库名，默认 pomelo |
| DB_USER | 是 | 数据库用户名 |
| DB_PASSWORD | 是 | 数据库密码 |
| JWT_SECRET | 是 | JWT 签名密钥（随机字符串） |
| DEEPSEEK_API_KEY | 是 | DeepSeek API 密钥 |
| DEEPSEEK_BASE_URL | 否 | DeepSeek API 地址 |
| DOCS_ROOT | 否 | 文档存储根目录，默认 ../docs |

## 云端部署

### 推荐方案

- App: Docker + Nginx 反向代理
- DB: 托管 MySQL 实例 (RDS / CloudSQL)
- 静态文件: `/docs/` 挂载持久卷

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 首次部署

1. 运行数据库迁移: `alembic upgrade head`
2. 注册第一个用户 (自动成为 admin)
3. 创建文档库
4. 配置 DeepSeek API 密钥
