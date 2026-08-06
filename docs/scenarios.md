# 五种操作场景

## 场景一：新增模块（raw 类型）

1. 把模块原始内容保存到 `sources/模块名.sgmodule`
2. 读取内容，汇报：模块名、包含哪些 `[]` 段落、大致规则条数
3. 确认后，按标签拆分内容，分别插入到 `fix.sgmodule` 对应标签段落末尾，用 BEGIN/END 包裹。涉及 HTTPS 解密的，提取域名合并进 `[MITM]` 那唯一一行
4. 按 [JS 脚本本地化管理](scripts.md) 处理该模块引用的脚本
5. 模块包含的 `#!arguments` 需添加到 fix.sgmodule 已有 `#!arguments` 下换行复制

Commit: `新增模块: <模块名>, 来源: <地址>`

## 场景二：已有模块的上游更新（raw 类型）

1. 拉取最新内容，与 `sources/模块名.sgmodule` 做 diff
2. 无差异 → 结束
3. 有差异 → 用最新覆盖 sources/，仅替换 fix.sgmodule 中该模块各段落内发生变化的部分，更新 `last-sync`
4. 按 [JS 脚本本地化管理](scripts.md) 同步该模块引用的脚本变更
5. 模块包含的 `#!arguments` 添加到 fix.sgmodule

Commit: `同步更新: <模块名>, 变化N行`

## 场景三：批量检查更新（仅 raw 类型）

1. 遍历 `sources/` 下 raw 类型文件
2. 只做哈希对比（curl + md5sum），不做内容 diff
3. 汇总汇报，确认后再逐个按场景二处理
4. manual 类型跳过

## 场景四：移除模块

1. 定位 fix.sgmodule 中各标签段落内的 BEGIN/END 区块，逐一整块删除
2. 清理 `scripts/<模块>/` 子目录和 `mapping.json` 条目
3. 检查 `[MITM]` 列表，摘除仅该模块使用的域名
4. 删除 `sources/` 下对应存档
5. 删除前先汇报确认

Commit: `移除模块: <模块名>, 原因: <说明>`

## 场景五：模块优先级调整

在同一标签段落内对调 BEGIN/END 区块的先后位置。不能跨标签段调整。

## 常用指令

新增 raw 模块：
> 新增模块 https://raw.githubusercontent.com/xxx/xxx.sgmodule，模块名叫"抖音去广告"，按场景一处理。

新增 manual 模块：
> 我把内容存到 sources/酷安去广告.sgmodule 了，这是个manual类型模块，原始来源是 http://script.hub/xxx，帮我合并进fix.sgmodule。

检查更新：
> 检查一下 sources 里所有raw类型模块有没有更新，先汇报，不用同步。

同步指定模块：
> "抖音去广告"这个模块有更新了，帮我同步，按场景二处理。

同步 manual 模块：
> 我把 sources/酷安去广告.sgmodule 内容更新了，帮我对比一下改了什么，同步进fix.sgmodule。
