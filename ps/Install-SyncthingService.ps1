# ==========================================
# Syncthing Windows Service Installer
# ==========================================

$ErrorActionPreference = "Stop"

# ------------------------------------------
# Auto-elevate to Administrator
# ------------------------------------------

$CurrentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$Principal = New-Object Security.Principal.WindowsPrincipal($CurrentIdentity)

$IsAdmin = $Principal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if (-not $IsAdmin) {

    Write-Host "Administrator privileges required." -ForegroundColor Yellow
    Write-Host "Requesting UAC elevation..." -ForegroundColor Yellow

    $ScriptPath = $MyInvocation.MyCommand.Path

    Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "`"$ScriptPath`""
        ) `
        -Verb RunAs

    exit
}

# ==========================================
# Configuration
# ==========================================

$ServiceName = "Syncthing"

$SyncthingExe = "C:\ProgramData\chocolatey\bin\syncthing.exe"

$NssmExe = "C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe"

# Automatically use the current Windows account
$ServiceUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Syncthing Windows Service Installer" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# ==========================================
# Check Syncthing
# ==========================================

Write-Host "[1/6] Checking Syncthing..." -ForegroundColor Yellow

if (-not (Test-Path $SyncthingExe)) {

    Write-Host "ERROR: Syncthing not found:" -ForegroundColor Red
    Write-Host $SyncthingExe

    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Found:" -ForegroundColor Green
Write-Host $SyncthingExe

# ==========================================
# Check / Install NSSM
# ==========================================

Write-Host ""
Write-Host "[2/6] Checking NSSM..." -ForegroundColor Yellow

if (-not (Test-Path $NssmExe)) {

    Write-Host "NSSM not found." -ForegroundColor Yellow
    Write-Host "Installing NSSM with Chocolatey..."

    & choco install nssm -y

    if (-not (Test-Path $NssmExe)) {

        Write-Host ""
        Write-Host "ERROR: NSSM installation failed." -ForegroundColor Red

        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host "Found:" -ForegroundColor Green
Write-Host $NssmExe

# ==========================================
# Ask for Windows password ONCE
# ==========================================

Write-Host ""
Write-Host "[3/6] Windows account" -ForegroundColor Yellow
Write-Host ""
Write-Host "Service account:" -ForegroundColor Cyan
Write-Host "  $ServiceUser"
Write-Host ""

$Password = Read-Host `
    "Enter Windows password" `
    -AsSecureString

# Convert SecureString to plaintext temporarily
$BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)

$PlainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($BSTR)

try {

    # ==========================================
    # Remove existing service
    # ==========================================

    Write-Host ""
    Write-Host "[4/6] Removing existing Syncthing service..." -ForegroundColor Yellow

    $ExistingService = Get-Service `
        -Name $ServiceName `
        -ErrorAction SilentlyContinue

    if ($ExistingService) {

        Write-Host "Existing service found."

        if ($ExistingService.Status -ne "Stopped") {

            Write-Host "Stopping service..."

            Stop-Service `
                -Name $ServiceName `
                -Force `
                -ErrorAction SilentlyContinue

            Start-Sleep -Seconds 2
        }

        Write-Host "Removing service..."

        & $NssmExe remove $ServiceName confirm 2>$null

        Start-Sleep -Seconds 2

        # Fallback
        if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {

            Write-Host "NSSM did not remove the service. Using SC..."

            & sc.exe delete $ServiceName

            Start-Sleep -Seconds 2
        }
    }

    # ==========================================
    # Create service
    # ==========================================

    Write-Host ""
    Write-Host "[5/6] Creating Syncthing service..." -ForegroundColor Yellow

    & $NssmExe install `
        $ServiceName `
        $SyncthingExe

    if ($LASTEXITCODE -ne 0) {
        throw "NSSM failed to create the service."
    }

    # Working directory
    & $NssmExe set `
        $ServiceName `
        AppDirectory `
        "C:\ProgramData\chocolatey\bin"

    # Automatic startup
    & $NssmExe set `
        $ServiceName `
        Start `
        SERVICE_AUTO_START

    # Run as current Windows user
    & $NssmExe set `
        $ServiceName `
        ObjectName `
        $ServiceUser `
        $PlainPassword

    # Restart automatically if Syncthing exits
    & $NssmExe set `
        $ServiceName `
        AppExit `
        Default `
        Restart

    # Wait 5 seconds before restart
    & $NssmExe set `
        $ServiceName `
        AppThrottle `
        5000

    # Description
    & $NssmExe set `
        $ServiceName `
        Description `
        "Syncthing file synchronization service"

    # ==========================================
    # Start
    # ==========================================

    Write-Host ""
    Write-Host "[6/6] Starting Syncthing..." -ForegroundColor Yellow

    Start-Service -Name $ServiceName

    Start-Sleep -Seconds 5

    # ==========================================
    # Result
    # ==========================================

    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "       Installation Complete" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""

    Get-Service -Name $ServiceName |
        Format-Table Name, Status, StartType -AutoSize

    Write-Host ""
    Write-Host "Service account:" -ForegroundColor Cyan
    Write-Host $ServiceUser

    Write-Host ""
    Write-Host "Executable:" -ForegroundColor Cyan
    Write-Host $SyncthingExe

    Write-Host ""
    Write-Host "Syncthing will start automatically when Windows boots." `
        -ForegroundColor Green

    Write-Host "No Windows login is required." `
        -ForegroundColor Green

}
catch {

    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "ERROR" -ForegroundColor Red
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red

}
finally {

    # Clear password from memory
    $PlainPassword = $null
    $Password = $null

    if ($BSTR) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
    }
}

Write-Host ""
Read-Host "Press Enter to exit"