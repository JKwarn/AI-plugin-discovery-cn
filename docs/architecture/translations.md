# Skill 中文译文存储与来源追踪

## 1. 设计目标

中文译文是独立的阅读内容，不是上游 Skill 原文的替代品。译文必须能够追溯到确定的上游 Skill 文件版本；上游内容变化时，系统能够识别译文已过期，要求重新审阅。

本机制不修改上游仓库，也不把译文写入同步程序生成的 `data/skills/index.json`。

## 2. 译文文件存储

每个 Skill 的简体中文译文存放在：

    content/skills/<skill-id>/SKILL.zh-CN.md

例如：

    content/skills/pstack.how/SKILL.zh-CN.md

一个 Skill 的不同语言版本可以使用独立 locale 文件名扩展，但本阶段只定义并启用 `zh-CN`。译文正文使用 Markdown；不要求复制原文 YAML Frontmatter，来源元数据统一放在注册表中。

## 3. 译文注册表

注册表路径：

    data/translations/skills.json

Schema：

    schemas/translation-index.schema.json

每条登记至少包含：

- `skill_id`、`locale`：唯一标识一份 Skill 译文。
- `path`：仓库内译文文件路径。
- `source_id`、`source_path`：上游来源和原始 Skill 路径。
- `source_url`：指向固定上游 revision 的原文链接。
- `source_revision`：翻译所依据的上游 commit SHA。
- `source_file_hash`：原始文件内容的 SHA-256。
- `source_blob_sha`：原始文件的 Git Blob SHA。
- `status`：`draft` 或 `reviewed`。
- `translated_at`：译文创建/最近一次实质修改时间。
- `reviewed_at`：状态为 `reviewed` 时必填。

注册表只登记已经存在的译文文件。尚未开始翻译的 Skill 不创建空记录。

## 4. 新鲜度与重新审阅

译文是否过期不作为人工维护的状态字段，而由校验程序动态计算。校验程序将注册表记录中的 `source_path`、`source_file_hash`、`source_blob_sha` 与当前 Skill 索引比较：

- 三项一致：来源版本仍匹配。
- 任一项变化：输出过期警告。译文记录保留原始来源信息，不自动改写为新 revision。
- 过期警告不使上游同步 PR 的数据校验失败；译文需要在后续 PR 中对照新原文更新并重新审阅。
- 重新翻译或确认无需修改后，更新来源字段、译文内容和 `translated_at`；只有完成审阅后才设置 `status: reviewed` 和 `reviewed_at`。

比较内容 hash 和 Blob SHA，而不是只比较仓库最新 commit。上游其他文件变化不会导致所有译文都被误判过期。

## 5. 校验规则

`scripts/validate/validate_translations.py` 校验：

1. 注册表符合 JSON Schema。
2. 每个 `skill_id + locale` 组合唯一，译文路径不能重复。
3. 每条记录引用现有 Skill。
4. 译文路径必须位于 `content/skills/` 且对应文件存在。
5. 来源 revision、文件 SHA-256 和 Blob SHA 格式正确。
6. `reviewed` 记录必须包含 `reviewed_at`。
7. 来源信息与当前 Skill 索引不一致时，输出过期警告，不阻断数据校验。

## 6. 翻译内容要求

- 保留 Markdown 标题层级、列表、表格和代码块结构。
- 命令、路径、配置键、变量名、API、代码标识符和可执行示例保持原样；必要时在代码块外解释。
- 不擅自删减限制条件、失败处理、工具调用规则或安全要求。
- 译文与原文语义不确定时保留原始术语并添加准确解释，不凭空补充行为。
- 译文用于阅读和检索，不代表可直接安装或执行的插件包。

## 7. 与上游同步的关系

上游同步程序继续只更新 Plugin/Skill 元数据和来源快照。它不读写 `content/skills/` 或 `data/translations/`。译文校验作为独立步骤加入仓库数据校验工作流；源文件变化只产生过期提示，不自动覆盖或删除译文。
