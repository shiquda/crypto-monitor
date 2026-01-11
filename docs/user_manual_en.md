# Crypto Monitor User Manual

Welcome to Crypto Monitor — your dedicated desktop cryptocurrency price assistant.
This manual will help you master everything from basic monitoring to advanced alerts.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Core Features](#2-core-features)
3. [Personalization](#3-personalization)
4. [Advanced Settings](#4-advanced-settings)
5. [FAQ](#5-faq)

---

## 1. Quick Start

### Installation & Launch
- **Download**: Get the latest `.exe` installer from the [GitHub Releases](https://github.com/shiquda/crypto-monitor/releases) page.
- **Launch**: Simply double-click to run. No administrator privileges required; it installs in the current directory or AppData by default.
- **Update**: The software has a built-in update checker. Go to `Settings > About > Check Update` to see if a new version is available.

> **Note**: On first run, Windows SmartScreen might warn you about "unrecognized app". This is common for open-source software without a purchased digital certificate. Click "Run anyway" to proceed.

### Interface Overview
The main interface consists of three key areas:
1. **Top Toolbar**: Contains Settings, Add Pair, Pin Window, Minimize, and Close buttons.
2. **Crypto Cards**: The core display area where each card represents a trading pair.
3. **Bottom Navigation**: Use the dots to switch pages if you follow many pairs (supports mouse wheel scrolling).

<p align="center">
  <img src="./imgs/crypto-monitor.png" alt="Main Interface" width="30%">
</p>

---

## 2. Core Features

### Real-time Monitoring
- **Data Sources**: Supports **Binance**, **OKX** centralized exchanges, and **On-Chain DEX** data (via DexScreener API).
- **Add Pair**: Click the `+` icon at the top. In the dialog, select your data source type:
  - **Exchange (CEX)**: Enter a pair name like `BTC-USDT` and select from the dropdown list.
  - **On-Chain (DEX)**: Switch to the "On-Chain (DEX)" tab, paste a token contract address (EVM `0x...` or Solana address), search, and select from the results.

<p align="center">
  <img src="./imgs/add-pair.png" alt="Add Pair" width="60%">
</p>

> **On-Chain Pairs Note**: DEX pairs fetch data via DexScreener, supporting Ethereum, Solana, BSC, Arbitrum, and other major chains. Double-clicking a DEX card opens its DexScreener page.

- **View Details**:
    - **Hover**: Hover your mouse over a card to reveal **24h High/Low**, **Volume**, and a **Mini Candle Chart**.
    - **Double Click**: Opens the exchange's trading page for that pair directly in your browser.

<p align="center">
  <img src="./imgs/hover.png" alt="Hover Details" width="60%">
</p>

### Smart Alert System
This is the most powerful feature to ensure you never miss a market move.
**Right-click** any card and select `Add Alert` to configure:

<p align="center">
  <img src="./imgs/add-alert.png" alt="Add Alert" width="60%">
</p>

#### Alert Types
| Type | Description | Use Case |
| :--- | :--- | :--- |
| **Above** | Triggered when price rises above the set value | Take-profit |
| **Below** | Triggered when price falls below the set value | Stop-loss / Buy-the-dip |
| **Touch** | Triggered when price **touches** the set value (±0.1% tolerance) | Key level monitoring |
| **Price Step** | Triggered every time price moves by a specific amount (e.g., every $1000 change) | Tracking volatility |
| **Change Step** | Triggered every time 24h change moves by a specific percentage (e.g., every 1% change) | Tracking momentum |

#### Frequency
- **Once**: Automatically disabled after triggering.
- **Repeating**: Triggers every time conditions are met, with a 60-second cooldown to prevent notification spam.

> **Tip**: Alerts are delivered via Windows native notifications. Clicking the notification opens the trading page.

---

## 3. Personalization

### Minimalist View (Boss Mode)
Designed for office environments. When enabled, the window strips away all clutter and only shows prices.

- **Enable**: Go to `Settings > Appearance > minimal view`.
- **Interaction**: 
    - When mouse **leaves** the window: Toolbar and pagination hide automatically; window shrinks to fit only the cards.
    - When mouse **enters** the window: All controls reappear for easy interaction.

### Visual & Interaction Habits
- **Color Schema**: Defaults to "Green Up / Red Down" (Standard). You can switch to "Red Up / Green Down" (Reverse) in `Settings > Appearance` if you prefer the Eastern style.
- **Dynamic Background**: When enabled, the background transparency subtly adjusts based on **price volatility intensity**, making the interface "breathe".
- **Auto Scroll**: Enables automatic pagination cycling with a configurable interval (5s - 300s). Perfect for hands-free monitoring.

### Pin & Layout
- Click the **Pin** icon in the toolbar to keep the window always on top of other applications.
- The window can be dragged anywhere, and it remembers its position when you close it.

---

## 4. Advanced Settings

Click the **Gear** icon to enter the Settings center.

<p align="center">
  <img src="./imgs/gear.png" alt="Settings" width="30%">
</p>

### Network & Data Source
- **CEX Data Source**: Defaults to OKX. If you cannot access it in your region, switch to Binance.
- **DEX Data**: On-chain pair data is provided by the DexScreener API, with automatic polling updates (approximately every 10 seconds).
- **Price Change Basis**:
    - **24h Rolling**: Shows change over the last 24 hours (default).
    - **UTC-0**: Shows change since 00:00 UTC (8:00 AM Beijing Time), suitable for intraday traders.
- **Proxy**: If API access is restricted, configure an HTTP or SOCKS5 proxy in `Settings > Network`.

### Hover Card Configuration
Customize what appears when you hover over a card in `Settings > Appearance`:
- **Content**: Independently toggle "Mini Chart" or "Detailed Statistics".
- **Chart Range**: Supports 5 timeframes: `1h`, `4h`, `12h`, `24h`, `7d`.
- **Chart Cache**: Adjust cache duration (10s - 10min) in Advanced Settings to save data and reduce API calls.

### Backup & Migration
- **Export Config**: Click `Export Config` at the bottom of Settings to backup all your pairs and complex alert setups to a JSON file.
- **Import Config**: Restore your setup easily after reinstalling the OS or moving to a new PC.

---

## 5. FAQ

**Q: Why does nothing happen when I click "Check Update"?**  
A: The update checker connects to the GitHub API. If your network cannot access GitHub, the check may fail silently or timeout. If an update is found, it will prompt you to download it via browser; it does **not** install silently in the background.

**Q: Why am I not receiving alert notifications?**  
A: Please check Windows "Focus Assist" or "Notification Settings" to ensure Crypto Monitor has permission to show notifications.

**Q: Does the app have a System Tray icon?**  
A: Currently, there is no system tray support. Minimizing the app sends it to the taskbar.

**Q: How do I completely reset the software?**  
A: Click `Reset to Defaults` at the bottom of Settings, or manually delete the `%APPDATA%/crypto-monitor` folder.

**Q: How often does on-chain DEX data update?**  
A: DEX pairs are updated via DexScreener API polling, approximately every 10 seconds. Since this uses HTTP polling rather than WebSocket, there may be a slight delay compared to CEX data.

---
*Last updated: 2026-01-11*
