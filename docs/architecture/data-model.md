# 数据模型规范（v1 草案）

> 当前是可执行校验的第一版草案，不代表分类体系已经永久冻结。结构调整通过 Schema 版本管理。

## 1. 数据文件

| 路径 | 用途 |
| --- | --- |
| `data/taxonomy/functions.json` | 功能分类节点 |
| `data/taxonomy/roles.json` | 使用者角色节点 |
| `data/taxonomy/scenarios.json` | 具体任务场景节点 |
| `data/taxonomy/tags.json` | 扁平标签节点 |
| `data/taxonomy/taxonomy-config.json` | 分类体系版本与维度配置 |
| `data/taxonomy/migrations.json` | 分类合并、拆分、弃用和归档记录 |
| `data/assignments/skills.json` | Skill 到分类节点的直接关联 |
| `data/skills/index.json` | Skill 资源索引 |
| `data/plugins/index.json` | Plugin 资源索引 |
| `data/proposals/index.json` | 待审核分类/关联提案 |

## 2. 分类节点

节点包含永久稳定的 `id`、URL 用 `slug`、中英文名称和描述、`parent_id`、别名、生命周期状态、排序及日期。

- ID 前缀分别为 `function.`、`role.`、`scenario.`、`tag.`。
- functions、roles、scenarios 允许多级父子关系；tags 不允许父节点。
- 正式节点状态为 `active`、`deprecated`、`archived`。
- 候选节点不进入正式 taxonomy 文件，而放在 proposals 中。
- 不允许删除或复用 ID。合并/拆分等操作必须保留迁移记录。

## 3. Skill 分类关联

`skills.json` 按 Skill ID 建立映射。每个 Skill 的四个维度都存在数组；数组可以为空。每条关联必须记录：

- `category_id`：分类节点 ID。
- `reason`：明确的语义依据，不得仅凭关键词匹配。
- `confidence`：0 到 1 的辅助置信度。
- `status`：`proposed`、`approved` 或 `rejected`。

审核通过的关联还必须包含 `reviewed_by` 和 `reviewed_at`。正式展示只读取 approved。每个正式发布的 Skill 至少应有一个 approved 功能分类。

## 4. 聚合语义

分类关联只保存直接关联。浏览父分类时，展示层向上聚合所有后代节点的 Skill，并去重；不创建父级关联。结果需区分直接匹配和子分类聚合。

Plugin 可以聚合其所属 Skill 的分类，但聚合结果必须保留来源 Skill ID，且不得反向推断 Plugin 下每个 Skill 都具备所有聚合能力。

## 5. 提案与迁移

AI 只能生成提案。提案状态为 pending、approved、rejected、needs_revision；正式分类节点没有 proposed 状态。

- merge：多个旧节点映射到一个新节点。
- split：一个旧节点拆为多个新节点；旧关联必须逐条重新审核，不可无条件复制。
- deprecate/archive：保留旧 ID 与历史记录。
- 重命名或调整父节点不改变 ID。

## 6. 版本与可追溯性

`schema_version` 表示数据结构版本；`taxonomy_version` 表示分类体系版本。同步资源时记录上游 commit SHA（40 位十六进制），资源文件 hash（SHA-256，64 位十六进制）。趋势分析依赖跨时间快照，因此不得只保留当前状态。

## 7. 校验边界

JSON Schema 负责单文件结构、字段类型和枚举；Python 校验器负责跨文件引用、ID 唯一性、维度前缀、父节点一致性、循环、审核记录和迁移语义。
