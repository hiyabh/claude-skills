<#
.SYNOPSIS
  Install Obsidian (if missing), download the Dataview/Excalidraw/Timelines plugins into the
  vault, register the vault in obsidian.json (UTF-8 WITHOUT BOM), and launch it.

.PARAMETER VaultPath
  Absolute path to the vault folder (the folder that contains the .obsidian directory).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File setup_obsidian.ps1 -VaultPath "C:\path\to\My Vault"

.NOTES
  - obsidian.json MUST be UTF-8 without BOM, or Obsidian's Node JSON.parse fails and the vault
    never loads. We write it via UTF8Encoding($false). Do NOT replace with Out-File -Encoding utf8.
  - First-run "Trust author and enable plugins" dialog needs a human click (security default).
  - Graph View is a core plugin and works even without the trust click.
#>
param(
  [Parameter(Mandatory = $true)] [string] $VaultPath
)

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ErrorActionPreference = "Stop"

if (-not (Test-Path $VaultPath)) { throw "VaultPath not found: $VaultPath" }
$VaultPath = (Resolve-Path $VaultPath).Path

# --- 1) Install Obsidian if missing ---------------------------------------
$exeCandidates = @(
  "$env:LOCALAPPDATA\Programs\Obsidian\Obsidian.exe",
  "$env:LOCALAPPDATA\Obsidian\Obsidian.exe",
  "$env:PROGRAMFILES\Obsidian\Obsidian.exe"
)
$exe = $exeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $exe) {
  Write-Output "Obsidian not found — installing via winget..."
  winget install --id Obsidian.Obsidian -e --silent `
    --accept-source-agreements --accept-package-agreements --scope user
  $exe = $exeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $exe) { throw "Obsidian.exe still not found after install." }
Write-Output "Obsidian: $exe ($((Get-Item $exe).VersionInfo.ProductVersion))"

# --- 2) Download community plugins into the vault -------------------------
$h = @{ "User-Agent" = "ps" }
$plugins = @(
  @{ id = "dataview";                  repo = "blacksmithgu/obsidian-dataview" },
  @{ id = "obsidian-excalidraw-plugin"; repo = "zsviczian/obsidian-excalidraw-plugin" },
  @{ id = "timelines-revamped";        repo = "seanlowe/obsidian-timelines" }   # NOT Darakah (de-listed)
)
$pluginRoot = Join-Path $VaultPath ".obsidian\plugins"
foreach ($p in $plugins) {
  $dir = Join-Path $pluginRoot $p.id
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  try {
    $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/$($p.repo)/releases/latest" -Headers $h -UseBasicParsing
    foreach ($a in $rel.assets) {
      if ($a.name -in @("manifest.json", "main.js", "styles.css")) {
        Invoke-WebRequest -Uri $a.browser_download_url -OutFile (Join-Path $dir $a.name) -UseBasicParsing
      }
    }
    Write-Output "plugin OK: $($p.id) ($($rel.tag_name))"
  } catch {
    Write-Output "plugin FAIL: $($p.id) -> $($_.Exception.Message) (install manually via Obsidian UI)"
  }
}

# --- 3) Register vault in obsidian.json (UTF-8 NO BOM) --------------------
$cfgDir  = "$env:APPDATA\obsidian"
$cfgFile = Join-Path $cfgDir "obsidian.json"
New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null

if (Test-Path $cfgFile) {
  $json = [System.IO.File]::ReadAllText($cfgFile).TrimStart([char]0xFEFF) | ConvertFrom-Json
} else {
  $json = [PSCustomObject]@{ vaults = [PSCustomObject]@{} }
}
if (-not $json.vaults) { $json | Add-Member vaults ([PSCustomObject]@{}) -Force }
foreach ($v in $json.vaults.PSObject.Properties) { if ($v.Value.open) { $v.Value.open = $false } }

$id = -join ((1..16) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
$ts = [int64]((Get-Date).ToUniversalTime() - (Get-Date "1970-01-01")).TotalMilliseconds
$entry = [PSCustomObject]@{ path = ($VaultPath -replace '\\', '/'); ts = $ts; open = $true }
$json.vaults | Add-Member -NotePropertyName $id -NotePropertyValue $entry -Force

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($cfgFile, ($json | ConvertTo-Json -Depth 10), $utf8NoBom)
Write-Output "Registered vault id=$id (UTF-8 no BOM)"

# --- 4) Launch and confirm load -------------------------------------------
Get-Process Obsidian -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Start-Process $exe
Start-Sleep -Seconds 6
$ws = Get-ChildItem (Join-Path $VaultPath ".obsidian") -Filter "workspace*.json" -ErrorAction SilentlyContinue
if ($ws) { Write-Output "VAULT LOADED ($($ws.Name))." }
else     { Write-Output "WARNING: workspace.json not found — vault may not have loaded. Check obsidian.json encoding." }
Write-Output "Reminder: click 'Trust author and enable plugins' on first run to activate Dataview/Excalidraw/Timelines."
