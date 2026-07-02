#!/usr/bin/env python3
"""生成旧 Chroma collection 迁移报告。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.shuyixiao_agent.kb.legacy_migration import (  # noqa: E402
    DEFAULT_MAPPING_FILE,
    DEFAULT_REPORT_PATH,
    generate_legacy_migration_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="只读扫描旧 Chroma collection 并生成迁移报告，不执行迁移。",
    )
    parser.add_argument(
        "--vector-db-path",
        default=None,
        help="Chroma 持久化目录；默认读取项目配置 settings.vector_db_path。",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_REPORT_PATH),
        help="报告输出路径。",
    )
    parser.add_argument(
        "--mapping-file",
        default=str(DEFAULT_MAPPING_FILE),
        help="可选历史名称映射 JSON 文件。",
    )
    args = parser.parse_args()

    rows = generate_legacy_migration_report(
        output_path=args.output,
        vector_db_path=args.vector_db_path,
        mapping_file=args.mapping_file,
    )
    print(f"已生成迁移报告: {args.output}")
    print(f"扫描 collection 数量: {len(rows)}")
    print("安全提示: 本脚本不删除、不重建、不登记任何 Chroma collection。")


if __name__ == "__main__":
    main()
