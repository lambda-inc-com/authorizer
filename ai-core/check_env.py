#!/usr/bin/env python3
"""
检查.env文件加载

验证API密钥是否能正确从.env文件中读取
"""

import os

def load_env_file():
    """加载.env文件中的环境变量"""
    env_paths = [
        "../server/.env",  # server目录下的.env
        "../.env",         # 项目根目录的.env
        ".env"             # 当前目录的.env
    ]
    
    loaded_vars = {}
    for env_path in env_paths:
        try:
            if os.path.exists(env_path):
                print(f"📁 找到 .env 文件: {env_path}")
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            # 去掉引号
                            value = value.strip().strip('"').strip("'")
                            loaded_vars[key] = value
                            # 设置到环境变量中
                            os.environ[key] = value
                print(f"✅ 成功加载 .env 文件: {env_path}")
                return loaded_vars, env_path
        except Exception as e:
            print(f"❌ 读取 {env_path} 失败: {e}")
            continue
    
    return {}, None

def main():
    """主检查函数"""
    print("🔍 检查 .env 文件加载")
    print("=" * 40)
    
    # 加载.env文件
    loaded_vars, env_path = load_env_file()
    
    if not loaded_vars:
        print("❌ 没有找到或无法加载 .env 文件")
        return
    
    print(f"\n📋 从 {env_path} 加载的变量:")
    
    # 检查API密钥
    api_keys = ["OPENAI_API_KEY", "CLAUDE_API_KEY", "XAI_API_KEY", "DEEPSEEK_API_KEY"]
    
    found_keys = []
    for key in api_keys:
        value = os.getenv(key)
        if value:
            # 只显示前几个字符，保护隐私
            masked_value = value[:8] + "..." if len(value) > 8 else value
            print(f"✅ {key}: {masked_value}")
            found_keys.append(key)
        else:
            print(f"❌ {key}: 未设置")
    
    print(f"\n📊 总结:")
    print(f"   - 找到 {len(found_keys)} 个API密钥")
    print(f"   - 可用API: {', '.join([k.replace('_API_KEY', '') for k in found_keys])}")
    
    if found_keys:
        print(f"\n✅ 配置正常！可以运行工作流测试")
        print(f"运行命令: python test_workflow.py")
    else:
        print(f"\n⚠️ 没有找到任何API密钥")

if __name__ == "__main__":
    main() 