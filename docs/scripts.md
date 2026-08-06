# JS 脚本本地化管理

`fix.sgmodule` 中所有 `script-path=` 引用的 JS 脚本都托管在本仓库的 `scripts/` 目录下，通过 `raw.githubusercontent.com/kun12356/ippure` 提供访问，不依赖外部作者的 repo。防止上游删库或设为私有时模块静默失效。

## 目录结构

```
scripts/
  模块名/
    xxx.js
    yyy.js
scripts/mapping.json    # 记录每个本地脚本对应的上游来源 URL
scripts/sync_upstream.py  # GitHub Actions 自动同步脚本
```

子目录名与模块名对应，由 fix.sgmodule 区块中的 `# scripts-dir:` 元数据指定。

## mapping.json 格式

```json
{
  "scripts/<模块>/<文件名>.js": {
    "upstream_url": "<原始远程URL>",
    "module": "<模块子目录名>"
  }
}
```

## 场景一（新增模块）中的脚本处理

在步骤3（插入 fix.sgmodule）之后：
1. 提取模块中所有 `script-path=` 外部 JS URL
2. 在 `scripts/` 下创建子目录，下载每个 JS
3. 将 fix.sgmodule 中的 `script-path=` 替换为本地 raw URL
4. 更新 `mapping.json`

## 场景二（更新模块）中的脚本处理

1. 对比新旧版本 `script-path=` 引用变化
2. 新增的 → 下载保存，更新 mapping
3. 移除的 → 删除本地文件和 mapping 条目
4. 保留的 → 哈希检查上游是否更新，有变化则覆盖

## 场景四（移除模块）中的脚本处理

1. 删除 `scripts/<模块>/` 整个子目录
2. 从 `mapping.json` 移除该模块所有条目

## 手动批量更新脚本

> 检查 scripts 目录下所有脚本的上游是否有更新，先汇报，不写入。

遍历 mapping.json，哈希对比，汇总后确认再写入。

Commit: `更新托管脚本: <脚本1>, <脚本2>（共N个）`
