# Pomelo

基于文档的学习平台 — 根据文档形成课程材料，安排学员完成学习任务，并通过测试给予结业证书。

## 技术栈

- **后端**: Python 3.11+, FastAPI, SQLAlchemy, MySQL
- **前端**: Vue 3 + Nuxt 3, Pinia, Axios
- **AI**: DeepSeek-v4-pro (OpenAI-compatible API)
- **认证**: JWT
- **文档存储**: 本地文件系统

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- pnpm
- MySQL 8.0+

### 后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env            # 编辑 .env 填入真实配置
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

访问 http://localhost:3000

## API 文档

启动后端后访问:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## 项目结构

```
pomelo/
├── backend/              # Python FastAPI 后端
│   ├── app/
│   │   ├── models/       # SQLAlchemy 数据模型
│   │   ├── schemas/      # Pydantic 请求/响应模型
│   │   ├── routers/      # API 路由
│   │   ├── services/     # 业务服务 (AI, 文档解析, 文件管理)
│   │   └── dependencies/ # 认证/授权依赖
│   └── tests/            # pytest 单元测试
├── frontend/             # Nuxt 3 前端
│   ├── pages/            # 页面组件
│   ├── stores/           # Pinia 状态管理
│   └── plugins/          # Axios 等插件
├── storage/              # 文档运行时存储
│   ├── docs/             # 文档库文件
│   ├── stage/            # 上传暂存
│   └── backup/           # 压缩备份
└── docs/                 # 开发文档
    ├── modules/          # 各模块设计文档
    ├── architecture.md   # 架构设计
    ├── api.md            # API 手册
    └── deployment.md     # 部署手册
```

## 命令

| 命令 | 位置 | 说明 |
|------|------|------|
| `uvicorn app.main:app --reload` | `backend/` | 启动开发服务器 |
| `pytest` | `backend/` | 运行测试 |
| `ruff check app/ tests/` | `backend/` | 代码检查 |
| `mypy app` | `backend/` | 类型检查 |
| `pnpm dev` | `frontend/` | 前端开发服务器 |
