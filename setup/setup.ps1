param([switch]$RepairCurrentUserSettings)

$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $scriptRoot
$stateRoot = Join-Path $env:ProgramData 'OpenParty'
$logPath = Join-Path $stateRoot 'install.log'
$toolsRoot = Join-Path $stateRoot 'tools'
$downloads = $null
$script:Failures = [System.Collections.Generic.List[string]]::new()

function Write-Log([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
}

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Set-ProtectedAcl([string]$Path, [bool]$AllowUsersRead) {
    $item = Get-Item -LiteralPath $Path -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing to use a reparse point in the installer directory: $Path"
    }
    $acl = Get-Acl -LiteralPath $Path
    $acl.SetAccessRuleProtection($true, $false)
    $acl.SetOwner([Security.Principal.NTAccount]::new('BUILTIN\Administrators'))
    foreach ($rule in @($acl.Access)) { $acl.RemoveAccessRuleSpecific($rule) }
    $inheritance = if ($item.PSIsContainer) {
        [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
            [Security.AccessControl.InheritanceFlags]::ObjectInherit
    } else {
        [Security.AccessControl.InheritanceFlags]::None
    }
    $adminRule = [Security.AccessControl.FileSystemAccessRule]::new(
        'BUILTIN\Administrators', [Security.AccessControl.FileSystemRights]::FullControl, $inheritance,
        [Security.AccessControl.PropagationFlags]::None,
        [Security.AccessControl.AccessControlType]::Allow
    )
    $systemRule = [Security.AccessControl.FileSystemAccessRule]::new(
        'NT AUTHORITY\SYSTEM', [Security.AccessControl.FileSystemRights]::FullControl, $inheritance,
        [Security.AccessControl.PropagationFlags]::None,
        [Security.AccessControl.AccessControlType]::Allow
    )
    $acl.AddAccessRule($adminRule)
    $acl.AddAccessRule($systemRule)
    if ($AllowUsersRead) {
        $usersRule = [Security.AccessControl.FileSystemAccessRule]::new(
            'BUILTIN\Users', [Security.AccessControl.FileSystemRights]::ReadAndExecute, $inheritance,
            [Security.AccessControl.PropagationFlags]::None,
            [Security.AccessControl.AccessControlType]::Allow
        )
        $acl.AddAccessRule($usersRule)
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}

function Register-PartyFileAssociation {
    $app = Join-Path $repoRoot 'dist\OpenParty.exe'
    if (-not (Test-Path -LiteralPath $app -PathType Leaf)) {
        Write-Host 'OpenParty.exe was not found under dist; skipping .oparty association.'
        return
    }
    $progId = 'OpenParty.Party'
    $classes = 'HKCU:\Software\Classes'
    New-Item -Path "$classes\.oparty" -Force | Out-Null
    Set-Item -LiteralPath "$classes\.oparty" -Value $progId
    New-Item -Path "$classes\$progId\shell\open\command" -Force | Out-Null
    $command = '"{0}" "%1"' -f $app
    Set-Item -LiteralPath "$classes\$progId\shell\open\command" -Value $command
    Write-Host '.oparty association registered for the current Windows user.'
}

function Restore-QBitLocalAuth {
    $config = Join-Path $env:APPDATA 'qBittorrent\qBittorrent.ini'
    if (-not (Test-Path -LiteralPath $config -PathType Leaf)) { return }
    $contents = [IO.File]::ReadAllText($config)
    $pattern = '(?im)^(\s*WebUI\\LocalHostAuth\s*=\s*)false(\s*)$'
    if ([regex]::IsMatch($contents, $pattern)) {
        $backup = "$config.openparty-backup-$(Get-Date -Format 'yyyyMMddHHmmss')"
        Copy-Item -LiteralPath $config -Destination $backup
        $updated = [regex]::Replace($contents, $pattern, '${1}true${2}')
        [IO.File]::WriteAllText($config, $updated, [Text.UTF8Encoding]::new($false))
        Write-Host "Re-enabled qBittorrent localhost authentication; backup saved to $backup. Restart qBittorrent."
    }
}

if ($RepairCurrentUserSettings) {
    try {
        Restore-QBitLocalAuth
        Register-PartyFileAssociation
        exit 0
    }
    catch {
        Write-Host "Could not update current-user settings: $($_.Exception.Message)"
        exit 1
    }
}

if (-not (Test-IsAdministrator)) {
    Write-Host 'Requesting administrator access to install VLC and the Visual C++ runtime.'
    try {
        $quotedScript = '"{0}"' -f $PSCommandPath
        $arguments = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $quotedScript)
        $windowsPowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        $child = Start-Process -FilePath $windowsPowerShell -ArgumentList $arguments -Verb RunAs -Wait -PassThru
        exit $child.ExitCode
    }
    catch {
        Write-Host "Setup could not get administrator access: $($_.Exception.Message)"
        exit 1
    }
}

if (-not [Environment]::Is64BitOperatingSystem) {
    Write-Host 'OpenParty requires 64-bit Windows.'
    exit 1
}

if (-not (Test-Path -LiteralPath $stateRoot)) {
    New-Item -ItemType Directory -Path $stateRoot -Force | Out-Null
}
Set-ProtectedAcl $stateRoot $true

if (-not (Test-Path -LiteralPath $toolsRoot)) {
    New-Item -ItemType Directory -Path $toolsRoot -Force | Out-Null
}
Set-ProtectedAcl $toolsRoot $true

# Repair ACLs on existing tool files before replacing or launching anything.
$existingTools = @(Get-ChildItem -LiteralPath $toolsRoot -Force -Recurse)
foreach ($tool in $existingTools) {
    if (($tool.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing to use a reparse point under $toolsRoot"
    }
}
foreach ($tool in ($existingTools | Sort-Object { $_.FullName.Length } -Descending)) {
    Set-ProtectedAcl $tool.FullName $true
}

$downloads = Join-Path $stateRoot ("SetupStaging-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $downloads -Force | Out-Null
Set-ProtectedAcl $downloads $false
if ((Test-Path -LiteralPath $logPath) -and
    ((Get-Item -LiteralPath $logPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'Refusing to write setup log through a reparse point.'
}
Set-Content -LiteralPath $logPath -Value "OpenParty setup started $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -Encoding UTF8
Set-ProtectedAcl $logPath $true
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Get-VerifiedDownload([string]$Uri, [string]$Path, [string]$ExpectedSha256) {
    Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    Write-Log "Downloading $Uri"
    Invoke-WebRequest -Uri $Uri -OutFile $Path -UseBasicParsing -MaximumRedirection 8
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Download did not create the expected file: $Path"
    }
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $ExpectedSha256.ToLowerInvariant()) {
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
        throw "SHA-256 verification failed for $([IO.Path]::GetFileName($Path)). Expected $ExpectedSha256, got $actual."
    }
    Write-Log "SHA-256 verified: $([IO.Path]::GetFileName($Path))"
}

function Expand-VerifiedZip([string]$Archive, [string]$Destination, [long]$MaxExpandedBytes = 1073741824) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($Archive)
    try {
        if ($zip.Entries.Count -gt 5000) { throw 'Archive contains too many entries.' }
        $total = [long]0
        $root = [IO.Path]::GetFullPath($Destination).TrimEnd('\') + '\'
        foreach ($entry in $zip.Entries) {
            $total += $entry.Length
            if ($total -gt $MaxExpandedBytes) { throw 'Archive expands beyond the allowed size.' }
            $name = $entry.FullName.Replace('/', '\')
            if ([IO.Path]::IsPathRooted($name) -or $name -match '(^|\\)\.\.(\\|$)') {
                throw 'Archive contains an unsafe path.'
            }
            $target = [IO.Path]::GetFullPath((Join-Path $Destination $name))
            if (-not $target.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Archive contains a path outside its destination.'
            }
            $unixType = ($entry.ExternalAttributes -shr 16) -band 0xF000
            if ($unixType -eq 0xA000) { throw 'Archive contains a symbolic link.' }
        }
    }
    finally {
        $zip.Dispose()
    }

    Remove-Item -LiteralPath $Destination -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Expand-Archive -LiteralPath $Archive -DestinationPath $Destination -Force
}

function Get-InstalledVlcVersion {
    $candidates = @(
        (Join-Path $env:ProgramFiles 'VideoLAN\VLC\vlc.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'VideoLAN\VLC\vlc.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\VideoLAN\VLC\vlc.exe')
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) }
    foreach ($candidate in $candidates) {
        $text = (Get-Item -LiteralPath $candidate).VersionInfo.ProductVersion
        if ($text -match '(\d+\.\d+\.\d+)') { return [version]$Matches[1] }
    }
    return $null
}

function Install-Vlc {
    $required = [version]'3.0.24'
    $current = Get-InstalledVlcVersion
    if ($current -and $current -ge $required) {
        Write-Log "VLC $current is already installed."
        return
    }

    $installer = Join-Path $downloads 'vlc-3.0.24-win64.exe'
    # The digest is published by VideoLAN beside the installer.
    Get-VerifiedDownload `
        'https://get.videolan.org/vlc/3.0.24/win64/vlc-3.0.24-win64.exe' `
        $installer `
        '2a9e62747a5e67ba80acfaeb6924e1cee0b128bdac46e6d6d206ec1a2ce96ced'
    $signature = Get-AuthenticodeSignature -LiteralPath $installer
    if ($signature.Status -ne 'Valid') { throw "VLC installer signature is not valid: $($signature.Status)" }

    Write-Log 'Installing VLC silently.'
    $process = Start-Process -FilePath $installer -ArgumentList '/S' -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "VLC installer exited with code $($process.ExitCode)." }
    if (-not (Get-InstalledVlcVersion)) { throw 'VLC installation could not be confirmed.' }
    Write-Log 'VLC installation verified.'
}

function Install-Aria2 {
    $version = '1.37.0'
    $destination = Join-Path $toolsRoot 'aria2'
    $exe = Join-Path $destination 'aria2c.exe'
    if (Test-Path -LiteralPath $exe -PathType Leaf) {
        $versionOutput = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion
        if ($versionOutput -match [regex]::Escape($version)) {
            Write-Log "aria2 $version is already installed in the OpenParty tools directory."
            return
        }
    }

    $archive = Join-Path $downloads 'aria2-1.37.0-win-64bit-build1.zip'
    # Pinned to the official aria2 GitHub release; digest is tracked by Scoop's package manifest.
    Get-VerifiedDownload `
        'https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip' `
        $archive `
        '67d015301eef0b612191212d564c5bb0a14b5b9c4796b76454276a4d28d9b288'
    $expanded = Join-Path $downloads 'aria2-expanded'
    Expand-VerifiedZip $archive $expanded
    $source = Get-ChildItem -LiteralPath $expanded -Filter 'aria2c.exe' -File -Recurse | Select-Object -First 1
    if (-not $source) { throw 'The verified aria2 archive did not contain aria2c.exe.' }

    Remove-Item -LiteralPath $destination -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Copy-Item -Path (Join-Path $source.Directory.FullName '*') -Destination $destination -Recurse -Force
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'aria2 installation could not be confirmed.' }
    Write-Log "aria2 $version installed and verified."
}

function Install-Syncplay {
    $version = '1.7.6'
    $destination = Join-Path $toolsRoot 'syncplay'
    $exe = Join-Path $destination 'Syncplay.exe'
    if (Test-Path -LiteralPath $exe -PathType Leaf) {
        $text = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion
        if ($text -match [regex]::Escape($version)) {
            Write-Log "Syncplay $version is already installed in the OpenParty tools directory."
            return
        }
    }

    $archive = Join-Path $downloads 'Syncplay_1.7.6_Portable.zip'
    # Pinned to Syncplay's signed GitHub release; digest is tracked by Scoop's package manifest.
    Get-VerifiedDownload `
        'https://github.com/Syncplay/syncplay/releases/download/v1.7.6/Syncplay_1.7.6_Portable.zip' `
        $archive `
        'b2e5d22dda78d6d1892ea9836fc642302dd7de9e29f6ded8af286a64d959de7c'
    Expand-VerifiedZip $archive $destination 536870912
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        $nested = Get-ChildItem -LiteralPath $destination -Filter 'Syncplay.exe' -File -Recurse | Select-Object -First 1
        if (-not $nested) { throw 'The verified Syncplay archive did not contain Syncplay.exe.' }
        $nestedRoot = $nested.Directory.FullName
        if ($nestedRoot -ne $destination) {
            Get-ChildItem -LiteralPath $nestedRoot -Force | Move-Item -Destination $destination -Force
        }
    }
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'Syncplay installation could not be confirmed.' }
    Write-Log "Syncplay $version installed and verified."
}

function Install-VcRuntime {
    $runtimeKey = 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x86'
    $runtime = Get-ItemProperty -LiteralPath $runtimeKey -ErrorAction SilentlyContinue
    if ($runtime -and $runtime.Installed -eq 1) {
        Write-Log 'Microsoft Visual C++ 2015-2022 x86 runtime is already installed.'
        return
    }

    $installer = Join-Path $downloads 'vc_redist.x86.exe'
    Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.x86.exe' -OutFile $installer -UseBasicParsing -MaximumRedirection 8
    $signature = Get-AuthenticodeSignature -LiteralPath $installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation') {
        throw 'Microsoft Visual C++ runtime signature verification failed.'
    }
    Write-Log 'Installing Microsoft Visual C++ 2015-2022 x86 runtime.'
    $process = Start-Process -FilePath $installer -ArgumentList '/install', '/quiet', '/norestart' -Wait -PassThru
    if ($process.ExitCode -notin @(0, 3010)) { throw "Visual C++ runtime installer exited with code $($process.ExitCode)." }
    Write-Log 'Microsoft Visual C++ runtime installed.'
}

Write-Log 'Installing or checking OpenParty dependencies.'
Write-Log 'Required components: VLC, Syncplay, aria2. Python and qBittorrent are not required by the packaged app.'

foreach ($task in @(
    @{ Name = 'VLC'; Action = { Install-Vlc } },
    @{ Name = 'aria2'; Action = { Install-Aria2 } },
    @{ Name = 'Syncplay'; Action = { Install-Syncplay } },
    @{ Name = 'Visual C++ runtime'; Action = { Install-VcRuntime } }
)) {
    try {
        & $task.Action
    }
    catch {
        $message = "$($task.Name): $($_.Exception.Message)"
        $script:Failures.Add($message)
        Write-Log "ERROR - $message"
    }
}

if ($script:Failures.Count -gt 0) {
    Write-Log 'Setup finished with errors. Fix the listed items and run setup.cmd again.'
    $script:Failures | ForEach-Object { Write-Host " - $_" }
    Remove-Item -LiteralPath $downloads -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Log 'Setup completed successfully. OpenParty is ready to use.'
Remove-Item -LiteralPath $downloads -Recurse -Force -ErrorAction SilentlyContinue
exit 0
