# Skill 中文译文

每个 Skill 的中文译文独立存放，不写入上游同步生成的元数据索引，也不修改上游原文。

## 文件路径

译文统一使用以下路径：

`content/skills/<skill-id>/SKILL.zh-CN.md`

例如：

`content/skills/pstack.how/SKILL.zh-CN.md`

## 来源与状态

译文的来源 revision、源文件 SHA-256、Git Blob SHA、原始路径和固定链接统一登记在 `data/translations/skills.json` 中。注册表是译文与上游来源之间的追踪关系，不复制上游正文。

译文状态只有 `draft` 和 `reviewed`。来源是否过期由校验程序比较注册表记录与当前 `data/skills/index.json` 中的源文件信息后计算，不手工维护第三种状态。

译文文件应保留原文的结构、代码块、命令、路径、配置键和技术标识符；不得把中文译文描述为可直接安装或执行的原始插件包。
