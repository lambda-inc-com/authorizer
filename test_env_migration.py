#!/usr/bin/env python3
"""
测试环境变量迁移 - 验证Python智能体是否正确从server/.env加载API密钥
"""

import os
import sys
sys.path.append('ai-core')

from dotenv import load_dotenv

def test_env_loading():
    """测试环境变量加载"""
    print("=== 环境变量迁移测试 ===")
    print()
    
    # 清除所有相关环境变量
    for key in ['CLAUDE_API_KEY', 'OPENAI_API_KEY', 'XAI_API_KEY']:
        if key in os.environ:
            del os.environ[key]
    
    print("1. 从ai-core/.env加载...")
    load_dotenv("ai-core/.env")
    claude_from_aicore = os.getenv("CLAUDE_API_KEY", "")
    print(f"   CLAUDE_API_KEY: {claude_from_aicore[:15]}...{claude_from_aicore[-5:] if len(claude_from_aicore) > 20 else claude_from_aicore}")
    
    # 清除环境变量
    for key in ['CLAUDE_API_KEY', 'OPENAI_API_KEY', 'XAI_API_KEY']:
        if key in os.environ:
            del os.environ[key]
    
    print("\n2. 从server/.env加载...")
    load_dotenv("server/.env")
    claude_from_server = os.getenv("CLAUDE_API_KEY", "")
    openai_from_server = os.getenv("OPENAI_API_KEY", "")
    xai_from_server = os.getenv("XAI_API_KEY", "")
    
    print(f"   CLAUDE_API_KEY: {claude_from_server[:15]}...{claude_from_server[-5:] if len(claude_from_server) > 20 else claude_from_server}")
    print(f"   OPENAI_API_KEY: {openai_from_server[:15]}...{openai_from_server[-5:] if len(openai_from_server) > 20 else openai_from_server}")
    print(f"   XAI_API_KEY: {xai_from_server[:15]}...{xai_from_server[-5:] if len(xai_from_server) > 20 else xai_from_server}")
    
    # 清除环境变量
    for key in ['CLAUDE_API_KEY', 'OPENAI_API_KEY', 'XAI_API_KEY']:
        if key in os.environ:
            del os.environ[key]
    
    print("\n3. 模拟Python智能体的加载顺序...")
    load_dotenv("server/.env")  # server目录 (优先)
    load_dotenv(".env")  # 上级目录
    load_dotenv("ai-core/.env")  # 当前目录 (最后)
    
    final_claude = os.getenv("CLAUDE_API_KEY", "")
    final_openai = os.getenv("OPENAI_API_KEY", "")
    final_xai = os.getenv("XAI_API_KEY", "")
    
    print(f"   最终 CLAUDE_API_KEY: {final_claude[:15]}...{final_claude[-5:] if len(final_claude) > 20 else final_claude}")
    print(f"   最终 OPENAI_API_KEY: {final_openai[:15]}...{final_openai[-5:] if len(final_openai) > 20 else final_openai}")
    print(f"   最终 XAI_API_KEY: {final_xai[:15]}...{final_xai[-5:] if len(final_xai) > 20 else final_xai}")
    
    print("\n=== 测试结果 ===")
    if claude_from_server and claude_from_server == final_claude:
        print("✅ 成功：Python智能体正在使用server/.env中的API密钥")
        print(f"   配置源：server/.env")
        print(f"   API密钥数量：{len([k for k in [final_claude, final_openai, final_xai] if k])}")
    else:
        print("❌ 失败：配置可能有问题")
        print(f"   server/.env中的密钥：{claude_from_server[:10]}...")
        print(f"   最终使用的密钥：{final_claude[:10]}...")
    
    return claude_from_server == final_claude

def test_workflow_system():
    """测试工作流系统的配置"""
    print("\n=== 工作流系统配置测试 ===")
    
    try:
        from workflow_generation_system import LLMClient
        
        client = LLMClient()
        config = client.config
        
        print(f"提供商：{config.get('provider')}")
        print(f"模型：{config.get('model_name')}")
        print(f"基础URL：{config.get('base_url')}")
        
        api_key = config.get('api_key', '')
        if api_key:
            print(f"API密钥：{api_key[:15]}...{api_key[-5:] if len(api_key) > 20 else api_key}")
            print("✅ 工作流系统成功加载API密钥")
            return True
        else:
            print("❌ 工作流系统未找到API密钥")
            return False
            
    except Exception as e:
        print(f"❌ 工作流系统测试失败：{str(e)}")
        return False

if __name__ == "__main__":
    print("🔧 测试环境变量迁移...")
    print()
    
    env_success = test_env_loading()
    workflow_success = test_workflow_system()
    
    print("\n" + "="*50)
    if env_success and workflow_success:
        print("🎉 迁移成功！Python智能体现在使用server/.env文件")
        print()
        print("📝 迁移总结：")
        print("   - ✅ 环境变量已从 ai-core/.env 迁移到 server/.env")
        print("   - ✅ Python代码优先加载 server/.env")
        print("   - ✅ 工作流系统正常加载API密钥")
        print("   - ✅ 统一了环境变量管理")
    else:
        print("❌ 迁移失败，请检查配置")
    print("="*50) 