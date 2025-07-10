"""
Python gRPC服务器 - AI Core流式服务
整合现有的多智能体工作流生成系统
"""

import asyncio
import grpc
from concurrent import futures
import time
import json
import logging
from typing import AsyncGenerator

# 导入现有的AI Core模块
from workflow_generation_system import WorkflowGenerationSystem
from multi_agent_workflow_generator import MultiAgentOrchestrator

# 导入生成的protobuf代码
import ai_service_stream_pb2
import ai_service_stream_pb2_grpc

logger = logging.getLogger(__name__)

class AIStreamServiceImpl(ai_service_stream_pb2_grpc.AIStreamServiceServicer):
    """AI流式服务实现"""
    
    def __init__(self):
        """初始化服务"""
        self.workflow_system = WorkflowGenerationSystem()
        
    async def StreamChat(self, request, context):
        """流式聊天接口实现"""
        try:
            logger.info(f"开始流式聊天，用户：{request.user_id}，模型：{request.model_name}")
            
            # 转换消息格式
            messages = []
            for msg in request.messages:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # 调用LLM客户端进行流式聊天
            llm_client = self.workflow_system.llm_client
            
            # 模拟流式响应（实际需要根据具体LLM API实现）
            response_text = ""
            tokens_used = 0
            
            # 这里应该调用实际的流式LLM API
            # 为演示目的，我们模拟分块响应
            full_response = await self._get_llm_response(messages, request.model_name)
            
            # 分块发送响应
            chunk_size = 10  # 每个chunk的字符数
            for i in range(0, len(full_response), chunk_size):
                chunk = full_response[i:i+chunk_size]
                response_text += chunk
                tokens_used += len(chunk.split())
                
                # 创建流式响应
                yield ai_service_stream_pb2.StreamChatResponse(
                    content=chunk,
                    is_complete=False,
                    model_used=request.model_name,
                    tokens_used=tokens_used,
                    points_consumed=tokens_used * 2,  # 示例计算
                    finish_reason="",
                    error=""
                )
                
                # 模拟处理延迟
                await asyncio.sleep(0.1)
            
            # 发送最终响应
            yield ai_service_stream_pb2.StreamChatResponse(
                content="",
                is_complete=True,
                model_used=request.model_name,
                tokens_used=tokens_used,
                points_consumed=tokens_used * 2,
                finish_reason="stop",
                error=""
            )
            
        except Exception as e:
            logger.error(f"流式聊天错误：{str(e)}")
            yield ai_service_stream_pb2.StreamChatResponse(
                content="",
                is_complete=True,
                model_used=request.model_name,
                tokens_used=0,
                points_consumed=0,
                finish_reason="error",
                error=str(e)
            )
    
    async def StreamWorkflowGenerate(self, request, context):
        """流式工作流生成接口"""
        try:
            logger.info(f"开始流式工作流生成，用户：{request.user_id}")
            
            # 从输入中获取需求描述
            requirement = request.inputs.get("requirement", "")
            if not requirement:
                yield ai_service_stream_pb2.StreamWorkflowResponse(
                    workflow_id="",
                    status="error",
                    current_step="validation",
                    step_output="",
                    progress=0.0,
                    is_complete=True,
                    final_outputs={},
                    error="需求描述不能为空"
                )
                return
            
            workflow_id = f"wf_{int(time.time())}"
            
            # 发送开始状态
            yield ai_service_stream_pb2.StreamWorkflowResponse(
                workflow_id=workflow_id,
                status="started",
                current_step="initialization",
                step_output="开始工作流生成...",
                progress=0.0,
                is_complete=False,
                final_outputs={},
                error=""
            )
            
            # 模拟三个阶段的工作流生成
            stages = [
                ("需求分析", "requirement_analysis", 0.33),
                ("工作流组合", "workflow_composition", 0.66),
                ("工作流验证", "workflow_validation", 1.0)
            ]
            
            final_result = None
            
            for stage_name, stage_key, progress in stages:
                # 发送当前阶段状态
                yield ai_service_stream_pb2.StreamWorkflowResponse(
                    workflow_id=workflow_id,
                    status="processing",
                    current_step=stage_key,
                    step_output=f"正在执行：{stage_name}...",
                    progress=progress,
                    is_complete=False,
                    final_outputs={},
                    error=""
                )
                
                # 模拟处理时间
                await asyncio.sleep(2)
                
                # 如果是最后阶段，调用实际的工作流生成
                if stage_key == "workflow_validation":
                    result = await self.workflow_system.generate_workflow_from_requirement(requirement)
                    final_result = result
                
                # 发送阶段完成状态
                yield ai_service_stream_pb2.StreamWorkflowResponse(
                    workflow_id=workflow_id,
                    status="processing",
                    current_step=stage_key,
                    step_output=f"{stage_name}完成",
                    progress=progress,
                    is_complete=False,
                    final_outputs={},
                    error=""
                )
            
            # 发送最终结果
            if final_result and final_result.get("success"):
                workflow = final_result["workflow"]
                final_outputs = {
                    "workflow_name": workflow.get("name", ""),
                    "node_count": str(len(workflow.get("nodes", []))),
                    "workflow_json": json.dumps(workflow, ensure_ascii=False)
                }
                
                yield ai_service_stream_pb2.StreamWorkflowResponse(
                    workflow_id=workflow_id,
                    status="completed",
                    current_step="finished",
                    step_output="工作流生成完成",
                    progress=1.0,
                    is_complete=True,
                    final_outputs=final_outputs,
                    error=""
                )
            else:
                error_msg = final_result.get("error", "生成失败") if final_result else "未知错误"
                yield ai_service_stream_pb2.StreamWorkflowResponse(
                    workflow_id=workflow_id,
                    status="failed",
                    current_step="error",
                    step_output="",
                    progress=1.0,
                    is_complete=True,
                    final_outputs={},
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"流式工作流生成错误：{str(e)}")
            yield ai_service_stream_pb2.StreamWorkflowResponse(
                workflow_id=workflow_id if 'workflow_id' in locals() else "",
                status="error",
                current_step="exception",
                step_output="",
                progress=0.0,
                is_complete=True,
                final_outputs={},
                error=str(e)
            )
    
    async def StreamWorkflowExecute(self, request, context):
        """流式工作流执行接口"""
        try:
            logger.info(f"开始流式工作流执行，用户：{request.user_id}，工作流：{request.workflow_name}")
            
            workflow_id = f"exec_{int(time.time())}"
            
            # 发送开始状态
            yield ai_service_stream_pb2.StreamWorkflowResponse(
                workflow_id=workflow_id,
                status="started",
                current_step="initialization",
                step_output="开始工作流执行...",
                progress=0.0,
                is_complete=False,
                final_outputs={},
                error=""
            )
            
            # 模拟工作流执行步骤
            steps = [
                ("输入验证", "input_validation", 0.2),
                ("节点执行", "node_execution", 0.6), 
                ("结果收集", "result_collection", 0.9),
                ("输出生成", "output_generation", 1.0)
            ]
            
            for step_name, step_key, progress in steps:
                # 发送步骤开始状态
                yield ai_service_stream_pb2.StreamWorkflowResponse(
                    workflow_id=workflow_id,
                    status="processing",
                    current_step=step_key,
                    step_output=f"正在执行：{step_name}...",
                    progress=progress,
                    is_complete=False,
                    final_outputs={},
                    error=""
                )
                
                # 模拟处理时间
                await asyncio.sleep(1.5)
                
                # 发送步骤完成状态
                yield ai_service_stream_pb2.StreamWorkflowResponse(
                    workflow_id=workflow_id,
                    status="processing", 
                    current_step=step_key,
                    step_output=f"{step_name}完成",
                    progress=progress,
                    is_complete=False,
                    final_outputs={},
                    error=""
                )
            
            # 发送最终完成状态
            final_outputs = {
                "execution_result": "工作流执行成功",
                "execution_time": "6.0s",
                "status": "completed"
            }
            
            yield ai_service_stream_pb2.StreamWorkflowResponse(
                workflow_id=workflow_id,
                status="completed",
                current_step="finished",
                step_output="工作流执行完成",
                progress=1.0,
                is_complete=True,
                final_outputs=final_outputs,
                error=""
            )
            
        except Exception as e:
            logger.error(f"流式工作流执行错误：{str(e)}")
            yield ai_service_stream_pb2.StreamWorkflowResponse(
                workflow_id=workflow_id if 'workflow_id' in locals() else "",
                status="error",
                current_step="exception",
                step_output="",
                progress=0.0,
                is_complete=True,
                final_outputs={},
                error=str(e)
            )
    
    async def _get_llm_response(self, messages, model_name):
        """获取LLM响应（示例实现）"""
        # 这里应该调用实际的LLM API
        # 为演示目的返回固定响应
        return f"这是来自{model_name}的响应，基于您的消息生成的回复内容。"


async def serve():
    """启动gRPC服务器"""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # 注册服务
    ai_service_stream_pb2_grpc.add_AIStreamServiceServicer_to_server(
        AIStreamServiceImpl(), server
    )
    
    # 配置监听地址
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    
    logger.info(f"启动AI gRPC流式服务，监听地址：{listen_addr}")
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("收到中断信号，关闭服务器...")
        await server.stop(5)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve()) 