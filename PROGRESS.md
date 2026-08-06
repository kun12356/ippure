# 自托管 JS 脚本 — 进度记录

## 1. 已完成

- [x] 创建 `scripts/` 目录及子目录：`scripts/kuan/`, `scripts/youtube/`, `scripts/wloc/`
- [x] 下载 `scripts/kuan/coolapk.js`（10789 bytes）— 来源 ddgksf2013/Scripts
- [x] 下载 `scripts/youtube/youtube.response.js`（132973 bytes）— 来源 Maasea/sgmodule

## 2. 正在做（当前卡点）

下载剩余 3 个脚本时遇到 curl exit code 56（网络接收失败），可能是 raw.githubusercontent.com 被墙/代理问题。
- `scripts/youtube/youtube.request.js` — Maasea/sgmodule，下载失败
- `scripts/wloc/wloc.js` — Yu9191/wloc，下载失败
- `scripts/wloc/wloc-settings.js` — Yu9191/wloc，下载失败

上述失败时伴随 deepseek-v4-pro 分类器不可用，可能是临时网络抖动。已成功重试下载前 2 个（coolapk.js 和 youtube.response.js），后续 3 个待重试。

## 3. 接下来的计划

1. 重试下载剩余 3 个脚本
2. 替换 `fix.sgmodule` 中所有 `script-path=` 外部 URL → 本地 raw URL（共 5 个唯一 URL，11 处引用）
3. 创建 `scripts/mapping.json`
4. 更新 `CLAUDE.md`，新增「JS 脚本本地化管理」章节
5. 验证 & commit

## 4. 关键文件路径

| 文件 | 状态 |
|------|------|
| `scripts/kuan/coolapk.js` | ✅ 已下载 |
| `scripts/youtube/youtube.response.js` | ✅ 已下载 |
| `scripts/youtube/youtube.request.js` | ❌ 待重试 |
| `scripts/wloc/wloc.js` | ❌ 待重试 |
| `scripts/wloc/wloc-settings.js` | ❌ 待重试 |
| `scripts/mapping.json` | ⬜ 待创建 |
| `fix.sgmodule` | ⬜ 待修改（script-path 替换） |
| `CLAUDE.md` | ⬜ 待更新 |
