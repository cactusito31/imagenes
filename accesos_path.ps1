param(
  [Parameter(Mandatory=$true)][ValidateSet('install','uninstall')][string]$Action,
  [Parameter(Mandatory=$true)][string]$AppDir,
  [string]$AppName = 'Imagenes',
  [string]$Icon = ''
)
$ErrorActionPreference = 'Stop'

$desktop   = [Environment]::GetFolderPath('Desktop')
$programs  = [Environment]::GetFolderPath('Programs')   # menu Inicio del usuario
$exe       = Join-Path $AppDir 'imagenes.exe'
if ([string]::IsNullOrWhiteSpace($Icon)) { $Icon = $exe }
$targets = @(
  (Join-Path $programs ($AppName + '.lnk')),
  (Join-Path $desktop  ($AppName + '.lnk'))
)

if ($Action -eq 'install') {
  $w = New-Object -ComObject WScript.Shell
  foreach ($t in $targets) {
    $s = $w.CreateShortcut($t)
    $s.TargetPath       = $exe
    $s.IconLocation     = $Icon
    $s.WorkingDirectory = $AppDir
    $s.Description      = 'Conversor de imagenes'
    $s.Save()
    Write-Host ("  acceso creado: " + $t)
  }
  $p = [Environment]::GetEnvironmentVariable('PATH','User'); if (-not $p) { $p = '' }
  if (($p -split ';') -notcontains $AppDir) {
    $new = ($p.TrimEnd(';') + ';' + $AppDir).TrimStart(';')
    [Environment]::SetEnvironmentVariable('PATH', $new, 'User')
    Write-Host '  PATH de usuario actualizado.'
  }
}
else {
  foreach ($t in $targets) { Remove-Item $t -ErrorAction SilentlyContinue }
  $p = [Environment]::GetEnvironmentVariable('PATH','User')
  if ($p) {
    $new = (($p -split ';') | Where-Object { $_ -and $_ -ne $AppDir }) -join ';'
    [Environment]::SetEnvironmentVariable('PATH', $new, 'User')
  }
  Write-Host '  accesos directos y PATH eliminados.'
}
