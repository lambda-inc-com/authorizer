#!/usr/bin/env python3
"""
交互式工作流生成测试器
Interactive Workflow Generation Tester

允许用户输入需求，测试多智能体工作流生成系统
"""

import asyncio
import sys
import json
import traceback
import os
from datetime import datetime
from typing import Dict, Any
from workflow_generation_system import WorkflowGenerationSystem

class WorkflowTester:
    """工作流测试器"""
    
    def __init__(self):
        self.system = WorkflowGenerationSystem()
        self.session_history = []
        self.output_dir = "generated_workflows"
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"📁 创建输出目录: {self.output_dir}")
    
    def print_header(self):
        """打印测试器头部信息"""
        print("=" * 80)
        print("🤖 多智能体工作流生成系统 - 交互式测试器")
        print("=" * 80)
        print("📝 请输入您的工作流需求，系统将自动生成相应的工作流配置")
        print("💡 支持的节点类型：数据库操作、HTTP请求、LLM对话、条件判断等")
        print("🔧 输入 'help' 查看使用说明，输入 'quit' 退出程序")
        print("=" * 80)
    
    def print_help(self):
        """打印帮助信息"""
        print("\n📚 使用说明:")
        print("1. 直接输入您的工作流需求描述")
        print("2. 系统将自动分析需求并生成工作流")
        print("3. 可以查看生成的工作流JSON配置")
        print("\n💡 需求描述示例:")
        print("- 创建一个用户注册工作流，包含邮箱验证和数据库存储")
        print("\n🔧 可用命令:")
        print("- help: 显示此帮助信息")
        print("- status: 查看系统状态")
        print("- history: 查看生成历史")
        print("- save: 保存指定的工作流到文件")
        print("- clear: 清空历史记录")
        print("- quit: 退出程序")
        print()
    
    def get_user_input(self) -> str:
        """获取用户输入"""
        try:
            print("\n" + "─" * 50)
            requirement = input("🎯 请输入您的工作流需求: ").strip()
            return requirement
        except KeyboardInterrupt:
            print("\n\n👋 用户取消操作")
            return "quit"
        except EOFError:
            print("\n\n👋 输入结束")
            return "quit"
    
    async def handle_command(self, command: str) -> bool:
        """处理特殊命令"""
        command = command.lower()
        
        if command == "quit":
            print("👋 感谢使用！再见！")
            return False
            
        elif command == "help":
            self.print_help()
            return True
            
        elif command == "status":
            await self.show_system_status()
            return True
            
        elif command == "history":
            await self.show_generation_history()
            return True
            
        elif command == "save":
            await self.save_workflow_interactive()
            return True
            
        elif command == "clear":
            self.session_history.clear()
            print("🧹 历史记录已清空")
            return True
            
        return True
    
    async def show_system_status(self):
        """显示系统状态"""
        print("\n🔍 系统状态:")
        try:
            status = self.system.get_system_status()
            print(f"   系统就绪: {'✅' if status['system_ready'] else '❌'}")
            print(f"   智能体数量: {len(status['agents_status'])}")
            
            print("\n🤖 智能体状态:")
            for role, agent_status in status['agents_status'].items():
                busy_icon = "🔥" if agent_status['is_busy'] else "💤"
                status_text = "忙碌" if agent_status['is_busy'] else "空闲"
                print(f"   {busy_icon} {role}: {status_text}")
                
        except Exception as e:
            print(f"   ❌ 获取状态失败: {str(e)}")
    
    async def show_generation_history(self):
        """显示生成历史"""
        print("\n📚 生成历史:")
        if not self.session_history:
            print("   📝 暂无历史记录")
            return
            
        for i, record in enumerate(self.session_history, 1):
            print(f"\n   {i}. 需求: {record['requirement'][:50]}...")
            print(f"      结果: {'✅ 成功' if record['success'] else '❌ 失败'}")
            if record['success']:
                workflow = record['result']['workflow']
                print(f"      工作流: {workflow['name']}")
                print(f"      节点数: {len(workflow['nodes'])}")
    
    async def generate_workflow(self, requirement: str):
        """生成工作流"""
        print(f"\n⏳ 正在分析需求: {requirement}")
        print("🔄 启动多智能体协作...")
        
        try:
            # 显示处理进度
            print("   📊 第1步: 需求分析智能体正在分析...")
            await asyncio.sleep(0.5)  # 模拟处理时间
            
            print("   🔧 第2步: 工作流组合智能体正在生成...")
            await asyncio.sleep(0.5)
            
            print("   ✅ 第3步: 工作流验证智能体正在验证...")
            await asyncio.sleep(0.5)
            
            # 调用系统生成工作流
            result = await self.system.generate_workflow_from_requirement(requirement)
            
            # 记录历史
            self.session_history.append({
                'requirement': requirement,
                'success': result['success'],
                'result': result,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            if result['success']:
                await self.display_success_result(result)
            else:
                await self.display_error_result(result)
                
        except Exception as e:
            print(f"❌ 生成过程中发生异常: {str(e)}")
            print(f"📋 错误详情:")
            traceback.print_exc()
    
    async def display_success_result(self, result: Dict[str, Any]):
        """显示成功结果"""
        workflow = result['workflow']
        
        print("\n" + "🎉" * 20)
        print("✅ 工作流生成成功!")
        print("🎉" * 20)
        
        print(f"\n📋 工作流信息:")
        print(f"   名称: {workflow['name']}")
        print(f"   描述: {workflow['description']}")
        print(f"   版本: {workflow['version']}")
        print(f"   节点数量: {len(workflow['nodes'])}")
        
        print(f"\n🔗 工作流节点:")
        for i, node in enumerate(workflow['nodes'], 1):
            print(f"   {i}. {node['name']} ({node['type']})")
            print(f"      描述: {node['desc']}")
        
        # 询问是否查看详细配置
        while True:
            try:
                choice = input("\n🔍 是否查看详细JSON配置? (y/n): ").strip().lower()
                if choice in ['y', 'yes']:
                    await self.display_detailed_config(workflow)
                    break
                elif choice in ['n', 'no']:
                    break
                else:
                    print("请输入 y 或 n")
            except (KeyboardInterrupt, EOFError):
                break
        
        # 询问是否保存到文件
        await self.ask_save_workflow(workflow)
    
    async def display_detailed_config(self, workflow: Dict[str, Any]):
        """显示详细配置"""
        print("\n" + "=" * 50)
        print("📄 详细工作流配置 (JSON格式)")
        print("=" * 50)
        
        try:
            # 格式化输出JSON
            formatted_json = json.dumps(workflow, ensure_ascii=False, indent=2)
            print(formatted_json)
        except Exception as e:
            print(f"❌ JSON格式化失败: {str(e)}")
            print(workflow)
        
        print("=" * 50)
    
    async def ask_save_workflow(self, workflow: Dict[str, Any]):
        """询问是否保存工作流到文件"""
        while True:
            try:
                choice = input("\n💾 是否保存工作流到文件? (y/n): ").strip().lower()
                if choice in ['y', 'yes']:
                    filename = await self.save_workflow_to_file(workflow)
                    if filename:
                        print(f"✅ 工作流已保存到: {filename}")
                    break
                elif choice in ['n', 'no']:
                    break
                else:
                    print("请输入 y 或 n")
            except (KeyboardInterrupt, EOFError):
                break
    
    async def save_workflow_to_file(self, workflow: Dict[str, Any]) -> str:
        """保存工作流到文件"""
        try:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            workflow_name = workflow['name'].replace(' ', '_').replace('/', '_')
            filename = f"{workflow_name}_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            # 添加生成时间信息
            workflow_with_meta = {
                "generated_at": datetime.now().isoformat(),
                "generator": "多智能体工作流生成系统",
                "version": "1.0.0",
                "workflow": workflow
            }
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(workflow_with_meta, f, ensure_ascii=False, indent=2)
            
            return filepath
            
        except Exception as e:
            print(f"❌ 保存文件失败: {str(e)}")
            return None
    
    async def save_workflow_interactive(self):
        """交互式保存工作流"""
        if not self.session_history:
            print("📝 暂无工作流可保存")
            return
        
        # 显示可保存的工作流
        successful_workflows = [
            (i, record) for i, record in enumerate(self.session_history) 
            if record['success']
        ]
        
        if not successful_workflows:
            print("📝 暂无成功生成的工作流可保存")
            return
        
        print("\n📚 可保存的工作流:")
        for i, (_, record) in enumerate(successful_workflows, 1):
            workflow = record['result']['workflow']
            print(f"   {i}. {workflow['name']}")
            print(f"      需求: {record['requirement'][:50]}...")
            print(f"      节点数: {len(workflow['nodes'])}")
        
        try:
            choice = input(f"\n请选择要保存的工作流 (1-{len(successful_workflows)}): ").strip()
            index = int(choice) - 1
            
            if 0 <= index < len(successful_workflows):
                _, record = successful_workflows[index]
                workflow = record['result']['workflow']
                filename = await self.save_workflow_to_file(workflow)
                if filename:
                    print(f"✅ 工作流已保存到: {filename}")
            else:
                print("❌ 无效的选择")
                
        except (ValueError, KeyboardInterrupt, EOFError):
            print("❌ 操作取消")
    
    async def display_error_result(self, result: Dict[str, Any]):
        """显示错误结果"""
        print("\n" + "❌" * 20)
        print("❌ 工作流生成失败!")
        print("❌" * 20)
        
        print(f"\n📋 错误信息:")
        print(f"   {result.get('error', '未知错误')}")
        
        if 'details' in result:
            print(f"\n📄 详细信息:")
            for key, value in result['details'].items():
                print(f"   {key}: {value}")
        
        print(f"\n💡 建议:")
        print("   1. 检查需求描述是否清晰明确")
        print("   2. 确认所需的节点类型是否支持")
        print("   3. 尝试简化需求或分步骤描述")
    
    async def run(self):
        """运行测试器"""
        self.print_header()
        
        while True:
            try:
                # 获取用户输入
                user_input = self.get_user_input()
                
                if not user_input:
                    continue
                
                # 处理特殊命令
                if user_input.startswith(('help', 'quit', 'status', 'history', 'save', 'clear')):
                    should_continue = await self.handle_command(user_input)
                    if not should_continue:
                        break
                    continue
                
                # 生成工作流
                await self.generate_workflow(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 用户中断操作")
                break
            except Exception as e:
                print(f"\n❌ 发生异常: {str(e)}")
                traceback.print_exc()


async def main():
    """主函数"""
    tester = WorkflowTester()
    await tester.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 程序异常退出: {str(e)}")
        sys.exit(1) 