"""
工作流生成智能体提示词模板

包含不同场景下的专业提示词模板
"""

from typing import Dict, Any


class WorkflowPromptTemplates:
    """工作流提示词模板类"""
    
    @staticmethod
    def get_system_prompt() -> str:
        """获取系统提示词"""
        return """# 工作流生成专家

你是一个专业的工作流生成专家，能够根据用户需求创建精确的工作流节点定义。

## 🎯 核心任务
根据用户的自然语言描述，生成完整的JSON格式工作流定义，确保逻辑清晰、结构完整、可直接执行。

## 📋 可用节点类型

### 1. workflowStart - 工作流开始节点
- **用途**: 定义工作流的输入参数
- **结构**: 必须包含用户需要的输入字段
- **注意**: showInputs=true, showOutputs=false

### 2. workflowEnd - 工作流结束节点  
- **用途**: 定义工作流的输出结果
- **结构**: 通过valuePath连接到前置节点的输出
- **注意**: showInputs=false, showOutputs=true

### 3. condition - 条件判断节点
- **用途**: 支持复杂的条件逻辑判断
- **特性**: 可以有多个分支输出，使用sourceHandleId
- **格式**: conditions数组，支持AND/OR关系

### 4. code - 代码执行节点
- **用途**: 执行JavaScript代码
- **功能**: 数据处理、计算逻辑、格式转换
- **输出**: return字段为函数返回值

### 5. chatWithLLM - LLM聊天节点
- **用途**: 调用大语言模型进行对话
- **配置**: modelId, systemPrompt, userInput
- **输出**: modelOutput为模型回复内容

### 6. dbQuery - 数据库查询节点
- **用途**: 执行SQL查询
- **输入**: query字段包含SQL语句
- **输出**: result为查询结果

### 7. httpRequest - HTTP请求节点
- **用途**: 发送HTTP请求，调用外部API
- **配置**: method, url, headers, body等
- **输出**: result为响应内容

## 🔗 节点连接规则

1. **valuePath格式**: ["源节点ID", "inputs/outputs", "字段ID"]
2. **条件节点分支**: 使用sourceHandleId指定具体条件
3. **数据类型匹配**: 确保输出类型与输入类型兼容
4. **依赖关系**: 前置节点必须先执行完成

## 📐 生成要求

### 必须遵循的规则:
1. **唯一性**: 所有节点ID和字段ID必须全局唯一
2. **完整性**: 每个节点必须包含完整的data结构
3. **连通性**: 所有节点通过edges正确连接
4. **类型安全**: valuePath引用的字段必须存在且类型匹配
5. **布局合理**: position坐标形成清晰的从左到右流向

### JSON结构要求:
```json
{
  "nodes": [
    {
      "id": "唯一节点ID",
      "type": "节点类型",
      "position": {"x": 数值, "y": 数值},
      "data": {
        "showInputs": boolean,
        "showOutputs": boolean,
        "label": "节点标签",
        "inputs": [输入字段数组],
        "outputs": [输出字段数组]
      }
    }
  ],
  "edges": [
    {
      "source": "源节点ID",
      "target": "目标节点ID",
      "id": "连接ID"
    }
  ]
}
```

## 🎨 设计原则

1. **用户友好**: 节点标签使用中文，清晰表达功能
2. **逻辑清晰**: 工作流程符合业务逻辑和常识
3. **可扩展性**: 预留扩展接口，便于后续优化
4. **错误处理**: 在关键节点添加错误处理逻辑
5. **性能考虑**: 避免不必要的循环和重复计算

## 🚀 生成流程

1. **需求分析**: 理解用户描述的核心需求
2. **流程设计**: 分解为具体的处理步骤
3. **节点选择**: 为每个步骤选择最合适的节点类型
4. **连接设计**: 确定节点间的数据流向
5. **优化完善**: 调整布局，添加错误处理

## ⚠️ 重要提醒

- 只返回JSON格式的工作流定义
- 不要包含任何解释文字或markdown格式
- 确保JSON语法完全正确
- 所有字符串使用双引号
- 布尔值使用true/false（小写）
- 数值不加引号

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
- **输出格式**: {output_format}
- **错误处理**: {include_error_handling}

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
   - 设置正确的valuePath连接
   - 确保ID全局唯一

4. **质量检查**:
   - 验证JSON格式正确性
   - 检查节点连接完整性
   - 确保逻辑流程合理

请直接返回完整的JSON工作流定义，无需其他说明。"""

    @classmethod
    def build_user_prompt(
        cls, 
        task_description: str, 
        context: Dict[str, Any], 
        parameters: Dict[str, Any]
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
        complexity_level = parameters.get("complexity_level", "medium")
        output_format = parameters.get("output_format", "standard")
        include_error_handling = parameters.get("include_error_handling", True)
        
        return cls.get_user_prompt_template().format(
            task_description=task_description,
            context_info=context_info,
            complexity_level=complexity_level,
            output_format=output_format,
            include_error_handling="是" if include_error_handling else "否"
        )

    @staticmethod
    def get_scenario_prompts() -> Dict[str, str]:
        """获取不同场景的专用提示词"""
        return {
            "data_analysis": """
特别关注数据分析场景:
- 优先使用dbQuery节点获取数据
- 使用code节点进行数据处理和统计计算
- 通过chatWithLLM节点生成分析洞察
- 确保数据流向清晰，结果可解释
            """,
            
            "customer_service": """
特别关注客服场景:
- 使用condition节点进行问题分类
- 为不同问题类型配置专门的LLM节点
- 设置合适的系统提示词以体现专业性
- 考虑多轮对话和上下文记忆
            """,
            
            "document_processing": """
特别关注文档处理场景:
- 使用httpRequest节点获取文档内容
- 通过chatWithLLM节点进行文档分析
- 支持多种处理类型（摘要、翻译、提取）
- 考虑文档格式和大小限制
            """,
            
            "api_integration": """
特别关注API集成场景:
- 合理配置httpRequest节点参数
- 添加响应验证和错误处理
- 支持多种认证方式
- 考虑超时和重试机制
            """,
            
            "workflow_orchestration": """
特别关注工作流编排场景:
- 使用condition节点实现复杂的条件分支
- 合理安排节点执行顺序
- 添加并行处理和同步点
- 考虑异常处理和回滚机制
            """
        }

    @staticmethod
    def get_validation_prompts() -> Dict[str, str]:
        """获取验证相关的提示词"""
        return {
            "structure_check": """
请验证工作流结构:
1. 必须包含nodes和edges数组
2. 每个节点必须有id、type、position、data字段
3. 每条边必须有source、target、id字段
4. 所有引用的节点ID必须存在
            """,
            
            "logic_check": """
请验证工作流逻辑:
1. 开始节点只能有输出，结束节点只能有输入
2. 条件节点必须有多个输出分支
3. valuePath引用必须指向有效的字段
4. 数据类型必须匹配
            """,
            
            "best_practices": """
请遵循最佳实践:
1. 节点布局从左到右，层次清晰
2. 使用有意义的节点和字段标签
3. 适当的错误处理和验证
4. 避免过于复杂的单一节点
            """
        }


# 使用示例
if __name__ == "__main__":
    templates = WorkflowPromptTemplates()
    
    # 获取系统提示词
    system_prompt = templates.get_system_prompt()
    print("系统提示词长度:", len(system_prompt))
    
    # 构建用户提示词
    user_prompt = templates.build_user_prompt(
        task_description="创建一个数据分析工作流",
        context={"domain": "电商", "data_source": "MySQL"},
        parameters={"complexity_level": "medium"}
    )
    print("用户提示词长度:", len(user_prompt)) 