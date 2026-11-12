param([string]$Mode)
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
if ($LASTEXITCODE -ne 0) { Fail 'WSL no pudo montar el disco.' }
try { wsl -d Ubuntu -u root -- bash '/mnt/d/Pump It Up Data/PIU/final_v363/patch10/aplicar.sh'; $code=$LASTEXITCODE }
finally { wsl --unmount "\\.\PHYSICALDRIVE$($disk.Number)" | Out-Null }
if ($code -ne 0) { Fail "No se aplico el parche 10 (codigo $code)." }
Write-Host "`nListo." -ForegroundColor Green
