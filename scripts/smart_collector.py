#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能必备条件收集器

核心功能：
1. 智能检测用例集整体是否需要某些必备条件
2. 针对整个评审任务收集一次必备条件
3. 支持配置保存与复用
"""

import sys
import json
import re
from typing import Dict, List, Optional, Tuple

# 设置Windows控制台输出编码为UTF-8
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass  # 忽略编码设置错误


# ──────────────────────────────────────────────────────────────
# 必备条件定义（无默认值，依赖智能检测或用户确认）
# ──────────────────────────────────────────────────────────────

PREREQUISITE_ITEMS = [
    {
        "id": "security_basic",
        "name": "基础安全校验",
        "description": "权限控制（水平/垂直越权、未授权访问）、敏感信息处理（脱敏、日志安全）",
        "examples": [
            "用户A能否访问用户B的订单数据（水平越权）",
            "普通用户能否执行管理员操作（垂直越权）",
            "未登录用户能否访问需鉴权接口",
            "手机号、身份证等敏感信息是否脱敏展示"
        ],
        # 智能检测关键词（用于自动识别用例是否已包含相关信息）
        "keywords": [
            "越权", "权限", "脱敏", "敏感信息", "身份证", "手机号", 
            "未授权", "鉴权", "登录校验", "权限控制", "水平越权",
            "垂直越权", "数据脱敏", "信息脱敏", "隐私保护"
        ]
    },
    {
        "id": "concurrency_conflict",
        "name": "并发冲突",
        "description": "多人同时操作同一资源时的处理机制（如抢购、抢号、并发修改）",
        "examples": [
            "100人同时抢购最后1件商品",
            "多人同时修改同一条数据",
            "并发场景下的库存扣减"
        ],
        "keywords": [
            "并发", "冲突", "抢购", "抢号", "并发修改", "同时操作",
            "竞争条件", "乐观锁", "悲观锁", "分布式锁", "库存扣减",
            "高并发", "并发控制", "资源竞争"
        ]
    },
    {
        "id": "duplicate_submit",
        "name": "重复提交",
        "description": "用户快速点击、网络重试等导致的重复提交问题",
        "examples": [
            "快速点击提交按钮生成重复订单",
            "支付回调重复通知",
            "表单重复提交"
        ],
        "keywords": [
            "重复提交", "防抖", "节流", "重复点击", "重复订单",
            "重复请求", "防重复", "幂等", "重复支付", "重复回调",
            "快速点击", "网络重试"
        ]
    },
    {
        "id": "idempotency",
        "name": "幂等性",
        "description": "同一请求重复发送，系统保证结果一致的机制",
        "examples": [
            "支付接口重复调用",
            "订单创建接口幂等性",
            "API重试机制"
        ],
        "keywords": [
            "幂等", "幂等性", "重复调用", "重试", "接口幂等",
            "请求幂等", "幂等性验证", "幂等设计", "重复结果",
            "多次请求", "结果一致"
        ]
    },
    {
        "id": "data_consistency",
        "name": "数据一致性",
        "description": "分布式事务、状态机异常、跨系统数据同步等一致性保障",
        "examples": [
            "支付成功但订单状态未更新",
            "库存扣减与订单创建的一致性",
            "分布式事务回滚"
        ],
        "keywords": [
            "数据一致性", "分布式事务", "状态机", "事务回滚",
            "跨系统", "数据同步", "一致性校验", "事务一致性",
            "状态一致", "数据同步", "最终一致性", "强一致性",
            "状态流转", "状态异常"
        ]
    },
    {
        "id": "performance_risk",
        "name": "性能风险",
        "description": "高并发、大数据量、响应时间敏感等性能需求",
        "examples": [
            "接口响应时间要求（如<1s）",
            "高并发场景（如1000 QPS）",
            "大数据量查询优化"
        ],
        "keywords": [
            "性能", "响应时间", "高并发", "大数据量", "QPS", "TPS",
            "延迟", "耗时", "加载时间", "性能优化", "慢查询",
            "性能测试", "压力测试", "负载测试", "响应慢"
        ]
    },
    {
        "id": "compatibility_risk",
        "name": "兼容性风险",
        "description": "浏览器、设备、操作系统、分辨率等兼容性需求",
        "examples": [
            "多浏览器兼容（Chrome/Safari/Firefox）",
            "移动端适配",
            "不同操作系统兼容"
        ],
        "keywords": [
            "兼容性", "浏览器", "移动端", "设备", "操作系统",
            "分辨率", "适配", "Chrome", "Safari", "Firefox",
            "iOS", "Android", "跨平台", "兼容测试", "适配测试"
        ]
    },
    {
        "id": "third_party_dependency",
        "name": "第三方依赖",
        "description": "核心流程依赖第三方服务的场景及异常处理",
        "examples": [
            "支付渠道异常（微信/支付宝接口故障）",
            "短信服务不可用",
            "第三方API超时"
        ],
        "keywords": [
            "第三方", "外部服务", "依赖", "微信", "支付宝",
            "短信", "API", "外部接口", "服务降级", "熔断",
            "第三方异常", "外部依赖", "服务不可用"
        ]
    },
    {
        "id": "business_security",
        "name": "业务安全",
        "description": "业务逻辑安全，如超卖、价格篡改、优惠券滥用等",
        "examples": [
            "并发抢购超卖问题",
            "订单金额篡改",
            "优惠券重复使用"
        ],
        "keywords": [
            "超卖", "价格篡改", "优惠券", "业务安全", "金额篡改",
            "库存超卖", "优惠滥用", "套利", "业务漏洞",
            "价格异常", "订单金额", "库存异常",
            "理赔", "打款", "支付", "退款", "发票", "处方"
        ]
    }
]


# ──────────────────────────────────────────────────────────────
# 智能检测函数
# ──────────────────────────────────────────────────────────────

def detect_prerequisite_in_case(testcase: Dict, prereq_id: str) -> Tuple[bool, str]:
    """
    智能检测测试用例是否包含某个必备条件的相关信息
    
    Args:
        testcase: 测试用例数据
        prereq_id: 必备条件ID
        
    Returns:
        Tuple[bool, str]: (是否检测到, 匹配的关键词或原因)
    """
    # 查找必备条件配置
    prereq = next((item for item in PREREQUISITE_ITEMS if item['id'] == prereq_id), None)
    if not prereq:
        return False, "未找到必备条件配置"
    
    keywords = prereq.get('keywords', [])
    if not keywords:
        return False, "未配置关键词"
    
    # 合并用例所有文本字段
    text_fields = []
    for field in ['title', 'module', 'path', 'steps', 'expected', 'remarks', 'tags']:
        value = testcase.get(field, '')
        if value and isinstance(value, str):
            text_fields.append(value)
    
    combined_text = ' '.join(text_fields)
    
    # 检测关键词匹配
    matched_keywords = []
    for keyword in keywords:
        # 使用正则表达式进行不区分大小写的匹配
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        if pattern.search(combined_text):
            matched_keywords.append(keyword)
    
    if matched_keywords:
        return True, f"检测到关键词: {', '.join(matched_keywords[:3])}"
    
    return False, "未检测到相关关键词"


def analyze_case_prerequisites(testcase: Dict) -> Dict[str, Tuple[bool, str]]:
    """
    分析单个测试用例的所有必备条件
    
    Args:
        testcase: 测试用例数据
        
    Returns:
        Dict[str, Tuple[bool, str]]: 每个必备条件的检测结果
    """
    results = {}
    for item in PREREQUISITE_ITEMS:
        detected, reason = detect_prerequisite_in_case(testcase, item['id'])
        results[item['id']] = (detected, reason)
    return results


# ──────────────────────────────────────────────────────────────
# 交互式收集函数
# ──────────────────────────────────────────────────────────────

def ask_prerequisite(item: Dict, detected: bool, reason: str) -> bool:
    """
    交互式询问用户是否需要校验某个必备条件
    
    Args:
        item: 必备条件配置
        detected: 是否自动检测到（ALL 标记时调用方传入 False）
        reason: 检测原因或未检测到的原因
        
    Returns:
        bool: 是否需要校验
    """
    keywords = item.get('keywords', [])
    force_ask = 'ALL' in [kw.upper() for kw in keywords]
    
    print(f"\n{'─'*70}")
    print(f"🔍 检查项: {item['name']}")
    print(f"📝 说明: {item['description']}")
    
    if force_ask:
        # ALL 标记：始终询问，不做自动判定
        print(f"🔖 ALL 标记: 此项已配置为始终询问，由用户决定是否校验")
        print(f"   智能检测参考: {reason}")
        print(f"   示例场景：")
        for example in item['examples'][:2]:
            print(f"   • {example}")
    elif detected:
        print(f"✅ 智能检测: {reason}")
        print(f"   系统检测到用例中包含相关信息，将自动纳入评审。")
        return True
    else:
        print(f"❓ 检测结果: {reason}")
        print(f"   示例场景：")
        for example in item['examples'][:2]:
            print(f"   • {example}")
    
    # 交互式询问
    while True:
        try:
            answer = input(f"\n   本次评审是否需要校验此项？[y/n]: ").strip().lower()
            
            if answer in ['y', 'yes', '是', '需要']:
                return True
            elif answer in ['n', 'no', '否', '不需要', '']:
                return False
            else:
                print("   ❌ 输入无效，请输入 y/n")
        except KeyboardInterrupt:
            print("\n\n❌ 用户取消操作")
            sys.exit(1)
        except EOFError:
            # 非交互模式，默认不需要
            return False


def analyze_all_cases_prerequisites(testcases: List[Dict]) -> Dict[str, Tuple[bool, str]]:
    """
    分析整个用例集的必备条件（合并检测所有用例）
    
    Args:
        testcases: 测试用例列表
        
    Returns:
        Dict[str, Tuple[bool, str]]: 每个必备条件的检测结果
    """
    results = {}
    
    for item in PREREQUISITE_ITEMS:
        prereq_id = item['id']
        keywords = item.get('keywords', [])
        
        # 在所有用例中检测关键词
        matched_cases = []
        
        for testcase in testcases:
            # 合并用例所有文本字段
            text_fields = []
            for field in ['title', 'module', 'path', 'steps', 'expected', 'remarks', 'tags']:
                value = testcase.get(field, '')
                if value and isinstance(value, str):
                    text_fields.append(value)
            
            combined_text = ' '.join(text_fields)
            
            # 检测关键词匹配
            for keyword in keywords:
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                if pattern.search(combined_text):
                    case_id = testcase.get('id', '未知')
                    case_title = testcase.get('title', '无标题')[:20]
                    matched_cases.append(f"{case_id}: {keyword}")
                    break  # 一个用例只需记录一次
        
        if matched_cases:
            # 显示匹配的前3个用例
            display_matches = matched_cases[:3]
            reason = f"在 {len(matched_cases)} 个用例中检测到相关关键词: {', '.join(display_matches)}"
            results[prereq_id] = (True, reason)
        else:
            results[prereq_id] = (False, "未在任何用例中检测到相关关键词")
    
    return results


def collect_prerequisites_batch(testcases: List[Dict]) -> Dict[str, bool]:
    """
    批量收集整个评审任务的必备条件（只收集一次）
    
    Args:
        testcases: 测试用例列表
        
    Returns:
        Dict[str, bool]: 必备条件配置（全局配置，应用于所有用例）
    """
    total_cases = len(testcases)
    
    print("\n" + "="*70)
    print("📋 测试用例智能评审 - 必备条件收集")
    print("="*70)
    print(f"\n共 {total_cases} 条测试用例，本次评审只收集一次必备条件...")
    print("   （各用例的必备条件配置将统一应用）\n")
    
    # 分析整个用例集
    analysis = analyze_all_cases_prerequisites(testcases)
    
    # 收集结果（全局配置）
    results = {}
    
    print(f"\n{'='*70}")
    print(f"【批量检测】智能分析用例集")
    print(f"{'='*70}")
    
    for idx, item in enumerate(PREREQUISITE_ITEMS, 1):
        detected, reason = analysis[item['id']]
        keywords = item.get('keywords', [])
        
        # ALL 特殊标记：不管是否检测到关键词，都强制询问用户
        force_ask = 'ALL' in [kw.upper() for kw in keywords]
        
        # 显示检测结果
        print(f"\n[{idx}/{len(PREREQUISITE_ITEMS)}] {item['name']}")
        if force_ask:
            print(f"  🔖 已配置 ALL 标记，始终询问用户确认")
            if detected:
                print(f"  ✅ {reason}")
            else:
                print(f"  ❌ {reason}")
        elif detected:
            print(f"  ✅ {reason}")
        else:
            print(f"  ❌ {reason}")
        
        # 交互式询问（ALL 标记时强制询问，不做自动判定）
        need_check = ask_prerequisite(item, detected if not force_ask else False, reason)
        results[item['id']] = need_check
        
        status = "✅ 需要校验" if need_check else "⏭️  跳过校验"
        print(f"\n   → {status}")
    
    # 显示收集结果摘要
    print_summary(results, total_cases)
    
    return results


def print_summary(results: Dict[str, bool], total_cases: int):
    """打印收集结果摘要"""
    print("\n" + "="*70)
    print("📊 收集结果摘要")
    print("="*70)
    
    enabled_count = sum(1 for v in results.values() if v)
    disabled_count = sum(1 for v in results.values() if not v)
    
    print(f"\n启用校验: {enabled_count} 项")
    print(f"跳过校验: {disabled_count} 项")
    print(f"\n启用项目：")
    for item in PREREQUISITE_ITEMS:
        if results.get(item['id'], False):
            print(f"  ✅ {item['name']}")
    
    if disabled_count > 0:
        print(f"\n跳过项目：")
        for item in PREREQUISITE_ITEMS:
            if not results.get(item['id'], False):
                print(f"  ⏭️  {item['name']}")
    
    print("\n" + "="*70)


# ──────────────────────────────────────────────────────────────
# 配置文件操作
# ──────────────────────────────────────────────────────────────

def save_prerequisites_to_file(results: Dict[str, bool], config_file: str):
    """保存必备条件配置到文件"""
    try:
        config = {
            'version': '3.0',
            'mode': 'per_review',
            'prerequisites': results
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 配置已保存到: {config_file}")
    except Exception as e:
        print(f"\n⚠️  保存配置失败: {e}")


def load_prerequisites_from_file(config_file: str) -> Optional[Dict[str, bool]]:
    """从文件加载必备条件配置"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            if 'prerequisites' in config:
                return config['prerequisites']
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────────────────────
# 主函数（用于测试）
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 测试用例示例
    test_case = {
        "id": "TC-0001",
        "title": "搜索医院/医生",
        "module": "挂号业务",
        "steps": "用户输入关键词搜索",
        "expected": "返回搜索结果",
        "remarks": "需要验证权限控制和敏感信息脱敏"
    }
    
    # 测试智能检测
    print("测试智能检测功能：")
    analysis = analyze_case_prerequisites(test_case)
    for prereq_id, (detected, reason) in analysis.items():
        prereq = next(item for item in PREREQUISITE_ITEMS if item['id'] == prereq_id)
        status = "✅" if detected else "❌"
        print(f"{status} {prereq['name']}: {reason}")
