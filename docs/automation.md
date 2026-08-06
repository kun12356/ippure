# GitHub Actions 自动同步

项目配置了 `.github/workflows/sync-upstream.yml`，每天北京时间 00:37 自动运行 `scripts/sync_upstream.py`。

## 功能

- 解析 `fix.sgmodule` 中所有 `type: raw` 的模块
- 哈希对比各模块上游内容与 `sources/` 存档
- 有变化则自动下载、更新 fix.sgmodule 对应区块
- 同步关联 JS 脚本（以 fix.sgmodule 实际引用为准，不会误删）
- 合并 MITM 域名列表
- 自动 commit + push

## 手动触发

GitHub Actions UI → Sync Upstream Modules → Run workflow

## scripts-dir 元数据

每个 raw 模块的 BEGIN 区块需标注 `# scripts-dir:`：

```
# ===== BEGIN: YouTubeNoAd =====
# source: https://raw.githubusercontent.com/.../YouTubeNoAd.sgmodule
# type: raw
# scripts-dir: youtube
# last-sync: 2026-07-12
```

若未标注，默认取模块名小写。
