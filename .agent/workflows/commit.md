---
description: 查看变更并进行约定式提交 (Conventional Commit)
---

1. 查看当前状态和差异
// turbo
git status; git diff

2. 分析变更并进行提交
   - 仔细查阅上面的 `git status` 和 `git diff` 输出。
   - 总结变更内容。
   - 对于临时文件，不应该进行提交。
   - 使用英文 (English) 撰写符合 Conventional Commits 规范的提交信息。
     - 格式: `<type>(<scope>): <subject>`
     - 例如: `feat(ui): add new settings button`, `fix(core): resolve websocket timeout`
   - 向用户提议提交命令。例如：`git commit -am "feat(workflow): add commit workflow"` (只有在确实要提交所有已跟踪文件的变更时才使用 -a，否则建议先 add 再 commit)