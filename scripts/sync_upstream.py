#!/usr/bin/env python3
"""
自动同步上游 raw 类型模块。

遍历 fix.sgmodule 中所有 type: raw 的模块，拉取上游最新内容，
与 sources/ 存档做哈希对比。有变化则更新 fix.sgmodule 中对应区块、
同步关联的 JS 脚本、合并 MITM 域名列表。

纯 Python stdlib，零第三方依赖，适配 GitHub Actions 环境。
"""

import hashlib
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import date
from typing import Optional

# ─── 路径常量 ───────────────────────────────────────────────

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_DIR = os.path.join(REPO_ROOT, "sources")
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
MAPPING_FILE = os.path.join(SCRIPTS_DIR, "mapping.json")
FIX_MODULE = os.path.join(REPO_ROOT, "fix.sgmodule")

GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "kun12356/ippure")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/refs/heads/{GITHUB_BRANCH}"

# ─── 正则 ────────────────────────────────────────────────────

SECTION_RE = re.compile(r"^\[(.+?)\]")
BLOCK_BEGIN_RE = re.compile(r"^# ===== BEGIN: (.+?) =====$")
BLOCK_END_RE = re.compile(r"^# ===== END: (.+?) =====$")
META_SOURCE_RE = re.compile(r"^# source:\s*(.*)$")
META_TYPE_RE = re.compile(r"^# type:\s*(.*)$")
META_LAST_SYNC_RE = re.compile(r"^# last-sync:\s*(.*)$")
META_SCRIPTS_DIR_RE = re.compile(r"^# scripts-dir:\s*(.*)$")
SCRIPT_PATH_RE = re.compile(r"script-path=(https?://[^\s,]+)")
MITM_HOST_RE = re.compile(r"hostname\s*=\s*%APPEND%\s*(.+)", re.IGNORECASE)

# ─── 工具函数 ────────────────────────────────────────────────

def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_url(url: str, timeout: int = 30, retries: int = 2) -> Optional[str]:
    """
    拉取远程 URL 内容，支持重试。
    返回文本内容，失败返回 None。
    """
    req = urllib.request.Request(url, headers={"User-Agent": "ippure-sync-bot/1.0"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if attempt == retries:
                print(f"  !! HTTP {e.code} fetching: {url}")
                return None
        except (urllib.error.URLError, OSError) as e:
            if attempt == retries:
                print(f"  !! Network error fetching: {url} ({e})")
                return None
        if attempt < retries:
            print(f"  Retry {attempt + 1}/{retries} for: {url}")
    return None


def set_output(name: str, value: str) -> None:
    """写入 GitHub Actions step output（支持多行值）。"""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"{name}<<EOF\n{value}\nEOF\n")


def is_dry_run() -> bool:
    return "--dry-run" in sys.argv


# ─── fix.sgmodule 解析 ────────────────────────────────────────

def parse_fix_module(path: str) -> tuple[list[str], dict[str, list[dict]], set[str], set[str]]:
    """
    解析 fix.sgmodule，返回:
      all_lines:        原始行列表（含换行符）
      blocks_by_section: {section_name: [block_dict, ...]}
      current_mitm_hosts: 当前 MITM hostname 集合
      raw_module_names:   所有 type: raw 的模块名集合

    block_dict:
      {
        "name": str,         # 模块名
        "source": str,       # 上游 URL
        "mod_type": str,     # "raw" / "manual"
        "last_sync": str,    # "2026-07-12"
        "scripts_dir": str,  # scripts/ 子目录名
        "section": str,      # 所属段落名
        "content_lines": [str],      # 规则内容行
        "header_lines": [str],       # 注释头行（source/type/last-sync 等）
        "start_idx": int,    # # ===== BEGIN 行索引
        "end_idx": int,      # # ===== END 行索引
      }
    """
    with open(path, "r", encoding="utf-8") as f:
        all_lines = f.readlines()

    blocks_by_section: dict[str, list[dict]] = {}
    current_section = ""
    current_mitm_hosts: set[str] = set()
    raw_module_names: set[str] = set()

    i = 0
    while i < len(all_lines):
        line = all_lines[i].rstrip("\n").rstrip("\r")

        # 段落头
        sec_match = SECTION_RE.match(line)
        if sec_match:
            current_section = sec_match.group(1).strip()

            # 解析现有 MITM hostnames
            if current_section == "MITM":
                for j in range(i + 1, min(i + 20, len(all_lines))):
                    m = MITM_HOST_RE.match(all_lines[j].strip())
                    if m:
                        hosts = [h.strip() for h in m.group(1).split(",") if h.strip()]
                        current_mitm_hosts.update(hosts)
                        break
            i += 1
            continue

        # BEGIN 标记
        begin_match = BLOCK_BEGIN_RE.match(line)
        if begin_match:
            name = begin_match.group(1).strip()
            start_idx = i
            header_lines = []
            content_lines = []
            mod_source = ""
            mod_type = ""
            last_sync = ""
            scripts_dir = ""

            i += 1
            # 读元数据行和内容行
            while i < len(all_lines):
                inner = all_lines[i].rstrip("\n").rstrip("\r")

                # END 标记
                end_match = BLOCK_END_RE.match(inner)
                if end_match and end_match.group(1).strip() == name:
                    break

                # 元数据
                src_m = META_SOURCE_RE.match(inner)
                type_m = META_TYPE_RE.match(inner)
                sync_m = META_LAST_SYNC_RE.match(inner)
                sd_m = META_SCRIPTS_DIR_RE.match(inner)

                if src_m:
                    mod_source = src_m.group(1).strip()
                elif type_m:
                    mod_type = type_m.group(1).strip().lower()
                elif sync_m:
                    last_sync = sync_m.group(1).strip()
                elif sd_m:
                    scripts_dir = sd_m.group(1).strip()
                elif inner.startswith("#"):
                    header_lines.append(inner)
                else:
                    content_lines.append(inner)

                i += 1

            end_idx = i

            # 默认 scripts_dir = 模块名小写
            if not scripts_dir:
                scripts_dir = name.lower()

            if current_section not in blocks_by_section:
                blocks_by_section[current_section] = []

            blocks_by_section[current_section].append({
                "name": name,
                "source": mod_source,
                "mod_type": mod_type,
                "last_sync": last_sync,
                "scripts_dir": scripts_dir,
                "section": current_section,
                "content_lines": content_lines,
                "header_lines": header_lines,
                "start_idx": start_idx,
                "end_idx": end_idx,
            })

            if mod_type == "raw":
                raw_module_names.add(name)

        i += 1

    return all_lines, blocks_by_section, current_mitm_hosts, raw_module_names


# ─── 上游模块解析 ────────────────────────────────────────────

def parse_upstream_module(content: str) -> dict:
    """
    解析上游 .sgmodule 内容，返回:
    {
      "sections": {section_name: [line, ...]},
      "mitm_hosts": set[str],
      "script_urls": set[str],
    }

    section 内容只保留非注释的规则行。
    注释行（# 开头）和空行不纳入 rules 比较。
    """
    lines = content.splitlines()
    sections: dict[str, list[str]] = {}
    mitm_hosts: set[str] = set()
    script_urls: set[str] = set()
    current_section = ""

    for line in lines:
        stripped = line.strip()

        # 段落头
        sec_match = SECTION_RE.match(stripped)
        if sec_match:
            current_section = sec_match.group(1).strip()
            if current_section not in sections:
                sections[current_section] = []
            continue

        if not current_section:
            continue

        # MITM hostname
        if current_section == "MITM":
            m = MITM_HOST_RE.match(stripped)
            if m:
                hosts = [h.strip() for h in m.group(1).split(",") if h.strip()]
                mitm_hosts.update(hosts)
            continue

        # 提取 script-path
        for m in SCRIPT_PATH_RE.finditer(stripped):
            script_urls.add(m.group(1))

        # 跳过注释和空行
        if stripped.startswith("#") or stripped == "":
            continue

        sections[current_section].append(stripped)

    return {
        "sections": sections,
        "mitm_hosts": mitm_hosts,
        "script_urls": script_urls,
    }


# ─── 脚本同步（以 fix.sgmodule 实际引用为准） ──────────────

LOCAL_SCRIPT_RE = re.compile(rf"script-path={re.escape(RAW_BASE)}/(scripts/.+?\.js)")

def sync_all_scripts(mapping: dict) -> list[str]:
    """
    以 fix.sgmodule 中实际引用的脚本路径为准，同步所有 JS 脚本：

    1. 扫描 fix.sgmodule 找出所有本地 script-path 引用
    2. 对于 fix.sgmodule 引用的脚本：
       - mapping 中有记录 → 检查上游是否更新
       - mapping 中无记录 → 尝试从 URL 文件名反查上游下载
    3. 对于 mapping 中有但 fix.sgmodule 不再引用的 → 删除本地文件和 mapping 条目

    返回变更描述列表，同时原地更新 mapping。
    """
    changes = []
    fix_content = read_file(FIX_MODULE) if os.path.exists(FIX_MODULE) else ""

    # 1. 收集 fix.sgmodule 中所有本地脚本引用
    referenced_paths: set[str] = set()
    for m in LOCAL_SCRIPT_RE.finditer(fix_content):
        referenced_paths.add(m.group(1))

    print(f"\n  fix.sgmodule 引用了 {len(referenced_paths)} 个本地脚本")

    # 2. 检查每个被引用的脚本
    for local_path in sorted(referenced_paths):
        abs_path = os.path.join(REPO_ROOT, local_path)
        exists = os.path.exists(abs_path)

        if local_path in mapping:
            upstream_url = mapping[local_path]["upstream_url"]

            # 检查上游是否有更新
            remote_content = fetch_url(upstream_url, timeout=60)
            if remote_content is None:
                if not exists:
                    changes.append(f"  !! 脚本缺失且无法下载: {local_path}")
                continue

            if not exists:
                # 文件被误删，重新下载
                if not is_dry_run():
                    write_file(abs_path, remote_content)
                changes.append(f"  + 恢复脚本: {local_path}")
            elif sha256(remote_content) != sha256(read_file(abs_path)):
                # 有更新
                if not is_dry_run():
                    write_file(abs_path, remote_content)
                filename = local_path.split("/")[-1]
                changes.append(f"  * 更新脚本: {filename}")
        else:
            # fix.sgmodule 引用了但 mapping 中没有
            # 尝试从上游模块的 BEGIN 块注释中查找该脚本的原始 URL
            # 如果找不到，只报告，不删除（因为是 fix.sgmodule 引用的）
            if not exists:
                changes.append(f"  !! 脚本缺失且无上游记录: {local_path}")

    # 3. 清理 fix.sgmodule 不再引用的脚本（仅当 fix.sgmodule 已更新后）
    to_remove = []
    for local_path in list(mapping.keys()):
        if local_path not in referenced_paths:
            to_remove.append(local_path)

    for local_path in to_remove:
        abs_path = os.path.join(REPO_ROOT, local_path)
        if is_dry_run():
            print(f"  [DRY-RUN] 清理未引用脚本: {local_path}")
        else:
            if os.path.exists(abs_path):
                os.remove(abs_path)
        del mapping[local_path]
        changes.append(f"  - 清理未引用脚本: {local_path}")

    return changes


# ─── MITM 合并 ────────────────────────────────────────────────

def merge_mitm_hosts(hosts: set[str]) -> str:
    """去重排序后生成 hostname = %APPEND% ... 行"""
    sorted_hosts = sorted(hosts)
    return "hostname = %APPEND% " + ", ".join(sorted_hosts)


# ─── script-path URL 替换 ─────────────────────────────────────

def replace_script_urls(lines: list[str], scripts_dir: str) -> list[str]:
    """
    将规则行中的外部 script-path= URL 替换为本地 raw URL。
    仅替换映射表中已存在的脚本（通过 scripts_dir 查找）。
    """
    script_dir_path = f"scripts/{scripts_dir}/"
    result = []
    for line in lines:
        altered = line
        for m in SCRIPT_PATH_RE.finditer(line):
            url = m.group(1)
            filename = url.rstrip("/").split("/")[-1]
            local_url = f"{RAW_BASE}/{script_dir_path}{filename}"
            altered = altered.replace(url, local_url)
        result.append(altered)
    return result


# ─── fix.sgmodule 区块更新 ────────────────────────────────────

def update_module_block(all_lines: list[str], block: dict,
                        new_content_lines: list[str], new_date: str) -> None:
    """
    原地更新 all_lines 中某个模块的 BEGIN/END 区块：
    - 更新 last-sync 日期
    - 替换规则内容行
    """
    start = block["start_idx"]

    # 更新 last-sync 行
    for i in range(block["start_idx"], block["end_idx"] + 1):
        stripped = all_lines[i].rstrip("\n").rstrip("\r")
        if META_LAST_SYNC_RE.match(stripped):
            all_lines[i] = f"# last-sync: {new_date}\n"
            break

    # 找到内容区的起止位置（在元数据/注释行之后，END 行之前）
    content_start = None
    for i in range(block["start_idx"] + 1, block["end_idx"]):
        stripped = all_lines[i].rstrip("\n").rstrip("\r")
        if (not stripped.startswith("#") and
            not META_SOURCE_RE.match(stripped) and
            not META_TYPE_RE.match(stripped) and
            not META_LAST_SYNC_RE.match(stripped) and
            not META_SCRIPTS_DIR_RE.match(stripped)):
            content_start = i
            break

    if content_start is None:
        # 没有旧内容行，在 END 之前插入
        insert_at = block["end_idx"]
    else:
        # 找到旧内容区的结束（第一个空行之后或 END 行之前）
        content_end = content_start
        for i in range(content_start, block["end_idx"]):
            stripped = all_lines[i].rstrip("\n").rstrip("\r")
            if BLOCK_END_RE.match(stripped):
                break
            content_end = i + 1

        # 替换内容
        new_lines_with_nl = [l + "\n" for l in new_content_lines]
        # 确保每个内容行后有空行分隔
        if new_lines_with_nl and not new_lines_with_nl[-1].endswith("\n\n"):
            new_lines_with_nl[-1] = new_lines_with_nl[-1].rstrip("\n") + "\n"

        all_lines[content_start:content_end] = new_lines_with_nl


def append_block_to_section(all_lines: list[str],
                            blocks_by_section: dict[str, list[dict]],
                            section_name: str,
                            block_name: str,
                            source_url: str,
                            scripts_dir: str,
                            content_lines: list[str]) -> None:
    """在指定段落末尾追加新的 BEGIN/END 区块。"""
    today = date.today().isoformat()

    new_block = [
        f"# ===== BEGIN: {block_name} =====\n",
        f"# source: {source_url}\n",
        f"# type: raw\n",
        f"# scripts-dir: {scripts_dir}\n",
        f"# last-sync: {today}\n",
    ]
    for line in content_lines:
        new_block.append(line + "\n")
    new_block.append(f"# ===== END: {block_name} =====\n")
    new_block.append("\n")

    # 查找该段落的插入位置
    if section_name in blocks_by_section and blocks_by_section[section_name]:
        # 在最后一个 END 行之后插入
        last_end = blocks_by_section[section_name][-1]["end_idx"]
        insert_at = last_end + 1
    else:
        # 段落不存在：在 [MITM] 之前创建
        insert_at = None
        for i, line in enumerate(all_lines):
            if line.strip() == "[MITM]":
                # 在 [MITM] 前插入新段落 + 区块
                all_lines.insert(i, "\n")
                all_lines.insert(i, "\n")
                insert_at = i
                break
        if insert_at is None:
            # 没有 [MITM]，追加到文件末尾
            insert_at = len(all_lines)

        # 插入段落头
        header = f"\n[{section_name}]\n"
        all_lines.insert(insert_at, header)
        insert_at += 1

    # 插入区块
    for line in reversed(new_block):
        all_lines.insert(insert_at, line)


def ensure_section_header(all_lines: list[str], section_name: str) -> int:
    """确保 fix.sgmodule 中存在某个段落头，返回该段落最后一次出现的位置索引。"""
    last_idx = -1
    for i, line in enumerate(all_lines):
        m = SECTION_RE.match(line.strip())
        if m and m.group(1).strip() == section_name:
            last_idx = i
    return last_idx


# ─── 主流程 ──────────────────────────────────────────────────

def main() -> None:
    dry = is_dry_run()
    if dry:
        print("=== DRY-RUN 模式: 不写入文件 ===")

    # 1. 解析 fix.sgmodule
    all_lines, blocks_by_section, mitm_hosts, raw_module_names = parse_fix_module(FIX_MODULE)

    # 2. 读取 mapping.json
    mapping = {}
    if os.path.exists(MAPPING_FILE):
        mapping = json.loads(read_file(MAPPING_FILE))

    # 3. 从 blocks_by_section 提取 raw 模块信息（去重，多个段落可能属于同一模块）
    raw_modules: dict[str, dict] = {}  # name → {"source": str, "scripts_dir": str, "blocks": [block_dict]}
    for section_name, blocks in blocks_by_section.items():
        for block in blocks:
            if block["mod_type"] != "raw":
                continue
            name = block["name"]
            if name not in raw_modules:
                raw_modules[name] = {
                    "source": block["source"],
                    "scripts_dir": block["scripts_dir"],
                    "blocks": [],
                }
            raw_modules[name]["blocks"].append(block)

    if not raw_modules:
        print("没有 raw 类型模块，跳过。")
        set_output("has_changes", "false")
        set_output("commit_message", "自动同步: 无 raw 类型模块")
        return

    print(f"发现 {len(raw_modules)} 个 raw 类型模块: {', '.join(raw_modules.keys())}")

    changes: list[str] = []
    errors: list[str] = []
    has_any_change = False

    # 4. 逐个处理 raw 模块
    for mod_name, mod_info in raw_modules.items():
        upstream_url = mod_info["source"]
        scripts_dir = mod_info["scripts_dir"]
        archive_path = os.path.join(SOURCES_DIR, f"{mod_name}.sgmodule")

        print(f"\n── 检查模块: {mod_name} ──")
        print(f"   上游: {upstream_url}")

        # 4a. 拉取最新
        latest_content = fetch_url(upstream_url)
        if latest_content is None:
            errors.append(f"模块 {mod_name}: 无法获取上游内容")
            continue

        # 4b. 哈希对比
        old_content = read_file(archive_path) if os.path.exists(archive_path) else ""
        if sha256(latest_content) == sha256(old_content):
            print(f"   ✅ 无变化")
            continue

        has_any_change = True
        print(f"   ⚡ 有变化，开始同步...")

        # 4c. 保存最新存档
        if not dry:
            write_file(archive_path, latest_content)

        # 4d. 解析新旧内容
        old_parsed = parse_upstream_module(old_content) if old_content else {"sections": {}, "mitm_hosts": set(), "script_urls": set()}
        new_parsed = parse_upstream_module(latest_content)

        # 4e. 更新各段落区块
        today = date.today().isoformat()
        all_section_names = set(old_parsed["sections"].keys()) | set(new_parsed["sections"].keys())
        section_changes = 0

        # 排除 MITM（单独处理）
        rule_sections = [s for s in all_section_names if s != "MITM"]

        for section_name in rule_sections:
            new_lines = new_parsed["sections"].get(section_name, [])

            # 替换 script-path → 本地 URL
            new_lines = replace_script_urls(new_lines, scripts_dir)

            # 查找该模块在此段落的现有区块
            target_block = None
            if section_name in blocks_by_section:
                for b in blocks_by_section[section_name]:
                    if b["name"] == mod_name:
                        target_block = b
                        break

            if target_block:
                update_module_block(all_lines, target_block, new_lines, today)
            else:
                # 新段落 — 确保段落头存在，追加区块
                sec_idx = ensure_section_header(all_lines, section_name)
                if sec_idx < 0:
                    # 需要创建段落头
                    append_block_to_section(all_lines, blocks_by_section,
                                            section_name, mod_name,
                                            upstream_url, scripts_dir, new_lines)
                    print(f"   + 新建段落 [{section_name}] + 区块")
                else:
                    print(f"   ⚠ 模块 {mod_name} 在 [{section_name}] 无现有区块，跳过（需手动处理）")
                    continue

            section_changes += 1

        if section_changes > 0:
            changes.append(f"同步更新: {mod_name}, 变化 {section_changes} 个段落")

        # 合并 MITM 域名
        mitm_hosts |= new_parsed["mitm_hosts"]

    # 5. 更新 MITM 行
    mitm_line = merge_mitm_hosts(mitm_hosts)
    mitm_updated = False
    for i, line in enumerate(all_lines):
        if line.strip() == "[MITM]":
            # 查找下一行中的 hostname 并替换
            for j in range(i + 1, min(i + 10, len(all_lines))):
                if MITM_HOST_RE.match(all_lines[j].strip()):
                    old_mitm = all_lines[j]
                    new_mitm_line = mitm_line + "\n"
                    if old_mitm != new_mitm_line:
                        all_lines[j] = new_mitm_line
                        mitm_updated = True
                    break
            break

    # 6. 写回 fix.sgmodule
    if has_any_change and not dry:
        write_file(FIX_MODULE, "".join(all_lines))
        print(f"\n✓ fix.sgmodule 已更新")

    # 6b. 同步脚本（以 fix.sgmodule 实际引用为准）
    script_changes = sync_all_scripts(mapping)
    if script_changes:
        has_any_change = True
        changes.extend(script_changes)

    # 7. 写回 mapping.json
    if has_any_change and not dry:
        write_file(MAPPING_FILE, json.dumps(mapping, ensure_ascii=False, indent=2) + "\n")
        print(f"✓ mapping.json 已更新")

    # 8. 构建 commit message
    commit_lines = []
    if has_any_change:
        module_names = ", ".join(raw_modules.keys())
        commit_lines.append(f"自动同步: {module_names}")
        commit_lines.append("")
        for c in changes:
            commit_lines.append(c)
    else:
        commit_lines.append("自动同步: 无变化")

    if errors:
        commit_lines.append("")
        commit_lines.append("警告/错误:")
        for e in errors:
            commit_lines.append(f"  - {e}")

    commit_message = "\n".join(commit_lines)
    print(f"\n── Commit Message ──\n{commit_message}\n")

    if dry:
        print("[DRY-RUN] 未写入任何文件")
    else:
        set_output("has_changes", "true" if has_any_change else "false")
        set_output("commit_message", commit_message)


if __name__ == "__main__":
    main()
