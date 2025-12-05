# 精简模式/滚动模式实现计划

## 需求总结

根据用户确认，精简模式需要实现以下功能：

1. **窗口高度**：自适应卡片内容（单个卡片高度）
2. **轮播方式**：
   - 支持自动轮播（可配置间隔）
   - 支持鼠标滚轮切换
   - 支持两侧按钮切换
3. **恢复方式**：右上角小按钮展开到完整模式
4. **添加币种**：只在设置窗口中（完整模式和精简模式都移除主窗口的加号按钮）

## 架构设计

### 1. 配置扩展 (config/settings.py)

在 `AppSettings` 中添加以下字段：

```python
@dataclass
class AppSettings:
    # ... 现有字段 ...

    # 精简模式配置
    compact_mode: bool = False  # 是否启用精简模式
    compact_auto_scroll: bool = True  # 是否自动轮播
    compact_scroll_interval: int = 5  # 轮播间隔（秒）

    # 窗口位置分离存储
    compact_window_x: int = 100  # 精简模式窗口X位置
    compact_window_y: int = 100  # 精简模式窗口Y位置
```

**设计理由**：
- 分离两种模式的窗口位置，避免切换时窗口跳动
- 轮播间隔可配置，满足不同用户需求
- 默认启用自动轮播，提供更好的开箱体验

### 2. UI 组件调整

#### 2.1 主窗口 (ui/main_window.py)

**核心改动**：
- 添加 `_compact_mode` 状态标志
- 实现 `_switch_to_compact_mode()` 和 `_switch_to_normal_mode()` 方法
- 在精简模式下：
  - 隐藏 Toolbar（包括加号按钮）
  - 隐藏 Pagination
  - 只显示一个 CryptoCard
  - 添加右上角展开按钮
  - 添加左右切换按钮
  - 调整窗口大小为自适应卡片高度

**窗口尺寸计算**：
```python
# 精简模式窗口高度 = 卡片高度 + 控制按钮高度 + 边距
# 卡片高度约 70px（图标16 + 价格16 + 间距）
# 控制按钮高度约 30px
# 总高度约 110px
COMPACT_HEIGHT = 110
COMPACT_WIDTH = 160  # 保持宽度不变
```

#### 2.2 新增组件：CompactControls (ui/widgets/compact_controls.py)

创建一个新的控件，包含：
- 左切换按钮（◀）
- 当前币种指示器（1/5）
- 右切换按钮（▶）
- 展开按钮（右上角，使用 FluentIcon.EXPANDER）

**布局**：
```
┌─────────────────────────────────┐
│  ◀  [BTC-USDT]  1/5  ▶      [↗] │
└─────────────────────────────────┘
```

#### 2.3 Toolbar 调整 (ui/widgets/toolbar.py)

**移除加号按钮**：
- 删除 `add_btn` 及相关代码
- 删除 `add_clicked` 信号
- 保留其他按钮（设置、最小化、置顶、关闭）

**设计理由**：用户明确要求添加币种功能只在设置窗口中

### 3. 轮播逻辑实现

#### 3.1 自动轮播

使用 `QTimer` 实现：

```python
class MainWindow(QMainWindow):
    def __init__(self):
        # ...
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.timeout.connect(self._auto_scroll_next)
        self._current_compact_index = 0

    def _start_auto_scroll(self):
        """启动自动轮播"""
        if self._settings_manager.settings.compact_auto_scroll:
            interval = self._settings_manager.settings.compact_scroll_interval * 1000
            self._auto_scroll_timer.start(interval)

    def _stop_auto_scroll(self):
        """停止自动轮播"""
        self._auto_scroll_timer.stop()

    def _auto_scroll_next(self):
        """自动切换到下一个币种"""
        self._show_next_pair()
```

#### 3.2 鼠标滚轮切换

重写 `wheelEvent`：

```python
def wheelEvent(self, event: QWheelEvent):
    """Handle mouse wheel for pair switching in compact mode."""
    if self._compact_mode:
        delta = event.angleDelta().y()
        if delta > 0:
            self._show_prev_pair()
        elif delta < 0:
            self._show_next_pair()
        event.accept()
    else:
        super().wheelEvent(event)
```

#### 3.3 按钮切换

CompactControls 的左右按钮直接调用 `_show_prev_pair()` 和 `_show_next_pair()`

#### 3.4 鼠标悬停暂停

```python
def enterEvent(self, event):
    """暂停自动轮播"""
    if self._compact_mode:
        self._stop_auto_scroll()
    super().enterEvent(event)

def leaveEvent(self, event):
    """恢复自动轮播"""
    if self._compact_mode:
        self._start_auto_scroll()
    super().leaveEvent(event)
```

### 4. 设置窗口扩展 (ui/settings_window.py)

#### 4.1 新增 CompactModeSettingCard

创建一个新的设置卡片：

```python
class CompactModeSettingCard(ExpandGroupSettingCard):
    """精简模式配置卡片"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            FluentIcon.MINIMIZE,
            "Compact Mode Settings",
            "Configure compact mode behavior and auto-scroll settings",
            parent
        )
        self._setup_ui()

    def _setup_ui(self):
        # 启用精简模式开关
        # 自动轮播开关
        # 轮播间隔滑块（1-30秒）
```

#### 4.2 设置窗口布局调整

在 Appearance 组中添加 CompactModeSettingCard：

```python
# Appearance settings group
appearance_group = SettingCardGroup("Appearance", content_widget)
self.theme_card = ThemeSettingCard(appearance_group)
self.compact_mode_card = CompactModeSettingCard(appearance_group)  # 新增
appearance_group.addSettingCard(self.theme_card)
appearance_group.addSettingCard(self.compact_mode_card)  # 新增
```

### 5. 模式切换流程

#### 5.1 启动时

```python
# main_window.py __init__
def __init__(self):
    # ... 现有初始化 ...

    # 根据设置决定启动模式
    if self._settings_manager.settings.compact_mode:
        self._switch_to_compact_mode()
    else:
        self._switch_to_normal_mode()
```

#### 5.2 切换到精简模式

```python
def _switch_to_compact_mode(self):
    """切换到精简模式"""
    self._compact_mode = True

    # 保存当前窗口位置（完整模式）
    pos = self.pos()
    self._settings_manager.settings.window_x = pos.x()
    self._settings_manager.settings.window_y = pos.y()

    # 隐藏组件
    self.toolbar.hide()
    self.pagination.hide()

    # 调整窗口大小
    self.setFixedSize(COMPACT_WIDTH, COMPACT_HEIGHT)

    # 移动到精简模式位置
    self.move(
        self._settings_manager.settings.compact_window_x,
        self._settings_manager.settings.compact_window_y
    )

    # 显示精简模式控件
    self.compact_controls.show()

    # 只显示第一个卡片
    self._current_compact_index = 0
    self._update_compact_display()

    # 启动自动轮播
    self._start_auto_scroll()
```

#### 5.3 切换到完整模式

```python
def _switch_to_normal_mode(self):
    """切换到完整模式"""
    self._compact_mode = False

    # 保存当前窗口位置（精简模式）
    pos = self.pos()
    self._settings_manager.settings.compact_window_x = pos.x()
    self._settings_manager.settings.compact_window_y = pos.y()

    # 停止自动轮播
    self._stop_auto_scroll()

    # 隐藏精简模式控件
    self.compact_controls.hide()

    # 显示组件
    self.toolbar.show()
    if self.pagination.total_pages() > 1:
        self.pagination.show()

    # 调整窗口大小
    self.setFixedSize(160, 320)

    # 移动到完整模式位置
    self.move(
        self._settings_manager.settings.window_x,
        self._settings_manager.settings.window_y
    )

    # 更新卡片显示
    self._update_cards_display()
```

### 6. 实现步骤

1. **配置层**：扩展 `AppSettings`，添加精简模式相关字段
2. **UI 组件**：创建 `CompactControls` 组件
3. **Toolbar 调整**：移除加号按钮
4. **主窗口改造**：
   - 添加模式切换逻辑
   - 实现轮播功能
   - 添加鼠标滚轮支持
5. **设置窗口**：添加 `CompactModeSettingCard`
6. **测试**：
   - 模式切换流畅性
   - 窗口位置保存/恢复
   - 自动轮播功能
   - 鼠标滚轮切换
   - 按钮切换

## 潜在问题与解决方案

### 问题 1：窗口高度自适应

**问题**：卡片高度可能因内容不同而变化（如价格位数、图标加载失败）

**解决方案**：
- 设置卡片最小高度，确保布局稳定
- 使用固定高度而非自适应，避免窗口抖动
- 建议固定高度为 110px

### 问题 2：轮播时的动画效果

**问题**：直接切换可能显得生硬

**解决方案**：
- 第一版不实现动画，保持简单
- 后续可使用 `QPropertyAnimation` 实现淡入淡出效果

### 问题 3：精简模式下的拖动

**问题**：没有 Toolbar，如何拖动窗口？

**解决方案**：
- 保持现有的 `mousePressEvent`/`mouseMoveEvent` 逻辑
- 整个窗口都可以拖动（除了按钮区域）

### 问题 4：设置更改后的即时生效

**问题**：用户在设置中切换精简模式，如何即时生效？

**解决方案**：
- 设置窗口添加 `compact_mode_changed` 信号
- 主窗口监听该信号，调用相应的切换方法
- 无需重启应用

## 文件清单

### 需要修改的文件

1. `config/settings.py` - 添加精简模式配置字段
2. `ui/main_window.py` - 实现模式切换和轮播逻辑
3. `ui/widgets/toolbar.py` - 移除加号按钮
4. `ui/settings_window.py` - 添加精简模式设置卡片
5. `ui/widgets/setting_cards.py` - 实现 `CompactModeSettingCard`

### 需要创建的文件

1. `ui/widgets/compact_controls.py` - 精简模式控制组件

### 需要更新的文件

1. `TODO.md` - 标记精简模式为已完成
2. `CLAUDE.md` - 更新项目文档

## 时间估算（仅供参考）

- 配置层扩展：30分钟
- CompactControls 组件：1小时
- 主窗口改造：2-3小时
- 设置窗口扩展：1小时
- 测试和调试：1-2小时

**总计**：约 5-7 小时的开发时间

## 后续优化方向

1. 添加切换动画效果
2. 支持键盘快捷键切换（左右箭头）
3. 精简模式下的右键菜单（快速访问设置、退出等）
4. 记忆精简模式下的当前币种索引
5. 支持点击卡片暂停/恢复自动轮播
