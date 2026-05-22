$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FfmpegDir = Join-Path $ProjectRoot "ffmpeg"
$DownloadUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$ChecksumUrl = "$DownloadUrl.sha256"
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("chzzk-rekoda-ffmpeg-" + [System.Guid]::NewGuid().ToString("N"))
$ZipPath = Join-Path $TempRoot "ffmpeg-release-essentials.zip"
$ChecksumPath = Join-Path $TempRoot "ffmpeg-release-essentials.zip.sha256"
$ExtractDir = Join-Path $TempRoot "extract"
$StagingDir = Join-Path $ProjectRoot "ffmpeg.new"
$BackupDir = Join-Path $ProjectRoot "ffmpeg.old"

function Enable-Tls12 {
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor 3072
    } catch {
        try {
            [Net.ServicePointManager]::SecurityProtocol = 3072
        } catch {
            Write-Host "Could not force TLS 1.2; continuing with system defaults."
        }
    }
}

function Download-FileWithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $lastError = $null
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Write-Host "Downloading $Url (attempt $attempt/3)"
            Remove-Item -LiteralPath $Destination -Force -ErrorAction SilentlyContinue
            Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing -TimeoutSec 120
            if ((Test-Path -LiteralPath $Destination) -and ((Get-Item -LiteralPath $Destination).Length -gt 0)) {
                return
            }
            throw "Downloaded file is empty: $Destination"
        } catch {
            $lastError = $_
            Start-Sleep -Seconds (2 * $attempt)
            try {
                $client = New-Object Net.WebClient
                $client.DownloadFile($Url, $Destination)
                if ((Test-Path -LiteralPath $Destination) -and ((Get-Item -LiteralPath $Destination).Length -gt 0)) {
                    return
                }
                throw "Downloaded file is empty: $Destination"
            } catch {
                $lastError = $_
                Start-Sleep -Seconds (2 * $attempt)
            }
        }
    }

    throw "Failed to download $Url. Last error: $lastError"
}

function Verify-Sha256 {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string]$ChecksumFile
    )

    $checksumText = Get-Content -LiteralPath $ChecksumFile -Raw
    $expected = [regex]::Match($checksumText, "[A-Fa-f0-9]{64}").Value.ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($expected)) {
        throw "Could not read SHA256 checksum from $ChecksumFile"
    }

    $actual = (Get-FileHash -LiteralPath $FilePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expected) {
        throw "SHA256 mismatch for ffmpeg archive. Expected $expected but got $actual"
    }
}

try {
    Enable-Tls12
    New-Item -ItemType Directory -Path $TempRoot, $ExtractDir -Force | Out-Null

    Download-FileWithRetry -Url $DownloadUrl -Destination $ZipPath
    Download-FileWithRetry -Url $ChecksumUrl -Destination $ChecksumPath
    Verify-Sha256 -FilePath $ZipPath -ChecksumFile $ChecksumPath

    Write-Host "Extracting ffmpeg archive"
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractDir -Force

    $ffmpegExe = Get-ChildItem -LiteralPath $ExtractDir -Filter "ffmpeg.exe" -Recurse -File |
        Where-Object { $_.FullName -match "[\\/]bin[\\/]ffmpeg\.exe$" } |
        Select-Object -First 1

    if ($null -eq $ffmpegExe) {
        throw "ffmpeg.exe was not found in the downloaded archive."
    }

    $sourceRoot = Split-Path -Parent (Split-Path -Parent $ffmpegExe.FullName)
    Remove-Item -LiteralPath $StagingDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $BackupDir -Recurse -Force -ErrorAction SilentlyContinue
    Copy-Item -LiteralPath $sourceRoot -Destination $StagingDir -Recurse -Force

    if (Test-Path -LiteralPath $FfmpegDir) {
        Move-Item -LiteralPath $FfmpegDir -Destination $BackupDir -Force
    }
    Move-Item -LiteralPath $StagingDir -Destination $FfmpegDir -Force
    Remove-Item -LiteralPath $BackupDir -Recurse -Force -ErrorAction SilentlyContinue

    $installedFfmpeg = Join-Path $FfmpegDir "bin\ffmpeg.exe"
    if (-not (Test-Path -LiteralPath $installedFfmpeg)) {
        throw "Installed ffmpeg.exe was not found at $installedFfmpeg"
    }

    & $installedFfmpeg -version | Select-Object -First 1
    if ($LASTEXITCODE -ne 0) {
        throw "Installed ffmpeg.exe did not run successfully."
    }

    Write-Host "ffmpeg installed successfully: $installedFfmpeg"
} finally {
    Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
