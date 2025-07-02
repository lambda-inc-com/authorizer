"""
统一LLM客户端

支持多种模型提供商的API调用，包括OpenAI、Claude、xAI等
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from loguru import logger
from services.llm_config_loader import LLMConfig, get_config_loader


class UnifiedLLMClient:
    """统一LLM客户端"""
    
    def __init__(self):
        """初始化客户端"""
        self.config_loader = get_config_loader()
        self.session = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def chat(
        self,
        model_key: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        统一的聊天接口
        
        Args:
            model_key: 模型配置key (如: openai_gpt-3.5-turbo, xai_grok-3-latest)
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            统一格式的响应
        """
        # 获取模型配置
        config = self.config_loader.get_config_by_key(model_key)
        if not config:
            raise ValueError(f"找不到模型配置: {model_key}")
        
        if not config.is_enabled:
            raise ValueError(f"模型未启用: {model_key}")
        
        if not config.api_key:
            raise ValueError(f"模型API密钥未配置: {model_key}")
        
        # 使用配置的max_tokens，如果未指定的话
        if max_tokens is None:
            max_tokens = config.max_tokens
        
        # 根据提供商类型调用相应的API
        if config.provider.lower() == "openai":
            return await self._call_openai_api(config, messages, temperature, max_tokens, **kwargs)
        elif config.provider.lower() == "anthropic":
            return await self._call_claude_api(config, messages, temperature, max_tokens, **kwargs)
        elif config.provider.lower() == "xai":
            return await self._call_xai_api(config, messages, temperature, max_tokens, **kwargs)
        elif config.provider.lower() == "deepseek":
            return await self._call_deepseek_api(config, messages, temperature, max_tokens, **kwargs)
        else:
            raise ValueError(f"不支持的提供商: {config.provider}")
    
    async def _call_openai_api(
        self,
        config: LLMConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """调用OpenAI API"""
        
        url = f"{config.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": config.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        logger.info(f"🤖 调用OpenAI API: {config.model_name}")
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "content": data["choices"][0]["message"]["content"],
                        "model": config.model_name,
                        "provider": config.provider,
                        "usage": data.get("usage", {}),
                        "raw_response": data
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API调用失败 ({response.status}): {error_text}")
                    
        except Exception as e:
            logger.error(f"❌ OpenAI API调用异常: {e}")
            raise
    
    async def _call_claude_api(
        self,
        config: LLMConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """调用Claude API"""
        
        url = f"{config.base_url}/messages"
        headers = {
            "x-api-key": config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Claude API需要特殊的消息格式处理
        system_prompt = ""
        claude_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        payload = {
            "model": config.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": claude_messages
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        logger.info(f"🤖 调用Claude API: {config.model_name}")
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "content": data["content"][0]["text"],
                        "model": config.model_name,
                        "provider": config.provider,
                        "usage": data.get("usage", {}),
                        "raw_response": data
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Claude API调用失败 ({response.status}): {error_text}")
                    
        except Exception as e:
            logger.error(f"❌ Claude API调用异常: {e}")
            raise
    
    async def _call_xai_api(
        self,
        config: LLMConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """调用xAI API"""
        
        url = f"{config.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": config.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        logger.info(f"🤖 调用xAI API: {config.model_name}")
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "content": data["choices"][0]["message"]["content"],
                        "model": config.model_name,
                        "provider": config.provider,
                        "usage": data.get("usage", {}),
                        "raw_response": data
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"xAI API调用失败 ({response.status}): {error_text}")
                    
        except Exception as e:
            logger.error(f"❌ xAI API调用异常: {e}")
            raise
    
    async def _call_deepseek_api(
        self,
        config: LLMConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """调用DeepSeek API"""
        
        url = f"{config.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": config.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        logger.info(f"🤖 调用DeepSeek API: {config.model_name}")
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "content": data["choices"][0]["message"]["content"],
                        "model": config.model_name,
                        "provider": config.provider,
                        "usage": data.get("usage", {}),
                        "raw_response": data
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"DeepSeek API调用失败 ({response.status}): {error_text}")
                    
        except Exception as e:
            logger.error(f"❌ DeepSeek API调用异常: {e}")
            raise
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """列出所有可用的模型"""
        return self.config_loader.list_available_models()
    
    def get_enabled_models(self) -> List[Dict[str, Any]]:
        """获取所有启用的模型"""
        all_models = self.list_available_models()
        return [model for model in all_models if model["is_enabled"] and model["has_api_key"]]


class ModelSelector:
    """模型选择器"""
    
    def __init__(self):
        self.client = UnifiedLLMClient()
    
    def get_model_recommendations(self, task_type: str = None) -> List[str]:
        """
        根据任务类型推荐模型
        
        Args:
            task_type: 任务类型 (workflow_generation, data_analysis, conversation, etc.)
            
        Returns:
            推荐的模型key列表
        """
        enabled_models = self.client.get_enabled_models()
        
        if not enabled_models:
            raise ValueError("没有可用的启用模型")
        
        # 根据任务类型推荐模型
        recommendations = {
            "workflow_generation": [
                "openai_gpt-4",
                "openai_gpt-3.5-turbo", 
                "xai_grok-3-latest",
                "anthropic_claude-3-sonnet-20240229",
                "deepseek_deepseek-chat"
            ],
            "data_analysis": [
                "openai_gpt-4",
                "anthropic_claude-3-sonnet-20240229",
                "deepseek_deepseek-chat",
                "xai_grok-3-latest"
            ],
            "conversation": [
                "anthropic_claude-3-sonnet-20240229",
                "openai_gpt-4",
                "deepseek_deepseek-chat",
                "xai_grok-3-latest"
            ],
            "code_generation": [
                "openai_gpt-4",
                "deepseek_deepseek-chat",
                "xai_grok-3-latest",
                "openai_gpt-3.5-turbo"
            ]
        }
        
        preferred_models = recommendations.get(task_type, [])
        enabled_keys = [model["key"] for model in enabled_models]
        
        # 返回推荐模型中可用的那些
        available_recommendations = [
            model_key for model_key in preferred_models 
            if model_key in enabled_keys
        ]
        
        # 如果没有推荐的可用模型，返回所有启用的模型
        if not available_recommendations:
            available_recommendations = enabled_keys
        
        return available_recommendations
    
    def select_best_model(self, task_type: str = None, prefer_speed: bool = False) -> str:
        """
        选择最佳模型
        
        Args:
            task_type: 任务类型
            prefer_speed: 是否优先考虑速度
            
        Returns:
            最佳模型的key
        """
        recommendations = self.get_model_recommendations(task_type)
        
        if not recommendations:
            raise ValueError("没有可用的推荐模型")
        
        if prefer_speed:
            # 速度优先：选择较轻量的模型
            speed_preference = [
                "openai_gpt-3.5-turbo",
                "xai_grok-3-latest", 
                "anthropic_claude-3-sonnet-20240229",
                "openai_gpt-4"
            ]
            for model_key in speed_preference:
                if model_key in recommendations:
                    return model_key
        
        # 质量优先：返回推荐列表的第一个
        return recommendations[0]


# 使用示例
async def demo_usage():
    """使用示例"""
    
    async with UnifiedLLMClient() as client:
        # 列出可用模型
        models = client.get_enabled_models()
        print("可用模型:")
        for model in models:
            print(f"  {model['key']}: {model['provider']} - {model['model_name']}")
        
        if models:
            # 选择第一个可用模型进行测试
            model_key = models[0]["key"]
            
            messages = [
                {"role": "system", "content": "你是一个有用的助手"},
                {"role": "user", "content": "创建一个简单的工作流"}
            ]
            
            try:
                response = await client.chat(
                    model_key=model_key,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=1000
                )
                
                print(f"\n使用模型: {response['model']}")
                print(f"响应: {response['content'][:200]}...")
                
            except Exception as e:
                print(f"调用失败: {e}")


if __name__ == "__main__":
    asyncio.run(demo_usage()) 