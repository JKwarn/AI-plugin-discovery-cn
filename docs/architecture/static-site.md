# 静态网站构建与部署

## 架构

网站是无构建时前端依赖的静态站点，部署目标为 GitHub Pages。

- `index.html`：站点入口。
- `assets/css/site.css`：响应式界面样式。
- `assets/js/app.js`：资源浏览、搜索、分类筛选和 Skill 阅读交互。
- `scripts/build/build_site.py`：从规范化数据生成发布目录。
- `dist/data/catalog.json`：站点消费的聚合数据。
- `dist/content/skills/`：仅复制注册表中状态为 `reviewed` 的中文译文。

## 本地构建

```bash
python scripts/build/build_site.py --output-dir dist
python -m http.server 8000 --directory dist
```

浏览器打开 `http://localhost:8000`。

## 页面能力

- 首页展示 Plugin、Skill 和已审核中文译文数量。
- 可按 Plugin / Skill 类型浏览，并按名称、描述和 ID 搜索。
- 四个分类维度显示正式分类节点及已审核 Skill 数量；待审核关联不会进入网站分类结果。
- Plugin 详情列出其包含的 Skill。
- Skill 详情提供中文译文和英文上游链接；中文译文只用于阅读，不是可执行安装包。
- 中英文界面切换；站点路径采用相对路径，以兼容 GitHub Pages 项目站点。

## 部署

`.github/workflows/pages.yml` 在 main 更新时执行测试、数据校验、静态构建和 Pages 部署。Pull Request 只构建和验证，不部署预览版本。

首次启用时，仓库 Settings → Pages → Build and deployment → Source 应选择 **GitHub Actions**。部署成功后，以 Actions 的 Pages deployment URL 为准。
