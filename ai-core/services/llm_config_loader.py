"""
LLM配置加载器

从server/configs/llm/目录加载各种模型配置
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
from loguru import logger


@dataclass
class LLMConfig:
    """LLM配置数据类"""
    provider: str
    model_type: str
    model_name: str
    api_key: str
    base_url: str
    max_tokens: int
    token_ratio: Dict[str, int]
    is_enabled: bool
    extra: Dict = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


class LLMConfigLoader:
    """LLM配置加载器"""
    
    def __init__(self, config_dir: str = None):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置目录路径，默认为server/configs/llm/
        """
        if config_dir is None:
            # 从ai-core目录向上查找server/configs/llm/
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent  # 向上两级到项目根目录
            config_dir = project_root / "server" / "configs" / "llm"
        
        self.config_dir = Path(config_dir)
        self.configs: Dict[str, LLMConfig] = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """加载所有配置文件"""
        if not self.config_dir.exists():
            logger.warning(f"配置目录不存在: {self.config_dir}")
            return
        
        for config_file in self.config_dir.glob("*.json"):
            try:
                config = self._load_single_config(config_file)
                if config:
                    # 使用 provider_model_name 作为key
                    config_key = f"{config.provider.lower()}_{config.model_name}"
                    self.configs[config_key] = config
                    logger.info(f"✅ 加载配置: {config_key}")
            except Exception as e:
                logger.error(f"❌ 加载配置失败 {config_file}: {e}")
    
    def _load_single_config(self, config_file: Path) -> Optional[LLMConfig]:
        """加载单个配置文件"""
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 处理环境变量
        api_key = data.get("api_key", "")
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]  # 移除 ${ 和 }
            api_key = os.getenv(env_var, "")
        
        return LLMConfig(
            provider=data.get("provider", ""),
            model_type=data.get("model_type", ""),
            model_name=data.get("model_name", ""),
            api_key=api_key,
            base_url=data.get("base_url", ""),
            max_tokens=data.get("max_tokens", 4096),
            token_ratio=data.get("token_ratio", {"input": 1, "output": 1}),
            is_enabled=data.get("is_enabled", False),
            extra=data.get("extra", {})
        )
    
    def get_config(self, provider: str, model_name: str = None) -> Optional[LLMConfig]:
        """
        获取特定模型的配置
        
        Args:
            provider: 提供商名称（如: openai, claude, xai）
            model_name: 模型名称（可选）
            
        Returns:
            LLMConfig或None
        """
        if model_name:
            config_key = f"{provider.lower()}_{model_name}"
            return self.configs.get(config_key)
        else:
            # 返回该提供商的第一个配置
            for key, config in self.configs.items():
                if config.provider.lower() == provider.lower():
                    return config
        return None
    
    def get_enabled_configs(self) -> Dict[str, LLMConfig]:
        """获取所有启用的配置"""
        return {k: v for k, v in self.configs.items() if v.is_enabled}
    
    def get_all_configs(self) -> Dict[str, LLMConfig]:
        """获取所有配置"""
        return self.configs.copy()
    
    def list_available_models(self) -> List[Dict[str, str]]:
        """列出所有可用的模型"""
        models = []
        for key, config in self.configs.items():
            models.append({
                "key": key,
                "provider": config.provider,
                "model_name": config.model_name,
                "model_type": config.model_type,
                "is_enabled": config.is_enabled,
                "has_api_key": bool(config.api_key)
            })
        return models
    
    def get_config_by_key(self, config_key: str) -> Optional[LLMConfig]:
        """根据配置key获取配置"""
        return self.configs.get(config_key)
    
    def reload_configs(self):
        """重新加载所有配置"""
        self.configs.clear()
        self._load_all_configs()
        logger.info("🔄 配置已重新加载")


# 全局配置加载器实例
_config_loader = None

def get_config_loader() -> LLMConfigLoader:
    """获取全局配置加载器实例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = LLMConfigLoader()
    return _config_loader


# 使用示例
if __name__ == "__main__":
    loader = LLMConfigLoader()
    
    # 列出所有可用模型
    models = loader.list_available_models()
    print("可用模型:")
    for model in models:
        print(f"  {model['key']}: {model['provider']} - {model['model_name']} (启用: {model['is_enabled']})")
    
    # 获取特定配置
    openai_config = loader.get_config("openai", "gpt-3.5-turbo")
    if openai_config:
        print(f"\nOpenAI配置: {openai_config.base_url}")
    
    claude_config = loader.get_config("anthropic")
    if claude_config:
        print(f"Claude配置: {claude_config.base_url}") 