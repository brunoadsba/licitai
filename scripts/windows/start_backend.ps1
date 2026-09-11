$venv = Join-Path $PSScriptRoot "backend\.venv\Scripts\python.exe"
$args = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--app-dir", "backend")
Start-Process -FilePath $venv -ArgumentList $args -WindowStyle Hidden -RedirectStandardOutput "backend\server_stdout.log" -RedirectStandardError "backend\server_stderr.log"
Start-Sleep -Seconds 6
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -ErrorAction Stop
    Write-Output "HEALTH: $($response | ConvertTo-Json -Compress)"
} catch {
    Write-Output "ERROR: $_"
}
