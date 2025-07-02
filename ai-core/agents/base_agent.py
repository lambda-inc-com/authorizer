"""
基础智能体类 - Base Agent

定义所有智能体的通用接口和基础功能
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime
from loguru import logger


class AgentCapability(Enum):
    """智能体能力枚举"""
    TEXT_GENERATION = "text_generation"
    DATA_ANALYSIS = "data_analysis"
    CODE_GENERATION = "code_generation"
    DOCUMENT_PROCESSING = "document_processing"
    WORKFLOW_ORCHESTRATION = "workflow_orchestration"
    API_INTEGRATION = "api_integration"
    DATABASE_QUERY = "database_query"
    FILE_PROCESSING = "file_processing"


@dataclass
class AgentConfig:
    """智能体配置"""
    name: str
    description: str
    capabilities: List[AgentCapability]
    model_preferences: Dict[str, str]
    max_iterations: int = 5
    timeout: int = 300


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    result: Dict[str, Any]
    error: Optional[str] = None
    execution_time: float = 0.0
    iterations_used: int = 0


class BaseAgent(ABC):
    """基础智能体抽象类"""
    
    def __init__(
        self, 
        model_service: Any = None, 
        workflow_engine: Any = None, 
        data_processor: Any = None
    ):
        self.model_service = model_service
        self.workflow_engine = workflow_engine
        self.data_processor = data_processor
        self.config = self.get_config()
        
    @abstractmethod
    def get_config(self) -> AgentConfig:
        """获取智能体配置"""
        pass
    
    @abstractmethod
    async def _execute_core_logic(
        self, 
        task_description: str, 
        context: Dict[str, Any], 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行核心逻辑 - 子类必须实现"""
        pass
    
    async def execute(
        self, 
        task_description: str, 
        context: Dict[str, Any] = None, 
        parameters: Dict[str, Any] = None
    ) -> ExecutionResult:
        """
        执行智能体任务
        
        Args:
            task_description: 任务描述
            context: 上下文信息
            parameters: 执行参数
            
        Returns:
            ExecutionResult: 执行结果
        """
        start_time = datetime.now()
        context = context or {}
        parameters = parameters or {}
        
        try:
            logger.info(f"🤖 智能体 {self.config.name} 开始执行任务: {task_description}")
            
            # 前置检查
            await self._pre_execution_checks(task_description, context, parameters)
            
            # 执行核心逻辑
            result = await asyncio.wait_for(
                self._execute_core_logic(task_description, context, parameters),
                timeout=self.config.timeout
            )
            
            # 后置处理
            final_result = await self._post_execution_processing(result, context)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.success(f"✅ 智能体 {self.config.name} 执行完成，耗时: {execution_time:.2f}s")
            
            return ExecutionResult(
                success=True,
                result=final_result,
                execution_time=execution_time,
                iterations_used=1
            )
            
        except asyncio.TimeoutError:
            error_msg = f"智能体执行超时 (>{self.config.timeout}s)"
            logger.error(f"⏰ {error_msg}")
            return ExecutionResult(
                success=False,
                result={},
                error=error_msg,
                execution_time=(datetime.now() - start_time).total_seconds()
            )
            
        except Exception as e:
            error_msg = f"智能体执行失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return ExecutionResult(
                success=False,
                result={},
                error=error_msg,
                execution_time=(datetime.now() - start_time).total_seconds()
            )
    
    async def _pre_execution_checks(
        self, 
        task_description: str, 
        context: Dict[str, Any], 
        parameters: Dict[str, Any]
    ):
        """前置执行检查"""
        # 基本检查
        if not task_description:
            raise ValueError("任务描述不能为空")
        
        # 调用子类的额外检查
        await self._additional_pre_checks(task_description, context, parameters)
    
    async def _additional_pre_checks(
        self, 
        task_description: str, 
        context: Dict[str, Any], 
        parameters: Dict[str, Any]
    ):
        """子类可重写的额外前置检查"""
        pass
    
    async def _post_execution_processing(
        self, 
        result: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """后置执行处理"""
        # 添加元数据
        result["_metadata"] = {
            "agent_name": self.config.name,
            "agent_capabilities": [cap.value for cap in self.config.capabilities],
            "execution_timestamp": datetime.now().isoformat(),
            "context_keys": list(context.keys()) if context else []
        }
        
        return result
    
    async def _call_model(
        self, 
        model_name: str, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> Dict[str, Any]:
        """调用模型服务"""
        if not self.model_service:
            raise ValueError("模型服务未配置")
        
        try:
            response = await self.model_service.chat(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response
            
        except Exception as e:
            logger.error(f"模型调用失败: {e}")
            
            # 尝试使用备用模型
            fallback_model = self.config.model_preferences.get("fallback_model")
            if fallback_model and fallback_model != model_name:
                logger.info(f"尝试使用备用模型: {fallback_model}")
                response = await self.model_service.chat(
                    model=fallback_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                return response
            else:
                raise e
    
    def get_capabilities(self) -> List[str]:
        """获取智能体能力列表"""
        return [cap.value for cap in self.config.capabilities]
    
    def supports_capability(self, capability: AgentCapability) -> bool:
        """检查是否支持特定能力"""
        return capability in self.config.capabilities
    
    def get_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        return {
            "name": self.config.name,
            "description": self.config.description,
            "capabilities": self.get_capabilities(),
            "model_preferences": self.config.model_preferences,
            "max_iterations": self.config.max_iterations,
            "timeout": self.config.timeout
        } 