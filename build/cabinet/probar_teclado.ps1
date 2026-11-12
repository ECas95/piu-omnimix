# Prueba CON TECLADO del disco del cabinet ya grabado, sin escribirlo: capa temporal + modulo de prueba.
param([string]$Variant='trial',[int]$RamMB=2048)
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
function Fail($m){ Write-Host "`nERROR: $m" -ForegroundColor Red; exit 1 }
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Fail 'Clic derecho > Ejecutar como administrador.' }
$Qemu = @('C:\Program Files\qemu\qemu-system-x86_64.exe','C:\qemu\qemu-system-x86_64.exe') | Where-Object { Test-Path $_ } | Select-Object -First 1
$Py = 'C:\Users\USER\AppData\Local\Programs\Python\Python311\python.exe'
if (Get-Process -Name 'qemu-system-x86_64','qemu-nbd' -ErrorAction SilentlyContinue) { Fail 'Cerra QEMU primero.' }
$disks = Get-Disk | Where-Object { -not $_.IsSystem -and -not $_.IsBoot -and $_.Size -ge 858993459200 -and $_.PartitionStyle -eq 'MBR' }
if (-not $disks) { Fail 'No veo el disco del cabinet conectado.' }
$disks | Format-Table Number, FriendlyName, SerialNumber, @{n='GB';e={[math]::Round($_.Size/1e9)}} -AutoSize
$n = Read-Host 'Numero del disco del CABINET'
$disk = $disks | Where-Object { "$($_.Number)" -eq $n }; if (-not $disk) { Fail 'Numero invalido.' }
Set-Disk -Number $disk.Number -IsOffline $true
$ErrorActionPreference = 'Continue'
try {
  & $Py -B (Join-Path $Here 'teclado.py') $disk.Number $Variant
  if ($LASTEXITCODE -ne 0) { Fail 'No se pudo preparar la capa de prueba.' }
  Write-Host "RAM de la VM: $RamMB MB" -ForegroundColor Yellow
  Write-Host "`nTeclado P1: Q E (arriba) / S (centro y START) / Z C (abajo). 5 = credito. Cerra la ventana para terminar." -ForegroundColor Cyan
  & $Qemu -name 'PIU MK9 disco grabado + teclado (capa temporal)' -machine pc -accel whpx,kernel-irqchip=off -accel tcg,thread=multi `
    -cpu qemu64,+sse2,+sse3,-svm -smp 4,sockets=1,cores=4,threads=1 -m $RamMB `
    -drive "file=$(Join-Path $Here 'teclado_capa.qcow2'),format=qcow2,if=ide,index=0,media=disk" `
    -boot c -vga none -device virtio-vga-gl,xres=1280,yres=720 -display sdl,gl=on `
    -device intel-hda -device hda-duplex -usb -device usb-kbd -net none -rtc base=localtime `
    -serial "file:$(Join-Path $Here 'logs\qemu_teclado_serial.log')"
  if ($Variant -eq 'bga') { & $Py -B (Join-Path $Here 'teclado_log.py') }
} finally { Set-Disk -Number $disk.Number -IsOffline $false }
Write-Host "`nListo. El disco no se modifico; la capa temporal (teclado_capa.qcow2) se recrea en cada prueba." -ForegroundColor Green
