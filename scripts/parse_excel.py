#!/usr/bin/env python3
"""
Excel 测试用例解析器（支持 .xlsx 和 .xls）

用法：
    py parse_excel.py <path/to/file.xlsx> [--sheet <sheet_name>] [--output <output.json>]

依赖：
    pip install openpyxl xlrd

输出：
    标准化的测试用例 JSON 格式
"""

import sys
import json
import os


# 字段名映射（与 parse_csv.py 保持一致）
FIELD_MAPPING = {
    "id": "id", "用例id": "id", "用例编号": "id", "编号": "id", "序号": "id",
    "case_id": "id", "caseid": "id", "test_id": "id",
    "title": "title", "name": "title", "标题": "title", "用例名称": "title",
    "用例标题": "title", "测试标题": "title", "case_name": "title",
    "module": "module", "feature": "module", "模块": "module", "功能模块": "module",
    "功能": "module", "所属模块": "module", "function": "module",
    "priority": "priority", "优先级": "priority", "级别": "priority",
    "level": "priority", "severity": "priority",
    "precondition": "precondition", "前置条件": "precondition",
    "preconditions": "precondition", "prerequisites": "precondition",
    "pre_condition": "precondition", "前提条件": "precondition",
    "steps": "steps", "step": "steps", "测试步骤": "steps", "操作步骤": "steps",
    "test_steps": "steps", "步骤": "steps",
    "expected": "expected", "expected_result": "expected", "预期结果": "expected",
    "期望结果": "expected", "期望": "expected", "result": "expected",
    "actual": "actual", "actual_result": "actual", "实际结果": "actual",
    "type": "type", "case_type": "type", "测试类型": "type", "用例类型": "type",
    "status": "status", "状态": "status", "执行状态": "status",
    "remarks": "remarks", "remark": "remarks", "备注": "remarks",
    "note": "remarks", "notes": "remarks", "comment": "remarks",
    "author": "author", "创建人": "author", "编写人": "author",
    "tags": "tags", "tag": "tags", "标签": "tags",
}


def normalize_header(header) -> str:
    if header is None:
        return ""
    key = str(header).strip().lower().replace(" ", "_").replace("-", "_")
    return FIELD_MAPPING.get(key, key)


def parse_excel(file_path: str, sheet_name: str = None) -> dict:
    """
    解析 Excel 测试用例文件

    支持两种布局：
    1. 标准表格：第一行为表头，后续行为数据
    2. 多层级表头：自动检测并跳过合并单元格表头行
    """
    result = {
        "format": "excel",
        "file": str(file_path),
        "total": 0,
        "fields": [],
        "sheets": [],
        "cases": [],
        "warnings": []
    }

    if not os.path.exists(file_path):
        result["warnings"].append(f"文件不存在: {file_path}")
        return result

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".xlsx":
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet_names = wb.sheetnames
            result["sheets"] = sheet_names

            # 确定要处理的 sheet
            if sheet_name:
                if sheet_name not in sheet_names:
                    result["warnings"].append(f"Sheet '{sheet_name}' 不存在，可用的 sheet: {sheet_names}")
                    return result
                target_sheets = [sheet_name]
            else:
                target_sheets = sheet_names

            all_cases = []
            for sname in target_sheets:
                ws = wb[sname]
                cases, fields, warns = _parse_xlsx_sheet(ws, sname)
                all_cases.extend(cases)
                result["warnings"].extend(warns)
                if not result["fields"] and fields:
                    result["fields"] = fields

            result["cases"] = all_cases
            result["total"] = len(all_cases)

        elif ext in (".xls",):
            try:
                import xlrd
            except ImportError:
                result["warnings"].append("解析 .xls 文件需要安装 xlrd：pip install xlrd")
                return result

            wb = xlrd.open_workbook(file_path)
            sheet_names = wb.sheet_names()
            result["sheets"] = sheet_names

            if sheet_name:
                if sheet_name not in sheet_names:
                    result["warnings"].append(f"Sheet '{sheet_name}' 不存在")
                    return result
                target_sheets = [sheet_name]
            else:
                target_sheets = sheet_names

            all_cases = []
            for sname in target_sheets:
                ws = wb.sheet_by_name(sname)
                cases, fields, warns = _parse_xls_sheet(ws, sname)
                all_cases.extend(cases)
                result["warnings"].extend(warns)
                if not result["fields"] and fields:
                    result["fields"] = fields

            result["cases"] = all_cases
            result["total"] = len(all_cases)

        else:
            result["warnings"].append(f"不支持的文件格式: {ext}，请使用 .xlsx 或 .xls")

    except ImportError as e:
        result["warnings"].append(f"缺少依赖库: {e}，请运行 pip install openpyxl")
    except Exception as e:
        result["warnings"].append(f"解析文件失败: {e}")

    return result


def _parse_xlsx_sheet(ws, sheet_name: str):
    """解析 openpyxl 工作表"""
    cases = []
    fields = []
    warnings = []

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        warnings.append(f"Sheet '{sheet_name}' 为空")
        return cases, fields, warnings

    # 找到表头行（第一个非空行）
    header_row_idx = 0
    for i, row in enumerate(rows):
        non_empty = [c for c in row if c is not None and str(c).strip()]
        if len(non_empty) >= 2:
            header_row_idx = i
            break

    headers = [normalize_header(c) for c in rows[header_row_idx]]
    fields = [h for h in headers if h]

    # 解析数据行
    for row_idx in range(header_row_idx + 1, len(rows)):
        row = rows[row_idx]
        # 跳过完全空行
        if all(c is None or str(c).strip() == "" for c in row):
            continue

        case = {"_sheet": sheet_name, "_row": row_idx + 1}
        for col_idx, header in enumerate(headers):
            if not header:
                continue
            val = row[col_idx] if col_idx < len(row) else None
            case[header] = str(val).strip() if val is not None else ""

        # 自动生成 ID
        if "id" not in case or not case["id"]:
            case["id"] = f"{sheet_name}-ROW{row_idx + 1}"

        cases.append(case)

    return cases, fields, warnings


def _parse_xls_sheet(ws, sheet_name: str):
    """解析 xlrd 工作表"""
    cases = []
    fields = []
    warnings = []

    if ws.nrows == 0:
        warnings.append(f"Sheet '{sheet_name}' 为空")
        return cases, fields, warnings

    # 找表头行
    header_row_idx = 0
    for i in range(ws.nrows):
        row = ws.row_values(i)
        non_empty = [c for c in row if c is not None and str(c).strip()]
        if len(non_empty) >= 2:
            header_row_idx = i
            break

    headers = [normalize_header(c) for c in ws.row_values(header_row_idx)]
    fields = [h for h in headers if h]

    for row_idx in range(header_row_idx + 1, ws.nrows):
        row = ws.row_values(row_idx)
        if all(str(c).strip() == "" for c in row):
            continue

        case = {"_sheet": sheet_name, "_row": row_idx + 1}
        for col_idx, header in enumerate(headers):
            if not header:
                continue
            val = row[col_idx] if col_idx < len(row) else ""
            # xlrd 数字处理
            if isinstance(val, float) and val == int(val):
                val = int(val)
            case[header] = str(val).strip()

        if "id" not in case or not case["id"]:
            case["id"] = f"{sheet_name}-ROW{row_idx + 1}"

        cases.append(case)

    return cases, fields, warnings


def main():
    if len(sys.argv) < 2:
        print("用法: py parse_excel.py <file.xlsx> [--sheet <sheet_name>] [--output <output.json>]")
        sys.exit(1)

    file_path = sys.argv[1]
    sheet_name = None
    output_path = None

    if "--sheet" in sys.argv:
        idx = sys.argv.index("--sheet")
        if idx + 1 < len(sys.argv):
            sheet_name = sys.argv[idx + 1]

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    result = parse_excel(file_path, sheet_name)
    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"解析完成，共 {result['total']} 条用例，结果已保存到: {output_path}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
