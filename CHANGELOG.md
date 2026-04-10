# Changelog

All notable changes to this project will be documented in this file.

## [0.5.1] - 2026-04-10

### Added

- **Data Source**: Added **GATE** real-time source with WebSocket push updates.
- **Data Source**: Added **Swap/Mark** variants for major exchanges: `OKX_MARK`, `BINANCE_MARK`, and `GATE_MARK`.
- **Settings**: Added **UTC+8 (Daily)** price-change basis option (alongside existing 24h rolling and UTC+0 modes).
- **Search**: Extended symbol search endpoints for spot/swap sources across OKX, Binance, and Gate.
- **I18n**: Added translation keys for swap source labels and UTC+8 basis in all supported locales.

### Changed

- **Architecture**: Extended unified source routing to support spot/mark market types with shared client structure.
- **OKX**: Improved swap instrument mapping and alias handling so UI pairs map correctly to `-SWAP` subscriptions.
- **Binance**: Optimized mark stream handling and open-price priming for basis-aware percentage calculation.
- **Gate**: Enhanced futures candle/ticker parsing compatibility for different payload shapes.
- **UI**: Updated data source selector to display localized labels while persisting canonical source values.
- **Chart**: Improved chart fetch path to instantiate source-specific clients for hover mini-chart data.
- **Search**: Normalized OKX/Gate swap symbol display to `BASE-QUOTE` while preserving exchange-native identifiers in raw fields.

### Fixed

- **UI**: Fixed crash when switching source due to passing float directly into Qt text setter.
- **Source Switch**: Fixed stale chart/ticker display after data source changes by resetting state and isolating chart cache behavior.
- **Percentage**: Fixed incorrect or stuck `0.00%` on mark sources by correcting open-price baseline logic.
- **Gate API**: Fixed failed open-price request caused by incompatible parameter combinations.
- **Navigation**: Fixed double-click browser routing so each source opens the correct exchange page instead of falling back to OKX.
- **Navigation**: Fixed OKX swap browser URL generation to avoid duplicate `-swap` suffix and restored locale-aware URL prefix.
- **Settings**: Fixed data source persistence issue where selection could revert to OKX after reopening settings.
- **Core**: Fixed Gate worker daily basis refresh path by adding missing candle row parser in WebSocket worker.
- **UI**: Removed duplicate `auto_scroll_changed` signal declaration in display settings card.
- **Docs**: Updated Chinese user manual with `UTC+8` basis description to keep docs aligned with settings.

## [0.5.0] - 2026-01-12

### Added

- **Feature**: Added **DEX Token Name Search** support to easily find tokens by name or symbol.
- **Feature**: Implemented **Multi-source Icon Fallback** (OKX -> Binance -> CoinGecko) to significantly improve icon coverage.
- **Feature**: Added **UTC+0 Mode** support for DEX tokens price change calculation.

### Changed

- **DEX**: Enhanced mini-charts with 24h High/Low data support.
- **Dev**: Optimized logging system (replaced print with logger) and improved documentation.
- **Docs**: Updated DEX feature documentation and translations.

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
