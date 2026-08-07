# 进度记录

## shad 基础模块

来源：本仓库自托管，订阅 URL `https://github.com/kun12356/ippure/blob/main/shad.sgmodule`

```
总行数: 2770

[General]          1条  force-http-engine-hosts
[Rule]           430条  DOMAIN/URL-REGEX 代理和拒绝规则
[URL Rewrite]   1762条  REJECT / http-response-jq 去广告重写
[Header Rewrite]   3条
[Body Rewrite]   482条  http-response-jq 体修改
[Map Local]       12条
[Script]          26条  脚本注入
[MITM]             1条  hostname = %APPEND% (解密域名列表)
```

无模块化注释，整体模块。
