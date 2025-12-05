# 配置文件迁移系统设计文档

## 🎯 设计目标

为 Crypto Monitor 实现完整的**配置文件迁移系统**，支持应用版本升级时的配置自动迁移、验证和恢复。

### 核心需求

1. **版本管理** - 配置文件的版本控制和兼容性检查
2. **自动迁移** - 应用启动时自动检测并迁移旧版本配置
3. **数据验证** - 迁移前后验证配置数据有效性
4. **安全备份** - 迁移前自动备份原配置文件
5. **失败回滚** - 迁移失败时自动回滚到之前版本
6. **向后兼容** - 支持多个历史版本的配置

---

## 📋 系统架构

### 1. 配置版本定义

```python
class ConfigVersion(Enum):
    """配置文件版本枚举"""
    V1_0_0 = "1.0.0"  # 初始版本 (当前无版本号)
    V2_0_0 = "2.0.0"  # 添加新功能 (compact_mode, 窗口位置等)
    V2_1_0 = "2.1.0"  # WebSocket重连增强 (新增统计配置)
    V3_0_0 = "3.0.0"  # 未来版本 (预留)
```

### 2. 迁移器接口

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseMigration(ABC):
    """配置迁移器基类"""

    @property
    @abstractmethod
    def from_version(self) -> ConfigVersion:
        """源版本"""
        pass

    @property
    @abstractmethod
    def to_version(self) -> ConfigVersion:
        """目标版本"""
        pass

    @abstractmethod
    def migrate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """执行迁移"""
        pass

    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> bool:
        """验证配置是否适用于此迁移器"""
        pass
```

### 3. 迁移管理器

```python
class MigrationManager:
    """配置迁移管理器"""

    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.migrations: List[BaseMigration] = []
        self.backup_dir = config_file.parent / 'backups'

    def register_migration(self, migration: BaseMigration):
        """注册迁移器"""
        self.migrations.append(migration)

    def migrate_if_needed(self) -> bool:
        """执行迁移（如果需要）"""
        # 1. 读取当前配置
        # 2. 检测版本
        # 3. 应用迁移链
        # 4. 验证结果
        # 5. 保存并备份
        pass
```

---

## 🔄 迁移流程

### 启动时迁移流程

```
应用启动
    ↓
读取配置文件
    ↓
检测版本号
    ↓
    ┌─────────────────────────┐
    │ 无版本号 (V1.0.0前)     │
    └─────────────────────────┘
    ↓
查找可用迁移器
    ↓
按顺序执行迁移链
    ↓
验证迁移结果
    ↓
    ┌──────────┬──────────────┐
    │ 验证成功 │  验证失败    │
    └──────────┴──────────────┘
    ↓           ↓
保存新配置   回滚并警告
    ↓
备份旧配置
    ↓
迁移完成
```

### 迁移示例：V1.0.0 → V2.0.0

**V1.0.0 配置结构:**
```json
{
  "theme_mode": "light",
  "opacity": 100,
  "crypto_pairs": ["BTC-USDT", "ETH-USDT"],
  "proxy": {...},
  "window_x": 100,
  "window_y": 100,
  "always_on_top": false
}
```

**V2.0.0 配置结构:**
```json
{
  "version": "2.0.0",
  "theme_mode": "light",
  "opacity": 100,
  "crypto_pairs": ["BTC-USDT", "ETH-USDT"],
  "proxy": {...},
  "window_x": 100,
  "window_y": 100,
  "always_on_top": false,
  "compact_mode": {              // 新增
    "enabled": false,
    "auto_scroll": true,
    "scroll_interval": 5,
    "window_x": 100,
    "window_y": 100
  }
}
```

**迁移逻辑:**
```python
def migrate_v1_to_v2(config):
    """V1.0.0 → V2.0.0 迁移器"""
    # 添加版本号
    config['version'] = '2.0.0'

    # 添加紧凑模式默认配置
    config['compact_mode'] = {
        'enabled': False,
        'auto_scroll': True,
        'scroll_interval': 5,
        'window_x': config.get('window_x', 100),
        'window_y': config.get('window_y', 100)
    }

    # 保留所有原有字段
    return config
```

---

## 💾 备份机制

### 备份目录结构

```
~/.config/crypto-monitor/
├── settings.json          # 当前配置
├── settings.json.backup   # 上次备份
├── backups/
│   ├── settings_20241205_143022_v1.0.0.json
│   ├── settings_20241205_143022_v2.0.0.json
│   └── settings_20241205_143022_v2.1.0.json
└── migrations.log         # 迁移日志
```

### 备份策略

1. **自动备份** - 每次迁移前自动备份
2. **时间戳命名** - `settings_YYYYMMDD_HHMMSS_v{version}.json`
3. **保留策略** - 保留最近5次备份
4. **压缩存储** - 可选压缩节省空间

---

## ✅ 验证机制

### 配置验证器

```python
class ConfigValidator:
    """配置数据验证器"""

    @staticmethod
    def validate_required_fields(config: Dict[str, Any]) -> bool:
        """验证必需字段"""
        required = ['theme_mode', 'opacity', 'crypto_pairs']
        return all(field in config for field in required)

    @staticmethod
    def validate_pairs(config: Dict[str, Any]) -> bool:
        """验证交易对格式"""
        pairs = config.get('crypto_pairs', [])
        for pair in pairs:
            if not re.match(r'^[A-Z0-9]+-[A-Z0-9]+$', pair):
                return False
        return True

    @staticmethod
    def validate_theme_mode(config: Dict[str, Any]) -> bool:
        """验证主题模式"""
        valid_modes = ['light', 'dark', 'auto']
        return config.get('theme_mode') in valid_modes

    @staticmethod
    def validate_opacity(config: Dict[str, Any]) -> bool:
        """验证透明度值"""
        opacity = config.get('opacity', 100)
        return isinstance(opacity, int) and 0 <= opacity <= 100
```

### 验证流程

```
迁移前验证
    ↓
应用迁移
    ↓
迁移后验证
    ↓
    ┌──────────┬──────────────┐
    │ 验证通过 │  验证失败    │
    └──────────┴──────────────┘
    ↓           ↓
保存配置    回滚配置
```

---

## 🛠️ 实现计划

### 阶段1: 核心框架
- [ ] 创建 `config/migration.py` 模块
- [ ] 定义 `ConfigVersion` 枚举
- [ ] 实现 `BaseMigration` 抽象类
- [ ] 实现 `MigrationManager` 类

### 阶段2: 迁移器实现
- [ ] 实现 V1→V2 迁移器 (添加compact_mode)
- [ ] 实现 V2→V3 迁移器 (预留)
- [ ] 集成到 SettingsManager

### 阶段3: 验证和备份
- [ ] 实现 ConfigValidator
- [ ] 实现自动备份机制
- [ ] 实现回滚机制
- [ ] 添加迁移日志

### 阶段4: 测试
- [ ] 单元测试
- [ ] 集成测试
- [ ] 边界情况测试
- [ ] 性能测试

---

## 📊 迁移器设计示例

### V1.0.0 → V2.0.0 迁移器

```python
class MigrationV1ToV2(BaseMigration):
    """V1.0.0 → V2.0.0 迁移器"""

    @property
    def from_version(self) -> ConfigVersion:
        return ConfigVersion.V1_0_0

    @property
    def to_version(self) -> ConfigVersion:
        return ConfigVersion.V2_0_0

    def validate(self, config: Dict[str, Any]) -> bool:
        """验证是否为V1.0.0配置"""
        return 'version' not in config and 'compact_mode' not in config

    def migrate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """执行迁移"""
        # 1. 添加版本号
        config['version'] = '2.0.0'

        # 2. 添加紧凑模式配置
        config['compact_mode'] = {
            'enabled': False,
            'auto_scroll': True,
            'scroll_interval': 5,
            'window_x': config.get('window_x', 100),
            'window_y': config.get('window_y', 100)
        }

        return config
```

### V2.0.0 → V2.1.0 迁移器

```python
class MigrationV2ToV21(BaseMigration):
    """V2.0.0 → V2.1.0 迁移器"""

    @property
    def from_version(self) -> ConfigVersion:
        return ConfigVersion.V2_0_0

    @property
    def to_version(self) -> ConfigVersion:
        return ConfigVersion.V2_1_0

    def validate(self, config: Dict[str, Any]) -> bool:
        """验证是否为V2.0.0配置"""
        return config.get('version') == '2.0.0'

    def migrate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """执行迁移"""
        # V2.1.0 主要添加WebSocket相关配置
        if 'websocket' not in config:
            config['websocket'] = {
                'auto_reconnect': True,
                'reconnect_initial_delay': 1.0,
                'reconnect_max_delay': 30.0,
                'heartbeat_timeout': 60
            }

        config['version'] = '2.1.0'
        return config
```

---

## 🔍 使用示例

### SettingsManager 集成

```python
class SettingsManager:
    """增强的配置管理器 - 包含迁移功能"""

    def __init__(self, config_dir: Optional[Path] = None):
        # ... 原有初始化 ...

        # 初始化迁移管理器
        self.migration_manager = MigrationManager(self.config_file)
        self._register_migrations()

    def _register_migrations(self):
        """注册所有迁移器"""
        self.migration_manager.register_migration(MigrationV1ToV2())
        self.migration_manager.register_migration(MigrationV2ToV21())

    def load(self) -> AppSettings:
        """加载配置 - 自动执行迁移"""
        # 先执行迁移
        migrated = self.migration_manager.migrate_if_needed()

        # 然后加载配置
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 解析配置...
                self.settings = self._parse_config(data)

            except Exception as e:
                print(f"Error loading settings: {e}")
                self.settings = AppSettings()

        return self.settings
```

### 手动触发迁移

```python
# 手动触发迁移（用于调试）
manager = get_settings_manager()
result = manager.migration_manager.migrate_if_needed()
if result:
    print("✅ 配置已迁移到最新版本")
else:
    print("❌ 配置迁移失败")
```

---

## ⚠️ 注意事项

### 兼容性
1. **向后兼容** - 始终保持对新版本配置格式的支持
2. **向前兼容** - 迁移器设计要考虑未来版本
3. **默认值** - 新字段必须提供合理默认值

### 安全性
1. **原子操作** - 迁移过程要保证原子性
2. **异常处理** - 捕获所有可能的异常
3. **日志记录** - 详细记录迁移过程

### 性能
1. **增量迁移** - 只迁移需要迁移的配置
2. **快速验证** - 验证逻辑要高效
3. **缓存机制** - 可缓存已验证的配置

---

## 📈 扩展计划

### 未来版本支持
- V3.0.0 - 多数据源支持
- V4.0.0 - 云端配置同步
- V5.0.0 - 插件系统配置

### 高级功能
1. **可视化迁移** - GUI显示迁移进度
2. **迁移预览** - 迁移前预览变更
3. **选择性迁移** - 用户选择迁移项
4. **配置合并** - 支持多份配置合并

---

## 🎉 总结

配置文件迁移系统将为 Crypto Monitor 提供：

- ✅ **零停机升级** - 应用启动时自动迁移
- ✅ **数据安全** - 自动备份和回滚机制
- ✅ **版本透明** - 用户无需关心配置版本
- ✅ **扩展性强** - 易于添加新迁移器
- ✅ **健壮性高** - 完善的验证和错误处理

这将大大提升用户体验和应用的可维护性！
