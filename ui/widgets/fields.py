"""
通用表单字段组件。
提供可复用的表单字段构建块。
"""

from typing import Optional, Union
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt


class LabeledField(QWidget):
    """
    通用标签字段组件。
    可以包装任何输入控件并提供标签。

    使用示例:
        field = LabeledField("Host:", QLineEdit())
        field = LabeledField("Port:", QSpinBox(), min_width=100)
    """

    def __init__(
        self,
        label: str,
        widget: QWidget,
        stretch_label: int = 0,
        stretch_widget: int = 1,
        min_label_width: int = 80,
        min_widget_width: int = 200,
        parent: Optional[QWidget] = None
    ):
        """
        初始化标签字段组件。

        Args:
            label: 标签文本
            widget: 要包装的控件
            stretch_label: 标签的拉伸因子
            stretch_widget: 控件的拉伸因子
            min_label_width: 标签最小宽度
            min_widget_width: 控件最小宽度
            parent: 父控件
        """
        super().__init__(parent)
        self._setup_ui(label, widget, stretch_label, stretch_widget, min_label_width, min_widget_width)

    def _setup_ui(
        self,
        label: str,
        widget: QWidget,
        stretch_label: int,
        stretch_widget: int,
        min_label_width: int,
        min_widget_width: int
    ):
        """设置UI布局"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 创建标签
        label_widget = QLabel(f"{label}:")
        label_widget.setMinimumWidth(min_label_width)

        layout.addWidget(label_widget, stretch_label)

        # 设置控件最小宽度
        widget.setMinimumWidth(min_widget_width)

        layout.addWidget(widget, stretch_widget)

    def get_widget(self) -> QWidget:
        """获取包装的控件"""
        # 布局中的第二个控件（索引1）是实际的输入控件
        return self.layout().itemAt(1).widget()


class LabeledLineEdit(LabeledField):
    """带标签的单行输入框"""

    def __init__(
        self,
        label: str,
        placeholder: str = "",
        is_password: bool = False,
        min_width: int = 250,
        parent: Optional[QWidget] = None
    ):
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        if is_password:
            edit.setEchoMode(QLineEdit.EchoMode.Password)

        super().__init__(label, edit, min_widget_width=min_width, parent=parent)

    def text(self) -> str:
        """获取输入文本"""
        return self.get_widget().text()

    def set_text(self, text: str):
        """设置输入文本"""
        self.get_widget().setText(text)


class LabeledSpinBox(LabeledField):
    """带标签的数值输入框"""

    def __init__(
        self,
        label: str,
        min_val: int,
        max_val: int,
        default: int,
        min_width: int = 150,
        parent: Optional[QWidget] = None
    ):
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)

        super().__init__(label, spin, min_widget_width=min_width, parent=parent)

    def value(self) -> int:
        """获取数值"""
        return self.get_widget().value()

    def set_value(self, val: int):
        """设置数值"""
        self.get_widget().setValue(val)


class LabeledComboBox(LabeledField):
    """带标签的下拉选择框"""

    def __init__(
        self,
        label: str,
        items: list,
        min_width: int = 150,
        parent: Optional[QWidget] = None
    ):
        combo = QComboBox()
        combo.addItems(items)

        super().__init__(label, combo, min_widget_width=min_width, parent=parent)

    def current_text(self) -> str:
        """获取当前选择文本"""
        return self.get_widget().currentText()

    def set_current_text(self, text: str):
        """设置当前选择文本"""
        self.get_widget().setCurrentText(text)


class LabeledCheckBox(QWidget):
    """带标签的复选框（占用整行）"""

    def __init__(
        self,
        label: str,
        checked: bool = False,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._setup_ui(label, checked)

    def _setup_ui(self, label: str, checked: bool):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.checkbox = QCheckBox(label)
        self.checkbox.setChecked(checked)

        layout.addWidget(self.checkbox)
        layout.addStretch()

    def is_checked(self) -> bool:
        """检查是否选中"""
        return self.checkbox.isChecked()

    def set_checked(self, checked: bool):
        """设置选中状态"""
        self.checkbox.setChecked(checked)
