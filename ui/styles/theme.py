"""
Theme and stylesheet management.
"""

# Dark theme colors
DARK_COLORS = {
    "background": "#1B2636",
    "card_background": "#13191D",
    "text": "#FFFFFF",
    "text_secondary": "#AAAAAA",
    "border": "#3A4A5A",
    "hover": "rgba(255, 255, 255, 0.1)",
    "positive": "#99FF99",
    "negative": "#FF9999",
    "accent": "#4A9A4A",
}

# Light theme colors
LIGHT_COLORS = {
    "background": "#F5F5F5",
    "card_background": "#FFFFFF",
    "text": "#000000",
    "text_secondary": "#666666",
    "border": "#E0E0E0",
    "hover": "rgba(0, 0, 0, 0.05)",
    "positive": "#2E7D32",
    "negative": "#C62828",
    "accent": "#1976D2",
}

# Default to light colors for backward compatibility
COLORS = LIGHT_COLORS

# Stylesheet templates
STYLESHEETS = {
    "main_window": f"""
        QMainWindow, QWidget#centralWidget {{
            background-color: {COLORS['background']};
        }}
    """,

    "crypto_card": f"""
        QWidget#cryptoCard {{
            background-color: {COLORS['card_background']};
            border-radius: 8px;
        }}
        QWidget#cryptoCard:hover {{
            background-color: #1A2228;
        }}
        QLabel#symbolLabel {{
            color: {COLORS['text']};
            font-size: 16px;
            font-weight: bold;
        }}
        QLabel#priceLabel {{
            color: {COLORS['text']};
            font-size: 16px;
            font-weight: bold;
        }}
        QLabel#percentageLabel {{
            font-size: 14px;
        }}
        QLabel#removeButton {{
            color: #FF6666;
            font-size: 14px;
            padding: 2px 6px;
        }}
        QLabel#removeButton:hover {{
            background-color: rgba(255, 100, 100, 0.2);
            border-radius: 4px;
        }}
    """,

    "settings_window": f"""
        QMainWindow {{
            background-color: {COLORS['background']};
        }}
        QWidget {{
            color: {COLORS['text']};
        }}
        QGroupBox {{
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }}
        QLineEdit, QSpinBox, QComboBox {{
            background-color: #2A3A4A;
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            padding: 8px;
            color: {COLORS['text']};
        }}
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border-color: {COLORS['accent']};
        }}
        QCheckBox {{
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid {COLORS['border']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {COLORS['accent']};
            border-color: {COLORS['accent']};
        }}
        QPushButton {{
            background-color: #3A4A5A;
            border: none;
            border-radius: 4px;
            padding: 10px 20px;
            color: {COLORS['text']};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #4A5A6A;
        }}
        QPushButton:pressed {{
            background-color: #2A3A4A;
        }}
        QPushButton#testButton {{
            background-color: {COLORS['accent']};
        }}
        QPushButton#testButton:hover {{
            background-color: #5AAA5A;
        }}
        QPushButton#resetButton {{
            background-color: #5A4A4A;
        }}
        QPushButton#resetButton:hover {{
            background-color: #6A5A5A;
        }}
        QLabel#statusLabel {{
            padding: 10px;
            border-radius: 4px;
        }}
        QLabel#statusInfo {{
            background-color: #E3F2FD;
            color: #1976D2;
        }}
        QLabel#statusSuccess {{
            background-color: #E8F5E9;
            color: #2E7D32;
        }}
        QLabel#statusError {{
            background-color: #FFEBEE;
            color: #C62828;
        }}
    """,
}


def get_theme_colors(theme_mode: str) -> dict:
    """Get color scheme based on theme mode."""
    if theme_mode == "dark":
        return DARK_COLORS
    else:  # "light" or default
        return LIGHT_COLORS


def get_stylesheet(name: str, theme_mode: str = "light") -> str:
    """Get a stylesheet by name with theme support."""
    colors = get_theme_colors(theme_mode)

    # Generate stylesheets dynamically based on theme
    stylesheets = {
        "main_window": f"""
            QMainWindow, QWidget#centralWidget {{
                background-color: {colors['background']};
            }}
        """,

        "crypto_card": f"""
            QWidget#cryptoCard {{
                background-color: {colors['card_background']};
                border-radius: 8px;
            }}
            QWidget#cryptoCard:hover {{
                background-color: {colors['hover']};
            }}
            QLabel#symbolLabel {{
                color: {colors['text']};
                font-size: 16px;
                font-weight: bold;
            }}
            QLabel#priceLabel {{
                color: {colors['text']};
                font-size: 16px;
                font-weight: bold;
            }}
            QLabel#percentageLabel {{
                font-size: 14px;
            }}
            QLabel#removeButton {{
                color: #FF6666;
                font-size: 14px;
                padding: 2px 6px;
            }}
            QLabel#removeButton:hover {{
                background-color: rgba(255, 100, 100, 0.2);
                border-radius: 4px;
            }}
        """,

        "settings_window": f"""
            QMainWindow {{
                background-color: {colors['background']};
            }}
            QWidget {{
                color: {colors['text']};
            }}
            QGroupBox {{
                border: 1px solid {colors['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QLineEdit, QSpinBox, QComboBox {{
                background-color: {colors['card_background']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 8px;
                color: {colors['text']};
            }}
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
                border-color: {colors['accent']};
            }}
            QCheckBox {{
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {colors['border']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors['accent']};
                border-color: {colors['accent']};
            }}
            QPushButton {{
                background-color: {colors['card_background']};
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                color: {colors['text']};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {colors['hover']};
            }}
            QPushButton:pressed {{
                background-color: {colors['border']};
            }}
            QPushButton#testButton {{
                background-color: {colors['accent']};
            }}
            QPushButton#testButton:hover {{
                background-color: {colors['accent']};
            }}
            QPushButton#resetButton {{
                background-color: #5A4A4A;
            }}
            QPushButton#resetButton:hover {{
                background-color: #6A5A5A;
            }}
            QLabel#statusLabel {{
                padding: 10px;
                border-radius: 4px;
            }}
            QLabel#statusInfo {{
                background-color: #E3F2FD;
                color: #1976D2;
            }}
            QLabel#statusSuccess {{
                background-color: #E8F5E9;
                color: #2E7D32;
            }}
            QLabel#statusError {{
                background-color: #FFEBEE;
                color: #C62828;
            }}
        """,
    }

    return stylesheets.get(name, "")


def get_color(name: str, theme_mode: str = "light") -> str:
    """Get a color by name with theme support."""
    colors = get_theme_colors(theme_mode)
    return colors.get(name, "#FFFFFF" if theme_mode == "light" else "#000000")
