<#
Windows equivalent of the Makefile.
Usage:  .\run.ps1 <command>
  setup | test | wiki-test | bg-all | bg-wiki | bg-youtube | status | logs | stop
If PowerShell blocks the script, run once per window:
  Set-ExecutionPolicy -Scope Process Bypass
#>
param([Parameter(Position = 0)][string]$Command = "help")

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"

New-Item -ItemType Directory -Force -Path logs, .pids | Out-Null

function Start-Job-BG($name, $pyArgs) {
    $pidFile = ".pids\$name.pid"
    if (Test-Path $pidFile) {
        $existing = Get-Process -Id (Get-Content $pidFile) -ErrorAction SilentlyContinue
        if ($existing) { Write-Host "$name already running (pid $($existing.Id))"; return }
    }
    $p = Start-Process -FilePath $Py -ArgumentList $pyArgs -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput "logs\$name.out.log" -RedirectStandardError "logs\$name.log"
    $p.Id | Set-Content $pidFile
    Write-Host "started $name (pid $($p.Id)) -> logs\$name.log"
}

switch ($Command) {
    "setup" {
        $pyCmd = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
        & $pyCmd -3 -m venv .venv 2>$null
        if (-not (Test-Path $Py)) { & python -m venv .venv }
        & $Py -m pip install -q -r requirements.txt
        if (-not (Test-Path .env)) { Copy-Item .env.example .env }
        Write-Host "Done. Now put your key in .env"
    }
    "test"       { & $Py -m pytest -q }
    "wiki-test"  { & $Py -m src.scrapers.wiki_scraper --wiki all --limit 10 }
    "wiki"       { & $Py -m src.scrapers.wiki_scraper --wiki all }
    "youtube"    { & $Py -m src.scrapers.youtube_scraper }
    "bg-wiki"    { Start-Job-BG "wiki" @("-m", "src.scrapers.wiki_scraper", "--wiki", "all") }
    "bg-youtube" { Start-Job-BG "youtube" @("-m", "src.scrapers.youtube_scraper") }
    "bg-all" {
        Start-Job-BG "wiki" @("-m", "src.scrapers.wiki_scraper", "--wiki", "all")
        Start-Job-BG "youtube" @("-m", "src.scrapers.youtube_scraper")
    }
    "status" {
        $any = $false
        Get-ChildItem .pids -Filter *.pid -ErrorAction SilentlyContinue | ForEach-Object {
            $any = $true
            $n = $_.BaseName
            $proc = Get-Process -Id (Get-Content $_.FullName) -ErrorAction SilentlyContinue
            if ($proc) { Write-Host "RUNNING  $n (pid $($proc.Id))" }
            else { Write-Host "STOPPED  $n"; Remove-Item $_.FullName }
        }
        if (-not $any) { Write-Host "no background jobs" }
        Write-Host "--- data collected ---"
        foreach ($d in (Get-ChildItem data\raw\wiki -Directory -ErrorAction SilentlyContinue) + (Get-Item data\raw\youtube -ErrorAction SilentlyContinue)) {
            $c = (Get-ChildItem $d.FullName -Filter *.json -File -ErrorAction SilentlyContinue | Measure-Object).Count
            Write-Host ("{0,-28} {1} files" -f (Resolve-Path -Relative $d.FullName), $c)
        }
    }
    "logs" {
        $files = Get-ChildItem logs -Filter "*.log" | Where-Object { $_.Name -notlike "*.out.log" }
        if (-not $files) { Write-Host "no logs yet"; return }
        Write-Host "Following logs (Ctrl+C stops the tail, NOT the jobs)"
        Get-Content $files.FullName -Tail 20 -Wait
    }
    "stop" {
        Get-ChildItem .pids -Filter *.pid -ErrorAction SilentlyContinue | ForEach-Object {
            $procId = Get-Content $_.FullName
            if (Get-Process -Id $procId -ErrorAction SilentlyContinue) {
                taskkill /PID $procId /T /F | Out-Null   # /T kills child processes too
                Write-Host "stopped $($_.BaseName)"
            }
            Remove-Item $_.FullName
        }
    }
    default {
        Write-Host "Commands: setup | test | wiki-test | bg-all | bg-wiki | bg-youtube | status | logs | stop"
    }
}
