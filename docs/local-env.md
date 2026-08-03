# 本地开发环境

## 后台启动（不阻塞终端）

```powershell
# 后端 8080
Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c cd /d `"D:\workspace\pomelo\backend`" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload"

# 前端 3000
Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c cd /d `"D:\workspace\pomelo\frontend`" && pnpm dev"
```

> 也可用项目根目录的 `backend\start.ps1` 和 `frontend\start.ps1`，`stop.ps1` 停止。

## 手动启动（需要两个终端窗口）

```bash
# 后端 (http://localhost:8080)
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

```bash
# 前端 (http://localhost:3000)
cd frontend
pnpm dev
```

## 停止

```powershell
# 按端口杀进程
$ports = @(8080, 3000); foreach ($p in $ports) { $conns = netstat -ano | Select-String ":$p\s+.*LISTENING"; if ($conns) { foreach ($conn in $conns) { if ($conn -match '\s+(\d+)\s*$') { taskkill /F /PID $Matches[1] 2>$null } } } }
```

也支持 `Ctrl+C` 各自中断（仅手动启动模式）。

## 状态检查

```powershell
netstat -ano | findstr ":8080 :3000" | findstr "LISTENING"
```

或:

- 后端: `curl http://localhost:8080/health` → `{"status":"healthy"}`
- 前端: 浏览器打开 `http://localhost:3000`

## 首次运行（仅需一次）

```bash
# 后端：安装依赖
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
# 复制 .env.example → .env，填入密钥

# 数据库（在 WSL 终端执行）
sudo mysql -uroot -e "
CREATE DATABASE IF NOT EXISTS pomelo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'pomelo'@'localhost' IDENTIFIED BY 'pomelo123';
GRANT ALL PRIVILEGES ON pomelo.* TO 'pomelo'@'localhost';
FLUSH PRIVILEGES;
"

# 数据库迁移
cd backend
venv\Scripts\activate
alembic revision --autogenerate -m "initial"
alembic upgrade head

# 前端：安装依赖
cd frontend
pnpm install
pnpm approve-builds esbuild
```

## 访问地址

| 服务 | 地址 |
|------|------|
| 后端 API | http://localhost:8080 |
| 前端页面 | http://localhost:3000 |
| API 文档 | http://localhost:8080/docs |

## 初始账号

| username | password | role |
|----------|----------|------|
| admin | admin123 | ADMIN |

> 第一个注册用户自动成为 ADMIN。
