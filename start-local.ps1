# Local server for Muscat flights board
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$port = 8765
if ($args.Count -gt 0) { $port = [int]$args[0] }

$python = $null
foreach ($cmd in @("python", "py", "python3")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $python = $cmd
        break
    }
}

if (-not $python) {
    Write-Host "Python not found. Install from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

$url = "http://localhost:$port/"
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Muscat Airport Flights - Local Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Folder: $Root"
Write-Host "Open:   $url" -ForegroundColor Green
Write-Host ""
Write-Host "Keep this window open. Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

Start-Process $url
& $python -m http.server $port --bind 127.0.0.1
