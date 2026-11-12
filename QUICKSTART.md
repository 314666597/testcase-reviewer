# 快速开始指南

## 安装依赖

```bash
# 基础依赖
pip install openpyxl pandas python-xmind defusedxml

# 通义千问SDK
pip install dashscope -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 配置API密钥

```bash
# Windows PowerShell
$env:ALI_QWEN_API_KEY="your-api-key-here"

# Linux/macOS
export ALI_QWEN_API_KEY="your-api-key"
```

**获取API密钥**：https://dashscope.console.aliyun.com/apiKey

## 快速开始

### 1. 评审XMind文件

```bash
# 先解析XMind文件
py scripts/parse_xmind.py test.xmind > test.json

# 执行智能审核（会交互式收集必备条件）
py scripts/review_testcases_llm.py test.json --output report.md
```

### 2. 评审Excel文件

```bash
# 先解析Excel文件
py scripts/parse_excel.py test.xlsx > test.json

# 执行智能审核
py scripts/review_testcases_llm.py test.json
```

### 3. 评审CSV文件

```bash
# 先解析CSV文件
py scripts/parse_csv.py test.csv > test.json

# 执行智能审核
py scripts/review_testcases_llm.py test.json
```

## 智能逐用例收集示例

### 示例1：用例已包含必备条件信息

**用例内容**：
```json
{
  "id": "TC-0001",
  "title": "订单退款（需验证权限控制和敏感信息脱敏）",
  "steps": "用户申请退款，管理员审核",
  "expected": "退款成功，订单状态更新"
}
```

**智能检测过程**：
```
【1/25】TC-0001 - 订单退款
──────────────────────────────────────────────────────────────────────────
📋 用例: TC-0001 - 订单退款
🔍 检查项: 基础安全校验
📝 说明: 权限控制、敏感信息处理

✅ 智能检测: 检测到关键词: 权限, 脱敏
   系统检测到用例中包含相关信息，将自动纳入评审。
   → ✅ 需要校验
```

### 示例2：用例未包含必备条件信息

**用例内容**：
```json
{
  "id": "TC-0002",
  "title": "搜索医院",
  "steps": "用户输入关键词搜索",
  "expected": "返回搜索结果"
}
```

**智能检测过程**：
```
【2/25】TC-0002 - 搜索医院
──────────────────────────────────────────────────────────────────────────
📋 用例: TC-0002 - 搜索医院
🔍 检查项: 基础安全校验
📝 说明: 权限控制、敏感信息处理

❓ 检测结果: 未检测到相关关键词
   示例场景：
   • 用户A能否访问用户B的订单数据（水平越权）
   • 普通用户能否执行管理员操作（垂直越权）

   是否需要校验此项？[y/n]: y
   → ✅ 需要校验
```

## 工作流程详解

### Step 1: 解析文件

根据文件类型选择对应的解析脚本：

```bash
# XMind
py scripts/parse_xmind.py your_file.xmind

# Excel
py scripts/parse_excel.py your_file.xlsx

# CSV
py scripts/parse_csv.py your_file.csv
```

解析后会输出标准化的JSON格式：

```json
{
  "format": "xmind",
  "file": "your_file.xmind",
  "total": 25,
  "fields": ["id", "title", "module", "steps", "expected", ...],
  "cases": [
    {
      "id": "TC-0001",
      "title": "测试用例标题",
      "module": "所属模块",
      "steps": "测试步骤",
      "expected": "预期结果",
      ...
    }
  ]
}
```

### Step 2: 智能收集必备条件

系统会针对每个测试用例进行智能检测和收集：

```
📋 测试用例智能评审 - 必备条件收集
======================================================================

共 25 条测试用例，开始逐个收集必备条件...

======================================================================
【1/25】TC-0001 - 搜索医院/医生
======================================================================

──────────────────────────────────────────────────────────────────────────
📋 用例: TC-0001 - 搜索医院/医生
🔍 检查项: 基础安全校验
📝 说明: 权限控制、敏感信息处理

❓ 检测结果: 未检测到相关关键词
   示例场景：
   • 用户A能否访问用户B的订单数据（水平越权）
   • 普通用户能否执行管理员操作（垂直越权）

   是否需要校验此项？[y/n]: 
```

**快捷操作**：
- 输入 `y` 或 `yes` → 需要校验
- 输入 `n` 或 `no` → 跳过校验
- 直接回车 → 默认跳过校验

### Step 3: 生成审核报告

审核完成后会生成详细的Markdown报告：

```markdown
# 测试用例智能审核报告

## 🔧 评审配置统计

| 必备条件 | 覆盖用例数 | 覆盖率 |
|----------|------------|--------|
| 基础安全校验 | 20/25 | 80.0% |
| 并发冲突 | 5/25 | 20.0% |
| ...

## 📊 审核总览

| 指标 | 数值 |
|------|------|
| 综合评分 | 🟡 75/100 (良好) |
| 用例总数 | 25 |
| ...
```

## 高级用法

### 1. 使用历史配置

```bash
# 使用上次保存的配置（跳过收集）
py scripts/review_testcases_llm.py test.json --skip-collect
```

### 2. 重新收集必备条件

```bash
# 不使用 --skip-collect，系统会询问是否使用历史配置
py scripts/review_testcases_llm.py test.json

# 输出：
# 📋 检测到历史配置，是否使用？
#    输入 'y' 使用历史配置，输入 'n' 重新收集
# 选择 [y/N]: n
```

### 3. 指定输出文件

```bash
py scripts/review_testcases_llm.py test.json --output my_report.md
```

## 最佳实践

### 1. 在用例中明确提及必备条件

**推荐做法**：
```
标题：订单退款（需验证权限控制和敏感信息脱敏）
步骤：用户申请退款，管理员审核
预期：退款成功，订单状态更新，敏感信息已脱敏
备注：需验证水平越权和垂直越权
```

**优点**：
- ✅ 系统自动识别，无需交互询问
- ✅ 提高评审效率
- ✅ 用例描述更清晰

### 2. 合理选择必备条件

**电商秒杀场景**：
- ✅ 基础安全校验
- ✅ 并发冲突（抢购场景）
- ✅ 重复提交
- ✅ 幂等性
- ✅ 数据一致性
- ✅ 性能风险
- ⏭️  兼容性风险（可选）
- ✅ 第三方依赖
- ✅ 业务安全（超卖问题）

**内部管理系统**：
- ✅ 基础安全校验
- ⏭️  并发冲突（内部系统并发低）
- ✅ 重复提交
- ✅ 幂等性
- ✅ 数据一致性
- ⏭️  性能风险（内部系统性能要求低）
- ⏭️  兼容性风险（可选）
- ✅ 第三方依赖
- ✅ 业务安全

### 3. 保存配置避免重复收集

首次评审后，配置会保存到 `.review_config.json`：

```json
{
  "version": "2.0",
  "mode": "per_case",
  "prerequisites": {
    "TC-0001": {
      "security_basic": true,
      "concurrency_conflict": false,
      ...
    },
    "TC-0002": {
      ...
    }
  }
}
```

下次评审时可选择使用历史配置。

## 故障排查

### 问题1：API密钥未配置

**错误信息**：
```
❌ 初始化通义千问客户端失败: 未检测到通义千问API密钥
```

**解决方案**：
```bash
# Windows PowerShell
$env:ALI_QWEN_API_KEY="your-api-key"

# Linux/macOS
export ALI_QWEN_API_KEY="your-api-key"
```

### 问题2：缺少依赖包

**错误信息**：
```
ModuleNotFoundError: No module named 'dashscope'
```

**解决方案**：
```bash
pip install dashscope -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题3：文件解析失败

**错误信息**：
```
⚠️  未解析到任何用例数据
```

**解决方案**：
1. 检查文件格式是否正确
2. 确认文件未损坏
3. 查看解析脚本输出的警告信息

### 问题4：JSON解析失败

**错误信息**：
```
⚠️  大模型返回格式异常，尝试修复...
```

**解决方案**：
1. 检查网络连接
2. 稍后重试
3. 查看报告中 `_raw_response` 字段的原始响应

## 获取帮助

如有问题或建议：
- 查看 `SKILL.md` 获取完整功能说明
- 查看 `references/review_standards.md` 了解评审标准
- 查看生成的审核报告中的详细问题清单
