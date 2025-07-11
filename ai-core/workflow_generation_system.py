"""
多智能体工作流生成系统 - 完整实现
Multi-Agent Workflow Generation System - Complete Implementation
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from multi_agent_workflow_generator import MultiAgentOrchestrator, AgentRole
from agents.requirement_analyzer import RequirementAnalyzer
from agents.workflow_composer import WorkflowComposer
from agents.workflow_validator import WorkflowValidator
import json
import os
from pathlib import Path
import anthropic
import openai
from dotenv import load_dotenv

# 加载环境变量 - 优先使用server目录下的.env文件
load_dotenv("../server/.env")  # server目录 (优先)
load_dotenv("../.env")  # 上级目录
load_dotenv()  # 当前目录 (最后)

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端接口"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # 不再在初始化时固定配置，而是每次请求时动态选择
        self._cached_config = config
        self._cached_client = None
        self._config_check_time = 0
        self._config_cache_ttl = 60  # 配置缓存60秒
        self.available_models = self._get_available_models()
    
    def _get_provider_priority(self) -> List[str]:
        """获取供应商优先级顺序"""
        return ["claude", "openai", "xai", "deepseek"]
    
    def _load_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """加载指定供应商的配置文件"""
        try:
            config_path = Path(f"../configs/llm/{provider_name}.json")
            if not config_path.exists():
                logger.debug(f"配置文件不存在: {config_path}")
                return None
                
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 处理环境变量
            if config.get("api_key", "").startswith("${"):
                env_var = config["api_key"][2:-1]
                api_key = os.getenv(env_var, "")
                if not api_key:
                    logger.debug(f"环境变量 {env_var} 未设置")
                    return None
                config["api_key"] = api_key
            
            # 检查必要字段
            if not config.get("api_key") or not config.get("is_enabled", False):
                logger.debug(f"供应商 {provider_name} 配置不完整或未启用")
                return None
                
            logger.debug(f"成功加载供应商配置: {provider_name}")
            return config
            
        except Exception as e:
            logger.debug(f"加载供应商 {provider_name} 配置失败: {str(e)}")
            return None
    
    def _test_provider_connectivity(self, config: Dict[str, Any]) -> bool:
        """测试供应商连通性"""
        try:
            provider = config.get("provider", "").lower()
            base_url = config.get("base_url", "")
            api_key = config.get("api_key", "")
            
            if not api_key:
                return False
            
            # 创建临时客户端进行连通性测试
            if provider == "anthropic":
                if "gptsapi.net" in base_url:
                    # 代理服务使用OpenAI兼容接口
                    if not base_url.endswith("/v1"):
                        base_url = base_url + "/v1"
                    import openai
                    test_client = openai.OpenAI(api_key=api_key, base_url=base_url)
                    # 简单的模型列表请求测试连通性
                    response = test_client.models.list()
                    return True
                else:
                    # 标准Anthropic接口
                    import anthropic
                    test_client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
                    # Claude API没有模型列表接口，这里假设API密钥格式正确就是可用的
                    return len(api_key) > 10 and api_key.startswith(("sk-", "claude-"))
            
            elif provider == "openai":
                import openai
                test_client = openai.OpenAI(api_key=api_key, base_url=base_url)
                response = test_client.models.list()
                return True
                
            elif provider in ["xai", "deepseek"]:
                # xAI和DeepSeek都使用OpenAI兼容接口
                import openai
                test_client = openai.OpenAI(api_key=api_key, base_url=base_url)
                response = test_client.models.list()
                return True
                
            return False
            
        except Exception as e:
            logger.debug(f"供应商连通性测试失败: {str(e)}")
            return False
    
    def _select_best_provider(self) -> Optional[Dict[str, Any]]:
        """按优先级选择最佳可用供应商"""
        import time
        current_time = time.time()
        
        # 检查配置缓存是否有效
        if (self._cached_config and 
            current_time - self._config_check_time < self._config_cache_ttl):
            logger.debug("使用缓存的供应商配置")
            return self._cached_config
        
        logger.info("🔍 开始动态检测可用的LLM供应商...")
        
        # 按优先级顺序检查供应商
        for provider_name in self._get_provider_priority():
            logger.info(f"📋 检查供应商: {provider_name}")
            
            # 加载配置
            config = self._load_provider_config(provider_name)
            if not config:
                logger.info(f"❌ {provider_name} 配置不可用")
                continue
            
            # 测试连通性
            logger.info(f"🔗 测试 {provider_name} 连通性...")
            if self._test_provider_connectivity(config):
                logger.info(f"✅ 选择供应商: {provider_name} ({config.get('model_name', 'unknown')})")
                
                # 缓存配置
                self._cached_config = config
                self._config_check_time = current_time
                self._cached_client = None  # 重置客户端缓存
                
                return config
            else:
                logger.info(f"❌ {provider_name} 连通性测试失败")
        
        logger.error("🚨 没有找到可用的LLM供应商")
        return None
    
    def _load_default_config(self) -> Dict[str, Any]:
        """动态加载最佳可用配置"""
        config = self._select_best_provider()
        
        if config:
            return config
        
        # 如果所有供应商都不可用，返回默认的Claude配置（作为回退）
        logger.warning("⚠️ 所有供应商都不可用，使用默认Claude配置")
        return {
            "provider": "Anthropic",
            "model_type": "claude",
            "model_name": "claude-3-5-sonnet-20241022",
            "api_key": os.getenv("CLAUDE_API_KEY", ""),
            "base_url": "https://api.anthropic.com/v1",
            "max_tokens": 4096,
            "is_enabled": True
        }
    
    def _initialize_client(self):
        """初始化客户端 - 支持动态配置"""
        # 如果有缓存的客户端且配置未变化，直接返回
        if self._cached_client and self._cached_config:
            return self._cached_client
        
        # 获取当前最佳配置
        if not self._cached_config:
            self._cached_config = self._load_default_config()
        
        config = self._cached_config
        
        if not config.get("api_key"):
            logger.error("未找到有效的API密钥")
            return None
        
        provider = config.get("provider", "").lower()
        
        try:
            if provider == "anthropic":
                # 使用自定义的 base_url
                base_url = config.get("base_url", "https://api.anthropic.com/v1")
                
                # 检查是否是代理服务，如果是则使用 OpenAI 客户端
                if "gptsapi.net" in base_url:
                    # 检查base_url是否已经包含/v1后缀，避免重复添加
                    if not base_url.endswith("/v1"):
                        base_url = base_url + "/v1"
                    client = openai.OpenAI(
                        api_key=config["api_key"],
                        base_url=base_url
                    )
                else:
                    client = anthropic.Anthropic(
                        api_key=config["api_key"],
                        base_url=base_url
                    )
            elif provider == "openai":
                base_url = config.get("base_url", "https://api.openai.com/v1")
                client = openai.OpenAI(
                    api_key=config["api_key"],
                    base_url=base_url
                )
            elif provider in ["xai", "deepseek"]:
                # xAI和DeepSeek都使用OpenAI兼容接口
                base_url = config.get("base_url")
                client = openai.OpenAI(
                    api_key=config["api_key"],
                    base_url=base_url
                )
            else:
                logger.error(f"不支持的提供商: {provider}")
                return None
            
            # 缓存客户端
            self._cached_client = client
            logger.info(f"✅ 成功初始化 {provider} 客户端")
            return client
            
        except Exception as e:
            logger.error(f"初始化 {provider} 客户端失败: {str(e)}")
            # 如果初始化失败，清除缓存，下次重新选择
            self._cached_config = None
            self._cached_client = None
            return None
    
    async def chat_completion(self, messages: list, model: str = None, **kwargs) -> str:
        """
        LLM聊天完成接口
        """
        if not self._initialize_client(): # 使用动态初始化
            raise RuntimeError("LLM客户端未初始化，请检查API密钥配置")
        
        try:
            # 使用配置中的模型名称
            model_name = model or self._cached_config.get("model_name", "claude-3-sonnet-20240229")
            max_tokens = kwargs.get("max_tokens", self._cached_config.get("max_tokens", 4096))
            temperature = kwargs.get("temperature", 0.3)
            
            provider = self._cached_config.get("provider", "").lower()
            
            if provider == "anthropic":
                # Claude API调用
                response = await self._call_claude_api(messages, model_name, max_tokens, temperature)
            elif provider == "openai":
                # OpenAI API调用
                response = await self._call_openai_api(messages, model_name, max_tokens, temperature)
            elif provider in ["xai", "deepseek"]:
                # xAI和DeepSeek API调用
                response = await self._call_openai_api(messages, model_name, max_tokens, temperature) # 统一调用OpenAI兼容接口
            else:
                raise ValueError(f"不支持的提供商: {provider}")
            
            return response
            
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            raise
    
    async def stream_chat_completion(self, messages: list, model: str = None, **kwargs):
        """
        LLM流式聊天完成接口 - 真正的流式响应
        """
        if not self._initialize_client(): # 使用动态初始化
            raise RuntimeError("LLM客户端未初始化，请检查API密钥配置")
        
        try:
            # 使用配置中的模型名称
            model_name = model or self._cached_config.get("model_name", "claude-3-sonnet-20240229")
            max_tokens = kwargs.get("max_tokens", self._cached_config.get("max_tokens", 4096))
            temperature = kwargs.get("temperature", 0.3)
            
            provider = self._cached_config.get("provider", "").lower()
            
            if provider == "anthropic":
                # Claude API流式调用
                async for chunk in self._stream_claude_api(messages, model_name, max_tokens, temperature):
                    yield chunk
            elif provider == "openai":
                # OpenAI API流式调用
                async for chunk in self._stream_openai_api(messages, model_name, max_tokens, temperature):
                    yield chunk
            elif provider in ["xai", "deepseek"]:
                # xAI和DeepSeek API流式调用
                async for chunk in self._stream_openai_api(messages, model_name, max_tokens, temperature): # 统一调用OpenAI兼容接口
                    yield chunk
            else:
                raise ValueError(f"不支持的提供商: {provider}")
                
        except Exception as e:
            logger.error(f"LLM流式调用失败: {str(e)}")
            raise
    
    async def _call_claude_api(self, messages: list, model: str, max_tokens: int, temperature: float) -> str:
        """调用Claude API - 兼容代理服务"""
        try:
            # 检查是否是代理服务（gptsapi.net）
            if "gptsapi.net" in self._cached_config.get("base_url", ""):
                # 使用 OpenAI 兼容格式
                return await self._call_openai_compatible_api(messages, model, max_tokens, temperature)
            else:
                # 使用标准 Claude API 格式
                return await self._call_standard_claude_api(messages, model, max_tokens, temperature)
            
        except Exception as e:
            logger.error(f"Claude API调用失败: {str(e)}")
            raise
    
    async def _call_standard_claude_api(self, messages: list, model: str, max_tokens: int, temperature: float) -> str:
        """调用标准Claude API"""
        # 转换消息格式
        claude_messages = []
        system_message = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # 异步调用
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._cached_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message,
                messages=claude_messages
            )
        )
        
        return response.content[0].text
    
    async def _call_openai_compatible_api(self, messages: list, model: str, max_tokens: int, temperature: float) -> str:
        """调用OpenAI兼容的API（用于代理服务）"""
        # 处理 system 消息 - 合并到第一个 user 消息中
        processed_messages = []
        system_content = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                processed_messages.append(msg)
        
        # 如果有 system 消息，合并到第一个 user 消息中
        if system_content and processed_messages:
            first_user_msg = processed_messages[0]
            if first_user_msg["role"] == "user":
                first_user_msg["content"] = f"{system_content}\n\n{first_user_msg['content']}"
        
        # 如果没有 user 消息，创建一个
        if not processed_messages:
            processed_messages = [{"role": "user", "content": system_content or "Hello"}]
        
        # 异步调用
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._cached_client.chat.completions.create(
                model=model,
                messages=processed_messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
        )
        
        return response.choices[0].message.content
    
    async def _call_openai_api(self, messages: list, model: str, max_tokens: int, temperature: float) -> str:
        """调用OpenAI API"""
        try:
            # 异步调用
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._cached_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {str(e)}")
            raise
    
    async def _stream_claude_api(self, messages: list, model: str, max_tokens: int, temperature: float):
        """流式调用Claude API"""
        try:
            # 检查是否是代理服务（gptsapi.net）
            if "gptsapi.net" in self._cached_config.get("base_url", ""):
                # 使用 OpenAI 兼容格式的流式调用
                async for chunk in self._stream_openai_compatible_api(messages, model, max_tokens, temperature):
                    yield chunk
            else:
                # 使用标准 Claude API 格式的流式调用
                async for chunk in self._stream_standard_claude_api(messages, model, max_tokens, temperature):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Claude 流式API调用失败: {str(e)}")
            raise
    
    async def _stream_standard_claude_api(self, messages: list, model: str, max_tokens: int, temperature: float):
        """流式调用标准Claude API"""
        # 转换消息格式
        claude_messages = []
        system_message = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # 创建流式请求
        def create_stream():
            return self._cached_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message,
                messages=claude_messages,
                stream=True  # 启用流式响应
            )
        
        # 在executor中运行流式调用
        stream = await asyncio.get_event_loop().run_in_executor(None, create_stream)
        
        # 处理流式响应
        for event in stream:
            if hasattr(event, 'delta') and hasattr(event.delta, 'text'):
                content = event.delta.text
                if content:
                    yield {
                        "content": content,
                        "is_complete": False,
                        "finish_reason": "",
                        "model_used": model
                    }
            elif hasattr(event, 'type') and event.type == 'message_stop':
                # 流式响应结束
                yield {
                    "content": "",
                    "is_complete": True,
                    "finish_reason": "stop",
                    "model_used": model
                }
                break
    
    async def _stream_openai_compatible_api(self, messages: list, model: str, max_tokens: int, temperature: float):
        """流式调用OpenAI兼容的API（用于代理服务）"""
        # 处理 system 消息 - 合并到第一个 user 消息中
        processed_messages = []
        system_content = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                processed_messages.append(msg)
        
        # 如果有 system 消息，合并到第一个 user 消息中
        if system_content and processed_messages:
            first_user_msg = processed_messages[0]
            if first_user_msg["role"] == "user":
                first_user_msg["content"] = f"{system_content}\n\n{first_user_msg['content']}"
        
        # 如果没有 user 消息，创建一个
        if not processed_messages:
            processed_messages = [{"role": "user", "content": system_content or "Hello"}]
        
        # 创建流式请求
        def create_stream():
            return self._cached_client.chat.completions.create(
                model=model,
                messages=processed_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True  # 启用流式响应
            )
        
        # 在executor中运行流式调用
        stream = await asyncio.get_event_loop().run_in_executor(None, create_stream)
        
        # 处理流式响应
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                choice = chunk.choices[0]
                if hasattr(choice, 'delta') and hasattr(choice.delta, 'content') and choice.delta.content:
                    content = choice.delta.content
                    yield {
                        "content": content,
                        "is_complete": False,
                        "finish_reason": "",
                        "model_used": model
                    }
                elif hasattr(choice, 'finish_reason') and choice.finish_reason:
                    # 流式响应结束
                    yield {
                        "content": "",
                        "is_complete": True,
                        "finish_reason": choice.finish_reason,
                        "model_used": model
                    }
                    break
    
    async def _stream_openai_api(self, messages: list, model: str, max_tokens: int, temperature: float):
        """流式调用OpenAI API"""
        try:
            # 创建流式请求
            def create_stream():
                return self._cached_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True  # 启用流式响应
                )
            
            # 在executor中运行流式调用
            stream = await asyncio.get_event_loop().run_in_executor(None, create_stream)
            
            # 处理流式响应
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    if hasattr(choice, 'delta') and hasattr(choice.delta, 'content') and choice.delta.content:
                        content = choice.delta.content
                        yield {
                            "content": content,
                            "is_complete": False,
                            "finish_reason": "",
                            "model_used": model
                        }
                    elif hasattr(choice, 'finish_reason') and choice.finish_reason:
                        # 流式响应结束
                        yield {
                            "content": "",
                            "is_complete": True,
                            "finish_reason": choice.finish_reason,
                            "model_used": model
                        }
                        break
                        
        except Exception as e:
            logger.error(f"OpenAI 流式API调用失败: {str(e)}")
            raise
    
    def _get_available_models(self) -> Dict[str, List[str]]:
        """获取不同服务提供商的可用模型列表"""
        return {
            "anthropic_official": [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022", 
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ],
            "gptsapi_proxy": [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-sonnet",
                "claude-3-sonnet-20240229",
                "claude-3-sonnet",
                "claude-3-haiku-20240307",
                "claude-3-haiku",
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-3.5-turbo"
            ],
            "openai_official": [
                "gpt-4o",
                "gpt-4o-mini", 
                "gpt-4-turbo",
                "gpt-4",
                "gpt-3.5-turbo"
            ],
            "xai_official": [
                "grok-3-latest",
                "grok-beta",
                "grok-vision-beta"
            ],
            "deepseek_official": [
                "deepseek-chat",
                "deepseek-coder"
            ]
        }
    
    async def test_connection_and_model(self) -> Dict[str, Any]:
        """测试连接和模型可用性"""
        if not self._initialize_client():
            return {
                "success": False,
                "error": "客户端未初始化",
                "model": None
            }
        
        # 确保有当前配置
        if not self._cached_config:
            self._cached_config = self._load_default_config()
        
        # 获取基础URL和提供商信息
        base_url = self._cached_config.get("base_url", "")
        provider = self._cached_config.get("provider", "").lower()
        current_model = self._cached_config.get("model_name", "")
        
        logger.info(f"测试连接 - 提供商: {provider}, 基础URL: {base_url}, 模型: {current_model}")
        
        # 确定服务类型
        service_type = "anthropic_official"
        if "gptsapi.net" in base_url:
            service_type = "gptsapi_proxy"
        elif provider == "openai":
            service_type = "openai_official"
        elif provider == "xai":
            service_type = "xai_official"
        elif provider == "deepseek":
            service_type = "deepseek_official"
        
        available_models = self.available_models.get(service_type, [])
        
        # 如果当前模型不在可用列表中，尝试找一个替代品
        if current_model not in available_models:
            logger.warning(f"当前模型 {current_model} 不在 {service_type} 的可用列表中")
            if available_models:
                new_model = available_models[0]  # 使用第一个可用模型
                logger.info(f"尝试使用替代模型: {new_model}")
                self._cached_config["model_name"] = new_model
                current_model = new_model
        
        # 测试简单请求
        try:
            test_messages = [
                {"role": "user", "content": "请回复'测试成功'"}
            ]
            
            response = await self.chat_completion(
                messages=test_messages,
                model=current_model,
                max_tokens=10,
                temperature=0
            )
            
            return {
                "success": True,
                "model": current_model,
                "provider": provider,
                "service_type": service_type,
                "response": response,
                "available_models": available_models
            }
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 如果是模型不存在错误，尝试其他模型
            if "model not found" in error_msg or "model" in error_msg:
                logger.warning(f"模型 {current_model} 测试失败: {str(e)}")
                
                # 尝试其他可用模型
                for alt_model in available_models:
                    if alt_model != current_model:
                        try:
                            logger.info(f"尝试备用模型: {alt_model}")
                            self._cached_config["model_name"] = alt_model
                            
                            response = await self.chat_completion(
                                messages=test_messages,
                                model=alt_model,
                                max_tokens=10,
                                temperature=0
                            )
                            
                            logger.info(f"备用模型 {alt_model} 测试成功")
                            return {
                                "success": True,
                                "model": alt_model,
                                "provider": provider,
                                "service_type": service_type,
                                "response": response,
                                "available_models": available_models,
                                "note": f"已从 {current_model} 切换到 {alt_model}"
                            }
                            
                        except Exception as alt_e:
                            logger.warning(f"备用模型 {alt_model} 也失败: {str(alt_e)}")
                            continue
            
            return {
                "success": False,
                "error": str(e),
                "model": current_model,
                "provider": provider,
                "service_type": service_type,
                "available_models": available_models
            }
    
    def get_recommended_models(self) -> Dict[str, str]:
        """根据配置推荐最佳模型"""
        # 确保有当前配置
        if not self._cached_config:
            self._cached_config = self._load_default_config()
            
        base_url = self._cached_config.get("base_url", "")
        
        if "gptsapi.net" in base_url:
            return {
                "primary": "claude-3-5-sonnet-20241022",
                "fallback": "gpt-4o-mini",
                "service": "gptsapi_proxy"
            }
        elif self._cached_config.get("provider", "").lower() == "openai":
            return {
                "primary": "gpt-4o-mini",
                "fallback": "gpt-3.5-turbo", 
                "service": "openai_official"
            }
        else:
            return {
                "primary": "claude-3-5-sonnet-20241022",
                "fallback": "claude-3-haiku-20240307",
                "service": "anthropic_official"
            }
    
    def force_refresh_config(self) -> Dict[str, Any]:
        """强制刷新配置，重新检测可用供应商"""
        logger.info("🔄 强制刷新LLM供应商配置...")
        
        # 清除缓存
        self._cached_config = None
        self._cached_client = None
        self._config_check_time = 0
        
        # 重新选择供应商
        config = self._select_best_provider()
        
        if config:
            logger.info(f"✅ 刷新完成，当前使用: {config.get('provider')} - {config.get('model_name')}")
            return {
                "success": True,
                "provider": config.get("provider"),
                "model_name": config.get("model_name"),
                "base_url": config.get("base_url")
            }
        else:
            logger.error("❌ 刷新失败，没有找到可用的供应商")
            return {
                "success": False,
                "error": "没有找到可用的LLM供应商"
            }
    
    def get_current_config_info(self) -> Dict[str, Any]:
        """获取当前配置信息"""
        if not self._cached_config:
            self._cached_config = self._load_default_config()
        
        return {
            "provider": self._cached_config.get("provider"),
            "model_name": self._cached_config.get("model_name"),
            "base_url": self._cached_config.get("base_url"),
            "cache_time": self._config_check_time,
            "cache_ttl": self._config_cache_ttl
        }


class WorkflowGenerationSystem(MultiAgentOrchestrator):
    """工作流生成系统 - 完整实现"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        # 先设置 llm_client，然后调用父类构造函数
        self.llm_client = llm_client or LLMClient()
        super().__init__()
    
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
            
            # 🔥 首先验证模型可用性
            logger.info("验证模型可用性...")
            model_test = await self.llm_client.test_connection_and_model()
            
            if not model_test.get("success"):
                error_msg = f"模型验证失败: {model_test.get('error', '未知错误')}"
                logger.error(error_msg)
                
                # 提供建议的模型
                recommended = self.llm_client.get_recommended_models()
                available_models = model_test.get("available_models", [])
                
                return {
                    "success": False,
                    "error": error_msg,
                    "message": "模型验证失败，请检查模型配置",
                    "suggestions": {
                        "recommended_models": recommended,
                        "available_models": available_models,
                        "current_config": {
                            "provider": self.llm_client._cached_config.get("provider") if self.llm_client._cached_config else None,
                            "base_url": self.llm_client._cached_config.get("base_url") if self.llm_client._cached_config else None,
                            "model_name": self.llm_client._cached_config.get("model_name") if self.llm_client._cached_config else None
                        }
                    }
                }
            
            # 模型验证成功，显示使用的模型信息
            used_model = model_test.get("model")
            service_type = model_test.get("service_type")
            logger.info(f"✅ 模型验证成功 - 使用模型: {used_model} (服务: {service_type})")
            
            if model_test.get("note"):
                logger.info(f"ℹ️  {model_test.get('note')}")
            
            # 调用父类的生成方法
            result = await self.generate_workflow(user_requirement)
            
            if result["success"]:
                logger.info("工作流生成成功")
                return {
                    "success": True,
                    "workflow": result["workflow"],
                    "generation_history": result["generation_history"],
                    "message": "工作流生成成功",
                    "model_info": {
                        "used_model": used_model,
                        "service_type": service_type,
                        "note": model_test.get("note")
                    }
                }
            else:
                logger.error(f"工作流生成失败: {result['error']}")
                return {
                    "success": False,
                    "error": result["error"],
                    "message": "工作流生成失败",
                    "model_info": {
                        "used_model": used_model,
                        "service_type": service_type
                    }
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