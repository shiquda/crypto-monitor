$iconPath = Resolve-Path "assets\icons\crypto-monitor.ico" -ErrorAction SilentlyContinue
if ($iconPath) {
    $iconParam = "--icon=$($iconPath.Path)"
} else {
    $iconParam = ""
}
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
uv run pyinstaller --onefile --windowed --name="crypto-monitor" $iconParam --add-data="assets;assets" --add-data="imgs;imgs" --add-data="i18n;i18n" main.py
explorer dist
