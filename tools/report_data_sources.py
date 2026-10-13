"""Render the current catalog inventory without changing source decisions."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fondontology.corpus.data_catalog import build_catalog_records


def main() -> int:
    root = ROOT / "data"
    catalog = root / "source_catalog.json"
    audit = build_catalog_records(catalog, data_root=root)
    documents = json.loads(catalog.read_text(encoding="utf-8"))["documents"]
    counts = Counter(item["status"] for item in documents)
    acquired = sum(item["raw_path"] is not None for item in documents)
    converted = sum(item["markdown_path"] is not None for item in documents)
    lines = [
        "# 来源恢复清单",
        "",
        f"共 {len(documents)} 个独立版本，已取得 {acquired} 份原件，"
        f"已生成 {converted} 份转换正文。",
        "状态：" + "，".join(f"{status}={counts[status]}" for status in
                           ("ready", "converted_unverified", "downloaded", "unresolved")) + "。",
        "",
        "ready 表示通过本目录入库门槛，不能直接理解为现行有效。"
        "converted_unverified 的原件可核查，转换文本尚不能用于权威答复。",
        "",
        "| 文档 / 版本 | 原件 | 转换正文 | 状态 | 待处理原因 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for document in documents:
        title = document["title"].replace("|", "\\|")
        raw = (f"[{document['format']}]({document['raw_path']})"
               if document["raw_path"] else "未确认")
        markdown = (f"[全文]({document['markdown_path']})"
                    if document["markdown_path"] else "未转换")
        reason = (document.get("failure_reason") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {title} | {raw} | {markdown} | {document['status']} | {reason} |")
    lines += [
        "",
        f"目录 SHA-256：`{hashlib.sha256(catalog.read_bytes()).hexdigest()}`。",
        f"入库审计通过：{len(audit['records'])} 项可选，{len(audit['skipped'])} 项排除。",
        "全部登记原件与正文哈希、可入库项的收据与转换记录绑定由审计重新验证；"
        "未通过项不通过旧 manifest 或目录扫描补入。",
        "",
    ]
    target = root / "SOURCE_RECOVERY.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"report": str(target), "documents": len(documents),
                      "acquired": acquired, "converted": converted, "counts": dict(counts)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
