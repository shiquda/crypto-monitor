# Parse arguments manually to support case-sensitive flags (-i vs -I)
$i = $args -ccontains '-i' # Build and generate installer
$I_flag = $args -ccontains '-I' # Generate installer only (skip build)

# 1. Build Application (Default or if -i is specified, BUT NOT if -I is specified)
# NOTE: If user passes both, -I takes precedence for skipping build, but we still generate installer if -i is present?
# Logic: Build unless -I is present.
if (-not $I_flag) {
    Write-Host "Building Application..." -ForegroundColor Cyan
    $iconPath = Resolve-Path "assets\icons\crypto-monitor.ico" -ErrorAction SilentlyContinue
    if ($iconPath) {
        $iconParam = "--icon=$($iconPath.Path)"
    } else {
        $iconParam = ""
    }
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
    uv run pyinstaller --onefile --windowed --name="crypto-monitor" $iconParam --add-data="assets/icons;assets/icons" --add-data="i18n;i18n" main.py
    
    if (-not $env:CI) {
        explorer dist
    }
} else {
    Write-Host "Skipping application build (-I specified)." -ForegroundColor Yellow
}

# 2. Generate Installer (if -i or -I is specified)
if ($i -or $I_flag) {
    # Try to find ISCC in PATH first, then check common locations
    $isccPath = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
    
    if (-not $isccPath) {
        $commonPaths = @(
            "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            "D:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        )
        foreach ($path in $commonPaths) {
            if (Test-Path $path) {
                $isccPath = $path
                break
            }
        }
    }

    if ($isccPath) {
        Write-Host "Found Inno Setup Compiler at $isccPath. Generating installer..." -ForegroundColor Green
        & $isccPath "setup.iss"
    } else {
        Write-Host "Inno Setup Compiler not found." -ForegroundColor Red
        Write-Host " Checked paths:"
        $isccPaths | ForEach-Object { Write-Host "  - $_" }
        Write-Host "Skipping installer generation. Please install Inno Setup 6." -ForegroundColor Yellow
    }
}
