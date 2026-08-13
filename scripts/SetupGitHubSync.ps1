[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$scriptsDirectory = Split-Path -Parent $PSCommandPath
$ProjectRoot = Split-Path -Parent $scriptsDirectory
$WatcherPath = Join-Path $scriptsDirectory 'AutoGitHubSync.ps1'
$ExpectedRemote = 'https://github.com/vignesh20050706-max/CafeManagementSystemZ.git'
$TaskName = 'Cafe Management System GitHub Auto Sync'

function Invoke-GitSetup {
    param([Parameter(Mandatory)][string[]]$Arguments)

    & git.exe -C $ProjectRoot @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed."
    }
}

if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) {
    throw 'Git is not installed. Install GitHub Desktop (which includes Git) and then run this setup again.'
}

if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot '.gitignore'))) {
    throw 'The protected .gitignore file is missing; setup stopped without changing the project.'
}

if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot '.git') -PathType Container)) {
    Invoke-GitSetup @('init', '-b', 'main')
    Invoke-GitSetup @('remote', 'add', 'origin', $ExpectedRemote)
    Invoke-GitSetup @('fetch', 'origin', 'main')

    Invoke-GitSetup @('add', '--all')
    & git.exe -C $ProjectRoot diff --cached --quiet
    if ($LASTEXITCODE -eq 1) {
        Invoke-GitSetup @('commit', '-m', 'Initial commit')
    } elseif ($LASTEXITCODE -ne 0) {
        throw 'Unable to inspect the initial staged changes.'
    }

    Invoke-GitSetup @('merge', 'origin/main', '--allow-unrelated-histories', '-m', 'Merge existing GitHub repository')
} else {
    $actualRemote = (& git.exe -C $ProjectRoot remote get-url origin).Trim()
    if ($LASTEXITCODE -ne 0 -or $actualRemote -ne $ExpectedRemote) {
        throw 'This project already has a different Git remote. Setup stopped without changing it.'
    }

    Invoke-GitSetup @('fetch', 'origin', 'main')
}

$configuredName = (& git.exe config --global --get user.name).Trim()
$configuredEmail = (& git.exe config --global --get user.email).Trim()
if (-not $configuredName -or -not $configuredEmail) {
    throw 'Git author name or email is not configured. In GitHub Desktop, open File > Options > Git and set both fields, then run setup again.'
}

Invoke-GitSetup @('push', '--set-upstream', 'origin', 'main')

$taskCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \`"$WatcherPath\`""
& schtasks.exe /Create /TN $TaskName /TR $taskCommand /SC ONLOGON /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw 'The project was pushed, but Windows could not create the automatic-start task. Run the setup file again from a regular PowerShell window.'
}

Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', $WatcherPath) -WindowStyle Hidden

Write-Host ''
Write-Host 'GitHub synchronization is active.'
Write-Host 'Saved changes will be committed and pushed after 15 seconds of inactivity.'
Write-Host "Log: $([Environment]::GetFolderPath('LocalApplicationData'))\CafeManagementSystemZ\auto-git-sync.log"

