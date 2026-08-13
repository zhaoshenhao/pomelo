# End-to-End Tests (Playwright)

浏览器端到端测试，覆盖核心用户旅程（登录、管理端列表、学生端页面）。

## 前置条件

E2E 依赖**已运行的服务**（不自动启动）：

```powershell
# 后端 (8080)
Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c cd /d `"D:\workspace\pomelo\backend`" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload"
# 前端 (3000)
Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c cd /d `"D:\workspace\pomelo\frontend`" && pnpm dev"
```

## 运行

```powershell
cd frontend
npx playwright test                 # 本地环境 (localhost:3000 + localhost:8080)
npx playwright test --headed        # 有头模式调试
npx playwright test login.spec.js   # 只跑指定文件
```

## 环境变量（可选）

| 变量 | 默认 | 说明 |
|---|---|---|
| `E2E_BASE_URL` | `http://localhost:3000` | 前端地址 |
| `E2E_API_BASE` | `http://localhost:8080` | 后端 API 源（不含 `/api` 后缀） |
| `E2E_ADMIN_USERNAME` | `admin` | 管理员账号 |
| `E2E_ADMIN_PASSWORD` | 无默认值（必填） | 管理员密码 |

### 对 mb-test 运行

```powershell
$env:E2E_BASE_URL="https://pomelo.dev.youbanban.com"
$env:E2E_API_BASE="https://pomelo.dev.youbanban.com"
$env:E2E_ADMIN_USERNAME="admin"
$env:E2E_ADMIN_PASSWORD="<真实密码>"
npx playwright test
```

## 说明

- 登录通过 API 获取 token 后注入 localStorage（`helpers/auth.js`），避免每次 UI 登录的脆弱性；`login.spec.js` 仍覆盖 UI 登录流程本身。
- 生成类流程（学习资料/题库/考试依赖 DeepSeek AI）不在 E2E 中自动化，避免真实 AI 调用的不稳定；E2E 聚焦确定性页面/导航断言。
