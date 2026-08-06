# fix.sgmodule 内部格式约定

**重要约束**：`[Rule]`、`[URL Rewrite]`、`[Script]` 等每种标签在整个文件里只允许出现一次（未确认小火箭解析器是否支持同一标签重复出现，为避免兼容性风险，一律不重复）。

每个来源模块的内容按类型拆分后，插入到对应标签段落内部，用注释包裹标出模块边界：

```
[Rule]
# ===== BEGIN: <模块名> =====
# source: <raw地址>
# type: raw 或 manual
# scripts-dir: <scripts子目录名>  (raw类型需要)
# last-sync: <YYYY-MM-DD>
...该模块属于 [Rule] 的部分...
# ===== END: <模块名> =====

# ===== BEGIN: <另一个模块名> =====
...
# ===== END: <另一个模块名> =====

[URL Rewrite]
# ===== BEGIN: <模块名> =====
...该模块属于 [URL Rewrite] 的部分...
# ===== END: <模块名> =====
```

如果某个模块只涉及部分标签（比如只有`[Rule]`没有`[Script]`），对应标签下就不需要为它建区块。

## MITM 段落的特殊处理（不可省略）

**`[MITM]` 不能省略，不能假设基础模块已经覆盖。** 新增模块的 `[URL Rewrite]`/`[Script]` 规则要生效，前提是对应域名必须出现在某个 MITM 解密名单里。基础模块的 MITM 列表通常只覆盖它自己规则涉及的域名，不会包含后续新增模块需要的域名。

因此 `fix.sgmodule` 必须维护自己的 `[MITM]` 段落，**必须使用 `%APPEND%` 语法**：

```
[MITM]
hostname = %APPEND% ad.douyin.com, track.douyin.com, ad.coolapk.com
```

不加 `%APPEND%` 会直接覆盖基础模块的 MITM 列表，破坏其原有功能，这是严重错误。

**`hostname` 属性全程只能有一行，禁止出现多行 `hostname = %APPEND% ...` 堆叠。** 新增模块时，从来源模块中提取域名与现有列表合并去重，仍只保留一行。移除模块时同理，从中摘除对应域名。

## 两种来源类型

### raw（静态链接，默认类型）

来源是普通 raw 文件链接（如 `raw.githubusercontent.com`），CC 可以自主抓取、diff、同步。

### manual（无法自动抓取的模块）

来源依赖实时转换服务（如 Script Hub），CC 无法直接下载。

**新增**：用户自行保存到 `sources/模块名.sgmodule`，告知 CC 合并。区块标注 `# type: manual`。

**更新**：用户覆盖 `sources/` 文件后告知 CC，CC 通过 `git diff` 对比改动并同步到 fix.sgmodule。

**批量检查**：manual 类型跳过，不计入自动检查范围。
