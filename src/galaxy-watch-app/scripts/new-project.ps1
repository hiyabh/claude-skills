# Scaffolds a new Wear OS project from the skill template.
# Example:
#   .\new-project.ps1 -Dir "C:\Projects\Watch Timer" -Package com.example.watchtimer -AppName "טיימר"
param(
    [Parameter(Mandatory = $true)][string]$Dir,
    [Parameter(Mandatory = $true)][string]$Package,   # e.g. com.example.watchtimer (lowercase, dots)
    [Parameter(Mandatory = $true)][string]$AppName,   # display name, Hebrew ok
    [string]$Slug = ""                                 # rootProject.name; default = last package segment
)

$ErrorActionPreference = "Stop"
$template = Join-Path $PSScriptRoot "..\assets\template"
if ($Slug -eq "") { $Slug = ($Package -split "\.")[-1] }
if ($Package -notmatch '^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$') { throw "Package must look like com.example.name" }

if (Test-Path -LiteralPath $Dir) {
    if ((Get-ChildItem -LiteralPath $Dir -Force | Measure-Object).Count -gt 0) { throw "Target dir is not empty: $Dir" }
} else {
    New-Item -ItemType Directory -Path $Dir | Out-Null
}

Copy-Item -Path (Join-Path $template "*") -Destination $Dir -Recurse -Force
# Copy-Item skips dotfiles in some shells - make sure .gitignore arrives.
Copy-Item -LiteralPath (Join-Path $template ".gitignore") -Destination (Join-Path $Dir ".gitignore") -Force

# Move the Kotlin sources to the new package path.
$srcRoot = Join-Path $Dir "app\src\main\java"
$testRoot = Join-Path $Dir "app\src\test\java"
$newPath = $Package -replace "\.", "\"
foreach ($root in @($srcRoot, $testRoot)) {
    $old = Join-Path $root "com\example\template"
    $new = Join-Path $root $newPath
    New-Item -ItemType Directory -Force -Path (Split-Path $new -Parent) | Out-Null
    Move-Item -LiteralPath $old -Destination $new
    $leftover = Join-Path $root "com\example"
    if ((Test-Path $leftover) -and ((Get-ChildItem $leftover -Force | Measure-Object).Count -eq 0)) { Remove-Item $leftover }
}

# Replace placeholders in text files.
$textFiles = Get-ChildItem -LiteralPath $Dir -Recurse -File | Where-Object { $_.Extension -in ".kt", ".kts", ".xml", ".toml", ".properties", ".md" }
foreach ($f in $textFiles) {
    $c = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8)
    $c2 = $c.Replace("com.example.template", $Package).Replace("__APP_NAME__", $AppName).Replace("__SLUG__", $Slug)
    if ($c2 -ne $c) { [System.IO.File]::WriteAllText($f.FullName, $c2, (New-Object System.Text.UTF8Encoding($false))) }
}

# SDK location (forward slashes - see references/toolchain.md).
$sdk = ($env:LOCALAPPDATA + "\Android\Sdk") -replace "\\", "/"
[System.IO.File]::WriteAllText((Join-Path $Dir "local.properties"), "sdk.dir=$sdk`n", (New-Object System.Text.UTF8Encoding($false)))

Write-Host "Scaffolded '$AppName' ($Package) in $Dir"
Write-Host "Build outputs will go to $env:LOCALAPPDATA\$Slug-build"
Write-Host "Next: cd into it, git init, then: .\gradlew.bat assembleDebug testDebugUnitTest --no-daemon --console=plain"
