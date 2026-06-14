# Deprecated — use pnpm docker:up (routes through scripts/docker.mjs).
Write-Warning "scripts/docker-up.ps1 is deprecated. Use: pnpm docker:up"
Set-Location $PSScriptRoot\..
node scripts/docker.mjs up @args
