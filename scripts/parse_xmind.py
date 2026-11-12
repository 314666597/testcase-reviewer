#!/usr/bin/env python3
"""
XMind 测试用例解析器（支持 .xmind 格式）

XMind 文件本质上是 ZIP 包，包含 content.json 或 content.xml。
本脚本支持 XMind 8（XML）和 XMind Zen/2022+（JSON）两种格式。

用法：
    py parse_xmind.py <path/to/file.xmind> [--output <output.json>]

依赖：
    pip install defusedxml

输出：
    标准化的测试用例 JSON 格式
"""

import sys
import json
import os
import zipfile
import re


def parse_xmind(file_path: str) -> dict:
    """
    解析 XMind 文件，将思维导图节点转换为测试用例列表

    XMind 测试用例约定（推荐结构）：
    - 根节点：测试模块/功能名称
    - 二级节点：子功能 or 用例分类
    - 叶节点：具体测试用例（节点标题即为用例标题）
    - 节点备注：可包含步骤、预期结果等信息
    """
    result = {
        "format": "xmind",
        "file": str(file_path),
        "total": 0,
        "fields": ["id", "title", "module", "path", "priority", "steps", "expected", "remarks"],
        "cases": [],
        "warnings": []
    }

    if not os.path.exists(file_path):
        result["warnings"].append(f"文件不存在: {file_path}")
        return result

    if not zipfile.is_zipfile(file_path):
        result["warnings"].append("文件不是有效的 XMind 格式（应为 ZIP 包）")
        return result

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            namelist = zf.namelist()

            # 优先尝试 JSON 格式（XMind Zen / 2022+）
            if "content.json" in namelist:
                content = zf.read("content.json").decode("utf-8")
                data = json.loads(content)
                cases = _parse_xmind_json(data)
                result["cases"] = cases
                result["total"] = len(cases)

            # 尝试 XML 格式（XMind 8）
            elif "content.xml" in namelist:
                try:
                    import defusedxml.ElementTree as ET
                except ImportError:
                    import xml.etree.ElementTree as ET
                    result["warnings"].append("建议安装 defusedxml 以提高安全性：pip install defusedxml")

                content = zf.read("content.xml").decode("utf-8")
                root = ET.fromstring(content)
                cases = _parse_xmind_xml(root)
                result["cases"] = cases
                result["total"] = len(cases)

            else:
                result["warnings"].append(f"未找到 content.json 或 content.xml，文件内容: {namelist[:10]}")

    except Exception as e:
        result["warnings"].append(f"解析 XMind 文件失败: {e}")

    return result


def _parse_xmind_json(data: list) -> list:
    """解析 XMind Zen/2022+ JSON 格式"""
    cases = []
    case_counter = [0]

    def walk(node, path: list, module: str):
        title = node.get("title", "").strip()
        if not title:
            return

        children = node.get("children", {})
        attached = children.get("attached", []) if isinstance(children, dict) else []

        # 提取备注
        notes = ""
        if "notes" in node:
            notes_data = node["notes"]
            if isinstance(notes_data, dict):
                plain = notes_data.get("plain", {})
                if isinstance(plain, dict):
                    notes = plain.get("content", "")
                elif isinstance(plain, str):
                    notes = plain
        
        # 提取标签作为优先级或标签
        labels = node.get("labels", [])
        priority = _extract_priority(labels + [title])
        tags = [l for l in labels if not _is_priority_label(l)]

        current_path = path + [title]

        # 叶节点 = 测试用例
        if not attached:
            case_counter[0] += 1
            steps, expected = _parse_notes(notes)
            cases.append({
                "id": f"TC-{case_counter[0]:04d}",
                "title": title,
                "module": module or (path[0] if path else ""),
                "path": " > ".join(current_path),
                "priority": priority or "中",
                "steps": steps,
                "expected": expected,
                "remarks": notes if not steps else "",
                "tags": ", ".join(tags) if tags else "",
            })
        else:
            # 非叶节点，继续递归
            new_module = module or title
            for child in attached:
                walk(child, current_path, new_module)

    # XMind JSON 结构是一个数组，每个元素是一个画布（sheet）
    for sheet in data:
        root_topic = sheet.get("rootTopic", {})
        if root_topic:
            walk(root_topic, [], "")

    return cases


def _parse_xmind_xml(root) -> list:
    """解析 XMind 8 XML 格式"""
    cases = []
    case_counter = [0]

    # XML 命名空间
    ns = {
        "xmind": "urn:xmind:xmap:xmlns:content:2.0",
        "fo": "http://www.w3.org/1999/XSL/Format",
        "svg": "http://www.w3.org/2000/svg",
        "xlink": "http://www.w3.org/1999/xlink",
        "xhtml": "http://www.w3.org/1999/xhtml",
    }

    def get_text(elem) -> str:
        if elem is None:
            return ""
        return (elem.text or "").strip()

    def find_title(topic):
        for child in topic:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "title":
                return get_text(child)
        return ""

    def find_children(topic):
        for child in topic:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "children":
                topics = []
                for sub in child:
                    sub_tag = sub.tag.split("}")[-1] if "}" in sub.tag else sub.tag
                    if sub_tag == "topics":
                        topics.extend(sub)
                return topics
        return []

    def find_notes(topic):
        for child in topic:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "notes":
                for sub in child:
                    return get_text(sub)
        return ""

    def walk(topic, path: list, module: str):
        title = find_title(topic)
        if not title:
            return

        children = find_children(topic)
        notes = find_notes(topic)
        current_path = path + [title]

        # 提取优先级标记
        priority = _extract_priority([title])

        if not children:
            case_counter[0] += 1
            steps, expected = _parse_notes(notes)
            cases.append({
                "id": f"TC-{case_counter[0]:04d}",
                "title": title,
                "module": module or (path[0] if path else ""),
                "path": " > ".join(current_path),
                "priority": priority or "中",
                "steps": steps,
                "expected": expected,
                "remarks": notes if not steps else "",
                "tags": "",
            })
        else:
            new_module = module or title
            for child in children:
                walk(child, current_path, new_module)

    # 找所有 sheet 的根节点
    for sheet in root:
        sheet_tag = sheet.tag.split("}")[-1] if "}" in sheet.tag else sheet.tag
        if sheet_tag == "sheet":
            for child in sheet:
                child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if child_tag == "topic":
                    walk(child, [], "")
                    break

    return cases


def _parse_notes(notes: str):
    """
    从备注中提取测试步骤和预期结果

    支持格式：
    - 步骤：xxx\n预期：xxx
    - Steps: xxx\nExpected: xxx
    - 1. step1\n2. step2\n期望：xxx
    """
    if not notes:
        return "", ""

    steps = ""
    expected = ""

    # 尝试匹配 "预期结果：" 分隔符
    patterns = [
        r"(?:预期结果|预期|期望结果|期望)[：:]\s*(.*)",
        r"(?:expected result|expected)[:\s]\s*(.*)",
    ]

    notes_lower = notes.lower()
    for pattern in patterns:
        m = re.search(pattern, notes, re.IGNORECASE | re.DOTALL)
        if m:
            expected = m.group(1).strip()
            # 步骤是预期之前的内容
            steps = notes[:m.start()].strip()
            # 去掉 "步骤：" 前缀
            steps = re.sub(r"^(?:步骤|测试步骤|操作步骤|steps?)[：:\s]*", "", steps, flags=re.IGNORECASE).strip()
            break

    if not steps and not expected:
        # 如果没有匹配到分隔符，全部作为步骤
        steps = notes.strip()

    return steps, expected


def _extract_priority(texts: list) -> str:
    """从文本列表中提取优先级"""
    priority_map = {
        "p0": "P0", "p1": "P1", "p2": "P2", "p3": "P3",
        "高": "高", "中": "中", "低": "低",
        "high": "高", "medium": "中", "low": "低",
        "critical": "P0", "major": "P1", "minor": "P2", "trivial": "P3",
        "blocker": "P0",
    }
    for text in texts:
        text_lower = text.lower().strip()
        for key, val in priority_map.items():
            if key in text_lower:
                return val
    return ""


def _is_priority_label(label: str) -> bool:
    priority_keywords = ["p0", "p1", "p2", "p3", "高", "中", "低", "high", "medium", "low"]
    return any(kw in label.lower() for kw in priority_keywords)


def main():
    if len(sys.argv) < 2:
        print("用法: py parse_xmind.py <file.xmind> [--output <output.json>]")
        sys.exit(1)

    file_path = sys.argv[1]
    output_path = None

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    result = parse_xmind(file_path)
    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"解析完成，共 {result['total']} 条用例，结果已保存到: {output_path}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
