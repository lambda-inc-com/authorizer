# 多智能体工作流生成系统

## 📖 系统概述

这是一个基于多智能体架构的工作流自动生成系统，采用三个专门的智能体协同工作：

1. **需求分析智能体** (RequirementAnalyzer) - 分析用户需求，识别所需节点
2. **工作流组合智能体** (WorkflowComposer) - 将节点组合成完整工作流
3. **工作流验证智能体** (WorkflowValidator) - 验证工作流正确性

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                 MultiAgentOrchestrator                 │
│                     (协调器)                            │
├─────────────────────────────────────────────────────────┤
│  MessageBus           SharedStateManager               │
│  (消息总线)             (共享状态管理)                    │
├─────────────────────────────────────────────────────────┤
│ RequirementAnalyzer │ WorkflowComposer │ WorkflowValidator│
│   (需求分析智能体)    │  (工作流组合智能体) │  (工作流验证智能体) │
└─────────────────────────────────────────────────────────┘
```

### 核心组件

- **MessageBus**: 负责智能体间的消息传递和通信
- **SharedStateManager**: 管理智能体间的共享状态和数据
- **BaseAgent**: 智能体基类，提供通用功能
- **LLMClient**: LLM服务客户端接口

## 🚀 快速开始

### 基本使用

```python
import asyncio
from ai_core.workflow_generation_system import WorkflowGenerationSystem

async def main():
    # 创建系统实例
    system = WorkflowGenerationSystem()
    
    # 生成工作流
    user_requirement = "我需要一个工作流来查询用户信息并发送邮件通知"
    result = await system.generate_workflow_from_requirement(user_requirement)
    
    if result["success"]:
        print("工作流生成成功!")
        print(f"工作流名称: {result['workflow']['name']}")
        print(f"节点数量: {len(result['workflow']['nodes'])}")
    else:
        print(f"生成失败: {result['error']}")

# 运行
asyncio.run(main())
```

### 集成真实LLM服务

```python
from ai_core.workflow_generation_system import WorkflowGenerationSystem, LLMClient

class RealLLMClient(LLMClient):
    async def chat_completion(self, messages: list, model: str = "gpt-4", **kwargs) -> str:
        # 集成真实的LLM API
        # 例如 OpenAI API
        import openai
        
        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=messages,
            **kwargs
        )
        
        return response.choices[0].message.content

# 使用真实LLM客户端
real_llm_client = RealLLMClient(api_key="your_api_key")
system = WorkflowGenerationSystem(llm_client=real_llm_client)
```

## 🎯 智能体详解

### 1. 需求分析智能体 (RequirementAnalyzer)

**职责**: 分析用户需求，识别所需的工作流节点

**输入**: 用户的自然语言需求描述

**输出**: 
```json
{
  "analysis": {
    "requirement_summary": "需求总结",
    "key_actions": ["关键行为1", "关键行为2"],
    "data_entities": ["数据实体1", "数据实体2"],
    "business_rules": ["业务规则1", "业务规则2"]
  },
  "required_nodes": [
    {
      "type": "节点类型",
      "purpose": "节点用途",
      "description": "详细描述",
      "suggested_name": "建议名称",
      "key_configs": {}
    }
  ]
}
```

**提示词策略**: 采用角色扮演 + 结构化输出的提示词设计，确保输出格式规范且分析全面。

### 2. 工作流组合智能体 (WorkflowComposer)

**职责**: 将分析出的节点组合成完整的可执行工作流

**输入**: 需求分析结果 + 用户原始需求

**输出**: 完整的工作流JSON配置

**核心功能**:
- 生成节点详细配置
- 建立节点连接关系
- 设置数据流引用
- 确保业务逻辑完整性

**提示词策略**: 强调数据流一致性和业务逻辑完整性，提供详细的节点模板参考。

### 3. 工作流验证智能体 (WorkflowValidator)

**职责**: 全面验证生成的工作流JSON

**验证维度**:
- **结构验证**: 检查必需字段、数据类型等
- **配置验证**: 验证节点配置的完整性和正确性
- **逻辑验证**: 检查节点连接关系、数据流等
- **可执行性验证**: 检测循环引用、死链等问题

**输出**: 详细的验证报告和改进建议

## 🔄 工作流程

```
1. 用户输入需求
    ↓
2. 需求分析智能体分析需求
    ↓ (共享状态更新)
3. 工作流组合智能体生成工作流
    ↓ (共享状态更新)
4. 工作流验证智能体验证工作流
    ↓
5. 如果验证失败，重试生成 (最多3次)
    ↓
6. 返回最终结果
```

## 📊 系统特性

### 💪 优势特性

1. **模块化设计**: 每个智能体职责单一，易于维护和扩展
2. **异步架构**: 支持高并发处理
3. **消息驱动**: 智能体间通过消息总线通信，松耦合
4. **状态管理**: 统一的共享状态管理，保证数据一致性
5. **错误恢复**: 支持自动重试和错误恢复机制
6. **可扩展性**: 容易添加新的智能体或功能

### 🛡️ 安全特性

1. **输入验证**: 严格的参数验证和格式检查
2. **错误隔离**: 单个智能体异常不会影响整个系统
3. **超时控制**: 防止长时间阻塞
4. **重试限制**: 避免无限重试

## 🔧 配置和扩展

### 添加新的智能体

```python
from ai_core.multi_agent_workflow_generator import BaseAgent, AgentRole, MessageType

class CustomAgent(BaseAgent):
    def __init__(self, message_bus, state_manager, llm_client):
        super().__init__(AgentRole.CUSTOM_ROLE, message_bus, state_manager)
        self.llm_client = llm_client
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        # 实现自定义逻辑
        pass
```

### 自定义消息类型

```python
class CustomMessageType(Enum):
    CUSTOM_TASK = "custom_task"
    CUSTOM_RESULT = "custom_result"
```

### 扩展验证规则

```python
class CustomValidator(WorkflowValidator):
    def _load_validation_rules(self) -> Dict[str, Any]:
        base_rules = super()._load_validation_rules()
        
        # 添加自定义验证规则
        base_rules["custom_rules"] = {
            "new_rule": "rule_definition"
        }
        
        return base_rules
```

## 📈 性能优化

### 并发处理

```python
# 支持批量处理
async def batch_generate_workflows(requirements: List[str]) -> List[Dict]:
    system = WorkflowGenerationSystem()
    
    tasks = [
        system.generate_workflow_from_requirement(req) 
        for req in requirements
    ]
    
    return await asyncio.gather(*tasks)
```

### 缓存机制

```python
class CachedLLMClient(LLMClient):
    def __init__(self):
        super().__init__()
        self.cache = {}
    
    async def chat_completion(self, messages: list, **kwargs) -> str:
        cache_key = hash(str(messages))
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        result = await super().chat_completion(messages, **kwargs)
        self.cache[cache_key] = result
        
        return result
```

## 🧪 测试

### 运行测试

```bash
cd ai-core
python workflow_generation_system.py
```

### 单元测试

```python
import pytest
from ai_core.workflow_generation_system import WorkflowGenerationSystem

@pytest.mark.asyncio
async def test_workflow_generation():
    system = WorkflowGenerationSystem()
    result = await system.generate_workflow_from_requirement("test requirement")
    
    assert result["success"] == True
    assert "workflow" in result
```

## 📝 支持的工作流节点

系统支持以下11种节点类型：

- `workflowStart` - 工作流开始节点
- `workflowEnd` - 工作流结束节点
- `dbQuery` - 数据库查询节点
- `dbCreate` - 数据库创建节点
- `dbUpdate` - 数据库更新节点
- `dbDelete` - 数据库删除节点
- `http` - HTTP请求节点
- `llm` - LLM对话节点
- `condition` - 条件判断节点
- `code` - 代码执行节点
- `transaction` - 数据库事务节点

每种节点都有详细的配置规范，请参考节点定义文档。

## 🐛 故障排除

### 常见问题

1. **LLM响应解析失败**
   - 检查LLM响应格式是否正确
   - 确保提示词设计合理

2. **工作流验证失败**
   - 检查节点配置是否完整
   - 验证数据引用路径是否正确

3. **智能体通信异常**
   - 检查消息总线状态
   - 确认智能体正确注册

### 调试模式

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

system = WorkflowGenerationSystem()
# 查看系统状态
print(system.get_system_status())
```

## 🔮 未来规划

1. **智能体能力增强**: 添加更多专门的智能体
2. **可视化界面**: 提供工作流设计的图形化界面
3. **模板库**: 预置常用工作流模板
4. **性能优化**: 缓存、并发优化
5. **监控告警**: 添加系统监控和告警机制

## 📜 许可证

本项目采用 MIT 许可证。

---

*如有问题或建议，请提交 Issue 或 Pull Request。* 