# 工作流生成智能体使用指南

## 📋 概述

工作流生成智能体（`WorkflowGeneratorAgent`）是一个专门用于根据用户需求自动生成工作流节点定义的AI智能体。它能够理解自然语言描述，并转换为完整的JSON格式工作流定义。

## 🚀 核心功能

### 支持的节点类型

1. **workflowStart** - 工作流开始节点
   - 定义工作流输入参数
   - 配置用户输入字段

2. **workflowEnd** - 工作流结束节点
   - 定义工作流输出结果
   - 连接前置节点的输出

3. **condition** - 条件判断节点
   - 复杂的条件逻辑判断
   - 多分支路由控制

4. **code** - 代码执行节点
   - JavaScript代码执行
   - 数据处理和计算

5. **chatWithLLM** - LLM聊天节点
   - 调用大语言模型
   - 智能对话和内容生成

6. **dbQuery** - 数据库查询节点
   - SQL查询执行
   - 数据库操作

7. **httpRequest** - HTTP请求节点
   - API调用
   - 外部服务集成

## 🛠️ 使用方法

### 基本调用

```python
from agents.workflow_generator_agent import WorkflowGeneratorAgent

# 创建智能体实例
agent = WorkflowGeneratorAgent(
    model_service=your_model_service,
    workflow_engine=None,
    data_processor=None
)

# 执行工作流生成
result = await agent.execute(
    task_description="创建一个智能客服工作流",
    context={
        "domain": "客户服务",
        "requirements": ["多语言支持", "问题分类"]
    },
    parameters={
        "complexity_level": "medium",
        "include_error_handling": True
    }
)

if result.success:
    workflow = result.result["workflow"]
    print(f"生成成功！节点数量: {len(workflow['nodes'])}")
else:
    print(f"生成失败: {result.error}")
```

### 参数说明

#### task_description (必需)
用户需求的自然语言描述，例如：
- "创建一个数据分析工作流，从数据库获取数据并生成报告"
- "设计智能问答系统，支持技术和商务问题分类"
- "构建文档处理流程，支持摘要和翻译功能"

#### context (可选)
提供额外的上下文信息：
```python
context = {
    "domain": "电商平台",           # 应用领域
    "data_sources": ["MySQL", "Redis"],  # 数据源
    "target_users": "客服人员",      # 目标用户
    "constraints": ["响应时间<5s"]   # 约束条件
}
```

#### parameters (可选)
生成参数配置：
```python
parameters = {
    "complexity_level": "simple|medium|advanced",  # 复杂度级别
    "output_format": "standard|detailed",          # 输出格式
    "include_error_handling": True,                # 是否包含错误处理
    "optimize_performance": True                   # 是否优化性能
}
```

## 📝 使用场景示例

### 1. 数据分析工作流

```python
result = await agent.execute(
    task_description="创建数据分析工作流，查询销售数据，计算趋势，生成AI洞察",
    context={
        "data_source": "PostgreSQL",
        "analysis_types": ["趋势分析", "同比分析"],
        "output_format": "可视化报告"
    }
)
```

生成的工作流包含：
- 数据库查询节点（获取销售数据）
- 代码执行节点（趋势计算）
- LLM分析节点（生成洞察）
- 结果输出节点

### 2. 智能客服工作流

```python
result = await agent.execute(
    task_description="构建智能客服系统，根据问题类型分配给不同专家AI",
    context={
        "question_types": ["技术", "商务", "投诉"],
        "response_style": "专业友好"
    }
)
```

生成的工作流包含：
- 问题输入节点
- 条件判断节点（问题分类）
- 多个专业LLM节点
- 统一回复输出节点

### 3. 文档处理工作流

```python
result = await agent.execute(
    task_description="设计文档处理流程，支持在线获取、内容提取、摘要生成",
    context={
        "document_types": ["PDF", "网页", "Word"],
        "processing_options": ["摘要", "翻译", "关键词提取"]
    }
)
```

## 🎯 最佳实践

### 1. 明确需求描述
- ✅ **好的描述**: "创建电商订单处理工作流，包含订单验证、库存检查、支付处理和发货通知"
- ❌ **不好的描述**: "做一个订单系统"

### 2. 提供充分的上下文
```python
context = {
    "business_domain": "在线教育平台",
    "user_roles": ["学生", "教师", "管理员"],
    "integration_systems": ["支付网关", "视频会议", "作业系统"],
    "performance_requirements": "支持1000并发用户"
}
```

### 3. 合理设置复杂度
- **simple**: 3-5个节点的基础流程
- **medium**: 5-10个节点，包含条件判断
- **advanced**: 10+节点，复杂逻辑和错误处理

### 4. 验证生成结果
```python
if result.success:
    workflow = result.result["workflow"]
    
    # 检查基本结构
    assert "nodes" in workflow
    assert "edges" in workflow
    
    # 验证节点完整性
    node_ids = {node["id"] for node in workflow["nodes"]}
    for edge in workflow["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids
    
    print("✅ 工作流验证通过")
```

## 🔧 高级配置

### 自定义系统提示词
智能体使用预定义的系统提示词，包含：
- 节点类型说明
- 连接规则
- 生成要求
- 最佳实践

### 错误处理
智能体内置多重错误处理：
- JSON格式验证
- 节点完整性检查
- 连接有效性验证
- 自动布局优化

### 性能优化
- 自动节点位置布局
- 重复ID检测和修复
- 边连接优化
- 代码逻辑验证

## 📊 输出格式

生成的工作流遵循标准JSON格式：

```json
{
  "workflow": {
    "nodes": [...],  // 节点数组
    "edges": [...]   // 连接数组
  },
  "node_count": 5,
  "edge_count": 4,
  "description": "用户需求描述",
  "generated_at": "2024-01-15T10:30:00",
  "agent_version": "1.0.0"
}
```

每个节点包含完整的配置：
- id, type, position
- data.inputs, data.outputs
- 节点特定配置

每条边包含：
- source, target, id
- sourceHandleId (条件节点)

## 🚨 注意事项

1. **模型服务依赖**: 需要配置有效的模型服务
2. **网络访问**: HTTP请求节点需要网络权限
3. **数据库配置**: 数据库查询节点需要数据库连接
4. **API限制**: 注意模型调用频次和Token限制
5. **安全考虑**: 代码执行节点需要安全沙箱

## 🔗 相关文档

- [基础智能体架构](base_agent.py)
- [智能体引擎](engine.py)
- [Authorizer项目集成](../README_AI_SYSTEM.md)

---

**版本**: 1.0.0  
**更新时间**: 2024年1月  
**维护者**: AI Core Team 