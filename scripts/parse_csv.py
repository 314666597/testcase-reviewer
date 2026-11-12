#!/usr/bin/env python3
"""
CSV 测试用例解析器

用法：
    py parse_csv.py <path/to/file.csv> [--output <output.json>]

输出：
    标准化的测试用例 JSON 格式，保存到指定文件或打印到 stdout
"""

import sys
import json
import csv
import os
from pathlib import Path


# 常见字段名映射（中英文兼容）
FIELD_MAPPING = {
    # ID 字段
    "id": "id", "用例id": "id", "用例编号": "id", "编号": "id", "序号": "id",
    "case_id": "id", "caseid": "id", "test_id": "id",
    # 标题/名称
    "title": "title", "name": "title", "标题": "title", "用例名称": "title",
    "用例标题": "title", "测试标题": "title", "case_name": "title",
    # 模块/功能
    "module": "module", "feature": "module", "模块": "module", "功能模块": "module",
    "功能": "module", "所属模块": "module", "function": "module",
    # 优先级
    "priority": "priority", "优先级": "priority", "级别": "priority",
    "level": "priority", "severity": "priority",
    # 前置条件
    "precondition": "precondition", "前置条件": "precondition",
    "preconditions": "precondition", "prerequisites": "precondition",
    "pre_condition": "precondition", "前提条件": "precondition",
    # 测试步骤
    "steps": "steps", "step": "steps", "测试步骤": "steps", "操作步骤": "steps",
    "test_steps": "steps", "步骤": "steps",
    # 预期结果
    "expected": "expected", "expected_result": "expected", "预期结果": "expected",
    "期望结果": "expected", "期望": "expected", "result": "expected",
    # 实际结果
    "actual": "actual", "actual_result": "actual", "实际结果": "actual",
    # 测试类型
    "type": "type", "case_type": "type", "测试类型": "type", "用例类型": "type",
    # 状态
    "status": "status", "状态": "status", "执行状态": "status",
    # 备注
    "remarks": "remarks", "remark": "remarks", "备注": "remarks",
    "note": "remarks", "notes": "remarks", "comment": "remarks",
    # 作者
    "author": "author", "创建人": "author", "编写人": "author",
    # 标签
    "tags": "tags", "tag": "tags", "标签": "tags",
}


def normalize_header(header: str) -> str:
    """将表头规范化为标准字段名"""
    key = header.strip().lower().replace(" ", "_").replace("-", "_")
    return FIELD_MAPPING.get(key, key)


def parse_csv(file_path: str) -> dict:
    """
    解析 CSV 测试用例文件

    Returns:
        dict: {
            "format": "csv",
            "file": file_path,
            "total": int,
            "fields": list,
            "cases": list[dict],
            "warnings": list[str]
        }
    """
    result = {
        "format": "csv",
        "file": str(file_path),
        "total": 0,
        "fields": [],
        "cases": [],
        "warnings": []
    }

    if not os.path.exists(file_path):
        result["warnings"].append(f"文件不存在: {file_path}")
        return result

    # 尝试不同编码
    encodings = ["utf-8-sig", "utf-8", "gbk", "gb2312", "gb18030"]
    content = None
    used_encoding = None

    for enc in encodings:
        try:
            with open(file_path, encoding=enc) as f:
                content = f.read()
            used_encoding = enc
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if content is None:
        result["warnings"].append("无法识别文件编码，请将文件保存为 UTF-8 格式")
        return result

    import io
    reader = csv.DictReader(io.StringIO(content))

    if not reader.fieldnames:
        result["warnings"].append("CSV 文件为空或没有表头")
        return result

    # 规范化字段名
    original_fields = list(reader.fieldnames)
    normalized_map = {f: normalize_header(f) for f in original_fields}
    result["fields"] = [normalize_header(f) for f in original_fields]

    cases = []
    for row_num, row in enumerate(reader, start=2):
        case = {"_row": row_num}
        for orig_field, value in row.items():
            if orig_field is None:
                continue
            norm_field = normalized_map.get(orig_field, orig_field)
            case[norm_field] = (value or "").strip()

        # 自动生成 ID（如果没有）
        if "id" not in case or not case["id"]:
            case["id"] = f"ROW-{row_num}"

        cases.append(case)

    result["total"] = len(cases)
    result["cases"] = cases

    if used_encoding and used_encoding != "utf-8-sig":
        result["warnings"].append(f"文件编码为 {used_encoding}，建议转换为 UTF-8")

    return result


def main():
    if len(sys.argv) < 2:
        print("用法: py parse_csv.py <file.csv> [--output <output.json>]")
        sys.exit(1)

    file_path = sys.argv[1]
    output_path = None

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    result = parse_csv(file_path)

    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"解析完成，共 {result['total']} 条用例，结果已保存到: {output_path}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
