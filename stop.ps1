$ports = @(8080, 3000)
$killed = $false

foreach ($p in $ports) {
    $conns = netstat -ano | Select-String ":$p\s+.*LISTENING"
    if ($conns) {
        foreach ($conn in $conns) {
            if ($conn -match '\s+(\d+)\s*$') {
                $pid = $Matches[1]
                taskkill /F /PID $pid 2>$null
                if ($LASTEXITCODE -eq 0) { $killed = $true }
            }
        }
    }
}

if ($killed) {
    Write-Host "Pomelo services stopped."
} else {
    Write-Host "No Pomelo services were running."
}
