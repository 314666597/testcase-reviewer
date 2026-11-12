#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用例智能审核引擎 (基于通义千问) - 批量收集版

使用通义千问大模型对标准化后的测试用例数据进行智能审核，输出 Markdown 格式审核报告。

特性：
1. 智能检测用例集是否包含必备条件信息
2. 针对整个评审任务收集一次必备条件（所有用例统一应用）
3. 支持配置保存与复用

用法：
    py review_testcases_llm.py <parsed_cases.json> [--output <report.md>] [--skip-collect]
    
参数：
    --output: 指定输出报告文件路径
    --skip-collect: 跳过必备条件收集，使用上次配置
    
环境变量：
    ALI_QWEN_API_KEY: 阿里云通义千问API密钥
"""

import sys
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 设置Windows控制台输出编码为UTF-8
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass  # 忽略编码设置错误

# 导入智能收集器
try:
    from smart_collector import (
        collect_prerequisites_batch,
        load_prerequisites_from_file,
        save_prerequisites_to_file,
        detect_prerequisite_in_case,
        PREREQUISITE_ITEMS
    )
except ImportError:
    # 如果直接运行，尝试从当前目录导入
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))
    from smart_collector import (
        collect_prerequisites_batch,
        load_prerequisites_from_file,
        save_prerequisites_to_file,
        detect_prerequisite_in_case,
        PREREQUISITE_ITEMS
    )


# ──────────────────────────────────────────────────────────────
# 通义千问调用封装
# ──────────────────────────────────────────────────────────────

class QwenClient:
    """通义千问客户端封装"""
    
    def __init__(self):
        """初始化通义千问客户端"""
        self.api_key = os.getenv("ALI_QWEN_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "未检测到通义千问API密钥，请设置环境变量：\n"
                "  Windows PowerShell: $env:ALI_QWEN_API_KEY=\"your-api-key\"\n"
                "  Linux/macOS: export ALI_QWEN_API_KEY=\"your-api-key\"\n\n"
                "获取API密钥：https://dashscope.console.aliyun.com/apiKey"
            )
        
        # 设置API密钥
        try:
            import dashscope
            dashscope.api_key = self.api_key
            from dashscope import Generation
            self.Generation = Generation
        except ImportError:
            raise ImportError(
                "请安装通义千问SDK: pip install dashscope\n"
                "或: pip install dashscope -i https://pypi.tuna.tsinghua.edu.cn/simple"
            )
    
    def chat(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        """调用通义千问进行对话"""
        try:
            response = self.Generation.call(
                model='qwen-plus',  # 使用qwen-plus模型，性价比高
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                result_format='message',
                temperature=temperature,
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                raise RuntimeError(
                    f"通义千问API调用失败:\n"
                    f"  状态码: {response.status_code}\n"
                    f"  错误信息: {response.message}"
                )
        except Exception as e:
            raise RuntimeError(f"调用通义千问失败: {str(e)}")


# ──────────────────────────────────────────────────────────────
# 审核引擎
# ──────────────────────────────────────────────────────────────

def load_prompt_template() -> str:
    """加载提示词模板"""
    script_dir = Path(__file__).parent
    prompt_file = script_dir.parent / "references" / "review_prompt.md"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"提示词模板文件不存在: {prompt_file}")
    
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read()


def build_case_specific_prompt(base_prompt: str, case_prereqs: Dict[str, bool]) -> str:
    """
    根据单个用例的必备条件配置自定义提示词
    
    Args:
        base_prompt: 基础提示词模板
        case_prereqs: 单个用例的必备条件配置
        
    Returns:
        str: 自定义后的提示词
    """
    # 获取启用和禁用的检查项
    enabled_items = [item for item in PREREQUISITE_ITEMS if case_prereqs.get(item['id'], False)]
    disabled_items = [item for item in PREREQUISITE_ITEMS if not case_prereqs.get(item['id'], False)]
    
    # 构造说明文本
    instructions = []
    
    if enabled_items:
        instructions.append("\n### 必须校验项（用户确认）⚠️")
        instructions.append("**评审原则**：以下检查项为用户确认的必须校验项，用例缺失将影响评审结论。")
        for item in enabled_items:
            instructions.append(f"- **{item['name']}**：{item['description']}")
    
    if disabled_items:
        instructions.append("\n### 跳过校验项（用户确认）⏭️")
        instructions.append("**评审原则**：以下检查项用户确认不需要校验，请忽略相关评审要求。")
        for item in disabled_items:
            instructions.append(f"- **{item['name']}**：{item['description']}")
    
    # 在基础提示词中插入自定义说明
    marker = "### 4. 基础安全校验"
    if marker in base_prompt:
        parts = base_prompt.split(marker, 1)
        custom_prompt = parts[0] + "\n".join(instructions) + "\n\n" + marker + parts[1]
    else:
        # 如果找不到标记，直接追加
        custom_prompt = base_prompt + "\n\n" + "\n".join(instructions)
    
    return custom_prompt


def review_with_llm(data: dict, llm_client: QwenClient, prerequisites: dict) -> dict:
    """
    使用通义千问进行审核
    
    Args:
        data: 测试用例数据
        llm_client: 通义千问客户端
        prerequisites: 必备条件配置（全局配置，应用于所有用例）
        
    Returns:
        dict: 审核结果
    """
    
    # 加载提示词模板
    base_prompt = load_prompt_template()
    
    cases = data.get('cases', [])
    
    # 获取启用的检查项
    enabled_items = [item for item in PREREQUISITE_ITEMS if prerequisites.get(item['id'], False)]
    enabled_names = [item['name'] for item in enabled_items]
    
    # 为每个用例添加必备条件标注
    cases_with_prereqs = []
    for case in cases:
        case_copy = case.copy()
        case_copy['_must_check'] = enabled_names
        cases_with_prereqs.append(case_copy)
    
    # 构造用户消息
    cases_json = json.dumps(cases_with_prereqs, ensure_ascii=False, indent=2)
    
    # 统计各必备条件的启用状态
    prereq_stats = {}
    for item in PREREQUISITE_ITEMS:
        enabled = prerequisites.get(item['id'], False)
        prereq_stats[item['name']] = "启用" if enabled else "跳过"
    
    user_message = f"""请对以下测试用例进行全面评审：

## 测试用例数据

文件：{data.get('file', '未知')}
格式：{data.get('format', '未知')}
用例总数：{len(cases)}

## 本次评审的必备条件配置

本次评审共收集一次必备条件配置，统一应用于所有 {len(cases)} 个用例：

{chr(10).join([f"- {name}: {status}" for name, status in prereq_stats.items()])}

## 用例列表

{cases_json}

## 评审要求

本次评审启用了以下必备条件校验：
{chr(10).join([f"- {name}" for name in enabled_names]) if enabled_names else "无"}

请按照评审标准进行详细分析，并以JSON格式输出评审结果。
"""
    
    print(f"\n正在调用通义千问大模型进行智能评审...")
    print(f"用例总数: {len(cases)}")
    print(f"必备条件覆盖率:")
    for name, count in prereq_stats.items():
        print(f"  - {name}: {count}")
    
    # 调用通义千问
    response = llm_client.chat(base_prompt, user_message, temperature=0.3)
    
    # 解析JSON结果
    try:
        # 提取JSON部分
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            result_json = json_match.group(1)
        else:
            # 尝试直接解析
            result_json = response
        
        result = json.loads(result_json)
        return result
    
    except json.JSONDecodeError as e:
        print(f"⚠️  大模型返回格式异常，尝试修复...")
        # 尝试提取关键信息
        return {
            "summary": {
                "total_cases": len(cases),
                "quality_score": 50,
                "overall_assessment": "待改进",
                "critical_issues": 0,
                "warning_issues": 0,
                "suggestions": 0
            },
            "issues": [],
            "coverage_analysis": {
                "requirement_coverage": "无法解析",
                "scenario_coverage": {"normal": "未知", "exception": "未知", "boundary": "未知"},
                "missing_scenarios": [],
                "security_coverage": "未知",
                "concurrency_coverage": "未知"
            },
            "conclusion": {
                "result": "有条件通过",
                "reason": "大模型返回格式异常，请手动审核",
                "priority_actions": ["检查大模型API配置", "查看原始响应"]
            },
            "_raw_response": response
        }


def generate_report(review_result: dict, data: dict, prerequisites: dict) -> str:
    """生成Markdown格式的审核报告"""
    
    summary = review_result.get("summary", {})
    issues = review_result.get("issues", [])
    coverage = review_result.get("coverage_analysis", {})
    conclusion = review_result.get("conclusion", {})
    
    cases = data.get('cases', [])
    total_cases = len(cases)
    
    # 构造报告
    report = []
    report.append("# 测试用例智能审核报告")
    report.append("")
    report.append(f"> 文件：`{data.get('file', '未知')}` ({data.get('format', '未知')})  ")
    report.append(f"> 审核时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    report.append(f"> 审核模型：**通义千问 (Qwen-Plus)**  ")
    report.append(f"> 用例总数：**{total_cases}** 条")
    report.append("")
    
    # 必备条件统计
    report.append("## 🔧 评审配置统计")
    report.append("")
    report.append("本次评审只收集一次必备条件配置，统一应用于所有用例：")
    report.append("")
    report.append("| 必备条件 | 状态 |")
    report.append("|----------|------|")
    
    for item in PREREQUISITE_ITEMS:
        enabled = prerequisites.get(item['id'], False)
        status = "✅ 启用" if enabled else "⏭️  跳过"
        report.append(f"| {item['name']} | {status} |")
    report.append("")
    
    # 审核总览
    score = summary.get('quality_score', 0)
    score_emoji = "🟢" if score >= 90 else "🟡" if score >= 70 else "🟠" if score >= 50 else "🔴"
    
    report.append("## 📊 审核总览")
    report.append("")
    report.append("| 指标 | 数值 |")
    report.append("|------|------|")
    report.append(f"| 综合评分 | {score_emoji} **{score}/100** ({summary.get('overall_assessment', '未知')}) |")
    report.append(f"| 用例总数 | {summary.get('total_cases', 0)} |")
    report.append(f"| 严重问题 | 🔴 {summary.get('critical_issues', 0)} |")
    report.append(f"| 警告问题 | 🟡 {summary.get('warning_issues', 0)} |")
    report.append(f"| 优化建议 | 💡 {summary.get('suggestions', 0)} |")
    report.append("")
    
    # 问题清单
    if issues:
        report.append("## 🔍 问题清单")
        report.append("")
        
        # 按严重程度分组
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        warning_issues = [i for i in issues if i.get('severity') == 'warning']
        suggestion_issues = [i for i in issues if i.get('severity') == 'suggestion']
        
        # 严重问题
        if critical_issues:
            report.append(f"### 🔴 严重问题（{len(critical_issues)} 个）")
            report.append("")
            report.append("| # | 用例ID | 维度 | 字段 | 问题描述 | 改进建议 |")
            report.append("|---|--------|------|------|----------|----------|")
            for idx, issue in enumerate(critical_issues, 1):
                report.append(f"| {idx} | `{issue.get('case_id', '?')}` | "
                            f"{issue.get('dimension', '-')} | {issue.get('field', '-')} | "
                            f"{issue.get('description', '-')} | {issue.get('suggestion', '-')} |")
            report.append("")
        
        # 警告问题
        if warning_issues:
            report.append(f"### 🟡 警告问题（{len(warning_issues)} 个）")
            report.append("")
            report.append("| # | 用例ID | 维度 | 字段 | 问题描述 | 改进建议 |")
            report.append("|---|--------|------|------|----------|----------|")
            for idx, issue in enumerate(warning_issues, 1):
                report.append(f"| {idx} | `{issue.get('case_id', '?')}` | "
                            f"{issue.get('dimension', '-')} | {issue.get('field', '-')} | "
                            f"{issue.get('description', '-')} | {issue.get('suggestion', '-')} |")
            report.append("")
        
        # 优化建议
        if suggestion_issues:
            report.append(f"### 💡 优化建议（{len(suggestion_issues)} 个）")
            report.append("")
            report.append("| # | 用例ID | 维度 | 建议描述 |")
            report.append("|---|--------|------|----------|")
            for idx, issue in enumerate(suggestion_issues, 1):
                report.append(f"| {idx} | `{issue.get('case_id', '?')}` | "
                            f"{issue.get('dimension', '-')} | {issue.get('suggestion', '-')} |")
            report.append("")
    
    # 覆盖率分析
    report.append("## 📈 覆盖率分析")
    report.append("")
    report.append("### 场景覆盖率")
    report.append("")
    scenario = coverage.get('scenario_coverage', {})
    report.append(f"- **正常场景**：{scenario.get('normal', '未知')}")
    report.append(f"- **异常场景**：{scenario.get('exception', '未知')}")
    report.append(f"- **边界场景**：{scenario.get('boundary', '未知')}")
    report.append("")
    report.append(f"### 需求覆盖")
    report.append(f"{coverage.get('requirement_coverage', '未知')}")
    report.append("")
    
    # 安全场景覆盖
    if prerequisites.get('security_basic', False):
        report.append(f"### 安全场景覆盖")
        report.append(f"{coverage.get('security_coverage', '未知')}")
        report.append("")
    
    # 并发场景覆盖
    concurrency_enabled = (prerequisites.get('concurrency_conflict', False) or 
                          prerequisites.get('duplicate_submit', False) or 
                          prerequisites.get('idempotency', False))
    if concurrency_enabled:
        report.append(f"### 并发场景覆盖")
        report.append(f"{coverage.get('concurrency_coverage', '未知')}")
        report.append("")
    
    # 缺失场景
    missing = coverage.get('missing_scenarios', [])
    if missing:
        report.append("### ⚠️ 缺失的关键场景")
        report.append("")
        for item in missing:
            report.append(f"- {item}")
        report.append("")
    
    # 评审结论
    result = conclusion.get('result', '未知')
    result_emoji = "✅" if result == "通过" else "⚠️" if result == "有条件通过" else "❌"
    
    report.append("## 🎯 评审结论")
    report.append("")
    report.append(f"### {result_emoji} {result}")
    report.append("")
    report.append(f"**原因**：{conclusion.get('reason', '未知')}")
    report.append("")
    
    priority_actions = conclusion.get('priority_actions', [])
    if priority_actions:
        report.append("### 📋 优先改进项")
        report.append("")
        for idx, action in enumerate(priority_actions, 1):
            report.append(f"{idx}. {action}")
        report.append("")
    
    # 必备条件配置详情
    enabled_names = [item['name'] for item in PREREQUISITE_ITEMS if prerequisites.get(item['id'], False)]
    must_check = ", ".join(enabled_names) if enabled_names else "无"
    
    report.append("## 📋 必备条件配置")
    report.append("")
    report.append(f"本次评审收集一次必备条件，统一应用于所有用例：")
    report.append(f"**必须校验项**：{must_check}")
    report.append("")
    
    report.append("---")
    report.append("*本报告由 testcase-reviewer skill (通义千问版 - 智能批量收集) 自动生成*")
    
    return "\n".join(report)


def main():
    if len(sys.argv) < 2:
        print("用法: py review_testcases_llm.py <file.json> [--output <report.md>] [--skip-collect]")
        print("\n参数：")
        print("  --output: 指定输出报告文件路径")
        print("  --skip-collect: 跳过必备条件收集，使用上次配置")
        print("\n环境变量：")
        print("  ALI_QWEN_API_KEY: 阿里云通义千问API密钥")
        print("\n获取API密钥：")
        print("  https://dashscope.console.aliyun.com/apiKey")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = None
    skip_collect = False
    
    # 解析参数
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]
    
    skip_collect = "--skip-collect" in sys.argv
    
    # 加载测试用例数据
    ext = os.path.splitext(input_path)[1].lower()
    
    if ext == ".json":
        with open(input_path, "rb") as f:
            data = json.load(f)
    else:
        print(f"⚠️  暂不支持直接解析 {ext} 文件，请先使用解析脚本转换为 JSON")
        print("   - CSV: py parse_csv.py <file.csv>")
        print("   - XMind: py parse_xmind.py <file.xmind>")
        print("   - Excel: py parse_excel.py <file.xlsx>")
        sys.exit(1)
    
    if not data.get("cases"):
        print("⚠️  未解析到任何用例数据")
        for w in data.get("warnings", []):
            print(f"   - {w}")
        sys.exit(1)
    
    # 初始化通义千问客户端
    try:
        llm_client = QwenClient()
    except Exception as e:
        print(f"❌ 初始化通义千问客户端失败: {e}")
        sys.exit(1)
    
    # 收集必备条件
    script_dir = Path(__file__).parent
    config_file = script_dir.parent / ".review_config.json"
    
    if skip_collect:
        # 尝试从配置文件加载
        prerequisites = load_prerequisites_from_file(str(config_file))
        if not prerequisites:
            print("⚠️  未找到历史配置，开始智能收集...")
            prerequisites = collect_prerequisites_batch(data['cases'])
    else:
        # 尝试从配置文件加载历史配置
        saved_prerequisites = load_prerequisites_from_file(str(config_file))
        if saved_prerequisites:
            print("\n📋 检测到历史配置，是否使用？")
            print("   输入 'y' 使用历史配置，输入 'n' 重新收集")
            try:
                choice = input("选择 [y/N]: ").strip().lower()
                if choice in ['y', 'yes', '是']:
                    prerequisites = saved_prerequisites
                    print("✅ 使用历史配置")
                else:
                    prerequisites = collect_prerequisites_batch(data['cases'])
            except (EOFError, KeyboardInterrupt):
                print("\n使用历史配置")
                prerequisites = saved_prerequisites
        else:
            # 交互式收集
            prerequisites = collect_prerequisites_batch(data['cases'])
        
        # 保存配置
        save_prerequisites_to_file(prerequisites, str(config_file))
    
    # 执行审核
    review_result = review_with_llm(data, llm_client, prerequisites)
    
    # 生成报告
    report_md = generate_report(review_result, data, prerequisites)
    
    # 输出结果
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"\n✅ 审核完成！")
        print(f"   使用模型: 通义千问 (Qwen-Plus)")
        print(f"   质量评分: {review_result['summary']['quality_score']}/100")
        print(f"   评审结论: {review_result['conclusion']['result']}")
        print(f"   报告已保存到: {output_path}")
    else:
        print("\n" + report_md)


if __name__ == "__main__":
    main()
