# Copia los logs del disco del cabinet a la PC (solo lectura). Ejecutar como administrador.
$ErrorActionPreference = 'Stop'
function Fail($m){ Write-Host "`nERROR: $m" -ForegroundColor Red; exit 1 }
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Fail 'Clic derecho > Ejecutar como administrador.' }
$disks = Get-Disk | Where-Object { -not $_.IsSystem -and -not $_.IsBoot -and $_.Size -ge 858993459200 -and $_.PartitionStyle -eq 'MBR' }
if (-not $disks) { Fail 'No veo el disco del cabinet conectado.' }
$disks | Format-Table Number, FriendlyName, SerialNumber, @{n='GB';e={[math]::Round($_.Size/1e9)}} -AutoSize
$n = Read-Host 'Numero del disco del CABINET'
$disk = $disks | Where-Object { "$($_.Number)" -eq $n }; if (-not $disk) { Fail 'Numero invalido.' }
$ErrorActionPreference = 'Continue'
wsl --mount "\\.\PHYSICALDRIVE$($disk.Number)" --bare
try { wsl -d Ubuntu -u root -- bash '/mnt/d/Pump It Up Data/PIU/final_v363/cabinet/leer_logs.sh' }
finally { wsl --unmount "\\.\PHYSICALDRIVE$($disk.Number)" | Out-Null }
Write-Host "`nLogs en D:\Pump It Up Data\PIU\final_v363\cabinet\logs\desde_cabinet" -ForegroundColor Green
