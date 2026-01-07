---
description: 执行软件版本发布流程：分析变更、更新文档与代码、生成 Git 标签
---

1. 获取当前最新版本及变更日志
// turbo
git fetch --tags; $latest = git tag --sort=-v:refname | Select-Object -First 1; Write-Host "Current Version: $latest"; Write-Host "Changes since last version:"; if ($latest) { git log "$latest..HEAD" --pretty=format:"- %s (%h)" --no-merges } else { git log --pretty=format:"- %s (%h)" --no-merges }

2. 确定新版本号
   - 审阅上述变更日志。
   - 遵循语义化版本控制 (SemVer) 原则确定新版本号 (Major.Minor.Patch)。

3. 更新项目文件
   - **CHANGELOG.md**: 在顶部新增版本章节，包含版本号、日期及分类后的变更列表 (Features, Fixes, etc.)。
   - **ui/settings_window.py**: 更新 `CURRENT_VERSION` 常量为新版本号。

4. 提交发布 Commit
   - 暂存更改: `git add CHANGELOG.md ui/settings_window.py`
   - 提交更改: `git commit -m "chore(release): bump version to vX.Y.Z"` (替换 vX.Y.Z 为实际版本号)

5. 在此处等待用户确认，确认无误后继续执行。

6. 打标签并推送
   - 创建标签: `git tag vX.Y.Z`
   - 推送所有内容: `git push && git push --tags`