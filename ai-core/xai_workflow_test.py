#!/usr/bin/env python3
"""
xAI工作流生成测试

专门使用xAI API进行工作流生成
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

async def generate_workflow_with_xai(task_description):
    """使用xAI生成工作流"""
    try:
        import aiohttp
        
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            print("❌ 没有xAI API密钥")
            return None
        
        url = "https://api.x.ai/v1/chat/completions"
        
        # 构建提示词
        system_prompt = """你是一个专业的工作流设计师。根据用户的需求描述，生成一个完整的工作流定义。

工作流必须包含以下JSON结构：
{
  "nodes": [
    {
      "id": "start_1",
      "type": "workflowStart", 
      "position": {"x": 100, "y": 100},
      "data": {"label": "开始"}
    },
    {
      "id": "step_1",
      "type": "formStep",
      "position": {"x": 300, "y": 100}, 
      "data": {"label": "步骤1", "description": "具体描述"}
    },
    {
      "id": "end_1",
      "type": "workflowEnd",
      "position": {"x": 500, "y": 100},
      "data": {"label": "结束"}
    }
  ],
  "edges": [
    {
      "id": "edge_1",
      "source": "start_1", 
      "target": "step_1"
    },
    {
      "id": "edge_2",
      "source": "step_1",
      "target": "end_1"
    }
  ]
}

要求：
1. 每个节点都有唯一的id、type、position、data
2. 每个连接都有唯一的id、source、target
3. 节点类型包括：workflowStart, workflowEnd, formStep, approvalStep, notificationStep, conditionStep
4. 工作流逻辑清晰，步骤合理
5. 只返回JSON格式，不要其他文字

"""

        user_prompt = f"任务：{task_description}\n\n请设计相应的工作流，包含合理的步骤和流程。"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "grok-3-latest",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 4000
        }
        
        print("⏳ 调用xAI API生成工作流...")
        
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    
                    print("✅ xAI API调用成功!")
                    print(f"📊 Token使用: 输入 {usage.get('prompt_tokens', 0)}, 输出 {usage.get('completion_tokens', 0)}")
                    
                    return content, usage
                else:
                    error_text = await response.text()
                    print(f"❌ xAI API调用失败 ({response.status}): {error_text}")
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
        
        # 验证节点
        node_ids = set()
        for node in nodes:
            if not isinstance(node, dict):
                raise ValueError("每个节点必须是对象")
            
            required_fields = ["id", "type", "position", "data"]
            for field in required_fields:
                if field not in node:
                    raise ValueError(f"节点缺少必填字段: {field}")
            
            node_id = node["id"]
            if node_id in node_ids:
                raise ValueError(f"重复的节点ID: {node_id}")
            node_ids.add(node_id)
        
        # 验证连接
        edge_ids = set()
        for edge in edges:
            if not isinstance(edge, dict):
                raise ValueError("每个连接必须是对象")
            
            required_fields = ["id", "source", "target"]
            for field in required_fields:
                if field not in edge:
                    raise ValueError(f"连接缺少必填字段: {field}")
            
            edge_id = edge["id"]
            if edge_id in edge_ids:
                raise ValueError(f"重复的连接ID: {edge_id}")
            edge_ids.add(edge_id)
            
            # 验证连接的节点存在
            if edge["source"] not in node_ids:
                raise ValueError(f"连接引用了不存在的源节点: {edge['source']}")
            if edge["target"] not in node_ids:
                raise ValueError(f"连接引用了不存在的目标节点: {edge['target']}")
        
        print(f"✅ 工作流验证通过")
        return workflow, None
        
    except json.JSONDecodeError as e:
        return None, f"JSON解析失败: {e}"
    except ValueError as e:
        return None, f"验证失败: {e}"
    except Exception as e:
        return None, f"未知错误: {e}"

async def test_workflow_scenarios():
    """测试多个工作流场景"""
    scenarios = [
        "创建用户注册工作流，包括邮箱验证、信息填写、账户激活",
        "设计请假审批流程，包括提交申请、上级审批、HR确认",
        "构建订单处理工作流，包括下单、付款、发货、收货",
        "建立客户投诉处理流程，包括接收投诉、分类处理、回复客户"
    ]
    
    results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🧪 测试场景 {i}: {scenario}")
        print("-" * 50)
        
        # 生成工作流
        content, usage = await generate_workflow_with_xai(scenario)
        
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
                for j, node in enumerate(workflow["nodes"][:5], 1):
                    label = node.get("data", {}).get("label", node.get("type", "Unknown"))
                    node_type = node.get("type", "unknown")
                    print(f"  {j}. {label} ({node_type})")
                
                if len(workflow["nodes"]) > 5:
                    print(f"  ... 还有 {len(workflow['nodes'])-5} 个节点")
                
                # 保存结果
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"workflow_scenario_{i}_{timestamp}.json"
                
                result_data = {
                    "scenario": scenario,
                    "workflow": workflow,
                    "statistics": {
                        "node_count": node_count,
                        "edge_count": edge_count
                    },
                    "generation_info": {
                        "model": "grok-3-latest",
                        "provider": "xAI",
                        "usage": usage,
                        "generated_at": datetime.now().isoformat()
                    }
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, indent=2, ensure_ascii=False)
                
                print(f"💾 已保存: {filename}")
                results.append({"scenario": scenario, "success": True, "file": filename})
                
            else:
                print(f"❌ 工作流验证失败: {error}")
                results.append({"scenario": scenario, "success": False, "error": error})
        else:
            print(f"❌ 生成失败")
            results.append({"scenario": scenario, "success": False, "error": "API调用失败"})
        
        # 短暂暂停避免频率限制
        if i < len(scenarios):
            print("⏳ 等待2秒...")
            await asyncio.sleep(2)
    
    return results

async def main():
    """主函数"""
    print("🚀 xAI工作流生成测试")
    print("=" * 50)
    
    # 加载环境变量
    if not load_env_from_server():
        print("⚠️ 无法加载环境变量")
    
    # 检查xAI API密钥
    api_key = os.getenv("XAI_API_KEY")
    if not api_key or len(api_key) < 10:
        print("❌ 没有有效的xAI API密钥")
        print("请在 server/.env 文件中设置 XAI_API_KEY")
        return
    
    print(f"✅ xAI API密钥: {api_key[:8]}...")
    
    # 测试多个场景
    results = await test_workflow_scenarios()
    
    # 总结结果
    print(f"\n📊 测试总结:")
    print("=" * 50)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"总测试数: {len(results)}")
    print(f"成功: {len(successful)}")
    print(f"失败: {len(failed)}")
    
    if successful:
        print(f"\n✅ 成功的场景:")
        for result in successful:
            print(f"  - {result['scenario']}")
    
    if failed:
        print(f"\n❌ 失败的场景:")
        for result in failed:
            print(f"  - {result['scenario']}: {result.get('error', '未知错误')}")
    
    if successful:
        print(f"\n🎉 测试完成！xAI工作流生成功能正常")
        print(f"✅ 成功率: {len(successful)/len(results)*100:.1f}%")
    else:
        print(f"\n❌ 所有测试都失败了")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被中断")
    except Exception as e:
        print(f"\n❌ 运行异常: {e}") 