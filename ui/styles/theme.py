"""
Theme and stylesheet management.
"""

# Dark theme colors
COLORS = {
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


def get_stylesheet(name: str) -> str:
    """Get a stylesheet by name."""
    return STYLESHEETS.get(name, "")


def get_color(name: str) -> str:
    """Get a color by name."""
    return COLORS.get(name, "#FFFFFF")
