[CmdletBinding()]
param(
    [switch]$Once,
    [int]$DebounceSeconds = 15
)

$ErrorActionPreference = 'Stop'

$scriptsDirectory = Split-Path -Parent $PSCommandPath
$ProjectRoot = Split-Path -Parent $scriptsDirectory
$LogDirectory = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'CafeManagementSystemZ'
$LogPath = Join-Path $LogDirectory 'auto-git-sync.log'
$LockPath = Join-Path $LogDirectory 'auto-git-sync.lock'

New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null

try {
    $LockHandle = [System.IO.File]::Open(
        $LockPath,
        [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
} catch {
    # Another watcher is already running for this project.
    exit 0
}

function Write-SyncLog {
    param([Parameter(Mandatory)][string]$Message)

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -LiteralPath $LogPath -Value "$timestamp  $Message"
}

function Invoke-Git {
    param([Parameter(Mandatory)][string[]]$Arguments)

    $output = & git.exe -C $ProjectRoot @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed: $($output -join ' ')"
    }

    return @($output | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
}

function Get-PendingPaths {
    $paths = @()
    $paths += Invoke-Git @('diff', '--name-only')
    $paths += Invoke-Git @('diff', '--cached', '--name-only')
    $paths += Invoke-Git @('ls-files', '--others', '--exclude-standard')
    return @($paths | Where-Object { $_ } | Sort-Object -Unique)
}

function Get-ProtectionReason {
    param([Parameter(Mandatory)][string]$RelativePath)

    $normalPath = $RelativePath.Replace('\', '/')
    $fileName = [System.IO.Path]::GetFileName($normalPath)

    if ($fileName -eq '.env' -or (
        $fileName -like '.env.*' -and
        $fileName -notin @('.env.example', '.env.sample', '.env.template')
    )) {
        return 'environment file'
    }

    if ($normalPath -match '(?i)(^|/)(?:venv|\.venv|node_modules|__pycache__|invoices|qr_codes|uploads|secrets|credentials)(/|$)') {
        return 'local-only directory'
    }

    if ($fileName -match '(?i)\.(?:db|sqlite|sqlite3|pem|key|p12|pfx)$' -or
        $fileName -match '(?i)^(?:id_rsa|id_ed25519)$' -or
        $fileName -match '(?i)\.db-') {
        return 'database or credential file'
    }

    return $null
}

function Get-SecretPatternMatch {
    param([Parameter(Mandatory)][string]$RelativePath)

    $extension = [System.IO.Path]::GetExtension($RelativePath).ToLowerInvariant()
    $textExtensions = @('.py', '.js', '.ts', '.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.txt', '.md', '.html', '.css', '.sh', '.ps1')
    if ($extension -notin $textExtensions) {
        return $null
    }

    $fullPath = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        return $null
    }

    $fileInfo = Get-Item -LiteralPath $fullPath
    if ($fileInfo.Length -gt 1MB) {
        return $null
    }

    try {
        $content = [System.IO.File]::ReadAllText($fullPath)
    } catch {
        return $null
    }

    $patterns = [ordered]@{
        'GitHub token' = 'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}'
        'OpenAI-style API key' = 'sk-[A-Za-z0-9]{20,}'
        'AWS access key' = 'AKIA[0-9A-Z]{16}'
        'private key' = '-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'
        'database URL with a password' = '(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|mssql)://[^\s:]+:[^\s@]+@'
        'hard-coded credential-like setting' = "(?im)^\s*(?:[A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)|DATABASE_URL)\s*[:=]\s*['`"]?(?!\$|\{|os\.environ|env\.)[^\r\n'`"]{12,}"
    }

    foreach ($entry in $patterns.GetEnumerator()) {
        if ($content -match $entry.Value) {
            return $entry.Key
        }
    }

    return $null
}

function Assert-SafeToSync {
    param([Parameter(Mandatory)][string[]]$Paths)

    $problems = @()
    foreach ($path in $Paths) {
        $protection = Get-ProtectionReason -RelativePath $path
        if ($protection) {
            $problems += "$path ($protection)"
            continue
        }

        $secret = Get-SecretPatternMatch -RelativePath $path
        if ($secret) {
            $problems += "$path (possible $secret)"
        }
    }

    if ($problems.Count -gt 0) {
        throw "Auto-sync stopped to protect: $($problems -join '; ')"
    }
}

function Sync-Repository {
    try {
        if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot '.git') -PathType Container)) {
            throw 'The project has not been initialized as a Git repository.'
        }

        $branch = (Invoke-Git @('rev-parse', '--abbrev-ref', 'HEAD'))[0]
        if (-not $branch -or $branch -eq 'HEAD') {
            throw 'No current Git branch is checked out.'
        }

        $upstream = Invoke-Git @('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}')
        if (-not $upstream) {
            throw "Branch '$branch' has no upstream repository. Run SetupGitHubSync.ps1 again."
        }

        $paths = Get-PendingPaths
        if ($paths.Count -eq 0) {
            return
        }

        Assert-SafeToSync -Paths $paths

        Invoke-Git @('fetch', '--quiet', 'origin', $branch) | Out-Null
        $revisionRange = "$branch...@{u}"
        $counts = (Invoke-Git @('rev-list', '--left-right', '--count', $revisionRange))[0] -split '\s+'
        $behind = [int]$counts[1]
        if ($behind -gt 0) {
            throw "GitHub has $behind newer commit(s). Pull and resolve them in GitHub Desktop before automatic syncing can resume."
        }

        Invoke-Git @('add', '--all') | Out-Null
        & git.exe -C $ProjectRoot diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            return
        }
        if ($LASTEXITCODE -ne 1) {
            throw 'Unable to inspect staged changes.'
        }

        $commitMessage = 'Auto-sync: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
        Invoke-Git @('commit', '-m', $commitMessage) | Out-Null
        Invoke-Git @('push', 'origin', $branch) | Out-Null
        Write-SyncLog "Pushed automatic commit to origin/$branch."
    } catch {
        Write-SyncLog $_.Exception.Message
    }
}

try {
    Sync-Repository
    if ($Once) {
        exit 0
    }

    $watcher = New-Object System.IO.FileSystemWatcher $ProjectRoot, '*'
    $watcher.IncludeSubdirectories = $true
    $watcher.NotifyFilter = [System.IO.NotifyFilters]'FileName, LastWrite, DirectoryName'
    $watcher.EnableRaisingEvents = $true

    $eventNames = @('Changed', 'Created', 'Deleted', 'Renamed')
    $sourceIds = @()
    foreach ($eventName in $eventNames) {
        $sourceId = "CafeManagementSystemZ.AutoSync.$eventName"
        Register-ObjectEvent -InputObject $watcher -EventName $eventName -SourceIdentifier $sourceId | Out-Null
        $sourceIds += $sourceId
    }

    Write-SyncLog 'Watcher started.'
    $pendingChange = $false
    $lastChange = Get-Date

    while ($true) {
        foreach ($sourceId in $sourceIds) {
            $events = @(Get-Event -SourceIdentifier $sourceId -ErrorAction SilentlyContinue)
            foreach ($event in $events) {
                Remove-Event -EventIdentifier $event.EventIdentifier -ErrorAction SilentlyContinue
                $pendingChange = $true
                $lastChange = Get-Date
            }
        }

        if ($pendingChange -and ((Get-Date) - $lastChange).TotalSeconds -ge $DebounceSeconds) {
            Sync-Repository
            $pendingChange = $false
        }

        Start-Sleep -Seconds 2
    }
} finally {
    if ($LockHandle) {
        $LockHandle.Dispose()
    }
}
