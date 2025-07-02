# 增强版工作流生成器

基于最新节点规范的专业工作流生成系统，支持11种节点类型、完整验证和自动优化。

## 🚀 主要特性

### 1. 完整的节点类型支持
- **workflowStart**: 工作流开始节点
- **workflowEnd**: 工作流结束节点  
- **code**: 代码执行节点 (TypeScript)
- **condition**: 条件判断节点
- **dbQuery**: 数据库查询节点
- **dbCreate**: 数据库创建节点
- **dbUpdate**: 数据库更新节点
- **dbDelete**: 数据库删除节点
- **http**: HTTP请求节点
- **llm**: LLM对话节点
- **transaction**: 数据库事务节点

### 2. 智能提示词系统
- 详细的节点规范说明
- 场景特定的提示词模板
- 数据引用规范指导
- 最佳实践建议

### 3. 完整的验证系统
- 节点结构验证
- 配置参数验证
- 数据流验证
- 命名规范检查

### 4. 自动优化功能
- 节点顺序优化
- 错误处理增强
- 性能参数调整
- 超时设置优化

## 📁 文件结构

```
ai-core/
├── prompts/
│   └── enhanced_workflow_prompts.py          # 增强版提示词模板
├── utils/
│   └── workflow_validator.py                 # 工作流验证器
├── agents/
│   └── ultimate_workflow_generator.py        # 终极版工作流生成器
└── test_ultimate_workflow_generator.py       # 测试脚本
```

## 🛠️ 快速开始

### 1. 基础使用

```python
from agents.ultimate_workflow_generator import create_workflow_with_ultimate_generator

# 生成简单工作流
result = await create_workflow_with_ultimate_generator(
    task_description="创建一个用户注册工作流，包括邮箱验证和信息保存",
    scenario="user_management",
    auto_validate=True,
    auto_optimize=True
)

if result["success"]:
    workflow = result["workflow"]
    print("工作流生成成功！")
else:
    print(f"生成失败: {result['error']}")
```

### 2. 高级使用

```python
from agents.ultimate_workflow_generator import UltimateWorkflowGeneratorAgent

# 创建生成器实例
generator = UltimateWorkflowGeneratorAgent(preferred_model="openai_gpt-4")

# 生成工作流
result = await generator.generate_workflow(
    task_description="复杂的订单处理流程",
    scenario="business_process",
    context={
        "business_rules": "支持库存检查和事务回滚",
        "performance_requirements": "高并发处理"
    },
    parameters={
        "complexity_level": "high",
        "include_error_handling": True,
        "priority_focus": "数据一致性"
    },
    auto_validate=True,
    auto_optimize=True
)
```

### 3. 批量生成

```python
from agents.ultimate_workflow_generator import batch_generate_workflows

tasks = [
    {
        "task_description": "用户认证工作流",
        "scenario": "user_management",
        "complexity": "simple"
    },
    {
        "task_description": "数据分析报告生成",
        "scenario": "data_processing", 
        "complexity": "medium"
    }
]

results = await batch_generate_workflows(
    tasks=tasks,
    auto_validate=True,
    auto_optimize=True
)
```

## 🎯 支持的场景

### 1. 用户管理 (user_management)
- 用户注册、登录、权限管理
- 使用 dbQuery, dbCreate, dbUpdate, condition 节点
- 事务保证数据一致性

### 2. 数据处理 (data_processing)
- 数据ETL、分析、报告生成
- 使用 dbQuery, code, condition 节点
- 支持大数据量分页处理

### 3. API集成 (api_integration)
- 第三方API调用、数据同步
- 使用 http, code, condition 节点
- 支持重试和错误处理

### 4. AI工作流 (ai_workflow)
- AI对话、内容生成、智能分析
- 使用 llm, code, condition 节点
- 优化提示词和参数配置

### 5. 业务流程 (business_process)
- 复杂业务逻辑、审批流程
- 使用 condition, transaction, http 节点
- 完整的错误处理机制

## 📋 节点规范

### 基本结构
```json
{
  "name": "节点名称",           // PascalCase命名，全局唯一
  "type": "节点类型",           // 11种预定义类型之一
  "desc": "节点功能描述",       // 清晰描述节点功能
  "inputs": {},                // 输入参数定义
  "outputs": {},               // 输出参数定义
  "configs": {},               // 节点特定配置
  "nextNodes": []              // 下一步流向
}
```

### 数据引用规范
- `$prevNode.outputs.字段名` - 引用前一个节点输出
- `$currentNode.inputs.字段名` - 引用当前节点输入
- `$currentNodeResult` - 引用当前节点执行结果

### 配置示例

#### 数据库查询节点
```json
{
  "name": "QueryUsers",
  "type": "dbQuery",
  "desc": "查询用户信息",
  "inputs": {
    "userId": {
      "type": "string",
      "value": "$prevNode.outputs.userId",
      "desc": "用户ID"
    }
  },
  "outputs": {
    "result": {
      "type": "array",
      "value": "$currentNodeResult",
      "desc": "查询结果"
    }
  },
  "configs": {
    "table": "users",
    "fields": ["id", "name", "email"],
    "filters": [
      {
        "field": "id",
        "operator": "=",
        "value": "$currentNode.inputs.userId"
      }
    ],
    "timeout": 30
  },
  "nextNodes": ["ProcessData"]
}
```

#### 条件判断节点
```json
{
  "name": "CheckUserStatus",
  "type": "condition",
  "desc": "检查用户状态",
  "inputs": {
    "userInfo": {
      "type": "object",
      "value": "$prevNode.outputs.result",
      "desc": "用户信息"
    }
  },
  "outputs": {
    "result": {
      "type": "object",
      "value": "$currentNodeResult",
      "desc": "判断结果"
    }
  },
  "configs": {
    "conditionGroups": [
      {
        "conditions": [
          {
            "left": "$currentNode.inputs.userInfo.status",
            "operator": "equal",
            "right": "active"
          }
        ],
        "relationship": "AND",
        "nextNode": "ActiveUserProcess"
      }
    ],
    "defaultNextNode": "InactiveUserProcess"
  },
  "nextNodes": []
}
```

## 🔍 验证规则

### 必填字段检查
- 每个节点必须包含: name, type, desc, inputs, outputs, configs, nextNodes
- 特定节点类型需要特定配置参数

### 命名规范
- 节点名称使用PascalCase格式
- 全局唯一性检查
- 描述性命名要求

### 数据流验证
- 数据引用语法检查
- 类型匹配验证
- 依赖关系检查

### 配置验证
- 数据库操作配置完整性
- HTTP请求参数有效性
- 条件判断逻辑正确性

## 🧪 测试系统

### 运行测试
```bash
cd ai-core
python test_ultimate_workflow_generator.py
```

### 测试场景
- 用户注册工作流
- 数据分析工作流
- API集成工作流
- AI对话工作流
- 复杂业务流程

### 测试指标
- 生成成功率
- 验证通过率
- 生成时间
- 节点数量
- 验证分数

## 📊 性能优化

### 自动优化功能
1. **节点顺序优化**: 确保开始和结束节点位置正确
2. **错误处理增强**: 自动添加超时和重试配置
3. **性能参数调整**: 合理设置限制和缓存
4. **安全检查**: 避免危险操作和注入攻击

### 推荐实践
- 为数据库操作添加适当的过滤条件
- 设置合理的超时时间
- 使用事务保证数据一致性
- 添加错误处理分支
- 优化数据传递路径

## 🛡️ 安全考虑

### 数据安全
- SQL注入防护
- 参数验证
- 敏感信息脱敏

### 操作安全
- 必要的权限检查
- 危险操作确认
- 审计日志记录

### 网络安全
- HTTPS通信
- 身份认证
- 访问控制

## 🔧 扩展开发

### 添加新节点类型
1. 在 `SUPPORTED_NODE_TYPES` 中添加类型
2. 在验证器中添加配置验证逻辑
3. 在提示词模板中添加使用说明
4. 更新测试用例

### 自定义验证规则
```python
from utils.workflow_validator import WorkflowValidator

class CustomValidator(WorkflowValidator):
    def _validate_custom_node(self, configs, node_name):
        # 自定义验证逻辑
        pass
```

### 扩展优化器
```python
def custom_optimizer(workflow):
    # 自定义优化逻辑
    return optimized_workflow
```

## 📝 使用建议

### 1. 任务描述最佳实践
- 明确描述业务需求
- 指定输入输出要求
- 说明错误处理需求
- 提及性能要求

### 2. 场景选择指导
- 用户管理：注册、登录、权限相关
- 数据处理：ETL、分析、报告相关  
- API集成：第三方调用、数据同步
- AI工作流：智能分析、内容生成
- 业务流程：复杂业务逻辑、审批流程

### 3. 参数配置建议
- `complexity_level`: simple/medium/high
- `include_error_handling`: 建议设为 true
- `priority_focus`: 功能完整性/性能优化/数据一致性

## 🤝 贡献指南

### 代码规范
- 遵循PEP 8编码规范
- 添加完整的类型注解
- 编写详细的文档字符串
- 添加适当的日志记录

### 测试要求
- 编写单元测试
- 集成测试覆盖
- 性能测试验证
- 错误处理测试

### 提交流程
1. Fork项目仓库
2. 创建功能分支
3. 编写代码和测试
4. 提交Pull Request

## 📞 技术支持

如有问题或建议，请通过以下方式联系：
- 创建GitHub Issue
- 发送邮件反馈
- 参与讨论群组

---

**版本**: 3.0.0  
**更新日期**: 2024年12月  
**维护团队**: AI核心开发组 