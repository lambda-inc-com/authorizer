"""
提示词模板包

包含各种智能体的提示词模板
"""

from .simple_prompts import get_workflow_system_prompt, build_user_prompt

__all__ = [
    'get_workflow_system_prompt',
    'build_user_prompt'
] 