# Changelog

All notable changes to this project will be documented in this file.

## [0.4.0] - 2026-01-11

### Added
- **Feature**: Implemented **Unified Exchange Client** with **DEX support** (Raydium via Jupiter API).
- **Feature**: Added **Infrastructure Optimization** with `WorkerController` for safer thread management.
- **Feature**: Added **Active Heartbeats** (Ping/Pong) to WebSocket connections for improved resilience.
- **Feature**: Added **Unit Tests** for AlertManager, Models, and SettingsManager.
- **I18n**: Synced and updated translations across all supported languages.

### Changed
- **Architecture**: Refactored architecture to decouple UI from data modeling.
- **Network**: Optimized connection resilience and zombie connection detection.

### Fixed
- **Installer**: Resolved notification alert failures by adding missing dependencies to the spec file.
- **Installer**: Improved logging initialization and error tracebacks in `notifier.py`.

## [0.3.3] - 2026-01-09

### Added
- **Feature**: Implemented **Configurable Sound Alerts** with chime support.
- **Feature**: Implemented **Price Change Basis** setting (24h Rolling vs UTC-0).
- **Feature**: Implemented **Minimalist View Mode** with robust auto-collapse/expand logic.
- **I18n**: Comprehensive **Internationalization Support** for 8 languages (EN, ZH, ES, FR, DE, RU, JP, PT) with auto-detection.
- **Docs**: Comprehensive **User Manual** update with detailed instructions and screenshots.
- **Docs**: Added **Platform Support Note** to README (Windows focused).
- **Docs**: Added LICENSE file.

### Fixed
- **CI**: Made Inno Setup command detection more robust in build script.
- **Core**: Fixed SyntaxError in binance_client and TypeError in settings_window.
- **UI**: Optimized window height calculation for dynamic content fitting.

## [0.3.2] - 2026-01-08

### Added
- **Feature**: Added **Symbol Search** functionality to easily find and add new cryptocurrency pairs.
- **Feature**: Implemented **Update Checker** with a "Check Update" button in Settings to notify users of new versions.
- **Feature**: Added configurable **Minichart Cache Time** setting (default 1 min) for performance optimization.
- **Feature**: Added **User Manual** documentation to guide users through the application.

### Changed
- **Core**: Refactored `MainWindow` to decouple market data logic into `MarketDataController`.
- **UI**: Refactored `SettingsWindow` to use modular page classes, improving code maintainability.
- **UI**: Refined Settings Navigation sidebar (improved icons and spacing).
- **UI**: Optimized **Minichart** appearance.
- **Notification**: Optimized **Alert** notification content (including current price, percentage change, and better formatting).

### Fixed
- **Fix**: Resolved price display precision issues in mini-charts and notifications (now correctly handles >2 decimal places).
- **Fix**: Fixed integer formatting bug in percentage step notifications.
- **Fix**: Fixed various UI bugs including input field displays and potential crashes.
- **Fix**: Resolved Binance network connection issues regarding proxy usage.

## [0.3.1] - 2026-01-07

### Added
- **UI**: Added a custom hover card for crypto pairs to display 24h stats (High, Low, Vol) with mini price chart.
- **Settings**: Added "Open Log Directory" button in the About section to easily access log files.
- **Workflow**: Automated release workflow now extracts changelogs and names artifacts with version numbers.
- **Dev**: Added Antigravity agent workflow files for better development automation.

### Changed
- **Settings**: Replaced "Open App Directory" with "Open Log Directory" for better debugging utility.

## [0.3.0] - 2026-01-07

### Added
- **Dynamic Background**: Crypto cards now dynamically change background opacity based on price change intensity (up to 40% opacity).
- **Settings**: Added "Dynamic Background" toggle in Display Settings to enable/disable this feature.
- **UI**: Optimized Settings window layout (increased width) and fixed sidebar icon scaling issues.
- **I18n**: Added Chinese translations for dynamic background settings and descriptions.

### Changed
- Improved `CryptoCard` visual feedback mechanism.
