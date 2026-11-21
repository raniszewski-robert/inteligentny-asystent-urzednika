<#
.SYNOPSIS
  Uruchamia asystenta UDIP na Windows: http://127.0.0.1:8000 i otwiera przeglądarkę.

.DESCRIPTION
  Czyta ustawienia z <repo>\.env (zmienne środowiskowe mają pierwszeństwo), używa środowiska z setup.ps1,
  przy pierwszym starcie (albo gdy brak bazy) wczytuje dane startowe UMB w trybie demo (scripts\seed.py). Serwer słucha tylko na 127.0.0.1
  i nie potrzebuje internetu. Zatrzymanie: Ctrl+C.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\run.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\run.ps1 -Port 8001 -NoBrowser

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\run.ps1 -Reseed
  Sprawy z arkusza od nowa, z datami demo przesuniętymi na dziś (przed nagraniem albo pokazem).
#>
[CmdletBinding()]
param(
    [int]$Port = 0,
    [switch]$NoBrowser,
    [switch]$Reseed,
    [switch]$RealDates
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$Repo = $PSScriptRoot
$HostAddr = '127.0.0.1'

function Write-Warn([string]$Msg) { Write-Host "UWAGA: $Msg" -ForegroundColor Yellow }
function Stop-Run([string]$Msg) {
    Write-Host "BŁĄD: $Msg" -ForegroundColor Red
    exit 1
}

# Pierwsza wartość każdego klucza, jak w udip/config.py.
function Read-DotEnv([string]$Path) {
    $map = @{}
    if (Test-Path -LiteralPath $Path) {
        foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
            $t = $line.Trim()
            if ($t -eq '' -or $t.StartsWith('#') -or -not $t.Contains('=')) { continue }
            $i = $t.IndexOf('=')
            $k = $t.Substring(0, $i).Trim()
            $v = $t.Substring($i + 1).Trim().Trim([char]'"').Trim([char]"'")
            if ($k -and -not $map.ContainsKey($k)) { $map[$k] = $v }
        }
    }
    return $map
}

function Resolve-RepoPath([string]$PathValue) {
    if ([System.IO.Path]::IsPathRooted($PathValue)) { return $PathValue }
    return (Join-Path $Repo $PathValue)
}

$EnvFile = [Environment]::GetEnvironmentVariable('UDIP_ENV_FILE')
if (-not $EnvFile) { $EnvFile = Join-Path $Repo '.env' }
$cfg = Read-DotEnv $EnvFile

# Zmienna środowiskowa > .env > wartość domyślna.
function Get-Setting([string]$Key, [string]$Default) {
    $v = [Environment]::GetEnvironmentVariable($Key)
    if ($v) { return $v }
    if ($cfg[$Key]) { return $cfg[$Key] }
    return $Default
}

$Venv = Resolve-RepoPath (Get-Setting 'UDIP_VENV' (Join-Path $Repo '.venv'))
$DataDir = Resolve-RepoPath (Get-Setting 'UDIP_DATA_DIR' (Join-Path $Repo 'var'))
if ($Port -eq 0) { $Port = [int](Get-Setting 'UDIP_PORT' '8000') }
$App = Get-Setting 'UDIP_APP' 'app.main:app'

$VenvPy = Join-Path $Venv 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPy)) {
    Stop-Run "brak środowiska Pythona ($Venv). Najpierw: powershell -ExecutionPolicy Bypass -File .\setup.ps1"
}
if ($App -eq 'app.main:app' -and -not (Test-Path -LiteralPath (Join-Path $Repo 'app\main.py'))) {
    Stop-Run 'brak app\main.py: aplikacja webowa nie jest jeszcze w tej wersji repozytorium.'
}

# Ta sesja: dane i pliki tymczasowe na dysku repozytorium; Python czyta i pisze pliki w UTF-8.
$TmpDir = Join-Path $DataDir 'tmp'
foreach ($d in @($DataDir, $TmpDir)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
$env:UDIP_ENV_FILE = $EnvFile
$env:UDIP_DATA_DIR = $DataDir
$env:TEMP = $TmpDir
$env:TMP = $TmpDir
$env:PIP_CACHE_DIR = Join-Path $DataDir 'pip-cache'
$env:PYTHONUTF8 = '1'

# Tesseract (opcjonalny): kod wywołuje "tesseract" z PATH, więc dokładamy katalog z TESSERACT_CMD na początek PATH.
$tess = Get-Setting 'TESSERACT_CMD' ''
if (-not $tess -and (Test-Path -LiteralPath 'D:\Tools\Tesseract-OCR\tesseract.exe')) { $tess = 'D:\Tools\Tesseract-OCR\tesseract.exe' }
if ($tess -and -not (Test-Path -LiteralPath $tess) -and (Get-Command $tess -ErrorAction SilentlyContinue)) {
    $tess = (Get-Command $tess).Source
}
if ($tess) {
    if (Test-Path -LiteralPath $tess) {
        $env:TESSERACT_CMD = $tess
        $env:PATH = (Split-Path -Parent $tess) + ';' + $env:PATH
    } else {
        Write-Warn "TESSERACT_CMD wskazuje na nieistniejący plik ($tess); skany PDF nie zostaną odczytane."
    }
}

# Dane startowe: przy pierwszym starcie, gdy brak bazy, albo na żądanie (-Reseed = seed.py --reset).
# Domyślnie tryb demo: daty wpływu przesunięte wokół dnia UDIP_TODAY (albo dziś), żeby kalendarz pokazał wszystkie kolory.
$seed = Join-Path $Repo 'scripts\seed.py'
$mark = Join-Path $DataDir '.seeded'
$dbFile = Join-Path $DataDir 'udip.sqlite'
if ((Test-Path -LiteralPath $seed) -and ($Reseed -or -not (Test-Path -LiteralPath $mark) -or -not (Test-Path -LiteralPath $dbFile))) {
    $seedArgs = @($seed)
    if (-not $RealDates) { $seedArgs += @('--demo-today', (Get-Setting 'UDIP_TODAY' (Get-Date -Format 'yyyy-MM-dd'))) }
    if ($Reseed) { $seedArgs += '--reset' }
    $extra = [Environment]::GetEnvironmentVariable('UDIP_SEED_ARGS')
    if ($extra) { $seedArgs += @($extra -split '\s+' | Where-Object { $_ }) }
    Write-Host ('Wczytuję dane startowe: scripts\seed.py ' + (($seedArgs | Select-Object -Skip 1) -join ' '))
    Push-Location -LiteralPath $Repo
    try {
        $ErrorActionPreference = 'Continue'
        & $VenvPy @seedArgs | Out-Host
        $rc = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'
    } finally { Pop-Location }
    if ($rc -ne 0) { Stop-Run 'scripts\seed.py zakończył się błędem (komunikat powyżej).' }
    [System.IO.File]::WriteAllText($mark, (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), (New-Object System.Text.UTF8Encoding($false)))
}

function Test-PortBusy([int]$P) {
    $c = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $c.BeginConnect($HostAddr, $P, $null, $null)
        $done = $iar.AsyncWaitHandle.WaitOne(700)
        return ($done -and $c.Connected)
    } catch {
        return $false
    } finally {
        $c.Close()
    }
}
$Url = "http://${HostAddr}:$Port/"
if (Test-PortBusy $Port) {
    Stop-Run "port $Port jest zajęty (może aplikacja już działa: $Url). Inny port: .\run.ps1 -Port 8001"
}

# Przeglądarkę otwiera zadanie w tle, gdy serwer zacznie przyjmować połączenia (najwyżej ok. 2 minuty).
$job = $null
if (-not $NoBrowser -and [Environment]::GetEnvironmentVariable('UDIP_NO_BROWSER') -ne '1') {
    $job = Start-Job -ArgumentList $HostAddr, $Port, $Url -ScriptBlock {
        param($H, $P, $U)
        for ($i = 0; $i -lt 120; $i++) {
            $c = New-Object System.Net.Sockets.TcpClient
            try {
                $c.Connect($H, $P)
                Start-Process $U
                return
            } catch {
                Start-Sleep -Milliseconds 500
            } finally {
                $c.Close()
            }
        }
    }
}

Write-Host "Asystent UDIP: $Url  (dane: $DataDir; Ctrl+C zatrzymuje)" -ForegroundColor Green
$rc = 0
Push-Location -LiteralPath $Repo
try {
    # uvicorn pisze logi na stderr; to nie są błędy skryptu.
    $ErrorActionPreference = 'Continue'
    & $VenvPy -m uvicorn $App --host $HostAddr --port $Port
    $rc = $LASTEXITCODE
} finally {
    Pop-Location
    if ($job) { Remove-Job -Job $job -Force -ErrorAction SilentlyContinue }
}
exit $rc
