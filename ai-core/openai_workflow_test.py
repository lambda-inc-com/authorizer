#!/usr/bin/env python3
"""
OpenAI工作流生成测试

使用系统配置的提示词进行工作流生成
"""

import asyncio
import json
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

async def generate_workflow_with_openai(task_description):
    """使用OpenAI生成工作流"""
    try:
        import aiohttp
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ 没有OpenAI API密钥")
            return None, None
        
        # 使用服务器配置的代理域名
        url = "https://api.gptsapi.net/v1/chat/completions"
        
        # 导入系统配置的提示词
        try:
            from prompts.simple_prompts import get_workflow_system_prompt, build_user_prompt
            print("✅ 使用系统配置的提示词")
        except ImportError:
            print("⚠️ 无法导入系统提示词，使用备用提示词")
            # 备用提示词
            def get_workflow_system_prompt():
                return """你是工作流生成专家，根据用户需求生成JSON格式的工作流定义。

支持节点类型：
- workflowStart: 开始节点，定义输入
- workflowEnd: 结束节点，定义输出  
- condition: 条件判断
- code: 代码执行
- chatWithLLM: AI对话
- dbQuery: 数据库查询
- httpRequest: HTTP请求

要求：
1. 生成完整的JSON结构
2. 确保所有ID唯一
3. 正确设置节点连接
4. 只返回JSON，不要其他文字

节点结构示例：
{
  "nodes": [节点数组],
  "edges": [连接数组]
}"""
            
            def build_user_prompt(task_description, context=None, parameters=None):
                prompt = f"任务：{task_description}\n"
                if context:
                    prompt += "上下文：\n"
                    for key, value in context.items():
                        prompt += f"- {key}: {value}\n"
                if parameters:
                    complexity = parameters.get("complexity_level", "medium")
                    prompt += f"复杂度：{complexity}\n"
                prompt += "\n请生成完整的工作流JSON定义："
                return prompt
        
        # 构建提示词
        system_prompt = get_workflow_system_prompt()
        user_prompt = build_user_prompt(
            task_description, 
            context={"系统": "业务流程管理"}, 
            parameters={"complexity_level": "simple"}
        )
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4000
        }
        
        print("⏳ 调用OpenAI API生成工作流...")
        
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        usage = data.get("usage", {})
                        
                        print("✅ OpenAI API调用成功!")
                        print(f"📊 Token使用: 输入 {usage.get('prompt_tokens', 0)}, 输出 {usage.get('completion_tokens', 0)}")
                        
                        return content, usage
                    else:
                        error_text = await response.text()
                        print(f"❌ OpenAI API调用失败 ({response.status}): {error_text}")
                        return None, None
            except Exception as e:
                print(f"❌ 网络连接失败: {e}")
                return None, None
                        
    except Exception as e:
        print(f"❌ 生成工作流失败: {e}")
        return None, None

def parse_and_validate_workflow(content):
    """解析和验证工作流"""
    try:
        # 清理可能的markdown格式
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        workflow = json.loads(content.strip())
        
        # 验证基本结构
        if "nodes" not in workflow or "edges" not in workflow:
            raise ValueError("工作流必须包含nodes和edges字段")
        
        nodes = workflow["nodes"]
        edges = workflow["edges"]
        
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise ValueError("nodes和edges必须是数组")
        
        if len(nodes) == 0:
            raise ValueError("工作流必须包含至少一个节点")
        
        print(f"✅ 工作流验证通过")
        return workflow, None
        
    except json.JSONDecodeError as e:
        return None, f"JSON解析失败: {e}"
    except ValueError as e:
        return None, f"验证失败: {e}"
    except Exception as e:
        return None, f"未知错误: {e}"

async def main():
    """主函数"""
    print("🚀 OpenAI工作流生成测试")
    print("=" * 50)
    
    # 加载环境变量
    if not load_env_from_server():
        print("⚠️ 无法加载环境变量")
    
    # 检查OpenAI API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or len(api_key) < 10:
        print("❌ 没有有效的OpenAI API密钥")
        print("请在 server/.env 文件中设置 OPENAI_API_KEY")
        return
    
    print(f"✅ OpenAI API密钥: {api_key[:8]}...")
    
    # 测试场景
    task_description = "创建员工入职流程工作流，包括资料收集、审核、系统开通、培训安排"
    
    print(f"\n🧪 测试场景: {task_description}")
    print("-" * 50)
    
    # 生成工作流
    content, usage = await generate_workflow_with_openai(task_description)
    
    if content:
        # 解析和验证
        workflow, error = parse_and_validate_workflow(content)
        
        if workflow:
            node_count = len(workflow["nodes"])
            edge_count = len(workflow["edges"])
            
            print(f"🎉 生成成功!")
            print(f"📊 统计:")
            print(f"  节点数: {node_count}")
            print(f"  连接数: {edge_count}")
            
            # 显示节点概览
            print(f"\n📦 节点概览:")
            for i, node in enumerate(workflow["nodes"][:5], 1):
                label = node.get("data", {}).get("label", node.get("type", "Unknown"))
                node_type = node.get("type", "unknown")
                print(f"  {i}. {label} ({node_type})")
            
            if len(workflow["nodes"]) > 5:
                print(f"  ... 还有 {len(workflow['nodes'])-5} 个节点")
            
            # 保存结果
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"openai_workflow_{timestamp}.json"
            
            result_data = {
                "scenario": task_description,
                "workflow": workflow,
                "statistics": {
                    "node_count": node_count,
                    "edge_count": edge_count
                },
                "generation_info": {
                    "model": "gpt-3.5-turbo",
                    "provider": "OpenAI",
                    "usage": usage,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 已保存: {filename}")
            print(f"\n🎉 OpenAI工作流生成测试完成！")
            
        else:
            print(f"❌ 工作流验证失败: {error}")
    else:
        print(f"❌ 生成失败")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被中断")
    except Exception as e:
        print(f"\n❌ 运行异常: {e}") 