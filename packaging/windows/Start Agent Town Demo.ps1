$ErrorActionPreference = "Stop"

$PackageDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile = Join-Path $PackageDir ".env"
$BackendDir = Join-Path $PackageDir "backend"
$PythonExe = Join-Path $BackendDir "python\python.exe"
$BackendEntry = Join-Path $BackendDir "backend_entry.py"
$GameExe = Join-Path $PackageDir "Agent Town Demo.exe"
$HealthUrl = "http://127.0.0.1:8000/api/health"
$BackendProcess = $null

foreach ($RequiredPath in @($PythonExe, $BackendEntry, $GameExe)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required packaged file is missing: $RequiredPath"
    }
}

if (Test-Path $EnvFile) {
    foreach ($Line in Get-Content -LiteralPath $EnvFile) {
        $Trimmed = $Line.Trim()
        if (-not $Trimmed -or $Trimmed.StartsWith("#")) {
            continue
        }
        $Parts = $Trimmed.Split("=", 2)
        if ($Parts.Count -eq 2 -and $Parts[0].Trim()) {
            [Environment]::SetEnvironmentVariable(
                $Parts[0].Trim(),
                $Parts[1].Trim(),
                "Process"
            )
        }
    }
}

if (-not $env:LOCALAPPDATA) {
    $env:LOCALAPPDATA = Join-Path $HOME "AppData\Local"
}
$DataDir = if ($env:AGENT_TOWN_DATA_DIR) {
    $env:AGENT_TOWN_DATA_DIR
} else {
    Join-Path $env:LOCALAPPDATA "Agent Town Demo"
}

if (-not $env:ENABLE_LLM) { $env:ENABLE_LLM = "false" }
if (-not $env:LLM_PROVIDER) { $env:LLM_PROVIDER = "mock" }
if (-not $env:AGENT_TOWN_DISABLE_VECTOR_RAG) {
    $env:AGENT_TOWN_DISABLE_VECTOR_RAG = "1"
}
if (-not $env:AGENT_TOWN_NPC_POLICY_MODE) {
    $env:AGENT_TOWN_NPC_POLICY_MODE = "rule"
}
$env:AGENT_TOWN_DATA_DIR = $DataDir
if (-not $env:AGENT_TOWN_GAME_SAVE_DIR) {
    $env:AGENT_TOWN_GAME_SAVE_DIR = Join-Path $DataDir "games"
}

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
$StdoutLog = Join-Path $DataDir "backend.stdout.log"
$StderrLog = Join-Path $DataDir "backend.stderr.log"

function Test-AgentTownHealth {
    try {
        $Response = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 1
        return $Response.status -eq "ok"
    } catch {
        return $false
    }
}

try {
    if (-not (Test-AgentTownHealth)) {
        $BackendProcess = Start-Process `
            -FilePath $PythonExe `
            -ArgumentList @("backend_entry.py") `
            -WorkingDirectory $BackendDir `
            -WindowStyle Hidden `
            -RedirectStandardOutput $StdoutLog `
            -RedirectStandardError $StderrLog `
            -PassThru

        $Ready = $false
        for ($Attempt = 0; $Attempt -lt 80; $Attempt++) {
            if ($BackendProcess.HasExited) {
                throw "Backend exited early. See $StderrLog"
            }
            if (Test-AgentTownHealth) {
                $Ready = $true
                break
            }
            Start-Sleep -Milliseconds 250
        }
        if (-not $Ready) {
            throw "Backend health check timed out. See $StderrLog"
        }
    }

    $GameProcess = Start-Process `
        -FilePath $GameExe `
        -WorkingDirectory $PackageDir `
        -PassThru
    $GameProcess.WaitForExit()
    exit $GameProcess.ExitCode
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    if ($BackendProcess -and -not $BackendProcess.HasExited) {
        Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
        $BackendProcess.WaitForExit()
    }
}
