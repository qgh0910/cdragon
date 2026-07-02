# 旧 Chroma Collection 迁移报告

- 生成时间：2026-07-02T09:36:19
- 扫描目录：`/Users/quguanhua/code/lawchat/cdragon/data/chroma`
- Collection 数量：3
- 默认建议目标：`legacy_admin_only`
- 安全边界：本报告仅执行只读扫描，不删除、不重建、不登记任何 Chroma collection。

## 迁移原则

- 不默认公开历史资料库。
- 无旧租户前缀的 collection 先按 `legacy_admin_only` 隐藏待处理。
- 带旧 `tenant_id__collection` 前缀的 collection 仅作为线索，需管理员人工确认后再迁移到用户库。
- 本报告不修改 SQLite `knowledge_bases`，不写入 Chroma，不调用删除或重建接口。

## 扫描结果

| collection 名 | original_name | 推断旧租户 | 文档数量 | 建议目标 | 备注 |
|---|---|---:|---:|---|---|
| public__public_law | public__public_law | default | 0 | legacy_admin_only | 疑似新知识库内部命名，需人工确认是否已迁移 |
| test | test | default | 75 | legacy_admin_only | 无旧租户前缀，默认隐藏待管理员确认 |
| user__usr_0ee3670afe_87edeb34_kb | user__usr_0ee3670afe_87edeb34_kb | default | 135 | legacy_admin_only | 疑似新知识库内部命名，需人工确认是否已迁移 |

## 人工确认清单

- 对每个 collection 确认是否仍需要保留。
- 对疑似旧租户前缀的 collection，确认旧租户与现有用户的对应关系。
- 确认后再通过后续迁移步骤登记到 `knowledge_bases`，或保持 `legacy_admin_only`。
