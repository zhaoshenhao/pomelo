Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList "/c cd /d `"$PSScriptRoot`" && pnpm dev"
Write-Host "Frontend launched on http://localhost:3000"
