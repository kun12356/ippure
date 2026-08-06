# 项目说明

维护一个小火箭(Shadowrocket)增量模块 `fix.sgmodule`，用于收纳陆续添加的其他作者模块。

## 目录结构

```
sources/         每个新增模块的原样存档
scripts/         所有模块引用的 JS 脚本本地副本（自托管，不依赖外部仓库）
fix.sgmodule     所有新增模块的合并产物，即最终被小火箭订阅的文件
```

不再单独维护 manifest 清单表，每个模块的来源地址直接以注释形式记录在 `fix.sgmodule` 对应区块内，信息不分散。

## 详细文档

- [fix.sgmodule 内部格式约定](docs/sgmodule-format.md)
- [五种操作场景](docs/scenarios.md)
- [JS 脚本本地化管理](docs/scripts.md)
- [GitHub Actions 自动同步](docs/automation.md)

## 禁止事项

- `sources/` 下 **raw 类型**文件只能被同步流程整体覆盖，禁止手动编辑；**manual 类型**靠用户手动覆盖
- 禁止对 `fix.sgmodule` 做整体重写，任何改动必须定位到具体模块的 BEGIN/END 区块
- 禁止在合并/更新时做规则去重或冲突检测，新内容直接追加
- 批量检查更新仅针对 raw 类型，只用哈希值判断
