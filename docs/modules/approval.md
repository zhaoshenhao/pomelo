# 审批流程

> ⚠️ 本文件已过时。审批现在基于 **`StageDocument` 状态机**：`new → content_review → rewrite → preview → completed / deleted`（无 ApprovalProcess/ApprovalStep 模型，无锁机制）。当前模型与端点见 `docs/architecture.md` 和 `routers/approvals.py`，实时接口以 `GET /docs` 为准。

## 流程

1. 上传文档进入暂存区（`storage/stage/<id>/`）。
2. **内容审核**：语义检查（content-diff）、拼写/语法改写、风格改写（rewrite，使用 AIPrompt）。
3. **预览**：保存预览内容。
4. **确认**：转为 `.md` 写入文档库（可选替换已有文档、或备份后替换）。
