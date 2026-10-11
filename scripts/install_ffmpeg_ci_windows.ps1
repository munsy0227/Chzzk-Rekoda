# CI requires the full build: essentials does not include libsvtav1.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Stop-Install {
    param([string]$Stage)
    & uv run --no-sync python scripts/run_recording_test.py windows-error $Stage
    exit 1
}

$archiveTool = (Get-Command 7z -ErrorAction Stop).Source
$installRoot = Join-Path $env:RUNNER_TEMP "chzzk-ffmpeg-full"
$archive = Join-Path $env:RUNNER_TEMP "ffmpeg-release-full.7z"
$checksumFile = "$archive.sha256"
$url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z"

Invoke-WebRequest -Uri $url -OutFile $archive -TimeoutSec 120
Invoke-WebRequest -Uri "$url.sha256" -OutFile $checksumFile -TimeoutSec 120
$checksum = Get-Content -LiteralPath $checksumFile -Raw
$expected = [regex]::Match($checksum, '\b[A-Fa-f0-9]{64}\b').Value.ToLowerInvariant()
$actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if (-not $expected -or $actual -ne $expected) {
    Stop-Install "SHA256"
}

New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
& $archiveTool x $archive "-o$installRoot" -y | Out-Null
if ($LASTEXITCODE -ne 0) {
    Stop-Install "7z/$LASTEXITCODE"
}
$binaries = @(Get-ChildItem -LiteralPath $installRoot -Filter ffmpeg.exe -Recurse -File |
    Where-Object { $_.FullName -match '[\\/]bin[\\/]ffmpeg\.exe$' })
if ($binaries.Count -ne 1) {
    Stop-Install "ffmpeg.exe/count=$($binaries.Count)"
}
$binDirectory = $binaries[0].DirectoryName
if (-not (Test-Path -LiteralPath (Join-Path $binDirectory "ffprobe.exe"))) {
    Stop-Install "ffprobe.exe"
}
& $binaries[0].FullName -version
if ($LASTEXITCODE -ne 0) {
    Stop-Install "ffmpeg/$LASTEXITCODE"
}
$binDirectory | Out-File -FilePath $env:GITHUB_PATH -Encoding utf8 -Append
Remove-Item -LiteralPath $archive -Force
Remove-Item -LiteralPath $checksumFile -Force
