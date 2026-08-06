- - - # 项目说明

      维护一个小火箭(Shadowrocket)增量模块 `fix.sgmodule`，用于收纳陆续添加的其他作者模块。

      ## 目录结构

      ```
      sources/         每个新增模块的原样存档
      scripts/         所有模块引用的 JS 脚本本地副本（自托管，不依赖外部仓库）
      fix.sgmodule     所有新增模块的合并产物，即最终被小火箭订阅的文件
      ```

      不再单独维护 manifest 清单表，每个模块的来源地址直接以注释形式记录在 `fix.sgmodule` 对应区块内，信息不分散。

      ------

      # fix.sgmodule 内部结构约定

      **重要约束**：`[Rule]`、`[URL Rewrite]`、`[Script]` 等每种标签在整个文件里只允许出现一次（未确认小火箭解析器是否支持同一标签重复出现，为避免兼容性风险，一律不重复）。

      每个来源模块的内容按类型拆分后，插入到对应标签段落内部，用注释包裹标出模块边界：

      ```
      [Rule]
      # ===== BEGIN: <模块名> =====
      # source: <raw地址>
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

      **`[MITM]` 不能省略，不能假设基础模块已经覆盖。** 新增模块的 `[URL Rewrite]`/`[Script]` 规则要生效，前提是对应域名必须出现在某个 MITM 解密名单里，否则流量不会被解密，规则不会触发，且不会有任何报错提示。基础模块的 MITM 列表通常只覆盖它自己规则涉及的域名，不会包含后续新增模块（新的 App）需要的域名。

      因此 `fix.sgmodule` 必须维护自己的 `[MITM]` 段落，汇总所有已收录模块各自需要解密的域名，去重后统一声明，**必须使用 `%APPEND%` 语法**：

      ```
      [MITM]
      hostname = %APPEND% ad.douyin.com, track.douyin.com, ad.coolapk.com
      ```
  
      不加 `%APPEND%` 会直接覆盖基础模块的 MITM 列表，破坏其原有功能，这是严重错误，务必检查。

      **`hostname` 属性全程只能有一行，禁止出现多行 `hostname = %APPEND% ...` 堆叠。** 新增模块时，来源模块自己原本可能也带了一整行 `hostname = %APPEND% xxx.com`，此时**不能把这行原样复制粘贴进 fix.sgmodule**，而是要从中提取出域名列表，与 fix.sgmodule 现有 `hostname` 行里的域名合并、去重，仍然只保留一行。移除模块时同理，从这唯一一行里摘除对应域名，而不是删除某一整行。

      新增/更新模块时，如果该模块涉及 HTTPS 解密（大部分去广告/重写类模块都需要），必须同步检查并更新这一行的域名列表；移除模块时同理，需要把该模块专属、其他模块不需要的域名从列表中摘除。

      ------

# JS 脚本本地化管理

`fix.sgmodule` 中所有 `script-path=` 引用的 JS 脚本都托管在本仓库的 `scripts/` 目录下，通过 `raw.githubusercontent.com/kun12356/ippure` 提供访问，不依赖外部作者的 repo。防止上游删库或设为私有时模块静默失效。

## 目录结构

```
scripts/
  模块名/
    xxx.js
    yyy.js
scripts/mapping.json    # 记录每个本地脚本对应的上游来源 URL
```

子目录名与 `sources/` 中的模块存档 basename 对应（使用简短易读的名称，不强制同名）。

## mapping.json 格式

每条记录以本地相对路径为 key：
```json
{
  "scripts/<模块>/<文件名>.js": {
    "upstream_url": "<原始远程URL>",
    "module": "<模块子目录名>"
  }
}
```

## 各场景中的脚本处理规则

### 场景一（新增模块）

在步骤3（拆分内容插入 fix.sgmodule）之后增加：

4. 从该模块内容中提取所有 `script-path=` 引用的外部 JS URL
5. 在 `scripts/` 下创建以模块名命名的子目录
6. 下载每个 JS 文件，保存到该子目录
7. 在插入 fix.sgmodule 的内容中，将所有 `script-path=` URL 替换为本地 raw URL：
   `https://raw.githubusercontent.com/kun12356/ippure/refs/heads/main/scripts/<模块>/<文件名>.js`
8. 更新 `scripts/mapping.json`，登记每个脚本的映射关系

### 场景二（已有模块更新，raw 类型）

在步骤3（有差异，替换变化部分）处理完 sgmodule 规则内容后：

4. 对比模块新旧版本中的 `script-path=` 引用：
   - **旧版有、新版无**：从 `scripts/<模块>/` 和 `mapping.json` 中移除
   - **旧版无、新版有**：下载保存，更新 `mapping.json`
   - **URL 变化但实际是同一脚本**：更新 mapping.json 中的 `upstream_url`，不重新下载
5. 对于所有保留的脚本 URL，用哈希对比检查上游脚本内容是否已更新：
   ```bash
   curl -sL <上游URL> | md5sum
   md5sum scripts/<模块>/<文件名>.js
   ```
   如有差异，下载最新内容覆盖本地
6. 确保 fix.sgmodule 中该模块的所有 script-path 引用使用的是本地 URL

### 场景四（移除模块）

在步骤1（删除 BEGIN/END 区块）之后增加：

1.5. 删除 `scripts/<模块>/` 整个子目录
1.6. 从 `scripts/mapping.json` 中移除该模块的所有条目

### 手动批量更新脚本

用户可通过指令单独更新所有已托管脚本（不涉及 sgmodule 规则）：

> 检查 scripts 目录下所有脚本的上游是否有更新，先汇报，不写入。

流程：
1. 遍历 `scripts/mapping.json` 中的所有条目
2. 对每条记录，curl 下载上游 URL 内容，与本地文件做哈希对比
3. 汇总列出有变化的脚本列表
4. 确认后逐个下载覆盖，commit message：
   ```
   更新托管脚本: <脚本1>, <脚本2>（共N个）
   ```

------

      # 两种来源类型

      模块按能否被自动抓取，分成两种类型，`fix.sgmodule` 每个区块的注释头需要标明 `type` 字段：

      ```
      # ===== BEGIN: <模块名> =====
      # source: <地址>
      # type: raw 或 manual
      # last-sync: <YYYY-MM-DD>
      ```

      ## 类型一：raw（静态链接，默认类型）
  
      来源是普通的 raw 文件链接（如 `raw.githubusercontent.com`），CC 可以自主抓取。处理方式与「场景一～四」完全一致：CC 自己下载、diff、同步，不需要用户介入内容获取环节。
  
      ## 类型二：manual（无法自动抓取的模块）
  
      适用场景：来源依赖实时转换服务（比如 Script Hub 类的链接）、或其他 CC 网络访问不到的地址，CC 无法直接下载到内容。
  
      **新增流程：**

      1. 用户自行获取到实际可用的内容（比如打开转换链接、手动导出等），直接复制粘贴保存为 `sources/模块名.sgmodule`
      2. 用户告知 CC 这是一个 manual 类型模块，并提供原始信息来源（比如原始 script.hub 链接、或内部真正的 raw 地址）用于注释记录
      3. CC 读取这份本地文件，按标签拆分内容，合并进 `fix.sgmodule`，操作方式与「场景一」步骤3-5相同，区别只是内容来源是用户提供的本地文件，而不是 CC 自己下载的
      4. 区块注释头写 `# type: manual`，`source` 字段记录用户提供的原始地址（仅作参考，不代表可自动抓取）
  
      **更新流程：**
  
      - manual 类型无法走"CC 自动拉取远程 diff"这条路，只能由用户重新获取最新内容后手动覆盖 `sources/模块名.sgmodule`
      - 用户覆盖完文件后告诉 CC："这个模块我更新了内容，帮我同步"
      - 因为 `sources/` 目录本身在 git 版本控制下，CC 通过 `git diff sources/模块名.sgmodule` 直接对比出用户这次改动了什么，不需要额外维护旧版本备份
      - 根据 diff 结果，定位到 `fix.sgmodule` 中该模块对应标签段落的 BEGIN/END 区块，仅替换发生变化的部分，更新 `last-sync` 日期

      **批量检查更新时的处理：**

      - 「场景三」批量检查只对 `type: raw` 的模块做哈希对比
      - manual 类型模块无法程序化检测更新，直接跳过，不计入检查范围（作者更新与否需要用户自己留意原始来源）
  
      ------
  
      # 场景一：新增一个模块（raw 类型）
  
      1. 把模块原始内容保存到 `sources/模块名.sgmodule`，原样不改
  
      2. 读取内容，简要汇报：模块名、包含哪些 `[]` 段落、大致规则条数
  
      3. 确认后，按标签拆分该模块内容，分别插入到 `fix.sgmodule` 对应标签段落末尾，用 BEGIN/END 包裹并写入来源地址和同步日期。**如该模块涉及 HTTPS 解密，把它需要的域名提取出来，合并进 `[MITM]` 那唯一一行 `hostname = %APPEND%` 列表里，不要新增一行**
  
      4. 无需与其他已收录模块做重复检测，新内容直接追加即可（如确实发现明显重复，按场景五做区块顺序处理即可）
  
      5. Commit message：
  
         ```
         新增模块: <模块名>, 来源: <地址>
         ```
  
      6.模块包含的#!arguments内容是编辑参数需要的默认值,需要添加到fix.sgmodule中,在已有的#!arguments下换行复制即可
  
      # 场景二：已有模块的上游更新（raw 类型，日常最常用，重点省 token）
  
      1. 拉取该模块最新内容，与 
  
         ```
         sources/模块名.sgmodule
         ```
  
         （上次存档）直接 diff：
  
         ```bash
         curl -s <raw地址> -o /tmp/latest.sgmodulediff sources/模块名.sgmodule /tmp/latest.sgmodule
         ```
  
      2. 无差异 → 结束，不碰 `fix.sgmodule`，也不需要读取任何文件内容
  
      3. 有差异 → 只处理 diff 出来的变化行：
  
         - 用最新内容覆盖 `sources/模块名.sgmodule`
         - 定位到 `fix.sgmodule` 中该模块在**各个相关标签段落**内的 BEGIN/END 区块（可能分布在 `[Rule]`、`[URL Rewrite]` 等多处），仅替换发生变化的部分，更新区块内的 `last-sync` 日期
         - 其余模块的区块一律不动
  
      4. Commit message：
  
         ```
         同步更新: <模块名>, 变化N行
         ```
  
      ------
  
      5,模块包含的#!arguments内容是编辑参数需要的默认值,需要添加到fix.sgmodule中,在已有的#!arguments下换行复制即可
  
      # 场景三：批量检查所有已收录模块是否有更新（仅 raw 类型）
  
      1. 遍历 `sources/` 目录下**标记为 raw 类型**的文件（跳过 manual 类型）
  
      2. 对每个文件，只拉取远程内容做
  
         哈希对比
  
         ，不做内容级diff：
      
         ```bash
         curl -s <raw地址> | md5summd5sum sources/模块名.sgmodule
         ```
  
      3. 汇总汇报哪些模块有变化，等待确认后再按场景二逐个处理，不主动写入
  
      4. manual 类型模块不在此列，如需检查更新需用户自行前往原始来源确认
  
      ------
  
      # 场景四：移除某个模块
  
      1. 定位 `fix.sgmodule` 中该模块在各个标签段落内的 BEGIN/END 区块，逐一整块删除
  
      2. 检查 `[MITM]` 列表中是否有仅该模块使用、其他模块不需要的域名，一并移除
  
      3. 删除 `sources/` 下对应存档文件
  
      4. 删除前先汇报模块名和影响，确认后再执行
  
      5. Commit message：
      
         ```
         移除模块: <模块名>, 原因: <说明>
         ```
  
      ------
  
      # 场景五：fix.sgmodule 内部，新增模块之间的顺序调整
  
      如果两个新增模块本身也存在规则冲突，在**同一个标签段落内**（比如都在`[Rule]`里），谁的区块排在靠前位置，谁的规则优先生效。如需调整优先级，在该标签段内对调对应 BEGIN/END 区块的先后位置即可，不涉及内容改动，也不能跨标签段调整（不同标签段之间没有先后优先级关系，各自独立生效）。
  
      ------
  
      # 常用指令示例
  
      新增模块（raw类型）：
  
      > 新增模块 https://raw.githubusercontent.com/xxx/xxx.sgmodule，模块名叫"抖音去广告"，按场景一处理。
  
      新增模块（manual类型）：
  
      > 我把内容存到 sources/酷安去广告.sgmodule 了，这是个manual类型模块，原始来源是 http://script.hub/xxx，帮我合并进fix.sgmodule。
  
      检查所有更新（raw类型）：
  
      > 检查一下 sources 里所有raw类型模块有没有更新，先汇报，不用同步。
  
      同步指定模块（raw类型）：
  
      > "抖音去广告"这个模块有更新了，帮我同步，按场景二处理，只动它自己的区块。
  
      同步指定模块（manual类型）：
  
      > 我把 sources/酷安去广告.sgmodule 内容更新了，帮我对比一下改了什么，同步进fix.sgmodule。
  
      ------
  
      # 禁止事项
      
      - `sources/` 目录下 **raw 类型**的文件只能被「场景二」的同步流程整体覆盖（用最新上游内容替换），禁止人为手动编辑其中的具体规则内容；**manual 类型**文件本身就是靠用户手动覆盖更新的，不受此限制
      - 禁止对 `fix.sgmodule` 做整体重写，任何改动必须定位到具体模块的 BEGIN/END 区块
      - 禁止在合并/更新时做规则去重或冲突检测，新内容直接追加即可
      - 批量检查更新（场景三）仅针对 raw 类型，禁止读取模块内容做对比，只用哈希值判断
