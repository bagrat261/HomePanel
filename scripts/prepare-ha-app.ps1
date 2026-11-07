$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$destination = Join-Path $projectRoot 'ha-app\homepanel\source'
$resolvedDestination = [IO.Path]::GetFullPath($destination)
$expectedParent = [IO.Path]::GetFullPath((Join-Path $projectRoot 'ha-app\homepanel'))
if (-not $resolvedDestination.StartsWith($expectedParent + [IO.Path]::DirectorySeparatorChar)) {
    throw 'Build destination must stay inside ha-app/homepanel'
}
New-Item -ItemType Directory -Path $destination -Force | Out-Null
foreach ($item in @('homepanel', 'pyproject.toml', 'README.md', 'LICENSE')) {
    Copy-Item -LiteralPath (Join-Path $projectRoot $item) -Destination $destination -Recurse -Force
}
Write-Output 'Prepared ha-app/homepanel/source. Copy the complete homepanel app folder to /addons/homepanel.'
