"""
通用表单区域组件。
用于分组相关的表单字段。
"""

from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget


class FormSection(QWidget):
    """
    通用表单区域组件。

    可以包含多个字段，自动管理布局。

    使用示例:
        section = FormSection("Proxy Configuration")
        section.add_field(field1)
        section.add_field(field2)
    """

    def __init__(
        self,
        title: str,
        show_border: bool = True,
        spacing: int = 12,
        parent: QWidget | None = None,
    ):
        """
        初始化表单区域。

        Args:
            title: 区域标题
            show_border: 是否显示边框
            spacing: 字段间距
            parent: 父控件
        """
        super().__init__(parent)
        self._title = title
        self._show_border = show_border
        self._spacing = spacing
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        if self._show_border:
            # 使用 QGroupBox 显示边框
            self.container = QGroupBox(self._title)
            layout = QVBoxLayout(self.container)
        else:
            # 使用普通容器
            self.container = QWidget()
            layout = QVBoxLayout(self.container)

        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(self._spacing)

        if not self._show_border:
            # 如果没有边框，添加标题
            title_label = QLabel(self._title)
            title_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; margin: 10px 0px 5px 0px;"
            )
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.addWidget(title_label)
            main_layout.addWidget(self.container)
        else:
            # 使用容器作为主要布局
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.addWidget(self.container)

    def add_field(self, field: QWidget):
        """
        添加字段到区域。

        Args:
            field: 要添加的字段组件
        """
        self.container.layout().addWidget(field)

    def add_stretch(self, stretch: int = 0):
        """
        在区域末尾添加拉伸。

        Args:
            stretch: 拉伸因子
        """
        self.container.layout().addStretch(stretch)

    def get_container(self) -> QWidget:
        """获取容器控件（用于访问布局）"""
        return self.container
