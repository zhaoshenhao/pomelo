# 审批流程

## 数据模型

### ApprovalProcess
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int (PK) | 自增主键 |
| library_id | FK | 目标文档库 |
| created_by | FK | 创建者 |
| status | str | semantic_check / content_review / final_preview / completed / cancelled |
| temp_dir | str | /docs/temp/<id>/ |
| locked_by | FK | 当前处理人 (锁定) |
| locked_at | datetime | 锁定时间 |

### ApprovalStep
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int (PK) | 自增主键 |
| process_id | FK | 所属审批 |
| step_type | str | 步骤类型 |
| step_data | JSON | 步骤数据 |

### BackupRecord
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int (PK) | 自增主键 |
| library_id | FK | 所属文档库 |
| backup_path | str | /docs/backup/<lib>-<hash>.zip |
| content_hash | str | SHA256 内容哈希 |
| file_count | int | 备份文件数 |
| total_size | int | 备份大小 (字节) |
| description | str | 操作描述 |

## 审批步骤

1. **semantic_check**: 全文语义比较，判断新文档与文档库关系
2. **selection**: 老师选择处理方式 (覆盖/替换/差异处理)
3. **content_review**: 拼写语法检查或 AI 改写
4. **final_preview**: 预览最终结果
5. **confirm**: 备份 → 格式转换 → 写入文档库

## 锁定机制

- 创建审批时自动锁定给当前用户
- 其他用户尝试操作同一审批 → HTTP 409
- 完成/取消时自动释放
- Admin 可通过 `DELETE /approvals/{id}/lock` 强制解锁
