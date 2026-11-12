# 测试用例智能审核技能 (Testcase Reviewer)

基于阿里云通义千问大模型的测试用例智能评审工具，支持 CSV、XMind、Excel 三种格式。

## ✨ 核心特性

- 🎯 **智能逐用例收集**：针对每个测试用例智能检测和收集必备条件
- 🧠 **自动识别已包含信息**：用例已提及 → 直接使用，未提及 → 问卷收集
- 🔒 **智能识别安全风险**：自动发现权限漏洞、敏感信息泄露等安全隐患
- ⚡ **并发问题检测**：识别并发冲突、幂等性问题等常见陷阱
- 💡 **专业改进建议**：提供具体的改进示例和最佳实践
- 📊 **7大维度评审**：全面覆盖测试用例质量的关键方面

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install openpyxl pandas python-xmind defusedxml dashscope
```

### 2. 配置API密钥

```bash
# Windows PowerShell
$env:ALI_QWEN_API_KEY="your-api-key-here"

# Linux/macOS
export ALI_QWEN_API_KEY="your-api-key"
```

获取API密钥：https://dashscope.console.aliyun.com/apiKey

### 3. 运行审核

```bash
# 解析XMind文件
py scripts/parse_xmind.py test.xmind > test.json

# 执行智能审核
py scripts/review_testcases_llm.py test.json --output report.md
```

## 📋 智能逐用例收集

### 核心理念

**不使用默认值配置，而是针对每个测试用例智能判断：**

1. **智能检测**：分析用例内容，判断是否已包含必备条件相关信息
2. **自动使用**：如果用例已提及 → 自动标记为"需要校验"
3. **问卷收集**：如果用例未提及 → 交互式询问用户

### 示例

**用例内容**：
```
标题：订单退款（需验证权限控制和敏感信息脱敏）
```

**智能检测**：
```
✅ 智能检测: 检测到关键词: 权限, 脱敏
   系统检测到用例中包含相关信息，将自动纳入评审。
   → ✅ 需要校验
```

## 📊 必备条件列表

| 检查项 | 说明 | 智能检测关键词 |
|--------|------|----------------|
| **基础安全校验** | 权限控制、敏感信息处理 | 越权、权限、脱敏、敏感信息... |
| **并发冲突** | 多人同时操作同一资源 | 并发、冲突、抢购、乐观锁... |
| **重复提交** | 快速点击、网络重试 | 重复提交、防抖、重复点击... |
| **幂等性** | 请求重复发送的一致性 | 幂等、重复调用、重试... |
| **数据一致性** | 分布式事务、状态机 | 数据一致性、分布式事务... |
| **性能风险** | 高并发、大数据量 | 性能、响应时间、QPS... |
| **兼容性风险** | 浏览器、设备兼容 | 兼容性、浏览器、移动端... |
| **第三方依赖** | 第三方服务异常 | 第三方、微信、支付宝... |
| **业务安全** | 超卖、价格篡改 | 超卖、价格篡改、优惠券... |

## 📁 项目结构

```
testcase-reviewer/
├── scripts/                      # 脚本目录
│   ├── parse_csv.py              # CSV解析器
│   ├── parse_excel.py            # Excel解析器
│   ├── parse_xmind.py            # XMind解析器
│   ├── smart_collector.py        # 智能逐用例收集器 ⭐ NEW
│   └── review_testcases_llm.py   # 通义千问审核引擎
│
├── references/                   # 参考文档
│   ├── review_standards.md       # 评审标准详解
│   ├── review_prompt.md          # 大模型提示词模板
│   └── field_definitions.md      # 字段定义说明
│
├── .review_config.json.example   # 配置文件示例
├── .gitignore                    # Git忽略文件
│
├── SKILL.md                      # 完整功能说明
├── QUICKSTART.md                 # 快速开始指南
├── UPGRADE_SUMMARY.md            # 版本更新说明
└── README.md                     # 项目文档（本文件）
```

## 🔧 使用方法

### 评审XMind文件

```bash
py scripts/parse_xmind.py test.xmind > test.json
py scripts/review_testcases_llm.py test.json --output report.md
```

### 评审Excel文件

```bash
py scripts/parse_excel.py test.xlsx > test.json
py scripts/review_testcases_llm.py test.json
```

### 评审CSV文件

```bash
py scripts/parse_csv.py test.csv > test.json
py scripts/review_testcases_llm.py test.json
```

### 使用历史配置

```bash
py scripts/review_testcases_llm.py test.json --skip-collect
```

## 📈 审核报告示例

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
| 严重问题 | 🔴 5 |
| 警告问题 | 🟡 10 |
| 优化建议 | 💡 8 |

## 🔍 问题清单

### 🔴 严重问题（5 个）

| # | 用例ID | 维度 | 问题描述 | 改进建议 |
|---|--------|------|----------|----------|
| 1 | TC-0001 | 安全性 | 缺失水平越权校验 | 添加用户A访问用户B数据的场景 |
| ...
```

## 🎯 最佳实践

### 1. 在用例中明确提及必备条件

**推荐做法**：
```
标题：订单退款（需验证权限控制和敏感信息脱敏）
备注：需验证水平越权和垂直越权
```

**优点**：
- ✅ 系统自动识别，无需交互询问
- ✅ 提高评审效率
- ✅ 用例描述更清晰

### 2. 合理选择必备条件

**电商秒杀场景**：
- ✅ 并发冲突（抢购场景）
- ✅ 性能风险
- ✅ 业务安全（超卖问题）

**内部管理系统**：
- ⏭️  并发冲突（内部系统并发低）
- ⏭️  性能风险（内部系统性能要求低）

### 3. 保存配置避免重复收集

首次评审后，配置会保存到 `.review_config.json`，下次评审时可选择使用历史配置。

## 📚 文档

- **[SKILL.md](SKILL.md)** - 完整功能说明
- **[QUICKSTART.md](QUICKSTART.md)** - 快速开始指南
- **[UPGRADE_SUMMARY.md](UPGRADE_SUMMARY.md)** - 版本更新说明
- **[references/](references/)** - 评审标准和参考文档

## ❓ 常见问题

### Q: 智能检测如何工作？
A: 系统会分析用例的所有文本字段（title、steps、expected、remarks等），检测是否包含必备条件相关的关键词。如果检测到，自动标记为"需要校验"。

### Q: 如何避免每次都重新收集？
A: 配置会保存到 `.review_config.json`，下次评审时可选择使用历史配置，或使用 `--skip-collect` 参数跳过收集。

### Q: 必备条件选择错误怎么办？
A: 重新运行评审，在询问是否使用历史配置时选择"不使用"，重新收集即可。

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！
