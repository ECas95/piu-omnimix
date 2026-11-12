# Arranca en QEMU el disco del cabinet YA GRABADO, en modo snapshot (no se escribe nada en el disco).
# Sin PIUIO no hay entradas: la prueba valida arranque autonomo + carga del juego. La salida del juego (tee /dev/ttyS0)
# queda en logs\qemu_disco_serial.log.
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Need = 858993459200
function Fail($m){ Write-Host "`nERROR: $m" -ForegroundColor Red; exit 1 }
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Fail 'Clic derecho > Ejecutar como administrador.' }
$Qemu = @('C:\Program Files\qemu\qemu-system-x86_64.exe','C:\qemu\qemu-system-x86_64.exe') | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Qemu) { Fail 'No encuentro QEMU.' }
if (Get-Process -Name 'qemu-system-x86_64' -ErrorAction SilentlyContinue) { Fail 'Ya hay un QEMU abierto.' }
$disks = Get-Disk | Where-Object { -not $_.IsSystem -and -not $_.IsBoot -and $_.Size -ge $Need }
if (-not $disks) { Fail 'No veo el disco del cabinet conectado.' }
$disks | Format-Table Number, FriendlyName, SerialNumber, @{n='GB';e={[math]::Round($_.Size/1e9)}}, PartitionStyle -AutoSize
$n = Read-Host 'Numero del disco del CABINET'
$disk = $disks | Where-Object { "$($_.Number)" -eq $n }; if (-not $disk) { Fail 'Numero invalido.' }
$logs = Join-Path $Here 'logs'; New-Item -ItemType Directory -Force $logs | Out-Null
$serial = Join-Path $logs 'qemu_disco_serial.log'; if (Test-Path $serial) { Remove-Item $serial }
Set-Disk -Number $disk.Number -IsOffline $true
try {
  Write-Host "`nArrancando disco $($disk.Number) en modo snapshot (nada se guarda en el disco)..." -ForegroundColor Cyan
  Write-Host 'Sin PIUIO el juego no responde al teclado: es lo esperado. Cerra la ventana de QEMU para terminar.'
  $ErrorActionPreference = 'Continue'   # QEMU warnings on stderr must not abort the run (PowerShell 5.1)
  & $Qemu -name 'PIU MK9 disco grabado (snapshot)' -machine pc -accel whpx,kernel-irqchip=off -accel tcg,thread=multi `
    -cpu qemu64,+sse2,+sse3,-svm -smp 4,sockets=1,cores=4,threads=1 -m 2048 `
    -drive "file=\\.\PhysicalDrive$($disk.Number),format=raw,if=ide,index=0,media=disk,snapshot=on" `
    -boot c -vga none -device virtio-vga-gl,xres=1280,yres=720 -display sdl,gl=on `
    -device intel-hda -device hda-duplex -usb -device usb-kbd -net none -rtc base=localtime `
    -serial "file:$serial"
  Write-Host "QEMU termino (codigo $LASTEXITCODE)."
} finally { Set-Disk -Number $disk.Number -IsOffline $false }
Write-Host "`nListo. Log del juego: $serial" -ForegroundColor Green
