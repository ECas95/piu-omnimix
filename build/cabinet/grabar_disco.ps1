# Graba la imagen de gabinete v379 (MK9, PIUIO original) en el disco fisico del cabinet y la verifica.
# Ejecutar como administrador desde GRABAR_DISCO_CABINET.bat. BORRA TODO el disco elegido.
$ErrorActionPreference = 'Stop'
$Here  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Image = Join-Path $Here 'PRIME_V379_CABINET.qcow2'
$Qemu  = 'C:\Program Files\qemu\qemu-img.exe'
$Need  = 858993459200   # 800 GiB

function Fail($msg) { Write-Host "`nERROR: $msg" -ForegroundColor Red; exit 1 }

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Fail 'Abri el .bat con clic derecho > Ejecutar como administrador.' }
if (-not (Test-Path $Image)) { Fail "No encuentro $Image" }
if (-not (Test-Path $Qemu)) { Fail "No encuentro $Qemu" }
if (-not (Test-Path 'E:\Pump It Up Data\PIU\anime_final_v8\PRIME_TROPICANIC_ROUTE.qcow2')) { Fail 'Conecta el disco E: (la imagen base vive ahi).' }
if (Get-Process -Name 'qemu-system-x86_64','qemu-nbd' -ErrorAction SilentlyContinue) { Fail 'Cerra QEMU antes de grabar.' }
$v = Get-Content (Join-Path $Here 'cabinet_verified.json') -Raw | ConvertFrom-Json
if (-not $v.pass_) { Fail 'La imagen de gabinete no esta verificada.' }

Write-Host "Imagen: $Image" -ForegroundColor Cyan
Write-Host "Discos que se pueden usar (no sistema, no arranque, >= 800 GiB):`n"
$disks = Get-Disk | Where-Object { -not $_.IsSystem -and -not $_.IsBoot -and $_.Size -ge $Need }
if (-not $disks) { Fail 'No hay ningun disco valido conectado (el del cabinet tiene que ser de 1 TB y no puede ser el de Windows).' }
$disks | Format-Table Number, FriendlyName, SerialNumber, @{n='GB';e={[math]::Round($_.Size/1e9)}}, BusType, PartitionStyle -AutoSize
$n = Read-Host 'Numero del disco del CABINET a grabar'
$disk = $disks | Where-Object { "$($_.Number)" -eq $n }
if (-not $disk) { Fail 'Ese numero no esta en la lista.' }
$vols = Get-Partition -DiskNumber $disk.Number -ErrorAction SilentlyContinue | Get-Volume -ErrorAction SilentlyContinue | Where-Object DriveLetter
Write-Host "`nVAS A BORRAR POR COMPLETO: Disco $($disk.Number) - $($disk.FriendlyName) - $([math]::Round($disk.Size/1e9)) GB" -ForegroundColor Yellow
if ($vols) { Write-Host ("Tiene las unidades: " + (($vols | ForEach-Object { "$($_.DriveLetter):" }) -join ' ')) -ForegroundColor Yellow }
$ok = Read-Host 'Escribi GRABAR para continuar'
if ($ok -ne 'GRABAR') { Fail 'Cancelado.' }

$target = "\\.\PhysicalDrive$($disk.Number)"
Set-Disk -Number $disk.Number -IsReadOnly $false
Set-Disk -Number $disk.Number -IsOffline $true   # Windows deja de usar sus volumenes mientras se graba
try {
    Write-Host "`n[1/2] Grabando (puede tardar varias horas; la imagen base se lee desde E:)..." -ForegroundColor Cyan
    & $Qemu convert -p -f qcow2 -O raw -n $Image $target
    if ($LASTEXITCODE -ne 0) { Fail "qemu-img convert termino con codigo $LASTEXITCODE. El disco quedo incompleto: volve a ejecutar." }
    Write-Host "`n[2/2] Verificando byte a byte contra la imagen..." -ForegroundColor Cyan
    & $Qemu compare -p -f qcow2 -F raw $Image $target
    if ($LASTEXITCODE -ne 0) { Fail "La verificacion encontro diferencias (codigo $LASTEXITCODE). No uses este disco; volve a grabar." }
} finally {
    Set-Disk -Number $disk.Number -IsOffline $false
}
$log = Join-Path $Here 'grabado_disco.json'
@{ disk_number=$disk.Number; model=$disk.FriendlyName; serial=$disk.SerialNumber; image=$Image; verified=$true; date=(Get-Date).ToString('s') } | ConvertTo-Json | Set-Content -Encoding utf8 $log
Write-Host "`nLISTO: disco grabado y verificado. Desconectalo y ponelo en el MK9." -ForegroundColor Green
Write-Host 'En el primer arranque el sistema detecta la placa NVIDIA, configura el driver y reinicia una vez: es normal.'
