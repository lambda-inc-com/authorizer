"""
多智能体工作流生成系统
Multi-Agent Workflow Generator System

该系统采用三个智能体协同工作：
1. RequirementAnalyzer - 需求分析智能体
2. WorkflowComposer - 工作流组合智能体  
3. WorkflowValidator - 工作流验证智能体
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
from abc import ABC, abstractmethod

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """智能体角色枚举"""
    REQUIREMENT_ANALYZER = "requirement_analyzer"
    WORKFLOW_COMPOSER = "workflow_composer"
    WORKFLOW_VALIDATOR = "workflow_validator"


class MessageType(Enum):
    """消息类型枚举"""
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    VALIDATION_FAILED = "validation_failed"
    RETRY_REQUEST = "retry_request"
    INFORMATION_SHARE = "information_share"


@dataclass
class AgentMessage:
    """智能体间消息"""
    sender: AgentRole
    receiver: Optional[AgentRole]
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: str = field(default_factory=lambda: str(datetime.now().timestamp()))


@dataclass
class SharedContext:
    """共享上下文"""
    user_requirement: str = ""
    analyzed_nodes: List[Dict[str, Any]] = field(default_factory=list)
    node_generation_prompts: List[Dict[str, Any]] = field(default_factory=list)
    composed_workflow: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    generation_history: List[Dict[str, Any]] = field(default_factory=list)


class MessageBus:
    """消息总线 - 负责智能体间的消息传递"""
    
    def __init__(self):
        self.subscribers: Dict[AgentRole, List[callable]] = {}
        self.message_history: List[AgentMessage] = []
    
    def subscribe(self, agent_role: AgentRole, callback: callable):
        """订阅消息"""
        if agent_role not in self.subscribers:
            self.subscribers[agent_role] = []
        self.subscribers[agent_role].append(callback)
    
    async def publish(self, message: AgentMessage):
        """发布消息"""
        self.message_history.append(message)
        logger.info(f"消息发布: {message.sender.value} -> {message.receiver.value if message.receiver else 'ALL'}: {message.message_type.value}")
        
        # 如果有指定接收者，只发送给指定接收者
        if message.receiver and message.receiver in self.subscribers:
            for callback in self.subscribers[message.receiver]:
                await callback(message)
        # 如果没有指定接收者，广播给所有订阅者
        elif not message.receiver:
            for role, callbacks in self.subscribers.items():
                if role != message.sender:  # 不发送给自己
                    for callback in callbacks:
                        await callback(message)


class SharedStateManager:
    """共享状态管理器"""
    
    def __init__(self):
        self.context = SharedContext()
        self._lock = asyncio.Lock()
    
    async def update_context(self, updates: Dict[str, Any]):
        """更新共享上下文"""
        async with self._lock:
            for key, value in updates.items():
                if hasattr(self.context, key):
                    setattr(self.context, key, value)
                    logger.info(f"更新共享上下文: {key}")
    
    async def get_context(self) -> SharedContext:
        """获取共享上下文"""
        async with self._lock:
            return self.context
    
    async def add_generation_history(self, stage: str, result: Dict[str, Any]):
        """添加生成历史记录"""
        async with self._lock:
            self.context.generation_history.append({
                "stage": stage,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })


class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, role: AgentRole, message_bus: MessageBus, state_manager: SharedStateManager):
        self.role = role
        self.message_bus = message_bus
        self.state_manager = state_manager
        self.is_busy = False
        self.last_task_success = True  # 跟踪最后一个任务的成功状态
        
        # 订阅消息
        self.message_bus.subscribe(self.role, self._handle_message)
    
    @abstractmethod
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务 - 子类必须实现"""
        pass
    
    async def _handle_message(self, message: AgentMessage):
        """处理接收到的消息"""
        logger.info(f"{self.role.value} 收到消息: {message.message_type.value}")
        
        if message.message_type == MessageType.TASK_START:
            await self._execute_task(message.content)
        elif message.message_type == MessageType.RETRY_REQUEST:
            await self._handle_retry(message.content)
    
    async def _execute_task(self, task_data: Dict[str, Any]):
        """执行任务"""
        try:
            self.is_busy = True
            self.last_task_success = False  # 默认为失败，成功完成后设置为True
            logger.info(f"{self.role.value} 开始执行任务")
            
            result = await self.process_task(task_data)
            
            # 任务成功完成
            self.last_task_success = True
            
            # 发送完成消息
            await self.message_bus.publish(AgentMessage(
                sender=self.role,
                receiver=None,
                message_type=MessageType.TASK_COMPLETE,
                content={"result": result}
            ))
            
            logger.info(f"{self.role.value} 任务完成")
            
        except Exception as e:
            self.last_task_success = False
            logger.error(f"{self.role.value} 任务失败: {str(e)}")
            await self.message_bus.publish(AgentMessage(
                sender=self.role,
                receiver=None,
                message_type=MessageType.TASK_FAILED,
                content={"error": str(e)}
            ))
        finally:
            self.is_busy = False
    
    async def _handle_retry(self, retry_data: Dict[str, Any]):
        """处理重试请求"""
        context = await self.state_manager.get_context()
        if context.retry_count < context.max_retries:
            await self.state_manager.update_context({"retry_count": context.retry_count + 1})
            await self._execute_task(retry_data)
        else:
            logger.error(f"{self.role.value} 达到最大重试次数，任务失败")


class MultiAgentOrchestrator:
    """多智能体协调器"""
    
    def __init__(self):
        self.message_bus = MessageBus()
        self.state_manager = SharedStateManager()
        self.agents: Dict[AgentRole, BaseAgent] = {}
        self._setup_agents()
    
    def _setup_agents(self):
        """设置智能体"""
        # 将在子类中实现具体的智能体
        pass
    
    async def generate_workflow(self, user_requirement: str) -> Dict[str, Any]:
        """生成工作流的主要方法"""
        try:
            # 初始化共享上下文
            await self.state_manager.update_context({
                "user_requirement": user_requirement,
                "retry_count": 0
            })
            
            logger.info("开始多智能体工作流生成")
            
            # 阶段1: 需求分析
            logger.info("阶段1: 需求分析")
            stage1_success = await self._execute_requirement_analysis()
            
            # 🔥 如果第一阶段失败，停止整个流程
            if not stage1_success:
                context = await self.state_manager.get_context()
                return {
                    "success": False,
                    "error": "需求分析阶段失败，无法继续生成工作流",
                    "generation_history": context.generation_history
                }
            
            # 阶段2: 工作流组合
            logger.info("阶段2: 工作流组合")
            stage2_success = await self._execute_workflow_composition()
            
            # 如果第二阶段失败，也停止流程
            if not stage2_success:
                context = await self.state_manager.get_context()
                return {
                    "success": False,
                    "error": "工作流组合阶段失败",
                    "generation_history": context.generation_history
                }
            
            # 阶段3: 工作流验证
            logger.info("阶段3: 工作流验证")
            validation_result = await self._execute_workflow_validation()
            
            # 如果验证失败，进行重试
            if not validation_result["is_valid"]:
                await self._handle_validation_failure(validation_result)
            
            context = await self.state_manager.get_context()
            return {
                "success": True,
                "workflow": context.composed_workflow,
                "generation_history": context.generation_history
            }
            
        except Exception as e:
            logger.error(f"工作流生成失败: {str(e)}")
            context = await self.state_manager.get_context()
            return {
                "success": False,
                "error": str(e),
                "generation_history": getattr(context, 'generation_history', [])
            }
    
    async def _execute_requirement_analysis(self) -> bool:
        """执行需求分析"""
        try:
            await self.message_bus.publish(AgentMessage(
                sender=AgentRole.REQUIREMENT_ANALYZER,
                receiver=AgentRole.REQUIREMENT_ANALYZER,
                message_type=MessageType.TASK_START,
                content={}
            ))
            
            # 等待任务完成
            success = await self._wait_for_task_completion(AgentRole.REQUIREMENT_ANALYZER)
            return success
        except Exception as e:
            logger.error(f"需求分析阶段异常: {str(e)}")
            return False
    
    async def _execute_workflow_composition(self) -> bool:
        """执行工作流组合"""
        try:
            await self.message_bus.publish(AgentMessage(
                sender=AgentRole.WORKFLOW_COMPOSER,
                receiver=AgentRole.WORKFLOW_COMPOSER,
                message_type=MessageType.TASK_START,
                content={}
            ))
            
            # 等待任务完成
            success = await self._wait_for_task_completion(AgentRole.WORKFLOW_COMPOSER)
            return success
        except Exception as e:
            logger.error(f"工作流组合阶段异常: {str(e)}")
            return False
    
    async def _execute_workflow_validation(self) -> Dict[str, Any]:
        """执行工作流验证"""
        await self.message_bus.publish(AgentMessage(
            sender=AgentRole.WORKFLOW_VALIDATOR,
            receiver=AgentRole.WORKFLOW_VALIDATOR,
            message_type=MessageType.TASK_START,
            content={}
        ))
        
        # 等待任务完成
        await self._wait_for_task_completion(AgentRole.WORKFLOW_VALIDATOR)
        
        context = await self.state_manager.get_context()
        return {
            "is_valid": len(context.validation_errors) == 0,
            "errors": context.validation_errors
        }
    
    async def _wait_for_task_completion(self, agent_role: AgentRole) -> bool:
        """等待任务完成并返回成功状态"""
        # 等待智能体完成任务
        timeout = 120  # 2分钟超时
        start_time = asyncio.get_event_loop().time()
        
        while self.agents[agent_role].is_busy:
            # 检查超时
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.error(f"{agent_role.value} 任务超时")
                return False
                
            await asyncio.sleep(0.1)
        
        # 检查任务是否成功完成
        # 我们需要在智能体中设置一个状态来跟踪最后的任务结果
        agent = self.agents[agent_role]
        if hasattr(agent, 'last_task_success'):
            return agent.last_task_success
        
        # 如果没有明确的失败信息，假设成功
        return True
    
    async def _handle_validation_failure(self, validation_result: Dict[str, Any]):
        """处理验证失败"""
        context = await self.state_manager.get_context()
        
        if context.retry_count < context.max_retries:
            logger.info(f"验证失败，开始第 {context.retry_count + 1} 次重试")
            
            # 发送重试请求给工作流组合智能体
            await self.message_bus.publish(AgentMessage(
                sender=AgentRole.WORKFLOW_VALIDATOR,
                receiver=AgentRole.WORKFLOW_COMPOSER,
                message_type=MessageType.RETRY_REQUEST,
                content={
                    "errors": validation_result["errors"],
                    "previous_workflow": context.composed_workflow
                }
            ))
            
            # 重新执行工作流组合和验证
            await self._execute_workflow_composition()
            await self._execute_workflow_validation()
        else:
            raise Exception(f"达到最大重试次数，工作流生成失败: {validation_result['errors']}") 