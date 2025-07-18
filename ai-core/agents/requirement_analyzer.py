"""
需求分析智能体 (Requirement Analyzer Agent)
负责分析用户需求，识别所需的节点类型和数量，并为每个节点生成专门的提示词和配置
"""

import json
import logging
from typing import Dict, List, Any, Optional
from multi_agent_workflow_generator import BaseAgent, AgentRole, MessageType

# 添加数据库相关导入
import os
import asyncio
import asyncpg
from dotenv import load_dotenv
from node_type_manager import node_type_manager

# 加载环境变量
load_dotenv("../../server/.env")  # server目录 (优先)
load_dotenv("../../.env")  # 上级目录
load_dotenv()  # 当前目录

logger = logging.getLogger(__name__)


class RequirementAnalyzer(BaseAgent):
    """需求分析智能体 - 增强版，支持细化节点生成"""
    
    def __init__(self, message_bus, state_manager, llm_client):
        super().__init__(AgentRole.REQUIREMENT_ANALYZER, message_bus, state_manager)
        self.llm_client = llm_client
        self.node_types_info = self._load_node_types_info()
        # 先使用默认模板，稍后异步加载数据库模板
        self.dsl_templates = self._get_default_templates()
        self._db_templates_loaded = False
    
    def _load_node_types_info(self) -> Dict[str, Any]:
        """加载节点类型信息"""
        return {
            "workflowStart": {
                "description": "工作流开始节点，定义工作流的输入参数和触发方式",
                "usage": "必须作为工作流的起始点，定义工作流的输入参数",
                "required": True
            },
            "workflowEnd": {
                "description": "工作流结束节点，定义工作流的输出结果", 
                "usage": "必须作为工作流的终止点，定义最终输出结果。可以有多个结束节点处理不同分支的结果",
                "required": True
            },
            "dbQuery": {
                "description": "数据库查询节点，用于执行数据库查询操作（SELECT）",
                "usage": "当需要从数据库中查询数据时使用，支持条件过滤、排序和分页",
                "scenarios": ["查询用户信息", "获取订单列表", "检索产品数据", "统计分析"]
            },
            "dbCreate": {
                "description": "数据库创建节点，用于在数据库中创建新记录（INSERT）",
                "usage": "当需要向数据库插入新数据时使用",
                "scenarios": ["创建用户", "添加订单", "插入日志", "保存配置"]
            },
            "dbUpdate": {
                "description": "数据库更新节点，用于更新数据库中的记录（UPDATE）",
                "usage": "当需要修改现有数据时使用",
                "scenarios": ["更新用户信息", "修改订单状态", "调整库存", "更新配置"]
            },
            "dbDelete": {
                "description": "数据库删除节点，用于删除数据库中的记录（DELETE）",
                "usage": "当需要删除数据时使用，必须提供WHERE条件",
                "scenarios": ["删除用户", "清理过期数据", "移除订单", "删除日志"]
            },
            "transaction": {
                "description": "数据库事务节点，用于将多个数据库操作包装在一个事务中",
                "usage": "当需要保证多个数据库操作的原子性时使用",
                "scenarios": ["转账操作", "订单创建", "批量更新", "复杂业务流程"]
            },
            "batch": {
                "description": "批量处理节点，实现Map-Reduce模式的批量数据处理",
                "usage": "当需要对数据列表进行批量处理时使用",
                "scenarios": ["批量数据插入", "批量数据更新", "批量API调用", "批量数据验证"]
            },
            "http": {
                "description": "HTTP请求节点，用于发送HTTP请求",
                "usage": "当需要调用外部API或服务时使用",
                "scenarios": ["调用第三方API", "发送通知", "数据同步", "外部验证"]
            },
            "chatWithLLM": {
                "description": "LLM对话节点，用于与大型语言模型进行交互",
                "usage": "当需要AI处理文本、生成内容或智能分析时使用",
                "scenarios": ["文本生成", "内容摘要", "智能分析", "自动回复"]
            },
            "condition": {
                "description": "条件判断节点，用于根据条件决定工作流的执行路径",
                "usage": "当需要根据数据进行条件判断和分支处理时使用",
                "scenarios": ["用户权限检查", "数据验证", "状态判断", "业务规则"]
            },
            "code": {
                "description": "代码执行节点，用于执行自定义JavaScript代码逻辑",
                "usage": "仅用于其他专业节点无法实现的复杂业务逻辑处理、数据转换和计算",
                "scenarios": ["复杂数据转换", "复杂业务计算", "复杂条件逻辑", "数据聚合分析"]
            },
            "workflow": {
                "description": "工作流节点，调用其他已定义的工作流，实现工作流复用和组合",
                "usage": "当需要调用其他工作流实现复用时使用",
                "scenarios": ["工作流复用", "工作流组合", "模块化处理", "子流程调用"]
            }
        }
    
    def _load_dsl_templates(self) -> Dict[str, str]:
        """从数据库中加载DSL模板"""
        try:
            # 检查是否已有运行中的事件循环
            try:
                # 尝试获取当前事件循环
                current_loop = asyncio.get_running_loop()
                logger.warning("检测到运行中的事件循环，跳过数据库加载，使用默认模板")
                return self._get_default_templates()
            except RuntimeError:
                # 没有运行中的事件循环，可以创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    templates = loop.run_until_complete(self._load_templates_from_db())
                    if templates:
                        logger.info(f"成功从数据库加载了 {len(templates)} 个节点模板")
                        return templates
                except Exception as inner_e:
                    logger.error(f"数据库模板加载执行失败: {str(inner_e)}")
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)
        except Exception as e:
            logger.error(f"从数据库加载DSL模板失败: {str(e)}，使用默认模板")
        
        # 如果数据库加载失败，使用默认模板
        return self._get_default_templates()

    async def _load_node_dsl_from_db(self) -> Dict[str, Dict[str, Any]]:
        """从数据库加载所有节点DSL数据"""
        conn = None
        try:
            # 获取数据库连接配置
            database_url = self._get_database_url()
            if not database_url:
                logger.warning("数据库URL未配置，无法连接数据库")
                return {}
            
            # 连接数据库
            conn = await asyncpg.connect(database_url)
            
            # 查询所有节点类型数据
            query = """
                SELECT id, node_type, description, example, schema, created_at, updated_at
                FROM node_types 
                ORDER BY node_type
            """
            
            rows = await conn.fetch(query)
            
            if not rows:
                logger.warning("数据库中没有找到节点类型数据")
                return {}
            
            # 构建节点DSL数据字典
            node_dsl_data = {}
            for row in rows:
                node_type = row['node_type']
                node_data = {
                    "id": row['id'],
                    "node_type": node_type,
                    "description": row['description'],
                    "example": row['example'],  # JSONB类型，已经是dict
                    "schema": row['schema'] if row['schema'] else {},  # JSONB类型
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                    # 为了兼容性，保留原有的template_content格式
                    "template_content": self._build_template_content(node_type, row['description'], row['example'])
                }
                
                node_dsl_data[node_type] = node_data
                logger.debug(f"加载节点DSL: {node_type}")
            
            logger.info(f"从数据库成功加载 {len(node_dsl_data)} 个节点DSL数据")
            return node_dsl_data
            
        except Exception as e:
            logger.error(f"数据库操作失败: {str(e)}")
            return {}
        finally:
            if conn:
                await conn.close()

    async def _load_templates_from_db(self) -> Dict[str, str]:
        """从数据库异步加载节点模板（兼容性方法）"""
        try:
            # 从共享上下文获取节点DSL数据
            context = await self.state_manager.get_context()
            node_dsl_data = getattr(context, 'node_dsl_data', {})
            
            if node_dsl_data:
                # 如果共享上下文中有DSL数据，直接使用
                templates = {}
                for node_type, data in node_dsl_data.items():
                    templates[node_type] = data.get('template_content', '')
                logger.info(f"从共享上下文获取 {len(templates)} 个节点模板")
                return templates
            else:
                # 如果共享上下文中没有DSL数据，从数据库查询
                node_dsl_data = await self._load_node_dsl_from_db()
                templates = {}
                for node_type, data in node_dsl_data.items():
                    templates[node_type] = data.get('template_content', '')
                return templates
                
        except Exception as e:
            logger.error(f"加载节点模板失败: {str(e)}")
            return self._get_default_templates()

    async def _load_templates_from_db_async(self) -> Dict[str, str]:
        """异步方式从数据库加载模板（推荐使用）"""
        try:
            return await self._load_templates_from_db()
        except Exception as e:
            logger.error(f"异步加载数据库模板失败: {str(e)}")
            return self._get_default_templates()
    
    async def _load_and_cache_node_dsl_data(self):
        """加载节点DSL数据并缓存到共享上下文中"""
        try:
            # 检查共享上下文中是否已有节点DSL数据
            context = await self.state_manager.get_context()
            existing_dsl_data = getattr(context, 'node_dsl_data', {})
            
            if existing_dsl_data:
                logger.info(f"共享上下文中已存在 {len(existing_dsl_data)} 个节点DSL数据，跳过重复加载")
                return
            
            logger.info("🔍 开始从数据库加载节点DSL数据...")
            
            # 从数据库加载节点DSL数据
            node_dsl_data = await self._load_node_dsl_from_db()
            
            if node_dsl_data:
                # 将节点DSL数据存储到共享上下文中
                await self.state_manager.update_context({
                    "node_dsl_data": node_dsl_data
                })
                
                # 🎯 更新节点类型管理器（使用完整DSL数据）
                node_type_manager.update_from_database(node_dsl_data)
                
                logger.info(f"✅ 成功加载并缓存 {len(node_dsl_data)} 个节点DSL数据到共享上下文")
                logger.info(f"📋 已加载的节点类型: {', '.join(node_dsl_data.keys())}")
                logger.info(f"🔄 已更新节点类型管理器，可用类型: {', '.join(node_type_manager.get_all_available_types())}")
                
            else:
                logger.warning("⚠️ 未能从数据库加载节点DSL数据，将使用默认模板")
                # 使用默认模板作为备选方案
                default_templates = self._get_default_templates()
                default_dsl_data = {}
                for node_type, template_content in default_templates.items():
                    default_dsl_data[node_type] = {
                        "node_type": node_type,
                        "description": f"默认{node_type}节点",
                        "example": {},
                        "schema": {},
                        "template_content": template_content
                    }
                
                await self.state_manager.update_context({
                    "node_dsl_data": default_dsl_data
                })
                
        except Exception as e:
            logger.error(f"❌ 加载节点DSL数据失败: {str(e)}")
            # 发生错误时，使用默认模板
            try:
                default_templates = self._get_default_templates()
                default_dsl_data = {}
                for node_type, template_content in default_templates.items():
                    default_dsl_data[node_type] = {
                        "node_type": node_type,
                        "description": f"默认{node_type}节点",
                        "example": {},
                        "schema": {},
                        "template_content": template_content
                    }
                
                await self.state_manager.update_context({
                    "node_dsl_data": default_dsl_data
                })
                
                logger.info("✅ 已使用默认模板作为备选方案")
                
            except Exception as fallback_error:
                logger.error(f"❌ 使用默认模板失败: {str(fallback_error)}")

    async def _generate_node_special_requirements(self, node_type: str, user_requirement: str) -> str:
        """根据节点类型动态生成特殊要求 - 使用数据库DSL数据"""
        try:
            # 从共享上下文获取节点DSL数据
            context = await self.state_manager.get_context()
            node_dsl_data = getattr(context, 'node_dsl_data', {})
            
            # 检查是否有该节点类型的DSL数据
            if node_type in node_dsl_data:
                dsl_data = node_dsl_data[node_type]
                description = dsl_data.get('description', '')
                example = dsl_data.get('example', {})
                
                # 基于DSL数据生成特殊要求
                requirements = f"""
## ⚠️ {node_type.upper()}节点特殊要求 ⚠️

**节点描述**：{description.split('。')[0]}。

"""
                
                # 根据节点类型特征添加通用要求
                if node_type_manager.is_start_node(node_type):
                    requirements += """
**开始节点特殊要求**：
1. **configs设置为空对象{{}}** - 此节点类型无需特殊配置
2. **outputs设置为空对象{{}}** - 此节点类型不产生输出数据
3. **inputs字段** - 用于定义工作流的初始输入参数
4. **nextNodes** - 指向下一个要执行的节点"""
                
                elif node_type_manager.is_end_node(node_type):
                    requirements += """
**结束节点特殊要求**：
1. **nextNodes必须设置为空数组[]** - 因为这是工作流的终点！
2. **configs设置为空对象{{}}** - 此节点类型无需特殊配置
3. **必须包含标准API响应字段**：
   - code: HTTP状态码（数字类型）
   - data: 响应数据（字符串、对象或数组类型）  
   - message: 响应消息（字符串类型）"""
                
                elif "db" in node_type.lower():
                    requirements += """
**数据库节点特殊要求**：
1. **configs必须包含**：
   - table: 表名称（字符串）
   - sql: SQL语句（字符串，支持变量引用）
2. **outputs字段已固定**，请基于节点类型设置适当的输出字段"""
                
                elif "http" in node_type.lower():
                    requirements += """
**HTTP节点特殊要求**：
1. **configs必须包含**：
   - method: 请求方法（GET/POST/PUT/DELETE等）
   - url: 请求URL（字符串）
   - bodyType: 请求体类型（none/json/form-data/text）
2. **outputs字段已固定**，不需要设置value字段"""
                
                elif "condition" in node_type.lower():
                    requirements += """
**条件节点特殊要求**：
1. **不包含nextNodes字段** - 条件节点的流向由条件配置决定
2. **不包含outputs字段** - 条件节点不产生数据输出
3. **configs必须包含conditionGroups** - 条件组配置（数组类型）"""
                
                elif "llm" in node_type.lower() or "chat" in node_type.lower():
                    requirements += """
**LLM节点特殊要求**：
1. **configs必须包含**：
   - modelId: 模型ID（字符串）
2. **outputs字段已固定**，不需要设置value字段"""
                
                else:
                    # 通用节点要求
                    requirements += """
**通用节点要求**：
1. **configs** - 根据节点功能设置相应配置
2. **outputs** - 设置适当的输出字段
3. **nextNodes** - 指向下一个执行的节点"""
                
                # 如果有示例，添加示例参考
                if example:
                    requirements += f"""

**节点示例参考**：
```json
{json.dumps(example, ensure_ascii=False, indent=2)}
```"""
                
                return requirements
            
            else:
                # 如果数据库中没有该节点类型，使用通用要求
                return f"""
## ⚠️ {node_type.upper()}节点要求 ⚠️

**注意**: 该节点类型在数据库中未找到具体DSL定义，请参考通用节点规范：

1. **必填字段**: name, type, desc, inputs, outputs, configs, nextNodes
2. **configs**: 根据节点功能设置相应配置
3. **outputs**: 设置适当的输出字段类型和描述
4. **nextNodes**: 指向下一个要执行的节点名称数组

请确保生成的JSON格式正确且完整。"""
                
        except Exception as e:
            logger.error(f"生成节点特殊要求失败: {str(e)}")
            return f"""
## ⚠️ {node_type.upper()}节点基本要求 ⚠️

1. **必填字段**: name, type, desc, inputs, outputs, configs, nextNodes
2. **请参考节点类型的通用规范进行配置**"""

    def _get_database_url(self) -> Optional[str]:
        """获取数据库连接URL"""
        try:
            # 首先尝试直接获取DATABASE_URL
            database_url = os.getenv('DATABASE_URLs')
            logger.info(database_url)
            if database_url:
                logger.info("使用环境变量 DATABASE_URLs")
                return database_url
            
            # 如果没有DATABASE_URL，则从各个组件构建
            db_host = os.getenv('DATABASE_HOST', 'localhost')
            db_port = os.getenv('DATABASE_PORT', '5432')
            db_name = os.getenv('DATABASE_NAME', '')
            db_user = os.getenv('DATABASE_USERNAME', '')
            db_password = os.getenv('DATABASE_PASSWORD', '')
            
            # 检查必需的配置
            if not all([db_name, db_user, db_password]):
                logger.warning("数据库配置不完整，缺少必要的环境变量: DATABASE_NAME, DATABASE_USERNAME, DATABASE_PASSWORD")
                return None
            
            # 构建连接URL
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            logger.info(f"构建数据库连接URL: postgresql://{db_user}:***@{db_host}:{db_port}/{db_name}")
            return database_url
            
        except Exception as e:
            logger.error(f"构建数据库URL失败: {str(e)}")
            return None
    
    def _build_template_content(self, node_type: str, description: str, example: dict) -> str:
        """构建节点模板内容"""
        try:
            template_content = f"""# {node_type.upper()} 节点

## 描述
{description}


## 配置示例
```json
{json.dumps(example, ensure_ascii=False, indent=2)}
```

## 重要说明
- 节点名称必须使用英文且以大写字母开头，采用PascalCase格式
- 所有必需字段都必须填写
- configs字段包含节点特定的配置参数
- nextNodes指定下一个要执行的节点名称列表"""

            return template_content
            
        except Exception as e:
            logger.error(f"构建模板内容失败: {str(e)}")
            return f"# {node_type} 节点\n{description}"
    
    def _extract_section_content(self, section: str, node_type: str) -> str:
        """提取章节内容"""
        # 确保节点类型开头有#号
        if not section.startswith('#'):
            section = '# ' + section
        return section
    
    def _get_default_templates(self) -> Dict[str, str]:
        """获取默认模板（作为备用）"""
        return {
            "workflowStart": "# 工作流开始节点\n基本工作流开始节点模板",
            "workflowEnd": "# 工作流结束节点\n基本工作流结束节点模板",
            "dbQuery": "# 数据库查询节点\n基本数据库查询节点模板",
            "dbCreate": "# 数据库创建节点\n基本数据库创建节点模板",
            "dbUpdate": "# 数据库更新节点\n基本数据库更新节点模板",
            "dbDelete": "# 数据库删除节点\n基本数据库删除节点模板",
            "transaction": "# 数据库事务节点\n基本数据库事务节点模板",
            "batch": "# 批量处理节点\n基本批量处理节点模板",
            "condition": "# 条件判断节点\n基本条件判断节点模板",
            "workflow": "# 工作流节点\n基本工作流节点模板",
            "code": "# 代码执行节点\n基本代码执行节点模板",
            "http": "# HTTP请求节点\n基本HTTP请求节点模板",
            "chatWithLLM": "# LLM对话节点\n基本LLM对话节点模板"
        }
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理需求分析任务 - 增强版流程"""
        try:
            # 🎯 首先加载节点DSL数据到共享上下文（所有阶段共享使用）
            await self._load_and_cache_node_dsl_data()
            
            # 确保数据库模板已加载
            await self._ensure_db_templates_loaded()
            
            # 获取共享上下文
            context = await self.state_manager.get_context()
            user_requirement = context.user_requirement
            
            logger.info(f"开始增强版需求分析: {user_requirement}")
            
            # 阶段1: 需求分析，确定需要的节点类型
            logger.info("阶段1: 分析需求，确定节点类型")
            node_analysis = await self._analyze_requirement_for_nodes(user_requirement)
            
            # 阶段2: 为每个节点生成专门的提示词
            logger.info("阶段2: 为每个节点生成专门的提示词")
            node_prompts = await self._generate_node_prompts(node_analysis, user_requirement)
            
            # 阶段3: 逐个生成节点配置
            logger.info("阶段3: 逐个生成节点配置")
            generated_nodes = await self._generate_individual_nodes(node_prompts, user_requirement)
            
            # 构建最终结果
            final_result = {
                "analysis": node_analysis["analysis"],
                "node_prompts": node_prompts,
                "generated_nodes": generated_nodes,
                "workflow_complexity": node_analysis["workflow_complexity"],
                "estimated_nodes_count": len(generated_nodes)
            }
            
            # 更新共享上下文
            await self.state_manager.update_context({
                "analyzed_nodes": generated_nodes,
                "node_generation_prompts": node_prompts
            })
            
            # 记录生成历史
            await self.state_manager.add_generation_history(
                "enhanced_requirement_analysis",
                final_result
            )
            
            logger.info(f"增强版需求分析完成，生成了 {len(generated_nodes)} 个节点")
            
            return final_result
            
        except Exception as e:
            logger.error(f"增强版需求分析失败: {str(e)}")
            raise
    
    async def _analyze_requirement_for_nodes(self, user_requirement: str) -> Dict[str, Any]:
        """第一阶段: 分析需求，确定需要的节点类型"""
        
        # 从共享上下文获取数据库信息
        context = await self.state_manager.get_context()
        db_info = getattr(context, 'db_info', "")

        # 如果提供了数据库信息，使用它；否则使用默认的硬编码信息
        if db_info and db_info.strip():
            # 使用传递的数据库表信息
            try:
                # 尝试解析JSON格式的数据库信息
                import json
                if db_info.strip().startswith('{'):
                    # JSON格式
                    db_config = json.loads(db_info)
                    if isinstance(db_config, dict) and 'name' in db_config:
                        # 如果是包含name字段的配置对象，提取name作为数据库表信息
                        database_tables_info = db_config.get('name', '默认数据库表信息')
                    else:
                        # 直接使用JSON字符串作为数据库表信息
                        database_tables_info = db_info
                else:
                    # 普通字符串格式
                    database_tables_info = db_info
                logger.info(f"使用动态传递的数据库表信息: {database_tables_info[:100]}...")
            except Exception as e:
                logger.warning(f"解析数据库信息失败，使用默认信息: {str(e)}")
                database_tables_info = """- users: 用户表(id, username, email, password, real_name, phone, role, status)
- categories: 商品分类表(id, parent_id, name, code, description)
- suppliers: 供应商表(id, code, name, contact_person, phone, email)
- customers: 客户表(id, code, name, type, contact_person, phone, email)
- products: 商品表(id, sku, name, category_id, brand, model, cost_price, sale_price, current_stock)
- warehouses: 仓库表(id, code, name, address, manager, phone)
- inventory: 库存表(id, warehouse_id, product_id, quantity, available_quantity)
- purchase_orders: 采购订单表(id, order_no, supplier_id, warehouse_id, total_amount, status)
- sales_orders: 销售订单表(id, order_no, customer_id, warehouse_id, total_amount, status)
- stock_movements: 库存变动记录表(id, warehouse_id, product_id, movement_type, quantity)"""
        else:
            # 使用默认的硬编码数据库表信息
            database_tables_info = """- users: 用户表(id, username, email, password, real_name, phone, role, status)
- categories: 商品分类表(id, parent_id, name, code, description)
- suppliers: 供应商表(id, code, name, contact_person, phone, email)
- customers: 客户表(id, code, name, type, contact_person, phone, email)
- products: 商品表(id, sku, name, category_id, brand, model, cost_price, sale_price, current_stock)
- warehouses: 仓库表(id, code, name, address, manager, phone)
- inventory: 库存表(id, warehouse_id, product_id, quantity, available_quantity)
- purchase_orders: 采购订单表(id, order_no, supplier_id, warehouse_id, total_amount, status)
- sales_orders: 销售订单表(id, order_no, customer_id, warehouse_id, total_amount, status)
- stock_movements: 库存变动记录表(id, warehouse_id, product_id, movement_type, quantity)"""
            logger.info("使用默认硬编码的数据库表信息")

        # 🎯 动态生成可用节点类型列表（基于数据库DSL数据）
        available_node_types = node_type_manager.generate_available_node_types_for_llm()
        if not available_node_types:
            logger.warning("⚠️ 无法生成可用节点类型列表，使用基本默认列表")
            available_node_types = "- **通用节点**: 请根据需求选择合适的节点类型"

        system_prompt = f"""# 工作流需求分析专家

你是一个专业的工作流需求分析专家，专门负责分析用户的业务需求，并识别出完成该需求所需的所有工作流节点类型。

## 你的任务
1. 仔细分析用户的需求描述
2. 识别出需要哪些类型的节点来完成这个需求
3. 为每个节点类型提供用途说明和业务上下文
4. 确保节点的选择合理且完整

## 可用节点类型
{available_node_types}

## 输出格式
请严格按照以下JSON格式输出：
```json
{{
  "analysis": {{
    "requirement_summary": "需求总结",
    "key_actions": ["关键行为1", "关键行为2"],
    "data_entities": ["数据实体1", "数据实体2"],
    "business_rules": ["业务规则1", "业务规则2"]
  }},
  "required_node_types": [
    {{
      "type": "节点类型",
      "purpose": "节点用途说明",
      "context": "在当前业务需求中的作用",
      "suggested_name": "建议的节点名称",
      "priority": 1,
      "dependencies": ["依赖的其他节点类型"]
    }}
  ],
  "workflow_complexity": "简单/中等/复杂"
}}
```"""
    
        user_prompt = f"""请分析以下用户需求，并识别出完成该需求所需的所有工作流节点类型：

**用户需求：**
{user_requirement}

**可用数据库表信息：**
{database_tables_info}

请按照分析原则，仔细分析用户需求，并按照指定的JSON格式输出结果。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
            ]
            
        response = await self.llm_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=8000
            )
            
        return self._parse_llm_response(response)
            
    async def _generate_node_prompts(self, node_analysis: Dict[str, Any], user_requirement: str) -> List[Dict[str, Any]]:
        """第二阶段: 为每个节点生成专门的提示词"""
        
        node_prompts = []
        
        for node_info in node_analysis["required_node_types"]:
            node_type = node_info["type"]
            
            # 获取该节点类型的DSL模板
            dsl_template = self.dsl_templates.get(node_type, "")
            
            # 生成专门的提示词（此阶段还没有前置节点配置，会在实际生成时动态更新）
            prompt = await self._create_node_generation_prompt(
                node_type=node_type,
                node_info=node_info,
                user_requirement=user_requirement,
                dsl_template=dsl_template,
                business_context=node_analysis["analysis"],
                previous_node_configs=[]  # 初始为空，在实际生成时会动态更新
            )
            
            node_prompts.append({
                "node_type": node_type,
                "node_info": node_info,
                "generation_prompt": prompt
            })
            
            logger.info(f"为节点类型 {node_type} 生成了专门的提示词")
            print(f"\n{'='*80}")
            print(f"节点类型: {node_type}")
            print(f"{'='*80}")
            print(prompt)
            print(f"{'='*80}\n")
        
        return node_prompts
    
    async def _create_node_generation_prompt(self, node_type: str, node_info: Dict[str, Any], 
                                           user_requirement: str, dsl_template: str, 
                                           business_context: Dict[str, Any], 
                                           previous_node_configs: List[Dict[str, Any]] = None) -> str:
        """为特定节点类型创建生成提示词"""
        
        # 获取特殊要求 - 使用数据库DSL数据动态生成
        
        base_prompt = f"""# {node_type.upper()} 节点生成专家

你是一个专门负责生成 {node_type} 节点配置的专家。请根据业务需求和节点规范，生成完整且准确的节点JSON配置。

## 业务背景
**用户需求**: {user_requirement}
**节点用途**: {node_info['purpose']}
**业务上下文**: {node_info['context']}
**建议名称**: {node_info['suggested_name']}

## 业务分析上下文
**需求总结**: {business_context['requirement_summary']}
**关键行为**: {', '.join(business_context['key_actions'])}
**数据实体**: {', '.join(business_context['data_entities'])}
**业务规则**: {', '.join(business_context['business_rules'])}

## 节点DSL规范
{dsl_template}

## 生成要求
1. **准确性**: 配置必须符合DSL规范和业务需求
2. **完整性**: 包含所有必需字段和合理的可选字段
3. **实用性**: 配置能够在实际业务场景中正常工作
4. **一致性**: 字段名和数据引用必须准确
5. **描述性**: 节点名称和描述要清晰明确
6. **英文命名**: 节点名称必须使用英文且以大写字母开头，采用PascalCase格式，如: "QuerySupplier", "CreateUser", "CheckUserExists"
7. **唯一性**: 节点名称必须唯一，不能与其他节点重复
8. **引用准确性**: 所有数据引用必须使用实际存在的节点名称，禁止使用虚构的节点名称

## 🚨 输入参数映射 - 必须遵循的规则

**如果当前节点有前置节点，且当前节点有input项目则必须在inputs字段中正确引用前置节点的输出：**

⚠️ **特别注意**: condition节点不使用inputs字段！condition节点通过configs.conditionGroups.conditions中的left字段引用前置节点数据。

**对于非condition节点**:
1. **必须使用正确的引用格式**: `"value": "$.NodeName.outputs.fieldName"`
2. **必须使用实际存在的字段**: 不能虚构字段名，严格按照节点类型的标准输出
3. **数据库节点特殊要求**: 只能引用 `data` 和 `affected` 字段
4. **必须包含type和desc**: 每个input字段都要有type和desc属性

## 🚨 数据库查询结果正确引用方式（重要）

**数据库查询节点的两个固定输出字段**:
- `affected`: 查询影响的行数（数字类型）- 用于存在性检查
- `data`: 查询结果数组（数组类型）- 包含实际的数据记录

**正确的引用方式**:
✅ **存在性检查**: `$.QuerySupplier.{{outputs}}.affected` (判断是否查询到结果)
✅ **获取具体ID**: `$.QuerySupplier.{{outputs}}.data[0].id` (从结果中获取供应商ID)
✅ **获取具体字段**: `$.QuerySupplier.{{outputs}}.data[0].name` (从结果中获取供应商名称)

**错误的引用方式**:
❌ **错误**: `"supplierId": {{"value": "$.QuerySupplier.{{outputs}}.affected"}}` (affected是数字，不是ID)
❌ **错误**: `"supplierName": {{"value": "$.QuerySupplier.{{outputs}}.supplier"}}` (supplier字段不存在)

**具体字段引用规则**:
- 需要ID时: 使用 `$.NodeName.{{outputs}}.data[0].id`
- 需要名称时: 使用 `$.NodeName.{{outputs}}.data[0].name` 
- 需要其他字段: 使用 `$.NodeName.{{outputs}}.data[0].fieldName`
- 需要判断存在性: 使用 `$.NodeName.{{outputs}}.affected > 0`

**错误示例** (禁止这样做):
```json
// ❌ 错误1: 空的inputs，没有引用前置节点
"inputs": {{{{}}}}

// ❌ 错误2: 引用不存在的字段
"inputs": {{{{
  "supplier": {{{{"value": "$.QuerySupplier.{{outputs}}.supplier"}}}}
}}}}

// ❌ 错误3: 用affected作为ID（类型不匹配）
"inputs": {{{{
  "supplierId": {{{{"value": "$.QuerySupplier.{{outputs}}.affected"}}}}
}}}}
```

**正确示例** (应该这样做):
```json
// ✅ 正确: 从数据库查询结果中获取具体字段
"inputs": {{{{
  "supplierId": {{{{
    "type": "string",
    "value": "$.QuerySupplier.{{outputs}}.data[0].id",
    "desc": "供应商ID（从查询结果中获取）"
  }}}},
  "supplierName": {{{{
    "type": "string", 
    "value": "$.QuerySupplier.{{outputs}}.data[0].name",
    "desc": "供应商名称（从查询结果中获取）"
  }}}},
  "affectedRows": {{{{
    "type": "number",
    "value": "$.QuerySupplier.{{outputs}}.affected", 
    "desc": "查询影响的行数（用于存在性检查）"
  }}}}
}}}}
```

**基于前置节点的正确示例**:
（此部分将在实际生成时基于真实前置节点配置动态生成）

## 输出格式
请直接输出完整的JSON节点配置，不要包含任何额外的说明文字：


请确保输出的JSON格式完全正确，可以直接解析使用。
**特别注意**: 节点名称必须使用英文且以大写字母开头，采用PascalCase格式，如 "QuerySupplier", "CreateUser", "CheckUserExists"。确保节点名称唯一，不与其他节点重复。"""
        
        return base_prompt
    
    def _generate_real_inputs_example(self, previous_node_configs: List[Dict[str, Any]], node_type: str = "") -> str:
        """基于真实的前置节点配置生成inputs示例"""
        try:
            # 🎯 特殊处理：condition节点不需要inputs字段
            if node_type and "condition" in node_type.lower():
                if previous_node_configs:
                    latest_node = previous_node_configs[-1]
                    node_name = latest_node.get('name', 'PreviousNode')
                    outputs = latest_node.get('config', {}).get('outputs', {})
                    
                    if outputs:
                        # 基于真实前置节点生成condition示例
                        first_output_field = list(outputs.keys())[0]
                        return f"""**condition节点特殊说明**:
根据DSL规范，condition节点不需要inputs字段，数据通过configs.conditionGroups中的conditions进行引用：

前置节点 `{node_name}` 的实际outputs:
```json
{json.dumps(outputs, ensure_ascii=False, indent=2)}
```

**对应的condition配置示例**:
```json
{{
  "configs": {{
    "conditionGroups": [
      {{
        "conditions": [
          {{
            "left": "$.{node_name}.outputs.{first_output_field}",
            "operator": "greaterThan", 
            "right": 0
          }}
        ],
        "relationship": "AND",
        "nextNode": "NextNodeName"
      }}
    ],
    "defaultNextNode": "DefaultNodeName"
  }}
}}
```

**重要**: condition节点通过configs.conditionGroups.conditions中的left字段引用前置节点数据，不使用inputs字段。"""
                    else:
                        return f"""**condition节点特殊说明**:
根据DSL规范，condition节点不需要inputs字段。前置节点 `{node_name}` 没有outputs，可引用其inputs：

```json
{{
  "configs": {{
    "conditionGroups": [
      {{
        "conditions": [
          {{
            "left": "$.{node_name}.inputs.fieldName",
            "operator": "equal", 
            "right": "expectedValue"
          }}
        ],
        "relationship": "AND",
        "nextNode": "NextNodeName"
      }}
    ],
    "defaultNextNode": "DefaultNodeName"
  }}
}}
```

**重要**: condition节点通过configs.conditionGroups.conditions中的left字段引用前置节点数据，不使用inputs字段。"""
                else:
                    return """**condition节点特殊说明**:
根据DSL规范，condition节点不需要inputs字段，数据通过configs.conditionGroups中的conditions进行引用：

```json
{
  "configs": {
    "conditionGroups": [
      {
        "conditions": [
          {
            "left": "$.PreviousNode.outputs.fieldName",
            "operator": "greaterThan", 
            "right": 0
          }
        ],
        "relationship": "AND",
        "nextNode": "NextNodeName"
      }
    ],
    "defaultNextNode": "DefaultNodeName"
  }
}
```

**重要**: condition节点通过configs.conditionGroups.conditions中的left字段引用前置节点数据，不使用inputs字段。"""

            if not previous_node_configs:
                return """**当前是第一个节点**，无需引用前置节点，inputs用于定义工作流的初始输入参数:
```json
"inputs": {{{{
  "parameters": {{{{
    "type": "object",
    "desc": "工作流输入参数"
  }}}}
}}}}
```"""
            
            # 获取最近的前置节点
            latest_node = previous_node_configs[-1]
            node_name = latest_node.get('name', 'PreviousNode')
            node_config = latest_node.get('config', {})
            outputs = node_config.get('outputs', {})
            
            if not outputs:
                return f"""**前置节点 `{node_name}` 没有outputs字段**，请根据节点类型设置合适的inputs:
```json
"inputs": {{{{
  "workflowParams": {{{{
    "type": "object",
    "value": "$.{node_name}.inputs.parameters",
    "desc": "来自前置节点的参数"
  }}}}
}}}}
```"""
            
            # 基于真实的前置节点outputs生成inputs示例
            example_inputs = {}
            for output_field, output_info in outputs.items():
                field_type = output_info.get('type', 'object')
                field_desc = output_info.get('desc', f'来自{node_name}的{output_field}数据')
                
                # 生成合适的input字段名
                input_field_name = self._generate_input_field_name(output_field, node_name)
                
                # 🎯 特殊处理数据库查询节点的data字段
                if output_field == "data" and "query" in node_name.lower():
                    # 为数据库查询结果提供具体的字段访问示例
                    example_inputs[input_field_name] = {
                        "type": field_type,
                        "value": f"$.{node_name}.outputs.{output_field}",
                        "desc": f"{field_desc}（完整数组）"
                    }
                    
                    # 添加具体字段访问示例
                    if "supplier" in node_name.lower():
                        example_inputs["supplierId"] = {
                            "type": "string",
                            "value": f"$.{node_name}.outputs.data[0].id",
                            "desc": "供应商ID（从查询结果中获取）"
                        }
                        example_inputs["supplierName"] = {
                            "type": "string", 
                            "value": f"$.{node_name}.outputs.data[0].name",
                            "desc": "供应商名称（从查询结果中获取）"
                        }
                    elif "product" in node_name.lower():
                        example_inputs["productId"] = {
                            "type": "string",
                            "value": f"$.{node_name}.outputs.data[0].id", 
                            "desc": "商品ID（从查询结果中获取）"
                        }
                        example_inputs["productName"] = {
                            "type": "string",
                            "value": f"$.{node_name}.outputs.data[0].name",
                            "desc": "商品名称（从查询结果中获取）"
                        }
                    elif "user" in node_name.lower():
                        example_inputs["userId"] = {
                            "type": "string",
                            "value": f"$.{node_name}.outputs.data[0].id",
                            "desc": "用户ID（从查询结果中获取）"
                        }
                        example_inputs["username"] = {
                            "type": "string",
                            "value": f"$.{node_name}.outputs.data[0].username",
                            "desc": "用户名（从查询结果中获取）"
                        }
                    else:
                        # 通用的ID和名称字段示例
                        example_inputs["entityId"] = {
                            "type": "string",
                            "value": f"$.{node_name}.outputs.data[0].id",
                            "desc": "实体ID（从查询结果中获取）"
                        }
                else:
                    example_inputs[input_field_name] = {
                        "type": field_type,
                        "value": f"$.{node_name}.outputs.{output_field}",
                        "desc": field_desc
                    }
            
            # 生成JSON示例
            inputs_json = json.dumps(example_inputs, ensure_ascii=False, indent=2)
            
            return f"""**基于真实前置节点 `{node_name}` 的正确示例**:

前置节点的实际outputs结构:
```json
{json.dumps(outputs, ensure_ascii=False, indent=2)}
```

**对应的inputs配置**:
```json
"inputs": {inputs_json}
```

**说明**: 以上示例是基于前置节点 `{node_name}` 的实际outputs字段生成的，请严格按照这种格式引用前置节点的数据。"""
            
        except Exception as e:
            logger.error(f"生成真实inputs示例失败: {str(e)}")
            return """**通用inputs示例**:
```json
"inputs": {{{{
  "previousResult": {{{{
    "type": "object",
    "value": "$.PreviousNode.outputs",
    "desc": "前置节点的输出结果"
  }}}}
}}}}
```"""
    
    async def _generate_individual_nodes(self, node_prompts: List[Dict[str, Any]], user_requirement: str) -> List[Dict[str, Any]]:
        """逐个生成节点配置"""
        generated_nodes = []
        generated_node_configs = []  # 存储已生成节点的完整配置
        
        # 收集所有节点的建议名称，用于引用验证
        all_node_names = []
        for prompt_info in node_prompts:
            node_info = prompt_info.get("node_info", {})
            suggested_name = node_info.get("suggested_name", "")
            if suggested_name:
                all_node_names.append(suggested_name)
        
        logger.info(f"所有节点的建议名称: {all_node_names}")
        
        for i, prompt_info in enumerate(node_prompts):
            node_type = prompt_info["node_type"]
            node_info = prompt_info["node_info"]
            
            # 🎯 动态重新生成包含真实前置节点配置的提示词
            context = await self.state_manager.get_context()
            user_requirement = context.user_requirement
            dsl_template = self.dsl_templates.get(node_type, "")
            
            # 使用基础的业务上下文（简化版本）
            business_context = {
                "requirement_summary": f"为{node_type}节点生成配置",
                "key_actions": [node_info.get("purpose", "执行节点功能")],
                "data_entities": ["数据处理"],
                "business_rules": ["遵循DSL规范"]
            }
            
            # 使用真实的前置节点配置重新生成提示词
            updated_prompt = await self._create_node_generation_prompt(
                node_type=node_type,
                node_info=node_info,
                user_requirement=user_requirement,
                dsl_template=dsl_template,
                business_context=business_context,
                previous_node_configs=generated_node_configs  # 🎯 传递真实的前置节点配置
            )
            
            # 在提示词中添加节点名称上下文和前置节点的详细配置
            enhanced_prompt = self._enhance_prompt_with_node_context(
                updated_prompt, all_node_names, i, generated_node_configs, node_type
            )
            
            logger.info(f"生成节点 {i+1}/{len(node_prompts)}: {node_type}")
            logger.info(f"🎯 使用了 {len(generated_node_configs)} 个前置节点的真实配置")
            
            try:
                # 调用LLM生成节点配置
                response = await self.llm_client.chat_completion(
                    [{"role": "user", "content": enhanced_prompt}],
                    max_tokens=self._get_max_tokens_for_node_type(node_type),
                    temperature=0.1
                )
                
                # 解析响应
                node_config = self._parse_node_response(response)
                
                # 验证节点配置
                # validated_config = self._validate_node_config(node_config, node_type)
                
                # 添加到结果中
                generated_nodes.append({
                    "node_type": node_type,
                    "node_config": node_config,
                    "generation_info": {
                        "prompt_used": enhanced_prompt,
                        "raw_response": response,
                        "validation_applied": True
                    }
                })
                
                # 保存已生成的节点配置，供后续节点参考
                generated_node_configs.append({
                    "name": node_config.get('name', 'unknown'),
                    "type": node_config.get('type', node_type),
                    "config": node_config
                })
                
                logger.info(f"成功生成节点: {node_config.get('name', 'unknown')}")
                
            except Exception as e:
                logger.error(f"生成节点 {node_type} 失败: {str(e)}")
                # 生成默认节点配置
                default_config = self._generate_default_node_config(node_type)
                generated_nodes.append({
                    "node_type": node_type,
                    "node_config": default_config,
                    "generation_info": {
                        "error": str(e),
                        "is_default": True
                    }
                })
                
                # 也要保存默认配置供后续节点参考
                generated_node_configs.append({
                    "name": default_config.get('name', 'unknown'),
                    "type": default_config.get('type', node_type),
                    "config": default_config
                })
        
        return generated_nodes
    
    def _enhance_prompt_with_node_context(self, base_prompt: str, all_node_names: List[str], current_index: int, generated_node_configs: List[Dict[str, Any]] = None, current_node_type: str = "") -> str:
        """增强提示词，添加节点名称上下文、前置节点详细配置和具体的输入参数映射指导"""
        
        # 获取前面已生成的节点名称
        previous_node_names = all_node_names[:current_index]
        remaining_node_names = all_node_names[current_index:]
        current_node_name = remaining_node_names[0] if remaining_node_names else "CurrentNode"
        
        # 生成前置节点的详细配置信息
        previous_nodes_details = self._generate_previous_nodes_details(generated_node_configs or [])
        
        # 🎯 生成基于真实前置节点配置的inputs示例
        real_inputs_example = self._generate_real_inputs_example(generated_node_configs or [], current_node_type)
        
        # 生成具体的输入参数映射指导（基于实际的前置节点配置）
        input_mapping_guidance = self._generate_enhanced_input_mapping_guidance(
            previous_node_names, current_node_name, current_index, generated_node_configs or []
        )
        
        context_info = f"""
## 节点名称上下文

**已生成的节点名称**:
{', '.join(previous_node_names) if previous_node_names else '无'}

**当前节点名称**: {current_node_name}

**后续节点名称**:
{', '.join(remaining_node_names[1:]) if len(remaining_node_names) > 1 else '无'}

## 📋 前置节点详细配置（重要参考）

{previous_nodes_details}

## 🎯 输入参数映射指导（基于实际前置节点）

{input_mapping_guidance}

## 🔧 基于真实前置节点的inputs配置示例

{real_inputs_example}

## 数据引用规范

**引用格式**:
- 引用前置节点输出: `$.NodeName.{{outputs}}.fieldName`
- 引用工作流输入: `$.workflowStart.{{inputs}}.fieldName`
- 数据库查询节点的固定输出: `data` (数组) 和 `affected` (数字)

**特别注意**:
- ⚠️ **数据库节点的输出结构是固定的**: 所有dbQuery/dbCreate/dbUpdate/dbDelete节点的{{outputs}}只有两个字段：
  - `data`: 查询结果数组 (type: "array")
  - `affected`: 受影响行数 (type: "number")
- ⚠️ **存在性检查**: 判断查询是否有结果请使用 `$.NodeName.{{outputs}}.affected > 0`
- ⚠️ **获取具体数据**: 获取查询结果中的字段请使用 `$.NodeName.{{outputs}}.data[0].fieldName`
- 节点名称必须以大写字母开头，采用PascalCase格式
- 禁止使用不存在的节点名称
- 必须使用实际已生成的节点名称进行引用
- ⚠️ **严格按照上述前置节点的实际outputs字段进行引用，不要虚构字段名称**
"""
        
        # 将上下文信息添加到基础提示词中
        enhanced_prompt = base_prompt + context_info
        
        return enhanced_prompt
    
    def _generate_previous_nodes_details(self, generated_node_configs: List[Dict[str, Any]]) -> str:
        """生成前置节点的详细配置信息"""
        try:
            if not generated_node_configs:
                return "**当前没有前置节点**，这是第一个节点。"
            
            details = "以下是已生成的前置节点的详细配置，当前节点可以引用这些节点的outputs：\n\n"
            
            for i, node_info in enumerate(generated_node_configs, 1):
                node_name = node_info.get('name', 'Unknown')
                node_type = node_info.get('type', 'unknown')
                node_config = node_info.get('config', {})
                
                # 获取节点的inputs、outputs和configs
                inputs = node_config.get('inputs', {})
                outputs = node_config.get('outputs', {})
                configs = node_config.get('configs', {})
                
                details += f"### {i}. 节点: {node_name} (类型: {node_type})\n\n"
                
                # 显示outputs结构（最重要，当前节点需要引用）
                if outputs:
                    details += "**🎯 可引用的outputs字段** (重要):\n"
                    details += "```json\n"
                    details += json.dumps(outputs, ensure_ascii=False, indent=2)
                    details += "\n```\n\n"
                    
                    # 生成具体的引用示例
                    details += "**引用示例**:\n"
                    for field_name, field_info in outputs.items():
                        field_type = field_info.get('type', 'unknown')
                        details += f"- `$.{node_name}.outputs.{field_name}` - {field_info.get('desc', '无描述')} (类型: {field_type})\n"
                    details += "\n"
                else:
                    details += "**outputs**: 空（该节点不产生输出数据）\n\n"
                
                # 显示configs（如果包含SQL或重要配置信息）
                if configs:
                    details += "**节点配置信息**:\n"
                    if 'sql' in configs:
                        details += f"- SQL语句: `{configs['sql']}`\n"
                    if 'table' in configs:
                        details += f"- 操作表: `{configs['table']}`\n"
                    if 'method' in configs:
                        details += f"- HTTP方法: `{configs['method']}`\n"
                    if 'url' in configs:
                        details += f"- 请求URL: `{configs['url']}`\n"
                    details += "\n"
                
                details += "---\n\n"
            
            details += "⚠️ **重要提醒**: 当前节点的inputs必须引用上述前置节点的outputs字段，不能虚构不存在的字段名称！"
            
            return details
            
        except Exception as e:
            logger.error(f"生成前置节点详细信息失败: {str(e)}")
            return "**无法获取前置节点详细信息**，请参考通用的数据引用规范。"
    
    def _generate_enhanced_input_mapping_guidance(self, previous_node_names: List[str], current_node_name: str, current_index: int, generated_node_configs: List[Dict[str, Any]]) -> str:
        """基于实际前置节点配置生成增强的输入映射指导"""
        try:
            if current_index == 0 or not generated_node_configs:
                return """**当前是第一个节点**:
- 通常是workflowStart节点，不需要引用其他节点的数据
- inputs用于定义工作流的初始输入参数
- 例如: `"inputs": {"parameters": {"type": "object", "desc": "工作流输入参数"}}`"""
            
            elif len(generated_node_configs) == 1:
                # 只有一个前置节点的情况
                prev_node_config = generated_node_configs[0]
                prev_node_name = prev_node_config.get('name', 'Unknown')
                prev_node_type = prev_node_config.get('type', 'unknown')
                prev_outputs = prev_node_config.get('config', {}).get('outputs', {})
                
                guidance = f"""**当前节点有一个前置节点: {prev_node_name} (类型: {prev_node_type})**

🎯 **基于实际前置节点的输入参数设置**:

"""
                
                if prev_outputs:
                    guidance += f"前置节点 `{prev_node_name}` 的实际outputs字段:\n\n"
                    
                    # 生成具体的inputs配置建议
                    suggested_inputs = {}
                    for field_name, field_info in prev_outputs.items():
                        field_type = field_info.get('type', 'object')
                        field_desc = field_info.get('desc', f'来自{prev_node_name}的{field_name}数据')
                        
                        # 生成合适的input字段名
                        input_field_name = self._generate_input_field_name(field_name, prev_node_name)
                        
                        suggested_inputs[input_field_name] = {
                            "type": field_type,
                            "value": f"$.{prev_node_name}.outputs.{field_name}",
                            "desc": field_desc
                        }
                    
                    guidance += "**推荐的inputs配置**:\n"
                    guidance += "```json\n"
                    guidance += '"inputs": ' + json.dumps(suggested_inputs, ensure_ascii=False, indent=2) + "\n"
                    guidance += "```\n\n"
                    
                    guidance += "**字段说明**:\n"
                    for input_name, input_config in suggested_inputs.items():
                        guidance += f"- `{input_name}`: {input_config['desc']} (引用: `{input_config['value']}`)\n"
                
                else:
                    guidance += f"⚠️ 前置节点 `{prev_node_name}` 没有outputs字段，请根据节点类型设置合适的inputs。\n"
                
                return guidance
            
            else:
                # 多个前置节点的情况
                most_recent_config = generated_node_configs[-1]
                most_recent_name = most_recent_config.get('name', 'Unknown')
                most_recent_outputs = most_recent_config.get('config', {}).get('outputs', {})
                
                guidance = f"""**当前节点有多个前置节点，最近的是: {most_recent_name}**

🎯 **建议主要引用最近的前置节点**:

"""
                
                if most_recent_outputs:
                    # 生成基于最近节点的inputs建议
                    suggested_inputs = {}
                    for field_name, field_info in most_recent_outputs.items():
                        field_type = field_info.get('type', 'object')
                        field_desc = field_info.get('desc', f'来自{most_recent_name}的{field_name}数据')
                        
                        input_field_name = self._generate_input_field_name(field_name, most_recent_name)
                        suggested_inputs[input_field_name] = {
                            "type": field_type,
                            "value": f"$.{most_recent_name}.outputs.{field_name}",
                            "desc": field_desc
                        }
                    
                    guidance += "**基于最近前置节点的推荐inputs配置**:\n"
                    guidance += "```json\n"
                    guidance += '"inputs": ' + json.dumps(suggested_inputs, ensure_ascii=False, indent=2) + "\n"
                    guidance += "```\n\n"
                
                # 列出所有可引用的前置节点
                guidance += "**所有可引用的前置节点**:\n"
                for config in generated_node_configs:
                    node_name = config.get('name', 'Unknown')
                    outputs = config.get('config', {}).get('outputs', {})
                    if outputs:
                        guidance += f"- `{node_name}`: 可引用字段 {list(outputs.keys())}\n"
                
                return guidance
        
        except Exception as e:
            logger.error(f"生成增强输入映射指导失败: {str(e)}")
            return f"""**基本输入映射指导**:
- 当前节点需要设置{{inputs}}字段来引用前置节点的数据
- 使用格式: `"value": "$.NodeName.{{outputs}}.fieldName"`
- 可引用的前置节点: {', '.join(previous_node_names) if previous_node_names else '无'}"""
    
    def _generate_input_field_name(self, output_field_name: str, source_node_name: str) -> str:
        """为输入字段生成合适的名称"""
        # 根据输出字段名生成合适的输入字段名
        field_mappings = {
            'data': 'queryResult',
            'affected': 'affectedRows',
            'code': 'statusCode',
            'response': 'llmResponse',
            'result': 'previousResult'
        }
        
        # 如果有预定义的映射，使用它
        if output_field_name in field_mappings:
            return field_mappings[output_field_name]
        
        # 否则，使用源节点名称+字段名
        if 'Query' in source_node_name and output_field_name == 'data':
            return 'queryResult'
        elif 'Http' in source_node_name and output_field_name == 'data':
            return 'httpResponse'
        else:
            # 通用情况
            return f"{output_field_name}FromPrevious"
    
    def _generate_input_mapping_guidance(self, previous_node_names: List[str], current_node_name: str, current_index: int) -> str:
        """生成具体的输入参数映射指导"""
        try:
            if current_index == 0:
                # 第一个节点（通常是开始节点）
                return """**当前是第一个节点**:
- 通常是workflowStart节点，不需要引用其他节点的数据
- inputs用于定义工作流的初始输入参数
- 例如: `"inputs": {"parameters": {"type": "object", "desc": "工作流输入参数"}}`"""
            
            elif len(previous_node_names) == 0:
                return """**没有前置节点**:
- 当前节点应该是工作流的起始节点
- inputs用于定义工作流的初始参数"""
            
            elif len(previous_node_names) == 1:
                # 只有一个前置节点的情况
                prev_node = previous_node_names[0]
                return f"""**当前节点有一个前置节点: {prev_node}**

🎯 **输入参数设置要求**:
当前节点需要从前置节点 `{prev_node}` 获取数据，请根据以下规则设置inputs字段：

1. **如果前置节点是数据库查询节点** (dbQuery/dbCreate/dbUpdate/dbDelete):
   ```json
   "inputs": {{{{
     "queryResult": {{{{
       "type": "array",
       "value": "$.{prev_node}.outputs.data",
       "desc": "前置查询的结果数据"
     }}}},
     "affectedRows": {{{{
       "type": "number", 
       "value": "$.{prev_node}.outputs.affected",
       "desc": "前置查询影响的行数"
     }}}}
   }}}}
   ```

2. **如果前置节点是HTTP请求节点**:
   ```json
   "inputs": {{{{
     "httpResponse": {{{{
       "type": "object",
       "value": "$.{prev_node}.outputs.data",
       "desc": "HTTP响应数据"
     }}}},
     "statusCode": {{{{
       "type": "number",
       "value": "$.{prev_node}.outputs.code", 
       "desc": "HTTP状态码"
     }}}}
   }}}}
   ```

3. **如果前置节点是开始节点** (workflowStart):
   ```json
   "inputs": {{{{
     "workflowParams": {{{{
       "type": "object",
       "value": "$.{prev_node}.inputs.parameters",
       "desc": "工作流输入参数"
     }}}}
   }}}}
   ```

4. **通用情况**:
   ```json
   "inputs": {{{{
     "previousResult": {{{{
       "type": "object",
       "value": "$.{prev_node}.outputs",
       "desc": "前置节点的输出结果"
     }}}}
   }}}}
   ```

⚠️ **关键注意事项**:
- 必须使用 `"value": "$.{{{{prev_node}}}}.{{outputs}}.fieldName"` 格式进行引用
- 数据库节点只有 `data` 和 `affected` 两个输出字段
- 不要虚构不存在的字段名称，严格按照节点类型的标准输出结构"""
            
            else:
                # 多个前置节点的情况
                prev_nodes_list = ', '.join(previous_node_names)
                most_recent_node = previous_node_names[-1]
                
                return f"""**当前节点有多个前置节点: {prev_nodes_list}**

🎯 **输入参数设置要求**:
当前节点可以引用多个前置节点的数据，建议主要引用最近的前置节点 `{most_recent_node}`：

**推荐的inputs设置**:
```json
"inputs": {{{{
  "primaryInput": {{{{
    "type": "object",
    "value": "$.{most_recent_node}.outputs",
    "desc": "主要输入数据（来自最近的前置节点）"
  }}}},
  "contextData": {{{{
    "type": "object", 
    "value": "$.{previous_node_names[0]}.outputs",
    "desc": "上下文数据（来自早期节点）"
  }}}}
}}}}
```

**如果需要引用特定节点的数据**:
可以根据业务需求引用任何前置节点：
- `$.{{{{previous_node_names[0]}}}}.{{outputs}}.xxx` - 引用第一个节点的输出
- `$.{{{{most_recent_node}}}}.{{outputs}}.xxx` - 引用最近节点的输出

⚠️ **数据库节点特别提醒**:
如果前置节点包含数据库操作，请使用标准的输出字段：
- `$.NodeName.{{outputs}}.data` - 查询结果数组
- `$.NodeName.{{outputs}}.affected` - 受影响行数"""
        
        except Exception as e:
            logger.error(f"生成输入映射指导失败: {str(e)}")
            return f"""**基本输入映射指导**:
- 当前节点需要设置{{inputs}}字段来引用前置节点的数据
- 使用格式: `"value": "$.NodeName.{{outputs}}.fieldName"`
- 可引用的前置节点: {', '.join(previous_node_names) if previous_node_names else '无'}"""
    
    def _get_max_tokens_for_node_type(self, node_type: str) -> int:
        """根据节点类型获取最大token数"""
        token_limits = {
            "transaction": 8000,  # 事务节点需要更多tokens
            "batch": 8000,        # 批处理节点需要更多tokens
            "chatWithLLM": 8000,  # LLM节点需要更多tokens
            "code": 80000,         # 代码节点需要更多tokens
            "condition": 8000,    # 条件节点
            "http": 8000,         # HTTP节点
            "workflow": 8000,     # 工作流节点
            "dbQuery": 8000,      # 数据库查询节点
            "dbCreate": 8000,     # 数据库创建节点
            "dbUpdate": 8000,     # 数据库更新节点
            "dbDelete": 8000,     # 数据库删除节点
            "workflowStart": 8000,  # 开始节点
            "workflowEnd": 8000,    # 结束节点
        }
        
        return token_limits.get(node_type, 1500)  # 默认1500 tokens
    
    def _generate_default_node_config(self, node_type: str) -> Dict[str, Any]:
        """生成默认节点配置"""
        default_configs = {
            "workflowStart": {
                "name": "WorkflowStart",
                "type": "workflowStart",
                "desc": "工作流开始节点",
                "inputs": {},
                "outputs": {},
                "configs": {},
                "nextNodes": []
            },
            "workflowEnd": {
                "name": "WorkflowEnd",
                "type": "workflowEnd",
                "desc": "工作流结束节点",
                "inputs": {},
                "outputs": {
                    "code": {"type": "number", "desc": "HTTP状态码"},
                    "data": {"type": "object", "desc": "响应数据"},
                    "message": {"type": "string", "desc": "响应消息"}
                },
                "configs": {},
                "nextNodes": ["end"]
            },
            "dbQuery": {
                "name": "QueryData",
                "type": "dbQuery",
                "desc": "数据库查询节点",
                "inputs": {},
                "outputs": {
                    "affected": {"type": "number", "desc": "影响的行数"},
                    "data": {"type": "array", "desc": "查询结果数据"}
                },
                "configs": {
                    "table": "table_name",
                    "sql": "SELECT * FROM table_name"
                },
                "nextNodes": []
            },
            "dbCreate": {
                "name": "CreateData",
                "type": "dbCreate",
                "desc": "数据库创建节点",
                "inputs": {},
                "outputs": {
                    "affected": {"type": "number", "desc": "影响的行数"},
                    "insertId": {"type": "string", "desc": "插入的ID"}
                },
                "configs": {
                    "table": "table_name",
                    "sql": "INSERT INTO table_name VALUES (...)"
                },
                "nextNodes": []
            },
            "dbUpdate": {
                "name": "UpdateData",
                "type": "dbUpdate",
                "desc": "数据库更新节点",
                "inputs": {},
                "outputs": {
                    "affected": {"type": "number", "desc": "影响的行数"}
                },
                "configs": {
                    "table": "table_name",
                    "sql": "UPDATE table_name SET ..."
                },
                "nextNodes": []
            },
            "dbDelete": {
                "name": "DeleteData",
                "type": "dbDelete",
                "desc": "数据库删除节点",
                "inputs": {},
                "outputs": {
                    "affected": {"type": "number", "desc": "影响的行数"}
                },
                "configs": {
                    "table": "table_name",
                    "sql": "DELETE FROM table_name WHERE ..."
                },
                "nextNodes": []
            },
            "condition": {
                "name": "CheckCondition",
                "type": "condition",
                "desc": "条件判断节点",
                "configs": {
                    "conditionGroups": [
                        {
                            "relationship": "AND",
                            "conditions": [
                                {
                                    "left": "$.input.value",
                                    "operator": "equal",
                                    "right": "expected_value"
                                }
                            ],
                            "nextNode": "NextNode"
                        }
                    ],
                    "defaultNextNode": "DefaultNode"
                }
            },
            "http": {
                "name": "HttpRequest",
                "type": "http",
                "desc": "HTTP请求节点",
                "inputs": {},
                "outputs": {
                    "code": {"type": "number", "desc": "HTTP状态码"},
                    "data": {"type": "object", "desc": "响应数据"}
                },
                "configs": {
                    "method": "GET",
                    "url": "https://api.example.com/endpoint",
                    "headers": {},
                    "timeout": 30
                },
                "nextNodes": []
            },
            "chatWithLLM": {
                "name": "ChatWithLLM",
                "type": "chatWithLLM",
                "desc": "LLM对话节点",
                "inputs": {},
                "outputs": {
                    "thinking": {"type": "string", "desc": "思考过程"},
                    "response": {"type": "string", "desc": "LLM响应"},
                    "tokens": {"type": "number", "desc": "使用的token数"}
                },
                "configs": {
                    "model": "default",
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                "nextNodes": []
            },
            "code": {
                "name": "ExecuteCode",
                "type": "code",
                "desc": "代码执行节点",
                "inputs": {},
                "outputs": {
                    "result": {"type": "object", "desc": "代码执行结果"},
                    "logs": {"type": "array", "desc": "执行日志"}
                },
                "configs": {
                    "code": "// JavaScript代码",
                    "timeout": 30
                },
                "nextNodes": []
            },
            "transaction": {
                "name": "TransactionProcess",
                "type": "transaction",
                "desc": "数据库事务节点",
                "inputs": {},
                "outputs": {
                    "committed": {"type": "boolean", "desc": "事务是否成功提交"},
                    "affectedTotal": {"type": "number", "desc": "事务中所有操作影响的总行数"},
                    "childResults": {"type": "array", "desc": "所有子节点的执行结果数组"},
                    "executionTime": {"type": "number", "desc": "事务执行耗时（毫秒）"}
                },
                "configs": {
                    "isolation": "READ_COMMITTED",
                    "timeout": 60,
                    "children": []
                },
                "nextNodes": []
            },
            "batch": {
                "name": "BatchProcess",
                "type": "batch",
                "desc": "批量处理节点",
                "inputs": {},
                "outputs": {
                    "totalProcessed": {"type": "number", "desc": "总处理数量"},
                    "successCount": {"type": "number", "desc": "成功处理数量"},
                    "failureCount": {"type": "number", "desc": "失败处理数量"},
                    "aggregatedResult": {"type": "object", "desc": "聚合结果"},
                    "executionTime": {"type": "number", "desc": "批处理执行耗时（毫秒）"}
                },
                "configs": {
                    "mapConfig": {
                        "dataSource": "$.input.data",
                        "concurrency": 5
                    },
                    "reduceConfig": {
                        "strategy": "sum"
                    },
                    "child": {}
                },
                "nextNodes": []
            },
            "workflow": {
                "name": "CallWorkflow",
                "type": "workflow",
                "desc": "工作流调用节点",
                "inputs": {},
                "outputs": {
                    "code": {"type": "number", "desc": "HTTP状态码"},
                    "data": {"type": "object", "desc": "响应数据"},
                    "message": {"type": "string", "desc": "响应消息"}
                },
                "configs": {
                    "workflowName": "target_workflow",
                    "inputMappings": {},
                    "outputMappings": {}
                },
                "nextNodes": []
            }
        }
        
        # 生成符合PascalCase格式的默认节点名称
        default_name = f"Default{node_type.title()}Node"
        if not default_name[0].isupper():
            default_name = default_name[0].upper() + default_name[1:]
        
        return default_configs.get(node_type, {
            "name": default_name,
            "type": node_type,
            "desc": f"默认{node_type}节点",
            "inputs": {},
            "outputs": {},
            "configs": {},
            "nextNodes": []
        })
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 尝试从响应中提取JSON
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()
            
            result = json.loads(json_str)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应JSON失败: {str(e)}")
            raise ValueError(f"LLM响应格式不正确: {str(e)}")
    
    def _parse_node_response(self, response: str) -> Dict[str, Any]:
        """解析节点生成响应"""
        try:
            # 尝试从响应中提取JSON
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                # 尝试直接解析整个响应
                json_str = response.strip()
                # 如果不是以{开头，尝试找到第一个{
                if not json_str.startswith("{"):
                    start_idx = json_str.find("{")
                    if start_idx != -1:
                        json_str = json_str[start_idx:]
            
            result = json.loads(json_str)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析节点配置JSON失败: {str(e)}")
            logger.error(f"原始响应: {response}")
            raise ValueError(f"节点配置格式不正确: {str(e)}")
    
    def _validate_node_config(self, node_config: Dict[str, Any], expected_type: str) -> Dict[str, Any]:
        """验证节点配置"""
        # 检查必需字段，但根据节点类型决定是否需要outputs和nextNodes
        required_fields = ["name", "type", "desc", "inputs", "configs"]
        
        # 根据节点类型决定是否需要outputs和nextNodes字段
        if expected_type != "condition":  # condition节点不需要outputs和nextNodes字段
            required_fields.extend(["outputs", "nextNodes"])
        
        for field in required_fields:
            if field not in node_config:
                # 对于开始和结束节点的configs/outputs字段，不产生警告
                should_warn = True
                if node_type_manager.is_start_node(expected_type) or node_type_manager.is_end_node(expected_type):
                    if field in ["configs", "outputs"]:
                        should_warn = False
                
                if should_warn:
                    logger.warning(f"节点配置缺少字段 {field}，将使用默认值")
                
                if field == "inputs":
                    node_config[field] = {}
                elif field == "outputs":
                    # 根据节点类型设置默认outputs
                    if node_type_manager.is_start_node(expected_type):
                        node_config[field] = {}  # 开始节点不产生输出数据
                    else:
                        node_config[field] = {}  # 其他节点设置为空，由系统自动生成
                elif field == "configs":
                    node_config[field] = {}
                elif field == "nextNodes":
                    # 根据节点类型设置正确的默认nextNodes
                    if expected_type == "workflowEnd":
                        node_config[field] = ["end"]
                    else:
                        node_config[field] = []
                else:
                    node_config[field] = ""
        
        # 验证节点类型
        if node_config.get("type") != expected_type:
            logger.warning(f"节点类型不匹配，期望 {expected_type}，实际 {node_config.get('type')}")
            node_config["type"] = expected_type
        
        # 特殊处理：condition节点不应该有outputs和nextNodes字段
        if expected_type == "condition":
            if "outputs" in node_config:
                logger.info(f"移除condition节点的outputs字段，因为condition节点不产生数据输出")
                del node_config["outputs"]
            if "nextNodes" in node_config:
                logger.info(f"移除condition节点的nextNodes字段，因为condition节点的流向由条件配置决定")
                del node_config["nextNodes"]
                
        # 特殊处理：确保结束节点的nextNodes正确
        if node_type_manager.is_end_node(expected_type):
            actual_end_type = node_type_manager.find_end_node_type() or expected_type
            if node_config.get("nextNodes") != ["end"]:
                logger.info(f"修正{actual_end_type}节点的nextNodes为['end']")
                node_config["nextNodes"] = ["end"]
                
            # 确保结束节点有必需的输出字段
            required_outputs = ["code", "data", "message"]
            outputs = node_config.get("outputs", {})
            for output_field in required_outputs:
                if output_field not in outputs:
                    logger.warning(f"{actual_end_type}节点缺少必需输出字段: {output_field}，添加默认配置")
                    if output_field == "code":
                        outputs[output_field] = {
                            "type": "number",
                            "value": "200",
                            "desc": "HTTP状态码"
                        }
                    elif output_field == "data":
                        outputs[output_field] = {
                            "type": "string",
                            "value": "操作成功",
                            "desc": "响应数据"
                        }
                    elif output_field == "message":
                        outputs[output_field] = {
                            "type": "string",
                            "value": "操作完成",
                            "desc": "响应消息"
                        }
            node_config["outputs"] = outputs
        
        return node_config
    
    async def _create_fallback_node(self, node_type: str, node_info: Dict[str, Any]) -> Dict[str, Any]:
        """创建后备节点配置 - 使用数据库DSL数据"""
        try:
            # 从共享上下文获取节点DSL数据
            context = await self.state_manager.get_context()
            node_dsl_data = getattr(context, 'node_dsl_data', {})
            
            # 基础节点结构
            fallback_node = {
                "name": node_info.get("suggested_name", f"Default{node_type.title()}"),
                "type": node_type,
                "desc": node_info.get("purpose", f"默认{node_type}节点"),
                "inputs": {},
                "outputs": {},
                "configs": {},
                "nextNodes": []
            }
            
            # 如果数据库中有该节点类型的DSL数据，使用它作为模板
            if node_type in node_dsl_data:
                dsl_data = node_dsl_data[node_type]
                example = dsl_data.get('example', {})
                
                # 使用数据库中的示例作为基础
                if example and isinstance(example, dict):
                    # 保留基础信息，使用示例的结构
                    for field in ["inputs", "outputs", "configs", "nextNodes"]:
                        if field in example:
                            fallback_node[field] = example[field]
                    
                    # 使用我们的建议名称覆盖示例名称
                    fallback_node["name"] = node_info.get("suggested_name", example.get("name", f"Default{node_type.title()}"))
                    fallback_node["desc"] = node_info.get("purpose", example.get("desc", f"默认{node_type}节点"))
                    
                    logger.info(f"使用数据库DSL示例创建 {node_type} 后备节点")
                    return fallback_node
            
            # 如果没有数据库DSL数据，使用节点类型管理器的通用逻辑
            if node_type_manager.is_start_node(node_type):
                # 开始节点的默认配置
                fallback_node["inputs"] = {"parameters": {"type": "object", "desc": "工作流输入参数"}}
                fallback_node["outputs"] = {}
                fallback_node["configs"] = {}
                
            elif node_type_manager.is_end_node(node_type):
                # 结束节点的默认配置
                fallback_node["nextNodes"] = ["end"]
                fallback_node["outputs"] = {
                    "code": {"type": "number", "value": "200", "desc": "HTTP状态码"},
                    "data": {"type": "string", "value": "操作成功", "desc": "响应数据"},
                    "message": {"type": "string", "value": "操作完成", "desc": "响应消息"}
                }
                fallback_node["configs"] = {}
                
            elif "db" in node_type.lower():
                # 数据库节点的通用配置
                fallback_node["outputs"] = {
                    "affected": {"type": "number", "desc": "影响的行数"}
                }
                fallback_node["configs"] = {
                    "table": "default_table",
                    "sql": "SELECT 1"
                }
                
                # 根据操作类型调整
                if "query" in node_type.lower() or "select" in node_type.lower():
                    fallback_node["outputs"]["data"] = {"type": "array", "desc": "查询结果数据"}
                elif "create" in node_type.lower() or "insert" in node_type.lower():
                    fallback_node["outputs"]["insertId"] = {"type": "string", "desc": "新插入记录的ID"}
                    
            elif "http" in node_type.lower():
                # HTTP节点的默认配置
                fallback_node["outputs"] = {
                    "code": {"type": "number", "desc": "HTTP状态码"},
                    "data": {"type": "object", "desc": "响应数据"}
                }
                fallback_node["configs"] = {
                    "method": "GET",
                    "url": "https://api.example.com",
                    "bodyType": "none"
                }
                
            elif "condition" in node_type.lower():
                # 条件节点的特殊处理
                fallback_node["outputs"] = {}  # 条件节点不产生输出
                fallback_node["nextNodes"] = []  # 条件节点不使用nextNodes
                fallback_node["configs"] = {
                    "conditionGroups": [],
                    "defaultNextNode": ""
                }
                
            elif "llm" in node_type.lower() or "chat" in node_type.lower():
                # LLM节点的默认配置
                fallback_node["outputs"] = {
                    "response": {"type": "string", "desc": "AI生成的回复"},
                    "tokens": {"type": "object", "desc": "Token使用情况"}
                }
                fallback_node["configs"] = {
                    "modelId": "gpt-3.5-turbo"
                }
                
            else:
                # 通用节点的默认配置
                fallback_node["outputs"] = {
                    "result": {"type": "object", "desc": "节点执行结果"}
                }
                fallback_node["configs"] = {}
            
            logger.info(f"使用通用逻辑创建 {node_type} 后备节点")
            return fallback_node
            
        except Exception as e:
            logger.error(f"创建后备节点失败: {str(e)}")
            # 如果所有方法都失败，返回最基本的节点结构
            return {
                "name": node_info.get("suggested_name", f"Default{node_type.title()}"),
                "type": node_type,
                "desc": node_info.get("purpose", f"默认{node_type}节点"),
                "inputs": {},
                "outputs": {"result": {"type": "object", "desc": "节点执行结果"}},
                "configs": {},
                "nextNodes": []
            } 

    async def _ensure_db_templates_loaded(self):
        """确保数据库模板已加载（首次调用时异步加载）"""
        if not hasattr(self, '_db_templates_loaded') or not self._db_templates_loaded:
            try:
                db_templates = await self._load_templates_from_db()
                if db_templates:
                    # 更新现有模板，数据库模板优先
                    self.dsl_templates.update(db_templates)
                    logger.info(f"成功异步加载 {len(db_templates)} 个数据库模板")
                else:
                    logger.info("数据库模板为空，继续使用默认模板")
                self._db_templates_loaded = True
            except Exception as e:
                logger.error(f"异步加载数据库模板失败: {str(e)}")
                self._db_templates_loaded = True  # 标记为已尝试，避免重复加载 