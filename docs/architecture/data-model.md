# 数据模型规范（v1.0.0，核心契约已冻结）

本文定义本仓库分类数据模型 v1.0.0。六份 JSON Schema 与本文共同构成当前核心数据契约。正式数据和测试夹具必须遵守这些结构；不得在不升级 `schema_version` 的情况下改变字段含义或结构。

## 1. 数据文件

| 路径 | 用途 | Schema |
| --- | --- | --- |
| `data/taxonomy/functions.json` | 功能分类节点 | `taxonomy-file.schema.json` |
| `data/taxonomy/roles.json` | 使用者角色节点 | `taxonomy-file.schema.json` |
| `data/taxonomy/scenarios.json` | 具体任务场景节点 | `taxonomy-file.schema.json` |
| `data/taxonomy/tags.json` | 扁平标签节点 | `taxonomy-file.schema.json` |
| `data/taxonomy/taxonomy-config.json` | 分类体系版本与维度配置 | `taxonomy-config.schema.json` |
| `data/taxonomy/migrations.json` | 分类合并、拆分、弃用和归档记录 | `migration.schema.json` |
| `data/assignments/skills.json` | Skill 到分类节点的直接关联 | `assignment.schema.json` |
| `data/proposals/index.json` | 待审核分类/关联提案 | `proposal.schema.json` |
| `data/taxonomy/changelog.json` | 正式分类变更摘要 | v1.0.0 暂不允许写入新条目；首次写入前必须补充专用 Schema |

Plugin 和 Skill 上游索引、来源快照属于资源同步模型，不属于本次分类核心 Schema 冻结范围。

## 2. 版本规则

- `schema_version` 表示数据结构与字段语义版本。v1 核心 Schema 当前固定为 `1.0.0`。
- `taxonomy_version` 表示分类体系本身的语义版本，与 Schema 版本独立。
- Schema 的字段结构或既有字段含义发生不兼容变化时，必须升级主版本。
- 增加可选字段或扩展枚举时，必须升级次版本，并同步更新 Schema、校验器、测试和文档。
- 仅修正不改变有效数据集合的描述或校验实现缺陷时，可升级补丁版本。
- 分类体系新增分类通常升级次版本；分类含义发生重大重组（例如影响既有分类解释的合并或拆分）升级主版本；不改变语义的文字修订可升级补丁版本。

当前数据中的 `schema_version` 和 `taxonomy_version` 均为 `1.0.0`。

## 3. 分类节点

节点包含永久稳定的 `id)、URL 用 `slug)、中英文名称和描述、`parent_id`、别名、生命周期状态、排序及日期。

- ID 前缀分别为 `function.`、`role.`、`scenario.`、`tag.`。
- functions、roles、scenarios 允许多级父子关系；tags 不允许父节点。
- 正式节点状态为 `active`、`deprecated`、`archived`。
- `id` 永不复用；`slug` 在同一维度内唯一。
- 候选节点不进入正式 taxonomy 文件，而放在 proposals 中。
- 不允许直接删除正式节点。合并、拆分、弃用和归档必须保留迁移记录。

## 4. Skill 分类关联

`skills.json` 按 Skill ID 建立映射。每个 Skill 的四个维度都存在数组；数组可以为空。每条关联必须记录：

- `category_id`：分类节点 ID。
- `reason`：明确的语义依据，不得仅凭关键词匹配。
- `confidence`：0 到 1 的辅助置信度。
- `status`：`proposed`、`approved` 或 `rejected`。

审核通过的关联还必须包含 `reviewed_by` 和 `reviewed_at`。正式展示只读取 approved。每个正式发布的 Skill 至少应有一个 approved 功能分类；该发布门槛由严格校验模式执行。

## 5. 提案与迁移

AI 只能生成提案。提案状态为 pending、approved、rejected、needs_revision；正式分类节点没有 proposed 状态。

- merge：至少两个来源节点映射到一个目标节点。
- split：一个来源节点映射到至少两个目标节点；旧关联必须逐条重新审核，不可无条件复制。
- deprecate/archive：一个来源节点，不设置目标节点。
- 所有迁移来源和目标必须存在，且属于迁移记录声明的维度。
- 重命名或调整父节点不改变 ID。

## 6. 聚合语义

分类关联只保存直接关联。浏览父分类时，展示层向上聚合所有后代节点的 Skill，并去重；不创建父级关联。结果需区分直接匹配和子分类聚合。

Plugin 可以聚合其所属 Skill 的分类，但聚合结果必须保留来源 Skill ID，且不得反向推断 Plugin 下每个 Skill 都具备所有聚合能力。聚合输出是可再生成的派生数据，不是事实来源。

## 7. 可追溯性

同步资源时记录上游 commit SHA（40 位十六进制），资源文件 hash（SHA-256，64 位十六进制）。分类关联保留审核信息及其依据的资源 revision。趋势分析依赖跨时间快照，因此不得只保留当前状态。

## 8. 校验边界

- JSON Schema 负责单文件结构、字段类型、必填字段、枚举和格式。
- Python 校验器负责跨文件引用、ID 唯一性、维度前缀、父节点一致性、循环、审核记录和迁移语义。
- 聚合程序只读取 active Skill 和 approved 关联，不修改分类注册表或关联源文件。
- 测试夹具与正式数据分离；测试夹具中的分类不构成正式分类事实。
