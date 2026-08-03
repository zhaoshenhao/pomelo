Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c cd /d `"$PSScriptRoot`" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload"
Write-Host "Backend launched on http://localhost:8080"
