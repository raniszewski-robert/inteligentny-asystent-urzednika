<#
.SYNOPSIS
  Instalacja asystenta UDIP na Windows. Wszystko zostaje na dysku repozytorium (np. D:), poza samym Pythonem.

.DESCRIPTION
  1. Sprawdza Pythona >= 3.11 i Git (podaje polecenie winget, jeśli czegoś brakuje).
  2. Tworzy albo uzupełnia <repo>\.env: UDIP_ENV_FILE, UDIP_VENV, UDIP_DATA_DIR, LLM_BUDGET_USD=15, UDIP_PROVIDER=openai_compat:bielik.
     Istniejących linii nie zmienia (w szczególności linii z kluczem API); dopisuje tylko brakujące klucze.
  3. Tworzy środowisko Pythona w <repo>\.venv; pamięć podręczna pip i pliki tymczasowe trafiają do <repo>\var.
  4. Instaluje paczki z requirements.txt i wczytuje dane startowe UMB (scripts\seed.py): 10 spraw z arkusza
     kalendarium i archiwum UMB, w trybie demo (daty wpływu przesunięte wokół dnia UDIP_TODAY albo dziś).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\setup.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Reseed
  Wczytuje sprawy z arkusza od nowa, z datami demo na dziś (kasuje historię statusów tych spraw).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -RealDates
  Dane startowe z prawdziwymi datami z arkusza (same zamknięte sprawy) zamiast trybu demo.
#>
[CmdletBinding()]
param(
    [switch]$Reseed,
    [switch]$RealDates,
    [switch]$SkipSeed
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$Repo = $PSScriptRoot
$MinPython = [version]'3.11'

function Write-Ok([string]$Msg)   { Write-Host "  [OK] $Msg" -ForegroundColor Green }
function Write-Warn([string]$Msg) { Write-Host "  [UWAGA] $Msg" -ForegroundColor Yellow }
function Stop-Setup([string]$Msg) {
    Write-Host ''
    Write-Host "BŁĄD: $Msg" -ForegroundColor Red
    exit 1
}

# Uruchamia program, pokazuje jego wyjście, zwraca kod wyjścia. Komunikaty na stderr (np. ostrzeżenia pip) nie przerywają skryptu.
function Invoke-Native([string]$Exe, [string[]]$ArgList) {
    $ErrorActionPreference = 'Continue'
    & $Exe @ArgList | Out-Host
    return $LASTEXITCODE
}

# Pierwsza wartość każdego klucza, jak w udip/config.py: bez komentarzy, bez cudzysłowów, bez interpolacji.
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

# Dopisuje linie na końcu pliku: UTF-8 bez BOM (udip czyta .env jako zwykłe UTF-8), bez naruszania istniejącej treści.
function Add-DotEnvLines([string]$Path, [string[]]$Lines) {
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $prefix = ''
    if (Test-Path -LiteralPath $Path) {
        $bytes = [System.IO.File]::ReadAllBytes($Path)
        if ($bytes.Length -gt 0 -and $bytes[$bytes.Length - 1] -ne 10) { $prefix = "`r`n" }
    }
    $text = $prefix + (($Lines | ForEach-Object { $_ + "`r`n" }) -join '')
    [System.IO.File]::AppendAllText($Path, $text, $utf8)
}

function Resolve-RepoPath([string]$PathValue) {
    if ([System.IO.Path]::IsPathRooted($PathValue)) { return $PathValue }
    return (Join-Path $Repo $PathValue)
}

function Get-Drive([string]$PathValue) { return ([System.IO.Path]::GetPathRoot($PathValue)).ToUpper() }

# Zwraca wersję Pythona albo $null (np. dla aliasu ze Sklepu Microsoft, który tylko wyświetla komunikat).
function Get-PythonVersion([string]$Exe, [string[]]$PreArgs) {
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $Exe @PreArgs -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { return [version](($out | Select-Object -Last 1).ToString().Trim()) }
    } catch { }
    return $null
}

Write-Host "Asystent UDIP: instalacja w $Repo"
Write-Host ''

# --- 1. Python i Git -------------------------------------------------------------------------
Write-Host '1. Python i Git'
$repoDrive = Get-Drive $Repo
if ($repoDrive -eq 'C:\') {
    Write-Warn 'Repozytorium leży na dysku C:, więc środowisko i dane też tam trafią. Sklonuj je na D:, jeśli C: ma być wolny.'
}

$candidates = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($v in @('-3.12', '-3.13', '-3.11', '-3.14', '-3')) { $candidates += , @('py', $v) }
}
foreach ($name in @('python', 'python3')) {
    if (Get-Command $name -ErrorAction SilentlyContinue) { $candidates += , @($name) }
}

$PyExe = $null
$PyArgs = @()
$PyVersion = $null
foreach ($c in $candidates) {
    $pre = @()
    if ($c.Count -gt 1) { $pre = @($c[1..($c.Count - 1)]) }
    $ver = Get-PythonVersion $c[0] $pre
    if ($ver -and $ver -ge $MinPython) { $PyExe = $c[0]; $PyArgs = $pre; $PyVersion = $ver; break }
}
if (-not $PyExe) {
    Stop-Setup ("Nie znaleziono Pythona 3.11 lub nowszego.`n" +
        "  Zainstaluj:  winget install -e --id Python.Python.3.12`n" +
        "  (albo instalator z python.org z opcją 'Add python.exe to PATH'), potem otwórz nowe okno PowerShell i uruchom setup.ps1 ponownie.")
}
Write-Ok "Python $PyVersion ($PyExe $($PyArgs -join ' '))"

if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Ok ((& git --version) | Select-Object -First 1)
} else {
    Write-Warn ("Brak Git. Aplikacja działa bez niego, ale do pobierania aktualizacji repozytorium jest potrzebny:`n" +
        "           winget install -e --id Git.Git")
}

# --- 2. Plik .env ----------------------------------------------------------------------------
Write-Host ''
Write-Host '2. Ustawienia (.env)'
$EnvFile = Join-Path $Repo '.env'
if (-not (Test-Path -LiteralPath $EnvFile)) {
    $example = Join-Path $Repo '.env.example'
    if (Test-Path -LiteralPath $example) {
        Copy-Item -LiteralPath $example -Destination $EnvFile
        Write-Ok '.env utworzony z .env.example'
    } else {
        [System.IO.File]::WriteAllText($EnvFile, '', (New-Object System.Text.UTF8Encoding($false)))
        Write-Ok '.env utworzony'
    }
}
# BOM na początku (Notatnik w starszych Windows) zepsułby odczyt pierwszego klucza: usuwamy tylko te 3 bajty.
$raw = [System.IO.File]::ReadAllBytes($EnvFile)
if ($raw.Length -ge 3 -and $raw[0] -eq 0xEF -and $raw[1] -eq 0xBB -and $raw[2] -eq 0xBF) {
    $rest = New-Object byte[] ($raw.Length - 3)
    [System.Array]::Copy($raw, 3, $rest, 0, $rest.Length)
    [System.IO.File]::WriteAllBytes($EnvFile, $rest)
    Write-Ok 'usunięto znacznik BOM z początku .env'
}

$cfg = Read-DotEnv $EnvFile
$Venv = Join-Path $Repo '.venv'
if ($cfg['UDIP_VENV']) { $Venv = Resolve-RepoPath $cfg['UDIP_VENV'] }
$DataDir = Join-Path $Repo 'var'
if ($cfg['UDIP_DATA_DIR']) { $DataDir = Resolve-RepoPath $cfg['UDIP_DATA_DIR'] }

$wanted = [ordered]@{
    'UDIP_ENV_FILE'  = $EnvFile
    'UDIP_VENV'      = $Venv
    'UDIP_DATA_DIR'  = $DataDir
    'LLM_BUDGET_USD' = '15'
    'UDIP_PROVIDER'  = 'openai_compat:bielik'
}
$tessDefault = 'D:\Tools\Tesseract-OCR\tesseract.exe'
if (-not $cfg['TESSERACT_CMD'] -and -not (Get-Command tesseract -ErrorAction SilentlyContinue) -and (Test-Path -LiteralPath $tessDefault)) {
    $wanted['TESSERACT_CMD'] = $tessDefault
}
$missing = @()
foreach ($k in $wanted.Keys) {
    if (-not $cfg.ContainsKey($k)) { $missing += "$k=$($wanted[$k])" }
}
if ($missing.Count -gt 0) {
    Add-DotEnvLines $EnvFile (@("# Dopisane przez setup.ps1 $(Get-Date -Format 'yyyy-MM-dd HH:mm')") + $missing)
    foreach ($m in $missing) { Write-Ok ('dopisano ' + ($m -split '=', 2)[0]) }
} else {
    Write-Ok '.env ma już wszystkie potrzebne klucze (niczego nie zmieniono)'
}
foreach ($p in @($Venv, $DataDir)) {
    if ((Get-Drive $p) -eq 'C:\' -and $repoDrive -ne 'C:\') { Write-Warn "$p leży na C: (ustawione w .env)." }
}

# Ta sesja: pamięć podręczna pip i pliki tymczasowe na dysku repozytorium, nie w profilu użytkownika na C:.
$PipCache = Join-Path $DataDir 'pip-cache'
$TmpDir = Join-Path $DataDir 'tmp'
foreach ($d in @($DataDir, $PipCache, $TmpDir)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
$env:UDIP_ENV_FILE = $EnvFile
$env:UDIP_DATA_DIR = $DataDir
$env:PIP_CACHE_DIR = $PipCache
$env:TEMP = $TmpDir
$env:TMP = $TmpDir
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
$env:PYTHONUTF8 = '1'
Write-Ok "dane: $DataDir; pip-cache i pliki tymczasowe: $DataDir"

# --- 3. Środowisko Pythona i paczki ----------------------------------------------------------
Write-Host ''
Write-Host '3. Środowisko Pythona i paczki'
$VenvPy = Join-Path $Venv 'Scripts\python.exe'
if (Test-Path -LiteralPath $VenvPy) {
    $vv = Get-PythonVersion $VenvPy @()
    if (-not $vv -or $vv -lt $MinPython) {
        Stop-Setup "Środowisko $Venv nie działa albo ma za starego Pythona. Usuń ten katalog i uruchom setup.ps1 ponownie."
    }
    Write-Ok "środowisko istnieje: $Venv (Python $vv)"
} else {
    $rc = Invoke-Native $PyExe ($PyArgs + @('-m', 'venv', $Venv))
    if ($rc -ne 0 -or -not (Test-Path -LiteralPath $VenvPy)) { Stop-Setup "Nie udało się utworzyć środowiska $Venv." }
    Write-Ok "utworzono środowisko: $Venv"
}

Write-Host '  Instaluję paczki z requirements.txt (pierwszy raz potrzebny internet, kilka minut)...'
$rc = Invoke-Native $VenvPy @('-m', 'pip', 'install', '-r', (Join-Path $Repo 'requirements.txt'))
if ($rc -ne 0) { Stop-Setup 'Instalacja paczek nie powiodła się (komunikat pip powyżej). Sprawdź połączenie z internetem i uruchom setup.ps1 ponownie.' }
Write-Ok 'paczki zainstalowane'

# --- 4. OCR (opcjonalnie) --------------------------------------------------------------------
Write-Host ''
Write-Host '4. Tesseract OCR (opcjonalny, tylko do skanów PDF)'
$tess = $null
if ($cfg['TESSERACT_CMD']) { $tess = $cfg['TESSERACT_CMD'] }
elseif ($wanted.Contains('TESSERACT_CMD')) { $tess = $wanted['TESSERACT_CMD'] }
elseif (Get-Command tesseract -ErrorAction SilentlyContinue) { $tess = (Get-Command tesseract).Source }
if ($tess -and -not (Test-Path -LiteralPath $tess) -and (Get-Command $tess -ErrorAction SilentlyContinue)) {
    $tess = (Get-Command $tess).Source
}
if ($tess -and (Test-Path -LiteralPath $tess)) {
    $ErrorActionPreference = 'Continue'
    $langs = (& $tess --list-langs 2>&1 | Out-String)
    $ErrorActionPreference = 'Stop'
    if ($langs -match '(?m)^pol\s*$') { Write-Ok "Tesseract z językiem polskim: $tess" }
    else { Write-Warn "Tesseract bez języka polskiego (pol.traineddata): $tess. Doinstaluj język w instalatorze." }
} elseif ($tess) {
    Write-Warn "TESSERACT_CMD w .env wskazuje na nieistniejący plik: $tess"
} else {
    Write-Warn ("Brak Tesseract. Pliki PDF z tekstem i Word działają bez niego; skany wymagają OCR:`n" +
        "           winget install -e --id UB-Mannheim.TesseractOCR --location D:\Tools\Tesseract-OCR`n" +
        "           (w instalatorze zaznacz język Polish), potem uruchom setup.ps1 ponownie.")
}

# --- 5. Dane startowe ------------------------------------------------------------------------
Write-Host ''
Write-Host '5. Dane startowe UMB'
$seed = Join-Path $Repo 'scripts\seed.py'
$mark = Join-Path $DataDir '.seeded'
$dbFile = Join-Path $DataDir 'udip.sqlite'
if ($SkipSeed) {
    Write-Ok 'pominięto (-SkipSeed)'
} elseif (-not (Test-Path -LiteralPath $seed)) {
    Write-Warn 'scripts\seed.py jeszcze nie istnieje w tej wersji; run.ps1 wczyta dane, gdy się pojawi.'
} elseif ((Test-Path -LiteralPath $mark) -and (Test-Path -LiteralPath $dbFile) -and -not $Reseed) {
    Write-Ok 'dane już wczytane (od nowa: setup.ps1 -Reseed albo run.ps1 -Reseed)'
} else {
    # seed.py można uruchamiać wielokrotnie: istniejące sprawy zostają, chyba że --reset (-Reseed).
    $seedArgs = @($seed)
    if (-not $RealDates) {
        $demoDay = [Environment]::GetEnvironmentVariable('UDIP_TODAY')
        if (-not $demoDay) { $demoDay = $cfg['UDIP_TODAY'] }
        if (-not $demoDay) { $demoDay = Get-Date -Format 'yyyy-MM-dd' }
        $seedArgs += @('--demo-today', $demoDay)
    }
    if ($Reseed) { $seedArgs += '--reset' }
    $extra = [Environment]::GetEnvironmentVariable('UDIP_SEED_ARGS')
    if ($extra) { $seedArgs += @($extra -split '\s+' | Where-Object { $_ }) }
    Write-Host ('  scripts\seed.py ' + (($seedArgs | Select-Object -Skip 1) -join ' '))
    Push-Location -LiteralPath $Repo
    try { $rc = Invoke-Native $VenvPy $seedArgs } finally { Pop-Location }
    if ($rc -ne 0) { Stop-Setup 'scripts\seed.py zakończył się błędem (komunikat powyżej).' }
    [System.IO.File]::WriteAllText($mark, (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), (New-Object System.Text.UTF8Encoding($false)))
    Write-Ok "dane wczytane do $dbFile"
}

Write-Host ''
Write-Host 'Gotowe. Uruchomienie aplikacji:' -ForegroundColor Green
Write-Host '  powershell -ExecutionPolicy Bypass -File .\run.ps1'
