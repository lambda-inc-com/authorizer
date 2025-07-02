"""
增强版工作流生成智能体提示词模板

基于最新的节点规范和最佳实践，提供专业的工作流生成提示词
"""

from typing import Dict, Any, List


class EnhancedWorkflowPromptTemplates:
    """增强版工作流提示词模板类"""
    
    @staticmethod
    def get_node_specifications() -> str:
        """获取详细的节点规范说明"""
        return """
# 工作流节点通用规范

## 节点基本结构
每个节点都必须包含以下基本字段：

```json
{
  "name": "节点名称",
  "type": "节点类型", 
  "desc": "节点功能描述",
  "inputs": {},
  "outputs": {},
  "configs": {},
  "nextNodes": []
}
```

## 字段说明

### name *(必填)*
- 节点的唯一标识符，必须在整个工作流中唯一
- 使用PascalCase命名，如: "GetUserData", "SendEmail"
- 名称应具有描述性，能够表达节点的主要功能

### type *(必填)*
- 节点类型，决定节点的执行逻辑
- 可选值: "workflowStart", "workflowEnd", "dbQuery", "dbCreate", "dbUpdate", "dbDelete", "transaction", "http", "llm", "condition", "code"

### desc *(可选)*
- 节点功能的详细描述，应该清楚说明节点做什么，处理什么数据

### inputs *(可选)*
输入参数定义，格式为键值对对象：
```json
{
  "参数名": {
    "type": "数据类型",
    "value": "数据来源引用",
    "desc": "参数描述"
  }
}
```

### outputs *(必填)*
输出参数定义，定义节点执行后产生的数据：
```json
{
  "输出字段名": {
    "type": "数据类型",
    "value": "$currentNodeResult",
    "desc": "输出描述"
  }
}
```

### configs *(必填)*
节点特定的配置参数，根据不同节点类型有不同的配置结构。

### nextNodes *(必填)*
定义当前节点执行完成后的流向：
- 数组格式: ["下一个节点名称"]
- 对于条件节点，不需要在此字段指定连接关系
- 对于结束节点，使用: ["end"]

## 数据引用规范

### 引用语法
- **前一节点输出**: `$prevNode.outputs.字段名`
- **当前节点输入**: `$currentNode.inputs.字段名`
- **当前节点执行结果**: `$currentNodeResult`

### 重要约束
1. **只能引用当前和前一个节点**：不能跨越多个节点进行引用
2. **数据传递规则**：如果字段在后续节点需要引用，必须通过节点间一致传递
3. **引用范围限制**：避免复杂的跨节点数据依赖，保持数据流的简洁性

## 可用节点类型详细说明

### 1. workflowStart - 工作流开始节点
```json
{
  "name": "WorkflowStart",
  "type": "workflowStart",
  "desc": "工作流开始节点，定义工作流的输入参数",
  "inputs": {
    "trigger": {
      "type": "string",
      "value": "manual",
      "desc": "触发方式：manual（手动）、webhook（Webhook）、schedule（定时）"
    },
    "parameters": {
      "type": "object",
      "value": {
        "userId": "string",
        "projectId": "string",
        "data": "object"
      },
      "desc": "工作流输入参数"
    }
  },
  "outputs": {},
  "configs": {},
  "nextNodes": ["下一个节点名称"]
}
```

### 2. workflowEnd - 工作流结束节点
```json
{
  "name": "WorkflowEnd",
  "type": "workflowEnd",
  "desc": "工作流结束节点，定义工作流的输出结果",
  "inputs": {
    "finalResult": {
      "type": "object",
      "value": "$prevNode.outputs.result",
      "desc": "最终输出结果"
    }
  },
  "outputs": {},
  "configs": {},
  "nextNodes": ["end"]
}
```

### 3. code - 代码执行节点
```json
{
  "name": "ProcessData",
  "type": "code",
  "desc": "执行自定义代码逻辑",
  "inputs": {
    "data": {
      "type": "object",
      "value": "$prevNode.outputs.data",
      "desc": "要处理的数据"
    }
  },
  "outputs": {
    "result": {
      "type": "object",
      "value": "$currentNodeResult",
      "desc": "处理结果"
    }
  },
  "configs": {
    "file": {
      "name": "process.ts",
      "content": "function main(inputs) { return { processed: inputs.data }; }"
    },
    "dependencies": ["lodash"],
    "timeout": 30
  },
  "nextNodes": ["下一个节点名称"]
}
```

### 4. condition - 条件判断节点
```json
{
  "name": "CheckCondition",
  "type": "condition",
  "desc": "根据条件判断执行分支",
  "inputs": {
    "data": {
      "type": "object",
      "value": "$prevNode.outputs.data",
      "desc": "判断条件的数据"
    }
  },
  "outputs": {
    "result": {
      "type": "object",
      "value": "$currentNodeResult",
      "desc": "条件判断结果"
    }
  },
  "configs": {
    "conditionGroups": [
      {
        "conditions": [
          {
            "left": "$currentNode.inputs.data.status",
            "operator": "equal",
            "right": "active"
          }
        ],
        "relationship": "AND",
        "nextNode": "ActiveUserProcess"
      }
    ],
    "defaultNextNode": "DefaultProcess"
  },
  "nextNodes": []
}
```

### 5. dbQuery - 数据库查询节点
```json
{
  "name": "QueryUsers",
  "type": "dbQuery",
  "desc": "查询用户数据",
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
  "nextNodes": ["下一个节点名称"]
}
```

### 6. dbCreate - 数据库创建节点
```json
{
  "name": "CreateUser",
  "type": "dbCreate",
  "desc": "创建新用户记录",
  "inputs": {
    "userData": {
      "type": "object",
      "value": "$prevNode.outputs.userData",
      "desc": "用户数据"
    }
  },
  "outputs": {
    "insertId": {
      "type": "string",
      "value": "$currentNodeResult",
      "desc": "新创建记录的ID"
    }
  },
  "configs": {
    "table": "users",
    "data": {
      "name": "$currentNode.inputs.userData.name",
      "email": "$currentNode.inputs.userData.email",
      "status": "active"
    },
    "timeout": 30
  },
  "nextNodes": ["下一个节点名称"]
}
```

### 7. dbUpdate - 数据库更新节点
```json
{
  "name": "UpdateUser",
  "type": "dbUpdate",
  "desc": "更新用户信息",
  "inputs": {
    "userId": {
      "type": "string",
      "value": "$prevNode.outputs.userId",
      "desc": "用户ID"
    },
    "updateData": {
      "type": "object",
      "value": "$prevNode.outputs.updateData",
      "desc": "更新数据"
    }
  },
  "outputs": {
    "affectedRows": {
      "type": "number",
      "value": "$currentNodeResult",
      "desc": "影响的行数"
    }
  },
  "configs": {
    "table": "users",
    "data": {
      "status": "$currentNode.inputs.updateData.status"
    },
    "filters": [
      {
        "field": "id",
        "operator": "=",
        "value": "$currentNode.inputs.userId"
      }
    ],
    "timeout": 30
  },
  "nextNodes": ["下一个节点名称"]
}
```

### 8. dbDelete - 数据库删除节点
```json
{
  "name": "DeleteUser",
  "type": "dbDelete",
  "desc": "删除用户记录",
  "inputs": {
    "userId": {
      "type": "string",
      "value": "$prevNode.outputs.userId",
      "desc": "用户ID"
    }
  },
  "outputs": {
    "affectedRows": {
      "type": "number",
      "value": "$currentNodeResult",
      "desc": "删除的行数"
    }
  },
  "configs": {
    "table": "users",
    "filters": [
      {
        "field": "id",
        "operator": "=",
        "value": "$currentNode.inputs.userId"
      }
    ],
    "timeout": 30
  },
  "nextNodes": ["下一个节点名称"]
}
```

### 9. http - HTTP请求节点
```json
{
  "name": "CallAPI",
  "type": "http",
  "desc": "调用外部API",
  "inputs": {
    "apiData": {
      "type": "object",
      "value": "$prevNode.outputs.apiData",
      "desc": "API请求数据"
    }
  },
  "outputs": {
    "result": {
      "type": "object",
      "value": "$currentNodeResult",
      "desc": "API响应结果"
    }
  },
  "configs": {
    "method": "POST",
    "url": "https://api.example.com/users",
    "headers": {
      "Content-Type": "application/json"
    },
    "bodyType": "json",
    "body": "$currentNode.inputs.apiData",
    "timeout": 30
  },
  "nextNodes": ["下一个节点名称"]
}
```

### 10. llm - LLM对话节点
```json
{
  "name": "ChatWithAI",
  "type": "llm",
  "desc": "与AI模型对话",
  "inputs": {
    "userInput": {
      "type": "string",
      "value": "$prevNode.outputs.userInput",
      "desc": "用户输入"
    }
  },
  "outputs": {
    "response": {
      "type": "string",
      "value": "$currentNodeResult",
      "desc": "AI回复"
    }
  },
  "configs": {
    "modelId": "gpt-4",
    "systemPrompt": "你是一个有用的AI助手",
    "temperature": 0.7,
    "maxTokens": 1000
  },
  "nextNodes": ["下一个节点名称"]
}
```

### 11. transaction - 数据库事务节点
```json
{
  "name": "UserTransaction",
  "type": "transaction",
  "desc": "执行用户创建事务",
  "inputs": {
    "userData": {
      "type": "object",
      "value": "$prevNode.outputs.userData",
      "desc": "用户数据"
    }
  },
  "outputs": {
    "transactionResult": {
      "type": "object",
      "value": "$currentNodeResult",
      "desc": "事务执行结果"
    }
  },
  "configs": {
    "isolation": "READ_COMMITTED",
    "timeout": 60
  },
  "children": [
    {
      "name": "CreateUser",
      "type": "dbCreate",
      "desc": "创建用户",
      "order": 1,
      "inputs": {},
      "outputs": {
        "insertId": {
          "type": "string",
          "value": "$currentNodeResult",
          "desc": "用户ID"
        }
      },
      "configs": {
        "table": "users",
        "data": {
          "name": "$currentNode.inputs.userData.name",
          "email": "$currentNode.inputs.userData.email"
        }
      }
    }
  ],
  "nextNodes": ["下一个节点名称"]
}
```
"""

    @staticmethod
    def get_system_prompt() -> str:
        """获取系统提示词"""
        node_specs = EnhancedWorkflowPromptTemplates.get_node_specifications()
        return f"""# 工作流生成专家

你是一个专业的工作流生成专家，能够根据用户需求创建精确的工作流节点定义。

## 🎯 核心任务
根据用户的自然语言描述，生成完整的JSON格式工作流定义，确保逻辑清晰、结构完整、可直接执行。

{node_specs}

## 🔗 工作流生成规则

### 1. 数据流设计
- **顺序执行**: 按照nextNodes定义的顺序执行节点
- **条件分支**: 条件节点通过内部逻辑决定流向
- **数据传递**: 严格遵循数据引用规范，确保数据流正确

### 2. 节点命名规范
- 使用PascalCase命名
- 名称具有描述性
- 全局唯一性

### 3. 错误处理
- 合理设置超时时间
- 添加必要的条件检查
- 考虑异常情况的处理

### 4. 性能优化
- 避免不必要的循环
- 合理使用并发执行
- 优化数据库查询

## 📐 生成要求

### JSON结构要求
```json
{{
  "nodes": [
    {{
      "name": "节点名称",
      "type": "节点类型",
      "desc": "节点描述",
      "inputs": {{}},
      "outputs": {{}},
      "configs": {{}},
      "nextNodes": []
    }}
  ]
}}
```

### 质量标准
1. **完整性**: 每个节点包含所有必需字段
2. **一致性**: 数据类型和引用路径正确
3. **可执行性**: 配置参数完整有效
4. **可读性**: 描述清晰，逻辑合理

## 🚀 生成流程

1. **需求分析**: 理解用户描述的核心需求
2. **流程设计**: 分解为具体的处理步骤
3. **节点选择**: 为每个步骤选择最合适的节点类型
4. **连接设计**: 确定节点间的数据流向
5. **优化完善**: 调整配置，添加错误处理

## ⚠️ 重要提醒

- 只返回JSON格式的工作流定义
- 不要包含任何解释文字或markdown格式
- 确保JSON语法完全正确
- 所有字符串使用双引号
- 严格遵循节点规范和数据引用规则

现在，请根据用户需求生成完整的工作流定义。"""

    @staticmethod
    def get_user_prompt_template() -> str:
        """获取用户提示词模板"""
        return """# 工作流生成请求

## 📝 用户需求
**任务描述**: {task_description}

## 🔍 上下文信息
{context_info}

## ⚙️ 生成参数
- **复杂度级别**: {complexity_level}
- **包含错误处理**: {include_error_handling}
- **优先考虑**: {priority_focus}

## 📋 具体要求

请按照以下步骤生成工作流:

1. **需求分析**: 
   - 识别核心业务流程
   - 确定必要的输入和输出
   - 分析处理步骤和逻辑

2. **节点规划**:
   - 选择合适的节点类型
   - 设计节点间的连接关系
   - 规划数据流向

3. **细节实现**:
   - 配置每个节点的详细参数
   - 设置正确的数据引用
   - 确保节点名称全局唯一

4. **质量检查**:
   - 验证JSON格式正确性
   - 检查节点连接完整性
   - 确保逻辑流程合理

请直接返回完整的JSON工作流定义，严格遵循节点规范，无需其他说明。"""

    @classmethod
    def build_user_prompt(
        cls, 
        task_description: str, 
        context: Dict[str, Any] = None, 
        parameters: Dict[str, Any] = None
    ) -> str:
        """构建用户提示词"""
        
        # 处理上下文信息
        context_info = ""
        if context:
            for key, value in context.items():
                context_info += f"- **{key}**: {value}\n"
        else:
            context_info = "- 无额外上下文信息"
        
        # 获取参数值
        if parameters is None:
            parameters = {}
            
        complexity_level = parameters.get("complexity_level", "medium")
        include_error_handling = parameters.get("include_error_handling", True)
        priority_focus = parameters.get("priority_focus", "功能完整性")
        
        return cls.get_user_prompt_template().format(
            task_description=task_description,
            context_info=context_info,
            complexity_level=complexity_level,
            include_error_handling="是" if include_error_handling else "否",
            priority_focus=priority_focus
        )

    @staticmethod
    def get_scenario_specific_prompts() -> Dict[str, str]:
        """获取特定场景的专用提示词"""
        return {
            "user_management": """
## 用户管理场景特殊要求:
- 使用 dbQuery 节点查询用户信息
- 使用 dbCreate/dbUpdate/dbDelete 节点管理用户数据
- 使用 condition 节点进行权限检查
- 使用 transaction 节点确保数据一致性
- 添加适当的错误处理和验证
            """,
            
            "data_processing": """
## 数据处理场景特殊要求:
- 使用 code 节点进行数据转换和计算
- 使用 dbQuery 节点获取源数据
- 使用 condition 节点进行数据验证
- 考虑大数据量的分页处理
- 添加数据质量检查
            """,
            
            "api_integration": """
## API集成场景特殊要求:
- 使用 http 节点调用外部API
- 添加请求重试和超时处理
- 使用 condition 节点检查响应状态
- 考虑认证和安全机制
- 处理不同的响应格式
            """,
            
            "ai_workflow": """
## AI工作流场景特殊要求:
- 使用 llm 节点进行AI对话
- 配置合适的系统提示词
- 使用 code 节点进行输入预处理
- 添加输出后处理和验证
- 考虑模型选择和参数优化
            """,
            
            "business_process": """
## 业务流程场景特殊要求:
- 使用 condition 节点实现业务规则
- 使用 transaction 节点确保事务性
- 添加多个审批和验证步骤
- 考虑并行处理和同步点
- 实现完整的错误处理机制
            """
        }

    @staticmethod
    def get_validation_rules() -> Dict[str, str]:
        """获取验证规则"""
        return {
            "required_fields": "每个节点必须包含 name, type, desc, inputs, outputs, configs, nextNodes 字段",
            "unique_names": "所有节点名称必须全局唯一",
            "valid_types": "节点类型必须是预定义的11种类型之一",
            "data_references": "数据引用必须遵循 $prevNode.outputs.* 或 $currentNode.inputs.* 格式",
            "flow_integrity": "每个节点（除结束节点）必须有明确的下一步流向",
            "json_format": "输出必须是有效的JSON格式"
        }

    @staticmethod
    def get_optimization_suggestions() -> List[str]:
        """获取优化建议"""
        return [
            "合理使用 transaction 节点确保数据一致性",
            "在关键节点添加 condition 检查避免错误传播",
            "设置合适的超时时间避免长时间等待",
            "使用 code 节点进行复杂的数据处理和验证",
            "为数据库操作添加适当的索引字段查询",
            "在 http 节点中添加重试机制",
            "为 llm 节点配置合适的参数以获得最佳效果",
            "使用并行处理提高整体执行效率",
            "添加错误处理分支处理异常情况",
            "优化节点间的数据传递减少不必要的数据复制"
        ] 