# Install luau-lsp (JohnnyMorganz) and the Roblox global type definitions next to this script (Windows).
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
$headers = @{}
if ($env:GITHUB_TOKEN) { $headers["Authorization"] = "token $env:GITHUB_TOKEN" }
$rel = Invoke-RestMethod -Uri "https://api.github.com/repos/JohnnyMorganz/luau-lsp/releases/latest" -Headers $headers
$asset = $rel.assets | Where-Object { $_.name -eq "luau-lsp-win64.zip" } | Select-Object -First 1
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile "luau-lsp.zip" -Headers $headers
Expand-Archive -Path "luau-lsp.zip" -DestinationPath $here -Force
Remove-Item "luau-lsp.zip"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/JohnnyMorganz/luau-lsp/main/scripts/globalTypes.d.luau" -OutFile "globalTypes.d.luau"
& "$here\luau-lsp.exe" --version
Write-Host "installed luau-lsp and globalTypes.d.luau in $here"
