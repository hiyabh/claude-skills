# Finds which system-setting keys a watch UI toggle changes.
# Usage:
#   .\discover-settings.ps1 -Snapshot before      # dump all namespaces
#   (change ONE setting on the watch)
#   .\discover-settings.ps1 -Snapshot after -DiffAgainst before
param(
    [Parameter(Mandatory = $true)][string]$Snapshot,
    [string]$DiffAgainst = ""
)

$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
$dir = Join-Path $PSScriptRoot "..\build\settings-snapshots"
New-Item -ItemType Directory -Force $dir | Out-Null

foreach ($ns in @("global", "secure", "system")) {
    $file = Join-Path $dir "$Snapshot-$ns.txt"
    & $adb shell settings list $ns | Sort-Object | Set-Content -Encoding utf8 $file
    Write-Host "wrote $file"
}

if ($DiffAgainst -ne "") {
    foreach ($ns in @("global", "secure", "system")) {
        $before = Get-Content (Join-Path $dir "$DiffAgainst-$ns.txt")
        $after = Get-Content (Join-Path $dir "$Snapshot-$ns.txt")
        $diff = Compare-Object $before $after
        if ($diff) {
            Write-Host "---- $ns ----"
            $diff | ForEach-Object { Write-Host ("{0} {1}" -f $_.SideIndicator, $_.InputObject) }
        }
    }
}
