$ErrorActionPreference = 'Stop'
function Fail($m){ Write-Host "`nERROR: $m" -ForegroundColor Red; exit 1 }
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Fail 'Clic derecho > Ejecutar como administrador.' }
$disks = Get-Disk | Where-Object { -not $_.IsSystem -and -not $_.IsBoot -and $_.Size -ge 30GB }
$disks | Format-Table Number, FriendlyName, SerialNumber, @{n='GB';e={[math]::Round($_.Size/1e9)}}, PartitionStyle -AutoSize
$n = Read-Host 'Numero del disco ORIGINAL de PRIME (solo se lee)'
$disk = $disks | Where-Object { "$($_.Number)" -eq $n }; if (-not $disk) { Fail 'Numero invalido.' }
$ErrorActionPreference = 'Continue'
wsl --mount "\\.\PHYSICALDRIVE$($disk.Number)" --bare
if ($LASTEXITCODE -ne 0) { Fail 'WSL no pudo montar el disco.' }
try { wsl -d Ubuntu -u root -- bash '/mnt/d/Pump It Up Data/PIU/final_v363/diag/leer_original.sh' }
finally { wsl --unmount "\\.\PHYSICALDRIVE$($disk.Number)" | Out-Null }
Write-Host "`nListo: D:\Pump It Up Data\PIU\final_v363\diag\disco_original" -ForegroundColor Green
