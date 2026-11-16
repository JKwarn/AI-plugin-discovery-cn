# 分类候选生成器

`scripts/classify/generate_proposals.py` 是首期可复现的规则型分类候选生成器。

## 输入

- `data/skills/index.json`：Skill 名称、描述、来源路径、上游 revision。
- `data/taxonomy/*.json`：当前有效分类节点。
- `data/sources/index.json`：上游来源 revision 的回退信息。

首期只分析资源元数据，不读取或执行 Skill 内容。规则集中定义在脚本的 `RULES` 中；只有命中明确的高信号表达才会生成候选。

## 输出

每个命中的 Skill 生成一条 `kind=assignment`、`status=pending` 的提案。候选关联包含分类 ID、理由、置信度、来源 revision、分类器版本和命中证据。

示例：

```bash
python scripts/classify/generate_proposals.py --output /tmp/classification-proposals.json
```

省略 `--output` 时，JSON 输出到标准输出，便于管道处理。

## 安全边界

- 不修改 `data/assignments/skills.json`。
- 不修改正式分类节点或分类版本。
- 不会将候选状态写成 `approved`。
- 不会自动覆盖 `data/proposals/index.json`；调用者必须明确指定输出文件。
- 候选只是元数据规则匹配结果，审核者仍需阅读对应 Skill 原文，判断语义是否成立。
- 规则未覆盖或证据不足的 Skill 不会被强行分类。

该实现是确定性的基线，不宣称具备 LLM 语义理解能力。后续可在相同提案契约上增加 AI 提案来源，但必须保留证据、来源 revision 和人工审核流程。
