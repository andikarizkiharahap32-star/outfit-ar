# ============================================================
# OutfitAR - Auto Tunnel Manager FINAL v3
# Strategi TERBUKTI BEKERJA:
#   - ngrok        -> Backend  port 8000 (stabil, pakai authtoken)
#   - cloudflared  -> Frontend port 5173 (gratis, stabil, tanpa login)
#
# Kenapa bukan localtunnel?
#   Server loca.lt sering DOWN / diblokir ISP Indonesia.
#
# Cara pakai:
#   powershell -ExecutionPolicy Bypass -File tunnel_manager.ps1
# ============================================================

$FRONTEND_PORT    = 5173
$BACKEND_PORT     = 8000
$SCRIPT_DIR       = Split-Path -Parent $MyInvocation.MyCommand.Path
$ENV_FILE         = Join-Path $SCRIPT_DIR "frontend\.env"
$CHECK_INTERVAL   = 20
$NGROK_API        = "http://localhost:4040/api/tunnels"
$CLOUDFLARED_EXE  = "C:\Final_outfitAR\cloudflared.exe"

$ltJob = $null

function Write-Status($msg, $color = "White") {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" -ForegroundColor $color
}

# ----------------------------------------------------------
# Ambil URL ngrok Backend dari API lokal
# ----------------------------------------------------------
function Get-NgrokUrl {
    try {
        $resp    = Invoke-WebRequest -Uri $NGROK_API -UseBasicParsing -TimeoutSec 4 -ErrorAction Stop
        $tunnels = ($resp.Content | ConvertFrom-Json).tunnels
        foreach ($t in $tunnels) {
            if ($t.proto -eq "https") { return $t.public_url }
        }
    } catch {}
    return $null
}

# ----------------------------------------------------------
# Ambil URL cloudflared Frontend dari output Job
# ----------------------------------------------------------
function Get-CloudflaredUrl($jobOutput) {
    # cloudflared prints: https://xxxx.trycloudflare.com
    if ($jobOutput -match "(https://[a-z0-9\-]+\.trycloudflare\.com)") {
        return $matches[1]
    }
    return $null
}

# ----------------------------------------------------------
# Update frontend/.env dengan URL backend terbaru
# ----------------------------------------------------------
function Update-EnvFile($beUrl) {
    $wsUrl = $beUrl -replace "^https://", "wss://"
    Set-Content -Path $ENV_FILE -Value "VITE_API_URL=$beUrl`nVITE_WS_URL=$wsUrl`n" -Encoding UTF8
    Write-Status "[ENV] frontend/.env diupdate -> $beUrl" "Cyan"
}

# ----------------------------------------------------------
# Tampilkan URL yang aktif
# ----------------------------------------------------------
function Print-Urls($feUrl, $beUrl) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  TUNNEL AKTIF - BUKA DI HP/BROWSER!" -ForegroundColor Yellow
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  [BUKA DI HP] $feUrl" -ForegroundColor Yellow
    Write-Host "  [BACKEND]    $beUrl" -ForegroundColor Cyan
    Write-Host "  Auto-restart : AKTIF (setiap ${CHECK_INTERVAL}s)" -ForegroundColor DarkGray
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
}

# ----------------------------------------------------------
# Start semua tunnel
# ----------------------------------------------------------
function Start-Tunnels {
    # --- Kill proses lama ---
    Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-Job -Name "CF_Frontend" -ErrorAction SilentlyContinue | Stop-Job -ErrorAction SilentlyContinue
    Get-Job -Name "CF_Frontend" -ErrorAction SilentlyContinue | Remove-Job -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    # --- Start ngrok untuk Backend ---
    Write-Status "[NGROK] Tunnel backend port $BACKEND_PORT..." "Yellow"
    Start-Process -FilePath "ngrok" `
        -ArgumentList "http", "$BACKEND_PORT" `
        -WindowStyle Hidden

    # --- Start cloudflared untuk Frontend (sebagai Background Job) ---
    Write-Status "[CF] Tunnel frontend port $FRONTEND_PORT via Cloudflare..." "Yellow"
    $job = Start-Job -Name "CF_Frontend" -ScriptBlock {
        param($exe, $port)
        # cloudflared quick tunnel: tidak perlu login, URL random per session
        & $exe tunnel --url "http://localhost:$port" 2>&1
    } -ArgumentList $CLOUDFLARED_EXE, $FRONTEND_PORT

    return $job
}

# ----------------------------------------------------------
# Tunggu kedua URL aktif (max $maxSec detik)
# ----------------------------------------------------------
function Wait-ForBothUrls($cfJob, $maxSec = 40) {
    $feUrl = $null
    $beUrl = $null

    for ($i = 0; $i -lt ($maxSec / 2); $i++) {
        Start-Sleep -Seconds 2

        if (-not $beUrl) {
            $beUrl = Get-NgrokUrl
        }

        if (-not $feUrl -and $cfJob) {
            $out   = $cfJob | Receive-Job -Keep 2>&1 | Out-String
            $feUrl = Get-CloudflaredUrl $out
        }

        $status = ""
        if ($beUrl) { $status += "[BE:OK] " } else { $status += "[BE:wait] " }
        if ($feUrl) { $status += "[FE:OK]" }  else { $status += "[FE:wait]" }
        Write-Status $status "DarkGray"

        if ($feUrl -and $beUrl) { break }
    }
    return @($feUrl, $beUrl)
}

# ============================================================
# MAIN
# ============================================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  OutfitAR Tunnel Manager v3 FINAL" -ForegroundColor Green
Write-Host "  ngrok(BE:8000) + Cloudflare(FE:5173)" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

$ltJob = Start-Tunnels
Write-Status "Menunggu kedua tunnel aktif (maks 40 detik)..." "Yellow"
$urls      = Wait-ForBothUrls $ltJob 40
$lastFeUrl = $urls[0]
$lastBeUrl = $urls[1]

if ($lastFeUrl -and $lastBeUrl) {
    Update-EnvFile $lastBeUrl
    Print-Urls $lastFeUrl $lastBeUrl
} else {
    Write-Status "[ERROR] Salah satu tunnel gagal aktif:" "Red"
    if (-not $lastBeUrl) { Write-Status "  ngrok backend (8000)       : GAGAL - pastikan ngrok sudah login" "Red" }
    if (-not $lastFeUrl) { Write-Status "  cloudflared frontend (5173) : GAGAL - cek koneksi internet" "Red" }
}

# ============================================================
# MONITORING LOOP - Auto-restart jika tunnel mati
# ============================================================
while ($true) {
    Start-Sleep -Seconds $CHECK_INTERVAL

    $beUrl = Get-NgrokUrl
    $out   = $ltJob | Receive-Job -Keep 2>&1 | Out-String
    $feUrl = Get-CloudflaredUrl $out

    $beOk = $null -ne $beUrl
    $feOk = $null -ne $feUrl

    if (-not $beOk -or -not $feOk) {
        Write-Status "[WARN] Tunnel mati (BE:$beOk FE:$feOk)! Restart..." "Red"

        $ltJob = Start-Tunnels
        $urls  = Wait-ForBothUrls $ltJob 40
        $feUrl = $urls[0]
        $beUrl = $urls[1]

        if (-not $feUrl -or -not $beUrl) {
            Write-Status "[ERROR] Restart gagal. Coba lagi dalam ${CHECK_INTERVAL}s..." "Red"
            continue
        }

        Update-EnvFile $beUrl
        Print-Urls $feUrl $beUrl
        $lastBeUrl = $beUrl
        $lastFeUrl = $feUrl
        continue
    }

    # Update .env jika URL backend berubah setelah restart
    if ($beUrl -ne $lastBeUrl) {
        Update-EnvFile $beUrl
        $lastBeUrl = $beUrl
        $lastFeUrl = $feUrl
        Print-Urls $feUrl $beUrl
    } else {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] OK | HP: $feUrl" -ForegroundColor DarkGray
    }
}
