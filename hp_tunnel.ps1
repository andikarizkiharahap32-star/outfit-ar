# ============================================================
# OutfitAR - HP Tunnel (Terminal 3)
# KHUSUS untuk akses dari HP via internet.
#
# Setup 3 Terminal:
#   Terminal 1 : uvicorn (backend port 8000)
#   Terminal 2 : npm run dev (localhost:5173) -> LAPTOP
#   Terminal 3 : script ini -> URL untuk HP
#
# Yang dilakukan script ini:
#   - ngrok       -> Backend  port 8000 (HTTPS publik)
#   - cloudflared -> Frontend port 5173 (HTTPS publik)
#   - Auto-update frontend/.env dengan URL ngrok backend
# ============================================================

$FRONTEND_PORT   = 5173
$BACKEND_PORT    = 8000
$SCRIPT_DIR      = Split-Path -Parent $MyInvocation.MyCommand.Path
$ENV_FILE        = Join-Path $SCRIPT_DIR "frontend\.env"
$CLOUDFLARED_EXE = "C:\Final_outfitAR\cloudflared.exe"
$NGROK_API       = "http://localhost:4040/api/tunnels"

function Write-Status($msg, $color = "White") {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" -ForegroundColor $color
}

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

function Get-CloudflaredUrl($jobOutput) {
    if ($jobOutput -match "(https://[a-z0-9\-]+\.trycloudflare\.com)") {
        return $matches[1]
    }
    return $null
}

function Update-EnvFile($beUrl) {
    $wsUrl = $beUrl -replace "^https://", "wss://"
    Set-Content -Path $ENV_FILE -Value "VITE_API_URL=$beUrl`nVITE_WS_URL=$wsUrl`n" -Encoding UTF8
    Write-Status "[ENV] frontend/.env diupdate -> $beUrl" "Cyan"

    # Restart Vite agar VITE_API_URL baru ter-embed ke bundle
    # (Vite hanya baca .env saat pertama start — harus restart biar URL ngrok aktif di HP)
    Write-Status "[VITE] Restart Vite agar .env baru aktif..." "Yellow"
    $nodeOnPort = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1
    if ($nodeOnPort) {
        Stop-Process -Id $nodeOnPort -Force -ErrorAction SilentlyContinue
        Write-Status "[VITE] Vite lama dihentikan (PID $nodeOnPort)" "DarkGray"
    }
    Start-Sleep -Seconds 2

    # Jalankan Vite lagi di background
    $frontendDir = Join-Path (Split-Path -Parent $SCRIPT_DIR) "outfit-ar\frontend"
    if (-not (Test-Path $frontendDir)) {
        $frontendDir = Join-Path $SCRIPT_DIR "frontend"
    }
    Start-Process -FilePath "cmd" `
        -ArgumentList "/c", "cd /d `"$frontendDir`" && npm run dev" `
        -WindowStyle Minimized
    Write-Status "[VITE] Vite di-restart di background (tunggu 5 detik sebelum buka di HP)" "Green"
    Start-Sleep -Seconds 5
}


# ============================================================
# MAIN
# ============================================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  OutfitAR - HP TUNNEL (Terminal 3)" -ForegroundColor Magenta
Write-Host "  Laptop pakai : http://localhost:5173" -ForegroundColor White
Write-Host "  HP pakai     : URL di bawah ini" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

# Kill proses lama
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Job -Name "CF_HP" -ErrorAction SilentlyContinue | Stop-Job -ErrorAction SilentlyContinue
Get-Job -Name "CF_HP" -ErrorAction SilentlyContinue | Remove-Job -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Start ngrok untuk Backend
Write-Status "[NGROK] Membuka tunnel backend port $BACKEND_PORT untuk HP..." "Yellow"
Start-Process -FilePath "ngrok" -ArgumentList "http", "$BACKEND_PORT" -WindowStyle Hidden

# Start cloudflared untuk Frontend
Write-Status "[CF] Membuka tunnel frontend port $FRONTEND_PORT untuk HP..." "Yellow"
$cfJob = Start-Job -Name "CF_HP" -ScriptBlock {
    param($exe, $port)
    & $exe tunnel --url "http://localhost:$port" 2>&1
} -ArgumentList $CLOUDFLARED_EXE, $FRONTEND_PORT

# Tunggu kedua URL siap (maks 40 detik)
Write-Status "Menunggu URL HP siap (maks 40 detik)..." "Yellow"
$feUrl = $null
$beUrl = $null

for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 2

    if (-not $beUrl) { $beUrl = Get-NgrokUrl }
    if (-not $feUrl) {
        $out   = $cfJob | Receive-Job -Keep 2>&1 | Out-String
        $feUrl = Get-CloudflaredUrl $out
    }

    $s = ""
    if ($beUrl) { $s += "[BE:OK] " } else { $s += "[BE:wait] " }
    if ($feUrl) { $s += "[FE:OK]" }  else { $s += "[FE:wait]" }
    Write-Status $s "DarkGray"

    if ($feUrl -and $beUrl) { break }
}

# ============================================================
# Tampilkan hasil
# ============================================================
if ($feUrl -and $beUrl) {
    Update-EnvFile $beUrl

    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  URL UNTUK HP - KETIK DI BROWSER HP ANDA" -ForegroundColor Yellow
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  [BUKA DI HP] $feUrl" -ForegroundColor Yellow
    Write-Host "  [BACKEND]    $beUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Laptop tetap pakai : http://localhost:5173" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Status "Tunnel HP aktif. Tekan CTRL+C untuk berhenti." "Green"

    # Monitoring: jaga jendela tetap terbuka dan cek kondisi tunnel
    while ($true) {
        Start-Sleep -Seconds 30
        $checkBe  = Get-NgrokUrl
        $checkOut = $cfJob | Receive-Job -Keep 2>&1 | Out-String
        $checkFe  = Get-CloudflaredUrl $checkOut
        $ts       = Get-Date -Format "HH:mm:ss"

        if ($checkBe -and $checkFe) {
            Write-Host "[$ts] HP Tunnel OK - Buka: $feUrl" -ForegroundColor DarkGray
        } else {
            Write-Status "[WARN] Tunnel HP mati! Jalankan ulang script ini." "Red"
        }
    }

} else {
    Write-Host ""
    Write-Status "[ERROR] Tunnel HP gagal aktif:" "Red"
    if (-not $beUrl) {
        Write-Status "  ngrok GAGAL       - pastikan backend sudah jalan di port 8000" "Red"
    }
    if (-not $feUrl) {
        Write-Status "  cloudflared GAGAL - cek koneksi internet" "Red"
    }
    Write-Host ""
    Write-Host "Tekan Enter untuk keluar..."
    Read-Host
}
