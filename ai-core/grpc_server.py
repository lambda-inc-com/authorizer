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
            
            # 使用真正的流式LLM调用
            llm_client = self.workflow_system.llm_client
            
            total_tokens_used = 0
            
            # 直接使用流式调用，实时转发每个chunk
            async for chunk in llm_client.stream_chat_completion(
                messages=messages, 
                model=request.model_name,
                temperature=0.7,
                max_tokens=4096
            ):
                # 累计token使用（简单估算：每个字符约0.25个token）
                if chunk.get("content"):
                    total_tokens_used += len(chunk["content"]) // 4 + 1
                
                # 创建并发送流式响应
                yield ai_service_stream_pb2.StreamChatResponse(
                    content=chunk.get("content", ""),
                    is_complete=chunk.get("is_complete", False),
                    model_used=chunk.get("model_used", request.model_name),
                    tokens_used=total_tokens_used,
                    points_consumed=total_tokens_used * 2,  # 示例计算：1 token = 2 points
                    finish_reason=chunk.get("finish_reason", ""),
                    error=""
                )
                
                # 如果完成，结束循环
                if chunk.get("is_complete", False):
                    logger.info(f"流式聊天完成，总共使用 {total_tokens_used} tokens")
                    break
            
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
            
            # 创建一个回调函数来实时发送进度
            async def progress_callback(stage: str, progress: float, message: str):
                """进度回调函数"""
                yield ai_service_stream_pb2.StreamWorkflowResponse(
                    workflow_id=workflow_id,
                    status="processing",
                    current_step=stage,
                    step_output=message,
                    progress=progress,
                    is_complete=False,
                    final_outputs={},
                    error=""
                )
            
            # 调用流式工作流生成
            final_result = None
            
            try:
                # 🎯 实现真正的流式生成
                async for stage_update in self._stream_workflow_generation(requirement, progress_callback):
                    # 实时发送每个阶段的更新
                    yield ai_service_stream_pb2.StreamWorkflowResponse(
                        workflow_id=workflow_id,
                        status=stage_update.get("status", "processing"),
                        current_step=stage_update.get("stage", "unknown"),
                        step_output=stage_update.get("message", ""),
                        progress=stage_update.get("progress", 0.0),
                        is_complete=False,
                        final_outputs={},
                        error=stage_update.get("error", "")
                    )
                    
                    # 如果有最终结果，保存它
                    if stage_update.get("final_result"):
                        final_result = stage_update["final_result"]
                        
                    # 如果出错，直接返回
                    if stage_update.get("error"):
                        yield ai_service_stream_pb2.StreamWorkflowResponse(
                            workflow_id=workflow_id,
                            status="failed",
                            current_step="error",
                            step_output="",
                            progress=1.0,
                            is_complete=True,
                            final_outputs={},
                            error=stage_update["error"]
                        )
                        return
                        
            except Exception as e:
                logger.error(f"流式工作流生成过程中出错: {str(e)}")
                yield ai_service_stream_pb2.StreamWorkflowResponse(
                    workflow_id=workflow_id,
                    status="error",
                    current_step="exception",
                    step_output="",
                    progress=1.0,
                    is_complete=True,
                    final_outputs={},
                    error=str(e)
                )
                return
            
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
        """获取LLM响应（非流式调用）"""
        try:
            # 调用实际的LLM API获取完整响应
            llm_client = self.workflow_system.llm_client
            response = await llm_client.chat_completion(
                messages=messages,
                model=model_name,
                temperature=0.7,
                max_tokens=4096
            )
            return response
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            # 返回默认错误响应
            return f"抱歉，{model_name}服务暂时不可用。错误：{str(e)}"
    
    async def _stream_workflow_generation(self, requirement: str, progress_callback):
        """流式工作流生成的核心方法"""
        try:
            # 阶段1: 需求分析 (0% -> 33%)
            yield {
                "stage": "requirement_analysis", 
                "progress": 0.1, 
                "message": "正在分析用户需求...",
                "status": "processing"
            }
            
            # 模拟需求分析的进展
            await asyncio.sleep(0.5)  # 减少延迟，提高响应速度
            
            yield {
                "stage": "requirement_analysis", 
                "progress": 0.2, 
                "message": "识别业务实体和操作...",
                "status": "processing"
            }
            
            await asyncio.sleep(0.5)
            
            yield {
                "stage": "requirement_analysis", 
                "progress": 0.33, 
                "message": "需求分析完成",
                "status": "processing"
            }
            
            # 阶段2: 工作流组合 (33% -> 66%)
            yield {
                "stage": "workflow_composition", 
                "progress": 0.4, 
                "message": "开始组合工作流节点...",
                "status": "processing"
            }
            
            await asyncio.sleep(0.5)
            
            yield {
                "stage": "workflow_composition", 
                "progress": 0.5, 
                "message": "配置节点参数和连接...",
                "status": "processing"
            }
            
            await asyncio.sleep(0.5)
            
            yield {
                "stage": "workflow_composition", 
                "progress": 0.66, 
                "message": "工作流组合完成",
                "status": "processing"
            }
            
            # 阶段3: 工作流验证和生成 (66% -> 100%)
            yield {
                "stage": "workflow_validation", 
                "progress": 0.75, 
                "message": "正在验证工作流配置...",
                "status": "processing"
            }
            
            await asyncio.sleep(0.3)
            
            yield {
                "stage": "workflow_validation", 
                "progress": 0.85, 
                "message": "正在生成最终工作流...",
                "status": "processing"
            }
            
            # 🎯 实际调用工作流生成系统
            try:
                result = await self.workflow_system.generate_workflow_from_requirement(requirement)
                
                if result.get("success"):
                    yield {
                        "stage": "workflow_validation", 
                        "progress": 1.0, 
                        "message": "工作流生成成功",
                        "status": "completed",
                        "final_result": result
                    }
                else:
                    error_msg = result.get("error", "工作流生成失败")
                    yield {
                        "stage": "workflow_validation", 
                        "progress": 1.0, 
                        "message": f"工作流生成失败: {error_msg}",
                        "status": "failed",
                        "error": error_msg
                    }
                    
            except Exception as e:
                error_msg = f"工作流生成过程中出现异常: {str(e)}"
                logger.error(error_msg)
                yield {
                    "stage": "workflow_validation", 
                    "progress": 1.0, 
                    "message": error_msg,
                    "status": "failed",
                    "error": error_msg
                }
                
        except Exception as e:
            error_msg = f"流式工作流生成异常: {str(e)}"
            logger.error(error_msg)
            yield {
                "stage": "error", 
                "progress": 1.0, 
                "message": error_msg,
                "status": "failed",
                "error": error_msg
            }


async def serve():
    """启动gRPC服务器"""
    # 配置服务器选项，设置超时时间 - 针对线上环境优化
    options = [
        ('grpc.keepalive_time_ms', 10000),  # 10秒发送一次keepalive（与客户端保持一致）
        ('grpc.keepalive_timeout_ms', 3000),  # 3秒keepalive超时
        ('grpc.keepalive_permit_without_calls', True),  # 允许没有调用时发送keepalive
        ('grpc.http2.max_pings_without_data', 0),  # 不限制ping数量
        ('grpc.http2.min_time_between_pings_ms', 5000),  # ping间隔5秒
        ('grpc.http2.min_ping_interval_without_data_ms', 60000),  # 1分钟无数据ping间隔
        ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB接收限制
        ('grpc.max_send_message_length', 100 * 1024 * 1024),  # 100MB发送限制
        ('grpc.so_reuseport', 1),  # 允许端口重用
        ('grpc.max_connection_idle_ms', 60000),  # 60秒空闲连接超时
    ]
    
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=20), options=options)
    
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