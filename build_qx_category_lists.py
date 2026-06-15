#!/usr/bin/env python3
"""按 QuantumultX/README.md 分类合并 .list 规则文件。"""

from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path

BASE = Path(__file__).resolve().parent / "QuantumultX"
README = BASE / "README.md"
OUT_DIR = Path(__file__).resolve().parent / "QuantumultX rule"

LINK_RE = re.compile(
    r"\[[^\]]*\]\(https://github\.com/blackmatrix7/ios_rule_script/tree/master/rule/QuantumultX/([^)]+)\)"
)
CATEGORY_RE = re.compile(r"^\|([📵🌏🇨🇳📺🎮🍎🗄️📟🚫🖥️][^|]+)\|")
RULE_LINE_RE = re.compile(
    r"^(HOST(?:-KEYWORD|-SUFFIX)?|IP(?:6)?-CIDR|USER-AGENT|GEOIP|FINAL|IP-ASN),"
)


def clean_category_name(raw: str) -> str:
    """去掉 emoji，得到文件名用的分类名。"""
    name = raw.strip()
    for ch in name:
        if ch.isalnum() or ch in "._-":
            break
        name = name[1:]
    return name.strip()


def parse_categories(readme_text: str) -> OrderedDict[str, list[str]]:
    """解析 README，返回 {分类名: [规则子目录相对路径]}。"""
    categories: OrderedDict[str, list[str]] = OrderedDict()
    current: str | None = None

    for line in readme_text.splitlines():
        cat_match = CATEGORY_RE.match(line)
        if cat_match:
            current = clean_category_name(cat_match.group(1))
            categories.setdefault(current, [])
            continue

        if current is None:
            continue

        for path in LINK_RE.findall(line):
            path = path.strip("/")
            if path and path not in categories[current]:
                categories[current].append(path)

    return categories


def collect_list_files(rule_path: str) -> list[Path]:
    """收集子目录下全部 .list 文件。"""
    folder = BASE / rule_path.replace("/", "\\")
    if not folder.is_dir():
        return []
    return sorted(folder.rglob("*.list"))


def parse_rule_line(line: str, policy: str) -> str | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if not RULE_LINE_RE.match(line):
        return None
    parts = line.rsplit(",", 1)
    if len(parts) != 2:
        return line
    return f"{parts[0]},{policy}"


def merge_category(policy: str, rule_paths: list[str]) -> tuple[list[str], dict[str, int]]:
    """合并一个分类下的所有规则，去重并保持顺序。"""
    seen: set[str] = set()
    merged: list[str] = []
    stats = {"sources": 0, "files": 0, "rules": 0, "skipped_paths": 0}

    for rule_path in rule_paths:
        list_files = collect_list_files(rule_path)
        if not list_files:
            stats["skipped_paths"] += 1
            continue
        stats["sources"] += 1
        for list_file in list_files:
            stats["files"] += 1
            text = list_file.read_text(encoding="utf-8", errors="replace")
            for raw_line in text.splitlines():
                rule = parse_rule_line(raw_line, policy)
                if rule is None:
                    continue
                if rule in seen:
                    continue
                seen.add(rule)
                merged.append(rule)
                stats["rules"] += 1

    return merged, stats


def write_category_list(policy: str, rules: list[str], stats: dict[str, int], source_count: int) -> None:
    header = [
        f"# NAME: {policy}",
        "# AUTHOR: blackmatrix7 (merged by category)",
        "# REPO: https://github.com/blackmatrix7/ios_rule_script",
        f"# CATEGORY: {policy}",
        f"# SOURCE_RULES: {source_count}",
        f"# SOURCE_FILES: {stats['files']}",
        f"# TOTAL: {len(rules)}",
        "",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / f"{policy}.list"
    out_file.write_text("\n".join(header + rules) + "\n", encoding="utf-8")


def main() -> None:
    categories = parse_categories(README.read_text(encoding="utf-8"))
    summary: list[str] = []

    for policy, rule_paths in categories.items():
        rules, stats = merge_category(policy, rule_paths)
        write_category_list(policy, rules, stats, len(rule_paths))
        summary.append(
            f"{policy}: {len(rules)} 条规则, "
            f"{stats['sources']} 个子目录, {stats['files']} 个 .list 文件, "
            f"{stats['skipped_paths']} 个缺失路径"
        )
        print(summary[-1])

    index = OUT_DIR / "README.md"
    index.write_text(
        "# QuantumultX 分类规则\n\n"
        "按 [QuantumultX/README.md](../QuantumultX/README.md) 分类合并生成。\n\n"
        + "\n".join(f"- {line}" for line in summary)
        + "\n",
        encoding="utf-8",
    )
    print(f"\n已写入: {OUT_DIR}")


if __name__ == "__main__":
    main()
