"""
多智能体工作流生成系统 - 完整实现
Multi-Agent Workflow Generation System - Complete Implementation
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from .multi_agent_workflow_generator import MultiAgentOrchestrator, AgentRole
from .agents.requirement_analyzer import RequirementAnalyzer
from .agents.workflow_composer import WorkflowComposer
from .agents.workflow_validator import WorkflowValidator

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端接口"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url
    
    async def chat_completion(self, messages: list, model: str = "gpt-4", **kwargs) -> str:
        """
        LLM聊天完成接口
        这里需要集成实际的LLM服务，比如OpenAI API
        """
        # 这里应该调用实际的LLM服务
        # 临时返回模拟响应
        return self._mock_llm_response(messages, model, **kwargs)
    
    def _mock_llm_response(self, messages: list, model: str, **kwargs) -> str:
        """模拟LLM响应，用于测试"""
        user_message = messages[-1]["content"] if messages else ""
        
        # 根据用户消息类型返回不同的模拟响应
        if "分析以下用户需求" in user_message:
            return self._mock_requirement_analysis_response()
        elif "请根据用户需求和需求分析结果" in user_message:
            return self._mock_workflow_composition_response()
        elif "请对以下工作流进行全面验证" in user_message:
            return self._mock_validation_response()
        else:
            return '{"error": "未知的请求类型"}'
    
    def _mock_requirement_analysis_response(self) -> str:
        """模拟需求分析响应"""
        return """```json
{
  "analysis": {
    "requirement_summary": "用户需要创建一个简单的数据查询和处理工作流",
    "key_actions": ["查询数据", "处理数据", "返回结果"],
    "data_entities": ["用户数据", "查询结果"],
    "business_rules": ["数据必须存在", "结果必须格式化"]
  },
  "required_nodes": [
    {
      "type": "workflowStart",
      "purpose": "工作流开始节点",
      "description": "定义工作流的输入参数和触发方式",
      "suggested_name": "WorkflowStart",
      "key_configs": {}
    },
    {
      "type": "dbQuery",
      "purpose": "查询用户数据",
      "description": "从数据库中查询用户信息",
      "suggested_name": "QueryUserData",
      "key_configs": {
        "table": "users",
        "fields": ["id", "name", "email"]
      }
    },
    {
      "type": "workflowEnd",
      "purpose": "工作流结束节点",
      "description": "定义工作流的输出结果",
      "suggested_name": "WorkflowEnd",
      "key_configs": {}
    }
  ],
  "workflow_complexity": "简单",
  "estimated_nodes_count": 3
}
```"""
    
    def _mock_workflow_composition_response(self) -> str:
        """模拟工作流组合响应"""
        return """```json
{
  "workflow": {
    "name": "用户数据查询工作流",
    "description": "查询和处理用户数据的工作流",
    "version": "1.0.0",
    "nodes": [
      {
        "name": "WorkflowStart",
        "type": "workflowStart",
        "desc": "工作流开始节点，定义输入参数",
        "inputs": {
          "userId": {
            "type": "string",
            "value": "",
            "desc": "用户ID"
          }
        },
        "outputs": {
          "userId": {
            "type": "string",
            "value": "$currentNode.inputs.userId",
            "desc": "用户ID"
          }
        },
        "configs": {},
        "nextNodes": ["QueryUserData"]
      },
      {
        "name": "QueryUserData",
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
          "userData": {
            "type": "object",
            "value": "$currentNodeResult",
            "desc": "用户数据"
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
          ]
        },
        "nextNodes": ["WorkflowEnd"]
      },
      {
        "name": "WorkflowEnd",
        "type": "workflowEnd",
        "desc": "工作流结束节点",
        "inputs": {
          "userData": {
            "type": "object",
            "value": "$prevNode.outputs.userData",
            "desc": "用户数据"
          }
        },
        "outputs": {
          "result": {
            "type": "object",
            "value": "$currentNode.inputs.userData",
            "desc": "最终结果"
          }
        },
        "configs": {},
        "nextNodes": ["end"]
      }
    ]
  },
  "composition_notes": {
    "data_flow": ["从开始节点获取userId", "传递到查询节点", "查询结果传递到结束节点"],
    "business_logic": ["简单的用户数据查询流程"],
    "key_decisions": ["使用数据库查询节点获取用户信息"]
  }
}
```"""
    
    def _mock_validation_response(self) -> str:
        """模拟验证响应"""
        return """```json
{
  "validation_result": {
    "is_valid": true,
    "overall_score": 95,
    "error_count": 0,
    "warning_count": 1
  },
  "detailed_results": {
    "structure_validation": {
      "passed": true,
      "errors": [],
      "warnings": []
    },
    "configuration_validation": {
      "passed": true,
      "errors": [],
      "warnings": ["建议为数据库查询添加超时配置"]
    },
    "logic_validation": {
      "passed": true,
      "errors": [],
      "warnings": []
    },
    "executability_validation": {
      "passed": true,
      "errors": [],
      "warnings": []
    }
  },
  "suggestions": [
    {
      "type": "warning",
      "description": "建议为数据库查询添加超时配置",
      "node": "QueryUserData",
      "solution": "在configs中添加timeout字段"
    }
  ],
  "compliance_check": {
    "node_specification_compliance": true,
    "data_flow_compliance": true,
    "business_logic_compliance": true
  }
}
```"""


class WorkflowGenerationSystem(MultiAgentOrchestrator):
    """工作流生成系统 - 完整实现"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__()
        self.llm_client = llm_client or LLMClient()
        self._setup_agents()
    
    def _setup_agents(self):
        """设置智能体"""
        # 创建三个智能体实例
        self.agents[AgentRole.REQUIREMENT_ANALYZER] = RequirementAnalyzer(
            self.message_bus,
            self.state_manager,
            self.llm_client
        )
        
        self.agents[AgentRole.WORKFLOW_COMPOSER] = WorkflowComposer(
            self.message_bus,
            self.state_manager,
            self.llm_client
        )
        
        self.agents[AgentRole.WORKFLOW_VALIDATOR] = WorkflowValidator(
            self.message_bus,
            self.state_manager,
            self.llm_client
        )
        
        logger.info("智能体设置完成")
    
    async def generate_workflow_from_requirement(self, user_requirement: str) -> Dict[str, Any]:
        """从用户需求生成工作流"""
        try:
            logger.info(f"开始生成工作流，用户需求: {user_requirement}")
            
            # 调用父类的生成方法
            result = await self.generate_workflow(user_requirement)
            
            if result["success"]:
                logger.info("工作流生成成功")
                return {
                    "success": True,
                    "workflow": result["workflow"],
                    "generation_history": result["generation_history"],
                    "message": "工作流生成成功"
                }
            else:
                logger.error(f"工作流生成失败: {result['error']}")
                return {
                    "success": False,
                    "error": result["error"],
                    "message": "工作流生成失败"
                }
        
        except Exception as e:
            logger.error(f"工作流生成系统异常: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "工作流生成系统异常"
            }
    
    async def validate_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """验证工作流"""
        try:
            # 更新共享上下文
            await self.state_manager.update_context({
                "composed_workflow": workflow
            })
            
            # 执行验证
            validation_result = await self._execute_workflow_validation()
            
            return {
                "success": True,
                "validation_result": validation_result,
                "message": "工作流验证完成"
            }
        
        except Exception as e:
            logger.error(f"工作流验证失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "工作流验证失败"
            }
    
    async def get_generation_history(self) -> Dict[str, Any]:
        """获取生成历史"""
        try:
            context = await self.state_manager.get_context()
            return {
                "success": True,
                "generation_history": context.generation_history,
                "message": "获取生成历史成功"
            }
        
        except Exception as e:
            logger.error(f"获取生成历史失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "获取生成历史失败"
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "agents_status": {
                role.value: {
                    "is_busy": agent.is_busy,
                    "role": role.value
                }
                for role, agent in self.agents.items()
            },
            "message_bus_status": {
                "subscribers_count": len(self.message_bus.subscribers),
                "message_history_count": len(self.message_bus.message_history)
            },
            "system_ready": len(self.agents) == 3
        }


# 使用示例和测试函数
async def test_workflow_generation():
    """测试工作流生成功能"""
    print("🚀 开始测试多智能体工作流生成系统")
    
    # 创建系统实例
    system = WorkflowGenerationSystem()
    
    # 测试系统状态
    print("\n📊 系统状态:")
    status = system.get_system_status()
    print(f"智能体数量: {len(status['agents_status'])}")
    print(f"系统就绪: {status['system_ready']}")
    
    # 测试工作流生成
    print("\n🔧 测试工作流生成:")
    user_requirement = "我需要一个工作流来查询用户信息，然后根据用户类型进行不同的处理"
    
    try:
        result = await system.generate_workflow_from_requirement(user_requirement)
        
        if result["success"]:
            print("✅ 工作流生成成功!")
            print(f"工作流名称: {result['workflow']['name']}")
            print(f"节点数量: {len(result['workflow']['nodes'])}")
            print(f"生成历史记录: {len(result['generation_history'])}")
            
            # 验证生成的工作流
            print("\n🔍 验证生成的工作流:")
            validation_result = await system.validate_workflow(result['workflow'])
            
            if validation_result["success"]:
                val_result = validation_result["validation_result"]
                print(f"✅ 验证通过: {val_result['validation_result']['is_valid']}")
                print(f"评分: {val_result['validation_result']['overall_score']}")
                print(f"错误数: {val_result['validation_result']['error_count']}")
                print(f"警告数: {val_result['validation_result']['warning_count']}")
            else:
                print(f"❌ 验证失败: {validation_result['error']}")
        else:
            print(f"❌ 工作流生成失败: {result['error']}")
    
    except Exception as e:
        print(f"❌ 测试过程中发生异常: {str(e)}")
    
    print("\n🎉 测试完成!")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_workflow_generation()) 