# 标准测试用例字段定义

本文档定义了 testcase-reviewer 技能识别和处理的所有标准字段，以及各格式文件中对应字段的中英文别名。

---

## 标准字段列表

| 标准字段名 | 类型 | 必填 | 说明 |
|-----------|------|------|------|
| `id` | string | 推荐 | 用例唯一标识符，如 TC-001 |
| `title` | string | **必填** | 用例标题，描述测试目的 |
| `module` | string | 推荐 | 所属功能模块 |
| `priority` | string | 推荐 | 优先级：P0/P1/P2/P3 或 高/中/低 |
| `precondition` | string | 推荐 | 执行前提条件 |
| `steps` | string | **必填** | 测试操作步骤 |
| `expected` | string | **必填** | 预期结果 |
| `actual` | string | 可选 | 实际结果（执行后填写） |
| `status` | string | 可选 | 执行状态：通过/失败/阻塞/未执行 |
| `type` | string | 可选 | 用例类型：功能/性能/安全/UI |
| `tags` | string | 可选 | 标签，多个用逗号分隔 |
| `author` | string | 可选 | 用例编写人 |
| `remarks` | string | 可选 | 备注说明 |

---

## 字段别名映射

解析器会自动将以下列名映射为标准字段名：

### ID 字段 (`id`)
- 中文：用例ID、用例编号、编号、序号
- 英文：id, case_id, caseid, test_id

### 标题字段 (`title`)
- 中文：标题、用例名称、用例标题、测试标题
- 英文：title, name, case_name

### 模块字段 (`module`)
- 中文：模块、功能模块、功能、所属模块
- 英文：module, feature, function

### 优先级字段 (`priority`)
- 中文：优先级、级别
- 英文：priority, level, severity

### 前置条件字段 (`precondition`)
- 中文：前置条件、前提条件
- 英文：precondition, preconditions, pre_condition, prerequisites

### 步骤字段 (`steps`)
- 中文：测试步骤、操作步骤、步骤
- 英文：steps, step, test_steps

### 预期结果字段 (`expected`)
- 中文：预期结果、期望结果、期望
- 英文：expected, expected_result, result

### 实际结果字段 (`actual`)
- 中文：实际结果
- 英文：actual, actual_result

### 备注字段 (`remarks`)
- 中文：备注
- 英文：remarks, remark, note, notes, comment

### 作者字段 (`author`)
- 中文：创建人、编写人
- 英文：author

### 标签字段 (`tags`)
- 中文：标签
- 英文：tags, tag

---

## 格式特殊说明

### CSV 格式
- 第一行必须为表头行
- 支持 UTF-8、GBK、GB2312 编码（自动检测）
- 推荐使用 UTF-8-BOM 格式保存（Excel 导出时选择）

### Excel 格式
- 支持 `.xlsx`（openpyxl）和 `.xls`（xlrd）
- 支持多 Sheet，默认解析所有 Sheet
- 自动跳过空行和合并单元格标题行
- 如需只解析特定 Sheet，使用 `--sheet` 参数

### XMind 格式
- 支持 XMind 8（.xmind，XML格式）和 XMind Zen/2022+（JSON格式）
- **叶节点**自动识别为一条测试用例
- **节点路径**自动生成模块层级（`module` 和 `path` 字段）
- **节点备注**可填写步骤和预期结果（使用约定格式）
- **节点标签**可用于设置优先级（P0/P1/P2/P3）

---

## 审核报告字段说明

| 字段 | 说明 |
|------|------|
| 综合评分 | 0-100 分，综合字段完整性、规范性、覆盖率 |
| 严重问题 | 必填字段缺失，直接影响用例可执行性 |
| 警告问题 | 质量问题，影响用例可读性和管理 |
| 优化建议 | 最佳实践建议，有助于长期维护 |
| 场景分布 | 正常/异常/边界/性能/安全场景的分布情况 |
| 模块分布 | 各功能模块的用例数量分布 |
