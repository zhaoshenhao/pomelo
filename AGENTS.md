# AGENTS.md

## 项目概述
Pomelo - 一个基于文档的学习平台，根据文档形成课程材料，安排学员完成学习任务，并且通过测试，给与结业证书。

---

## Repository-Specific Guidance

### 技术栈
- **后端**: `backend/` — Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), MySQL
- **前端**: `frontend/` — Vue 3 + Nuxt 3 (minimal template), Pinia, Axios
- **AI**: DeepSeek-v4-pro via OpenAI-compatible API (`async openai` client)
- **认证**: JWT (python-jose + passlib bcrypt 4.2.x, **not 5.x**)
- **文件存储**: 本地 `storage/` 目录 (docs, stage, backup)

### 项目目录
```
backend/          Python FastAPI (pip + venv, 不以 pnpm 管理)
frontend/         Nuxt 3 (pnpm)
storage/          文档运行时存储 (不提交 Git)
docs/             开发文档
AGENTS.md         本文件 (256 行通用规范 + 本 repo-specific 节)
PLAN.md           实现计划 (checkbox 跟踪进度)
```

### 后端命令
```bash
cd backend
python -m venv venv
venv\Scripts\activate                    # Windows
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8080  # 开发服务器 (勿直接调用，走启动脚本)
pytest                                    # 运行所有测试
ruff check app/ tests/                    # Lint
```
- 使用 `bcrypt==4.2.1`，不要升级到 5.x (passlib 不兼容)
- 测试用 SQLite 内存数据库，不需要 MySQL
- AI 相关测试在没有 `DEEPSEEK_API_KEY` 环境变量时自动跳过

### 前端命令
```bash
cd frontend
pnpm install
pnpm dev                                 # localhost:3000，axios baseURL 直连 http://localhost:8080/api
```
- 前端 axios base URL 直连后端 8080（Nuxt dev proxy 不生效，已移除）
- esbuild 构建被 pnpm 安全策略忽略，不影响开发 (可忽略 warning)

### 本地服务启动 / 停止 (Windows 非阻塞)
⚠️ **严禁在工具中直接运行 `uvicorn` 或 `pnpm dev`**，会因控制台句柄继承导致进程僵死。
**唯一可靠方式**：`Start-Process -WindowStyle Hidden` 创建完全独立进程，调用方立即返回不阻塞。

```powershell
# 启动后端 (端口 8080)
Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c cd /d `"D:\workspace\pomelo\backend`" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload"

# 启动前端 (端口 3000)
Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c cd /d `"D:\workspace\pomelo\frontend`" && pnpm dev"

# 停止所有服务 (杀端口进程)
$ports = @(8080, 3000); foreach ($p in $ports) { $conns = netstat -ano | Select-String ":$p\s+.*LISTENING"; if ($conns) { foreach ($conn in $conns) { if ($conn -match '\s+(\d+)\s*$') { taskkill /F /PID $Matches[1] 2>$null } } } }
```

- 后端实际端口 **8080**（8000 被 Windows 占用）
- 前端实际端口 **3000**，axios `baseURL` 通过 Nuxt `runtimeConfig.public.apiBase` 配置（默认 `http://localhost:8080/api`）
- 前端 Nuxt 4 minimal template 的 `srcDir` 是 `app/`，所有 `pages/`、`stores/`、`plugins/`、`middleware/` 放在 `frontend/app/` 下
- 前端 `.vue` 文件未加 `lang="ts"`，禁止写 TypeScript 类型标注（如 `catch (e: any)`）

### 数据模型
- - `User` (admin/teacher/student), `DocumentLibrary`, `Document`
- `ApprovalProcess`, `ApprovalStep`, `BackupRecord`, `AIPrompt`, `StudyMaterial`, `Exam`, `ExamAssignment`
- 所有模型在 `app/models/__init__.py` 注册，Alembic 可自动检测

### 外部配置
- 后端配置全部走 `pydantic-settings.BaseSettings`，优先级：环境变量 > `.env` 文件 > 代码默认值
- `.env.example` 在 `backend/.env.example`，列出所有可配置字段
- 提示词（改写/学习资料的结构默认）存储在 `backend/config/prompts.yaml`，运行时通过 `PROMPTS_FILE` env 可指向自定义路径
- AI 参数（temperature, max_tokens, truncation 长度等）全部 env 可覆盖
- DB 连接池大小 (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`) env 可覆盖
- TTS 配音（`TTS_DEFAULT_VOICE`, `TTS_AVAILABLE_VOICES`, `TTS_FALLBACK_CHARS_PER_SEC`）env 可覆盖；`edge-tts` 需出站访问 `speech.platform.bing.com:443`
- 前端 API base URL 通过 Nuxt `runtimeConfig.public.apiBase` 配置（`NUXT_PUBLIC_API_BASE` env）
- `APP_PORT` 在 Dockerfile entrypoint 中读取，默认 8080
- 云端部署通过 K8s Secret (`pomelo-secrets`) 注入所有配置

### 审批流程
- 4 步: semantic_check → content_review → preview → confirm
- 创建审批时自动锁定给当前用户 (locked_by)
- 其他人操作返回 409，Admin 可通过 `/approvals/{id}/lock` 强制解锁

### 已知约束
- 第一个注册用户自动成为 admin
- 所有文档最终转为 `.md` 格式存入文档库
- 支持上传: `.txt`, `.md`, `.pdf`, `.docx`, `.xlsx`, `.xls`
- 备份按 SHA256 去重，文件名: `<库名>-<hash>.zip`
- Student 角色无任何文档模块访问权限

---

## 一、项目原则（最高优先级）

### 1.1 核心原则
- **可维护性优先**：优先保证代码的可维护性，而非最快完成
- **简单优于复杂**：选择最简单的解决方案，避免过度工程
- **禁止过度设计**：不引入未使用的抽象、模式或功能
- **增量修改优先**：优先修改已有代码，而非重新实现
- **可测试性**：所有修改必须可测试

---

## 二、代码安全（强制）

### 2.1 敏感信息保护
- ❌ **禁止任何硬编码**：包括URL、密钥、密码、Token等
- ❌ **禁止敏感信息出现在代码里**：所有凭证必须通过环境变量或密钥管理服务获取
- ✅ 使用环境变量或配置中心管理敏感信息

### 2.2 安全编码规范
- ❌ **禁止SQL注入**：必须使用参数化查询或ORM
- ❌ **禁止路径遍历**：文件操作必须验证路径
- ✅ **必须验证输入**：所有用户输入必须经过验证和净化
- ✅ **必须转义输出**：所有输出到HTML/XML/JSON的内容必须转义
- ✅ **必须使用最小权限原则**：服务运行账户、数据库账户权限最小化

---

## 三、性能要求

### 3.1 数据库
- ❌ **禁止全表扫描**：查询必须使用索引
- ✅ **使用批处理**：批量操作必须使用批处理接口
- ✅ **使用缓存**：热点数据必须使用缓存策略

### 3.2 资源管理
- ✅ **使用懒加载**：大型资源在需要时加载
- ✅ **连接池管理**：数据库/HTTP连接必须使用连接池

---

## 四、依赖管理

### 4.1 原则
- ✅ **最小依赖原则**：仅引入必要的依赖，定期审查和清理
- ✅ **License合规**：必须收集所有依赖的License文件，统一存放在 `licenses/` 目录下
- ✅ **版本固定**：使用固定版本号，避免使用 `latest`

---

## 五、错误处理（统一规范）

### 5.1 异常处理要求
- ✅ 使用有意义的自定义异常类型
- ✅ 必须记录日志
- ✅ 必须保留完整的堆栈跟踪

### 5.2 错误信息格式
每个错误信息必须包含三要素：
- **What**：发生了什么错误
- **Where**：在哪个模块/函数发生
- **How to fix**：如何修复此问题

**示例**：
```json
{
  "error": "Database connection failed",
  "where": "UserRepository.getUserById()",
  "how_to_fix": "检查数据库连接字符串是否正确，确认数据库服务是否运行"
}
```

---

## 六、日志规范

### 6.1 强制要求
- ✅ **必须使用日志框架**：禁止使用 `print()`、`console.log()` 等
- ✅ **结构化日志**：使用JSON格式，包含以下字段：
  - `timestamp`：ISO 8601格式
  - `level`：ERROR/WARN/INFO/DEBUG
  - `request_id`：请求唯一标识
  - `trace_id`：分布式追踪ID
  - `message`：日志信息
  - `user_id`：用户标识（如有）
  - `module`：模块名称

**示例**：
```json
{
  "timestamp": "2026-01-23T10:30:00Z",
  "level": "INFO",
  "request_id": "req-abc123",
  "trace_id": "trace-xyz789",
  "module": "UserService",
  "message": "User login successful",
  "user_id": "user-001"
}
```

---

## 七、测试规范

### 7.1 覆盖率要求
- ✅ **每个模块必须有单元测试**
- ✅ **分支覆盖率 ≥ 95%**

### 7.2 测试类型要求
每个功能必须包含三类测试：
- ✅ **Happy Path**：正常流程测试
- ✅ **Failure Path**：异常流程测试
- ✅ **Boundary Test**：边界值测试

---

## 八、代码提交规范

### 8.1 提交方式
- ⚠️ **禁止自动提交**：不要自动执行 `git commit` 或 `git push`
- ✅ 让开发人员手动审查并提交代码
- ✅ 等待开发人员明确提交命令后再执行

---

## 九、命名规范

### 9.1 基本原则
- ✅ **使用有意义的名字**：名称应清晰表达用途和意图
- ❌ **禁止使用缩写**：避免使用非通用缩写
  - ❌ 错误：`usrSvc`、`dbMgr`、`cfg`
  - ✅ 正确：`UserService`、`DatabaseManager`、`Configuration`

---

## 十、模块架构设计

### 10.1 设计原则
- ✅ **高凝聚力**：模块内功能高度相关
- ✅ **低耦合**：模块间依赖最小化
- ❌ **禁止循环依赖**：A依赖B，B不能依赖A
- ❌ **禁止全局状态**：避免使用全局变量或单例模式滥用

### 10.2 界面设计原则
- ✅ **编辑页面**：退出界面前需要进行脏数据检查，并确认退出；
- ✅ **新建、修改、删除**：等必须进行二次确认

---

## 十一、配置管理

### 11.1 强制要求
- ❌ **禁止任何硬编码**：包括URL、端点、超时时间等所有配置项
- ❌ **禁止敏感信息出现在代码里**：密钥、密码、Token必须通过安全方式注入
- ✅ 使用环境变量或配置中心管理配置
- ✅ 本地开发使用 `.env` 文件（不提交到Git）

---

## 十二、API 设计规范

### 12.1 统一标准
- ✅ 所有API遵循统一格式和标准
- ✅ 使用RESTful或GraphQL规范（根据项目选择）
- ✅ 统一响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "timestamp": "2026-01-23T10:30:00Z",
  "request_id": "req-abc123"
}
```

### 12.2 HTTP状态码
- 200：成功
- 400：客户端错误
- 401：未授权
- 403：禁止访问
- 404：资源不存在
- 500：服务器错误

---

## 十三、可观测性

### 13.1 必须支持
- ✅ **指标（Metrics）**：性能指标、业务指标
- ✅ **健康检查（Health Check）**：服务健康状态
- ✅ **追踪（Tracing）**：分布式链路追踪
- ✅ **分析（Analysis）**：日志分析和监控

### 13.2 API端点
- `GET /health`：服务健康状态
- `GET /ready`：服务就绪状态
- `GET /metrics`：性能指标（需要API保护）

### 13.3 安全保护
- 敏感指标数据必须通过认证和授权保护
- 使用API Key或OAuth保护 `/metrics` 端点

---

## 十四、部署规范

### 14.1 云端部署要求
- ✅ **Immutable Build**：不可变构建，每次部署生成新的构建产物
- ✅ **Container First**：优先使用容器化部署（Docker/Kubernetes）
- ✅ **Health Check**：配置健康检查探针
- ✅ **Graceful Shutdown**：优雅关闭，处理存量请求
- ✅ **Zero Downtime**：零停机部署（蓝绿部署或滚动更新）

### 14.2 文档要求
提供详细的部署文档：
- ✅ 云端部署文档（含步骤和配置）
- ✅ 本地开发部署文档

### 14.3 本地开发部署
- ✅ 使用 `.env` 文件隔离敏感信息
- ✅ `.env` 文件不提交到Git仓库
- ✅ 提供 `.env.example` 模板文件

---

## 十五、文档标准

### 15.1 必须提供的文档
- ✅ **项目架构和设计文档**：整体架构图、技术选型说明
- ✅ **每个模块设计文档**：模块职责、接口定义、依赖关系
- ✅ **命令行手册**：含使用样例
- ✅ **API手册**：含使用样例（请求/响应示例）
- ✅ **云端部署手册**：完整的部署步骤和配置说明

---

## 十六、AI 可交付成果清单

在提交代码前，必须确认以下所有项：

- [ ] **Build passes**：构建通过
- [ ] **Tests pass**：所有测试通过
- [ ] **Lint passes**：代码检查通过
- [ ] **Docs updated**：相关文档已更新
- [ ] **Security checked**：安全检查通过（无硬编码、无SQL注入等）
- [ ] **Performance considered**：性能已评估（无全表扫描、有缓存等）
- [ ] **Breaking changes documented**：破坏性变更已记录
- [ ] **Migration documented**：数据迁移方案已记录
- [ ] **No duplicated logic**：无重复逻辑
- [ ] **No dead code**：无死代码
- [ ] **No TODO left**：无未处理的TODO
- [ ] **No hardcoded value**：无硬编码值

---

## 附录

### A. 环境变量示例（.env.example）
```env
# 应用配置
APP_PORT=8080
APP_ENV=development

# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myapp
DB_USER=user
DB_PASSWORD= # 请设置强密码

# 缓存配置
REDIS_HOST=localhost
REDIS_PORT=6379

# 密钥配置
JWT_SECRET= # 请生成强密钥
API_KEY= # 请生成API密钥
```

### B. 错误码规范
| 错误码 | 说明 | 示例 |
|--------|------|------|
| 0 | 成功 | - |
| 1000 | 参数错误 | 缺少必填参数 |
| 1001 | 认证失败 | Token无效或过期 |
| 1002 | 权限不足 | 无操作权限 |
| 2000 | 业务逻辑错误 | 余额不足 |
| 5000 | 系统内部错误 | 数据库连接失败 |

---

*本模板根据项目实际需求可进行适当调整和扩充。*