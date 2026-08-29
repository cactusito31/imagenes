<#
  Crea o elimina la integracion de Imagenes con Windows:
    - accesos directos en Escritorio y Menu Inicio
    - acceso en "Enviar a"            (clic derecho > Enviar a > Imagenes)
    - entrada en el menu contextual   (clic derecho sobre una carpeta)
    - carpeta en el PATH del usuario
    - registro en "Agregar o quitar programas"
  Todo en HKCU: no necesita permisos de administrador.
#>
param(
  [Parameter(Mandatory=$true)][ValidateSet('install','uninstall')][string]$Action,
  [Parameter(Mandatory=$true)][string]$AppDir,
  [string]$AppName = 'Imagenes',
  [string]$Icon = '',
  [string]$Version = ''
)
$ErrorActionPreference = 'Stop'

$desktop  = [Environment]::GetFolderPath('Desktop')
$programs = [Environment]::GetFolderPath('Programs')
$sendto   = [Environment]::GetFolderPath('SendTo')
$exe      = Join-Path $AppDir 'imagenes.exe'
if ([string]::IsNullOrWhiteSpace($Icon)) { $Icon = $exe }

$shortcuts = @(
  (Join-Path $programs ($AppName + '.lnk')),
  (Join-Path $desktop  ($AppName + '.lnk')),
  (Join-Path $sendto   ($AppName + '.lnk'))
)

$regShell   = 'HKCU:\Software\Classes\Directory\shell\' + $AppName
$regBack    = 'HKCU:\Software\Classes\Directory\Background\shell\' + $AppName
$regUninst  = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\' + $AppName

function New-Shortcut($path, $target, $arguments) {
  $w = New-Object -ComObject WScript.Shell
  $s = $w.CreateShortcut($path)
  $s.TargetPath       = $target
  $s.Arguments        = $arguments
  $s.IconLocation     = $Icon
  $s.WorkingDirectory = $AppDir
  $s.Description      = 'Conversor de imagenes'
  $s.Save()
}

function Set-ContextMenu($key, $argToken) {
  New-Item -Path $key -Force | Out-Null
  New-Item -Path ($key + '\command') -Force | Out-Null
  Set-ItemProperty -Path $key -Name '(Default)' -Value 'Convertir imagenes'
  Set-ItemProperty -Path $key -Name 'Icon' -Value $exe
  Set-ItemProperty -Path ($key + '\command') -Name '(Default)' `
                   -Value ('"' + $exe + '" "' + $argToken + '"')
}

if ($Action -eq 'install') {

  if (-not (Test-Path $exe)) { throw ('No se encuentra ' + $exe) }

  foreach ($t in $shortcuts) {
    New-Shortcut $t $exe ''
    Write-Host ('  acceso creado: ' + $t)
  }

  Set-ContextMenu $regShell '%1'
  Set-ContextMenu $regBack  '%V'
  Write-Host '  menu contextual: clic derecho sobre una carpeta > Convertir imagenes'

  $p = [Environment]::GetEnvironmentVariable('PATH','User')
  if (-not $p) { $p = '' }
  if (($p -split ';') -notcontains $AppDir) {
    $new = ($p.TrimEnd(';') + ';' + $AppDir).TrimStart(';')
    [Environment]::SetEnvironmentVariable('PATH', $new, 'User')
    Write-Host '  PATH de usuario actualizado.'
  } else {
    Write-Host '  la carpeta ya estaba en el PATH.'
  }

  New-Item -Path $regUninst -Force | Out-Null
  Set-ItemProperty -Path $regUninst -Name 'DisplayName'     -Value $AppName
  Set-ItemProperty -Path $regUninst -Name 'DisplayIcon'     -Value $Icon
  Set-ItemProperty -Path $regUninst -Name 'DisplayVersion'  -Value $Version
  Set-ItemProperty -Path $regUninst -Name 'Publisher'       -Value 'nbGroup'
  Set-ItemProperty -Path $regUninst -Name 'InstallLocation' -Value $AppDir
  Set-ItemProperty -Path $regUninst -Name 'NoModify'        -Value 1 -Type DWord
  Set-ItemProperty -Path $regUninst -Name 'NoRepair'        -Value 1 -Type DWord
  Set-ItemProperty -Path $regUninst -Name 'UninstallString' `
                   -Value ('"' + (Join-Path $AppDir 'DESINSTALAR.bat') + '"')
  Write-Host '  registrado en Agregar o quitar programas.'

} else {

  foreach ($t in $shortcuts) {
    if (Test-Path $t) { Remove-Item $t -Force -ErrorAction SilentlyContinue }
  }
  foreach ($k in @($regShell, $regBack, $regUninst)) {
    if (Test-Path $k) { Remove-Item $k -Recurse -Force -ErrorAction SilentlyContinue }
  }
  $p = [Environment]::GetEnvironmentVariable('PATH','User')
  if ($p) {
    $new = (($p -split ';') | Where-Object { $_ -and $_ -ne $AppDir }) -join ';'
    [Environment]::SetEnvironmentVariable('PATH', $new, 'User')
  }
  Write-Host '  accesos directos, menu contextual, registro y PATH eliminados.'
}
