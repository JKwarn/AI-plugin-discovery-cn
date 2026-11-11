# How：理解代码库与系统工作原理

探索代码库，以回答“X 是如何工作的？”这类问题。应从资深工程师接手某个子系统时所需的视角，给出架构层面的解释，使读者能够建立可用的心智模型；但不要写成逐行注释式的源代码导读。

每次派生任务（spawn）都必须是一个 Task 子代理，设置 subagent_type: generalPurpose 和 readonly: true。探索者使用 pstack-models.mdc 规则中的 how explorer 配置行（默认模型为 grok-4.7-xhigh-fast）；每个讲解者使用其中的 how explainer 配置行（默认模型为 claude-opus-5-5-xhigh）。将该配置行的值设置为 model；如果规则或对应配置行不存在，则使用默认值。如果值为 auto 或 inherit-parent，则不设置 model。如果 Task 工具拒绝某个模型标识符（slug），则使用默认值并说明这一点。如果默认值也被拒绝，则根据错误信息使用同一模型系列中最接近的有效标识符。根据 poteto-mode Skill 的 Subagents 章节，为任务选择推理级别以及 fast 或 standard 速度。

## 1. 评估复杂度

如果问题范围不明确，先说明你的理解，然后进行探索。用户可以纠正或调整方向。

- **简单问题**（单个模块、小型工具，或“函数 X 如何工作”这类范围狭窄的问题）：不启动探索者。启动一个讲解者，让其在一次任务中完成探索和解释。其提示词基于 references/explainer-prompt.md 构建，但省略 explorer-findings 部分。然后进入第 4 步。
- **复杂问题**（跨多个文件或服务的子系统、横切功能、完整架构概览）：进入第 2 步。

拿不准时，选择简单路径。

## 2. 探索（仅复杂问题）

将问题拆分为 2 到 4 个角度，每个角度对应子系统中一个彼此独立的部分。使用一条消息同时启动所有探索者；每个探索者都使用填入相应角度的 references/explorer-prompt.md 作为提示词。

## 3. 综合（仅复杂问题）

所有探索者返回结果后，启动一个讲解者，将每位探索者的发现填入 references/explainer-prompt.md。

## 4. 呈现

呈现讲解者的输出。可以为了清晰度或结合对话上下文进行轻微编辑，但不要大幅改写。

## 输出格式

解释应使用 references/explainer-prompt.md 中定义的章节；不适用的章节可以省略。章节包括：Overview（概览）、Key Concepts（关键概念）、How It Works（工作原理）、Where Things Live（代码位置）和 Gotchas（注意事项）。
