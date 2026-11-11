# 分类聚合规则

本模块生成只读聚合视图，不修改正式分类、Skill 索引或分类关联源文件。

## 纳入范围

- 只纳入 `status=active` 的 Skill。
- 只纳入 `status=approved` 的分类关联。
- `proposed` 和 `rejected` 关联不参与正式聚合。
- 上游已移除的 Skill 不参与当前聚合。

## 分类树聚合

关联只记录在直接分类节点。每个节点的聚合结果包含：

- `direct_skill_ids`：直接关联到当前节点的 Skill。
- `descendant_skill_ids`：通过后代节点聚合而来、且未直接关联当前节点的 Skill。
- `skill_ids`：上述两者的去重并集。

因此浏览父分类时可以包含全部后代 Skill，同时区分直接匹配和后代聚合。一个 Skill 即使通过多个后代节点到达同一父节点，也只出现一次。

## Plugin 聚合

Plugin 按其所属 Skill 聚合分类。每个 Plugin 的分类项保留 `source_skill_ids`，明确指出哪些 Skill 贡献了该分类。分类祖先也会接收相同来源 Skill，以支持从 Plugin 维度浏览分类树。

Plugin 聚合只用于发现导航，不意味着 Plugin 内所有 Skill 都具备该 Plugin 聚合出的全部能力。

## 运行

输出到标准输出：

    python -m scripts.build.aggregate_taxonomy --data-dir data

写入构建产物：

    python -m scripts.build.aggregate_taxonomy --data-dir data --output build/taxonomy-aggregation.json

输出是可再生成的派生数据，不应手工编辑或提交为分类事实来源。
