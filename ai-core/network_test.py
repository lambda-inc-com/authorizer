#!/usr/bin/env python3
"""
网络连接测试

测试各API的连通性
"""

import asyncio
import os
import sys
from datetime import datetime

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def load_env_from_server():
    """从server/.env加载环境变量"""
    env_file = os.path.join(current_dir, "../server/.env")
    if os.path.exists(env_file):
        print(f"📁 加载 {env_file}")
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                count = 0
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if value:
                            os.environ[key] = value
                            count += 1
                print(f"✅ 加载了 {count} 个环境变量")
                return True
        except Exception as e:
            print(f"❌ 加载失败: {e}")
    return False

async def test_api_connection(name, url, api_key):
    """测试API连接"""
    try:
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=10)
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 简单的健康检查请求
        test_payload = {
            "model": "gpt-3.5-turbo" if "gpt" in url else ("grok-3-latest" if "x.ai" in url else "claude-3-sonnet-20240229"),
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10
        }
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(url, headers=headers, json=test_payload) as response:
                    status = response.status
                    if status == 200:
                        print(f"✅ {name}: 连接正常 (200)")
                        return True
                    elif status == 401:
                        print(f"⚠️ {name}: 认证失败 (401) - 请检查API密钥")
                        return False
                    elif status == 429:
                        print(f"⚠️ {name}: 频率限制 (429)")
                        return False
                    else:
                        error_text = await response.text()
                        print(f"❌ {name}: HTTP {status} - {error_text[:100]}")
                        return False
            except asyncio.TimeoutError:
                print(f"❌ {name}: 连接超时")
                return False
            except Exception as e:
                print(f"❌ {name}: 连接错误 - {str(e)}")
                return False
                
    except ImportError:
        print(f"❌ {name}: 缺少aiohttp依赖")
        return False
    except Exception as e:
        print(f"❌ {name}: 未知错误 - {str(e)}")
        return False

async def main():
    """主函数"""
    print("🌐 API连接性测试")
    print("=" * 40)
    
    # 加载环境变量
    if not load_env_from_server():
        print("⚠️ 无法加载环境变量")
    
    # 定义API配置
    apis = {
        "xAI": {
            "url": "https://api.x.ai/v1/chat/completions",
            "key": os.getenv("XAI_API_KEY")
        },
        "OpenAI(代理)": {
            "url": "https://api.gptsapi.net/v1/chat/completions", 
            "key": os.getenv("OPENAI_API_KEY")
        },
        "Claude(代理)": {
            "url": "https://api.gptsapi.net/v1/chat/completions",
            "key": os.getenv("CLAUDE_API_KEY")
        }
    }
    
    # 检查密钥
    print("\n🔍 检查API密钥:")
    available_apis = {}
    for name, config in apis.items():
        key = config["key"]
        if key and len(key) > 10:
            print(f"✅ {name}: {key[:8]}...")
            available_apis[name] = config
        else:
            print(f"❌ {name}: 未设置或无效")
    
    if not available_apis:
        print("\n❌ 没有可用的API配置")
        return
    
    print(f"\n🚀 开始连接测试...")
    
    # 逐个测试
    working_apis = []
    for name, config in available_apis.items():
        print(f"\n🧪 测试 {name}...")
        try:
            success = await test_api_connection(name, config["url"], config["key"])
            if success:
                working_apis.append(name)
        except Exception as e:
            print(f"❌ {name}: 测试异常 - {e}")
    
    # 总结
    print(f"\n📊 测试结果:")
    print(f"  总计: {len(available_apis)} 个API")
    print(f"  可用: {len(working_apis)} 个API")
    
    if working_apis:
        print(f"✅ 可用的API:")
        for api in working_apis:
            print(f"  - {api}")
        
        print(f"\n🎯 建议: 使用 {working_apis[0]} 进行工作流生成测试")
    else:
        print(f"❌ 没有API可用")
        print(f"建议检查:")
        print(f"  1. 网络连接")
        print(f"  2. API密钥有效性")
        print(f"  3. 防火墙设置")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被中断")
    except Exception as e:
        print(f"\n❌ 运行异常: {e}") 