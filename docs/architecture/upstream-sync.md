# Cursor Plugins 上游同步

## 当前实现范围

同步程序从已经 checkout 的 Cursor Plugins Git 仓库读取固定 HEAD。它会：

1. 读取 Git commit SHA 和 commit 时间。
2. 发现 Cursor Plugin、Agent Plugin 和 Claude Plugin 三种 manifest。
3. 按最长目录前缀将 Skill 归属到正确 Plugin，支持 third_party 和嵌套目录。
4. 提取 manifest 名称、显示名称、描述、版本和格式。
5. 从 Skill Markdown frontmatter 提取 name 与 description。
6. 计算 Git Blob SHA 和文件内容 SHA-256。
7. 更新当前 Plugin / Skill 索引。
8. 将已从上游消失的资源保留为 removed tombstone，避免历史分类关联变成悬空引用。
9. 按上游 commit SHA 保存历史快照，并报告新增、修改和移除的资源。

程序只保存元数据和原始文件固定链接，不复制 Skill 正文，不翻译、不分类，也不批准分类关联。

## 目录约定

- 当前资源索引：data/plugins/index.json、data/skills/index.json
- 来源索引：data/sources/index.json
- 历史快照：data/sources/snapshots/cursor.plugins/<commit-sha>.json

快照按 commit SHA 命名，不覆盖旧快照。资源记录中的 source_revision 表示该资源文件内容最后一次发生变化时所在的上游 commit；顶层快照 revision 表示本次扫描的完整仓库 commit。

## 本地运行

要求 Python 3.12+ 和 Git。先将 Cursor Plugins 仓库 checkout 到本地，然后执行：

    python scripts/sync/sync_cursor_plugins.py --source-dir path/to/plugins --data-dir data

只扫描并显示变更、不写文件：

    python scripts/sync/sync_cursor_plugins.py --source-dir path/to/plugins --data-dir data --dry-run

## GitHub 运行

项目提供手动触发的 GitHub Actions 工作流。运行后会 checkout Cursor Plugins 的 main 分支，执行同步，并创建或更新一个同步 PR。正式数据只有在 PR 审核合并后才进入 main。

当前没有设置定时运行。是否每天、每周或按其他频率检查上游，应在确认维护节奏后再配置。

## 变更语义

- added：本次快照首次发现的资源。
- modified：Skill 文件 SHA-256 或 Plugin manifest Blob SHA 发生变化。
- removed：上游当前快照中不再存在的资源。
- removed 资源保留在当前索引中并标记 status=removed；它们不会被误认为仍存在于上游，但历史关联与审计记录不会丢失。

Plugin ID 由 manifest 所在目录路径生成；Skill ID 由 Plugin ID 和 skills 目录下的相对路径生成。上游资源移动目录会形成旧 ID removed、新 ID added，后续需要人工决定是否建立迁移关系。
