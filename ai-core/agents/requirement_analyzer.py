"""
需求分析智能体 (Requirement Analyzer Agent)
负责分析用户需求，识别所需的节点类型和数量，并为每个节点生成专门的提示词和配置
"""

import json
import logging
from typing import Dict, List, Any, Optional
from multi_agent_workflow_generator import BaseAgent, AgentRole, MessageType

logger = logging.getLogger(__name__)


class RequirementAnalyzer(BaseAgent):
    """需求分析智能体 - 增强版，支持细化节点生成"""
    
    def __init__(self, message_bus, state_manager, llm_client):
        super().__init__(AgentRole.REQUIREMENT_ANALYZER, message_bus, state_manager)
        self.llm_client = llm_client
        self.node_types_info = self._load_node_types_info()
        self.dsl_templates = self._load_dsl_templates()
    
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
        """加载DSL模板，从dsl.md文件中读取每个节点类型的详细配置说明"""
        try:
            # 读取DSL文件
            import os
            dsl_file_path = os.path.join(os.path.dirname(__file__), "..", "dsl.md")
            
            if not os.path.exists(dsl_file_path):
                logger.warning("dsl.md文件不存在，使用默认模板")
                return self._get_default_templates()
            
            with open(dsl_file_path, 'r', encoding='utf-8') as f:
                dsl_content = f.read()
            
            # 解析DSL内容，提取各个节点类型的定义
            templates = {}
            
            # 分割不同的节点类型章节
            sections = dsl_content.split('\n# ')
            
            for section in sections:
                if not section.strip():
                    continue
                
                # 提取节点类型名称
                lines = section.split('\n')
                if not lines:
                    continue
                
                title = lines[0].strip()
                
                # 匹配节点类型
                if '工作流开始节点' in title or 'Start Node' in title:
                    templates['workflowStart'] = self._extract_section_content(section, 'workflowStart')
                elif '工作流结束节点' in title or 'End Node' in title:
                    templates['workflowEnd'] = self._extract_section_content(section, 'workflowEnd')
                elif '批量处理节点' in title or 'Batch Node' in title:
                    templates['batch'] = self._extract_section_content(section, 'batch')
                elif '条件判断节点' in title or 'Condition Node' in title:
                    templates['condition'] = self._extract_section_content(section, 'condition')
                elif '工作流节点' in title and 'Workflow Node' in title:
                    templates['workflow'] = self._extract_section_content(section, 'workflow')
                elif '数据库查询节点' in title or 'DbQuery Node' in title:
                    templates['dbQuery'] = self._extract_section_content(section, 'dbQuery')
                elif '数据库创建节点' in title or 'DbCreate Node' in title:
                    templates['dbCreate'] = self._extract_section_content(section, 'dbCreate')
                elif '数据库更新节点' in title or 'DbUpdate Node' in title:
                    templates['dbUpdate'] = self._extract_section_content(section, 'dbUpdate')
                elif '数据库删除节点' in title or 'DbDelete Node' in title:
                    templates['dbDelete'] = self._extract_section_content(section, 'dbDelete')
                elif '数据库事务节点' in title or 'Transaction Node' in title:
                    templates['transaction'] = self._extract_section_content(section, 'transaction')
                elif '代码执行节点' in title or 'Code Node' in title:
                    templates['code'] = self._extract_section_content(section, 'code')
                elif 'HTTP请求节点' in title or 'HTTP Request Node' in title:
                    templates['http'] = self._extract_section_content(section, 'http')
                elif 'LLM对话节点' in title or 'LLM Node' in title:
                    templates['chatWithLLM'] = self._extract_section_content(section, 'chatWithLLM')
            
            logger.info(f"成功从dsl.md加载了 {len(templates)} 个节点模板")
            return templates
            
        except Exception as e:
            logger.error(f"加载DSL模板失败: {str(e)}")
            return self._get_default_templates()
    
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
        
        system_prompt = """# 工作流需求分析专家

你是一个专业的工作流需求分析专家，专门负责分析用户的业务需求，并识别出完成该需求所需的所有工作流节点类型。

## 你的任务
1. 仔细分析用户的需求描述
2. 识别出需要哪些类型的节点来完成这个需求
3. 为每个节点类型提供用途说明和业务上下文
4. 确保节点的选择合理且完整

## 可用节点类型
- **workflowStart**: 工作流开始节点（必需）
- **workflowEnd**: 工作流结束节点（必需）  
- **dbQuery**: 数据库查询节点
- **dbCreate**: 数据库创建节点
- **dbUpdate**: 数据库更新节点
- **dbDelete**: 数据库删除节点
- **http**: HTTP请求节点
- **chatWithLLM**: LLM对话节点
- **condition**: 条件判断节点
- **code**: 代码执行节点
- **transaction**: 数据库事务节点
- **batch**: 批量处理节点
- **workflow**: 工作流节点

## 输出格式
请严格按照以下JSON格式输出：
```json
{
  "analysis": {
    "requirement_summary": "需求总结",
    "key_actions": ["关键行为1", "关键行为2"],
    "data_entities": ["数据实体1", "数据实体2"],
    "business_rules": ["业务规则1", "业务规则2"]
  },
  "required_node_types": [
    {
      "type": "节点类型",
      "purpose": "节点用途说明",
      "context": "在当前业务需求中的作用",
      "suggested_name": "建议的节点名称",
      "priority": 1,
      "dependencies": ["依赖的其他节点类型"]
    }
  ],
  "workflow_complexity": "简单/中等/复杂"
}
```"""
    
        user_prompt = f"""请分析以下用户需求，并识别出完成该需求所需的所有工作流节点类型：

**用户需求：**
{user_requirement}

**可用数据库表信息：**
- users: 用户表(id, username, email, password, real_name, phone, role, status)
- categories: 商品分类表(id, parent_id, name, code, description)
- suppliers: 供应商表(id, code, name, contact_person, phone, email)
- customers: 客户表(id, code, name, type, contact_person, phone, email)
- products: 商品表(id, sku, name, category_id, brand, model, cost_price, sale_price, current_stock)
- warehouses: 仓库表(id, code, name, address, manager, phone)
- inventory: 库存表(id, warehouse_id, product_id, quantity, available_quantity)
- purchase_orders: 采购订单表(id, order_no, supplier_id, warehouse_id, total_amount, status)
- sales_orders: 销售订单表(id, order_no, customer_id, warehouse_id, total_amount, status)
- stock_movements: 库存变动记录表(id, warehouse_id, product_id, movement_type, quantity)

请按照分析原则，仔细分析用户需求，并按照指定的JSON格式输出结果。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
            ]
            
        response = await self.llm_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
        return self._parse_llm_response(response)
            
    async def _generate_node_prompts(self, node_analysis: Dict[str, Any], user_requirement: str) -> List[Dict[str, Any]]:
        """第二阶段: 为每个节点生成专门的提示词"""
        
        node_prompts = []
        
        for node_info in node_analysis["required_node_types"]:
            node_type = node_info["type"]
            
            # 获取该节点类型的DSL模板
            dsl_template = self.dsl_templates.get(node_type, "")
            
            # 生成专门的提示词
            prompt = await self._create_node_generation_prompt(
                node_type=node_type,
                node_info=node_info,
                user_requirement=user_requirement,
                dsl_template=dsl_template,
                business_context=node_analysis["analysis"]
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
                                           business_context: Dict[str, Any]) -> str:
        """为特定节点类型创建生成提示词"""
        
        # 根据节点类型添加特殊要求
        special_requirements = ""
        if node_type == "workflowStart":
            special_requirements = """
## ⚠️ workflowStart节点特殊要求 ⚠️
1. **configs设置为空对象{}** - 此节点类型无需特殊配置
2. **outputs设置为空对象{}** - 此节点类型不产生输出数据
3. **inputs字段** - 用于定义工作流的初始输入参数
4. **nextNodes** - 指向下一个要执行的节点"""
        elif node_type == "workflowEnd":
            special_requirements = """
## ⚠️ workflowEnd节点特殊要求 ⚠️
1. **nextNodes必须设置为空数组[]** - 因为这是工作流的终点！
2. **configs设置为空对象{}** - 此节点类型无需特殊配置
3. **必须包含标准API响应字段**：
   - code: HTTP状态码（数字类型）
   - data: 响应数据（字符串、对象或数组类型）  
   - message: 响应消息（字符串类型）
4. **outputs字段示例**：
```json
"outputs": {
  "code": {
    "type": "number",
    "value": "200",
    "desc": "HTTP状态码"
  },
  "data": {
    "type": "string", 
    "value": "$.PrevNode.outputs.result",
    "desc": "响应数据"
  },
  "message": {
    "type": "string",
    "value": "操作成功",
    "desc": "响应消息"
  }
}
```"""
        elif node_type.startswith("db"):
            special_requirements = f"""
## ⚠️ {node_type}节点特殊要求 ⚠️
1. **configs必须包含**：
   - table: 表名称（字符串）
   - sql: SQL语句（字符串，支持变量引用）
2. **outputs字段已固定**，不需要设置value字段：
   {"- affected: 影响的行数（数字类型）" if node_type != "dbQuery" else "- affected: 查询返回的行数（数字类型）"}
   {"- data: 查询结果数据（数组类型）" if node_type == "dbQuery" else ""}
   {"- insertId: 新插入记录的ID（字符串类型）" if node_type == "dbCreate" else ""}"""
        elif node_type == "http":
            special_requirements = """
## ⚠️ HTTP节点特殊要求 ⚠️
1. **configs必须包含**：
   - method: 请求方法（GET/POST/PUT/DELETE等）
   - url: 请求URL（字符串）
   - bodyType: 请求体类型（none/json/form-data/text）
2. **outputs字段已固定**，不需要设置value字段：
   - code: HTTP状态码（数字类型）
   - data: 响应数据（对象类型）"""
        elif node_type == "chatWithLLM":
            special_requirements = """
## ⚠️ LLM节点特殊要求 ⚠️
1. **configs必须包含**：
   - modelId: 模型ID（字符串）
2. **outputs字段已固定**，不需要设置value字段：
   - thinking: AI思考过程（字符串类型）
   - response: AI生成的回复（字符串类型）
   - tokens: Token使用情况（对象类型）"""
        elif node_type == "condition":
            special_requirements = """
## ⚠️ Condition节点特殊要求 ⚠️
1. **configs必须包含**：
   - conditionGroups: 条件组配置（数组）
   - defaultNextNode: 默认跳转节点（字符串，可选）
2. **不需要nextNodes字段** - 条件节点不设置nextNodes数组，流向由条件配置决定
3. **不需要outputs字段** - 条件节点不产生数据输出
4. **条件组配置要求**：
   - conditions: 单个条件组内的条件列表
   - relationship: 条件组内的逻辑关系 (AND/OR)
   - nextNode: 条件满足时跳转的节点ID
5. **支持的操作符**：
   - equal, notEqual, greaterThan, greaterThanEqual, lessThan, lessThanEqual
   - isNull, isNotNull, include, notInclude
6. **变量引用格式**：使用`$.节点名.inputs.字段名`格式引用数据"""
        elif node_type == "batch":
            special_requirements = """
## ⚠️ Batch节点特殊要求 ⚠️
1. **configs必须包含**：
   - mapConfig: Map配置（包含dataSource等）
   - reduceConfig: Reduce配置（包含strategy等）
   - child: 子节点完整配置（对象）
2. **outputs字段已固定**，不需要设置value字段"""
        elif node_type == "transaction":
            special_requirements = """
## ⚠️ Transaction节点特殊要求 ⚠️
1. **configs必须包含**：
   - isolation: 事务隔离级别（可选，默认READ_COMMITTED）
   - timeout: 事务超时时间（可选，默认60秒）
   - children: 子节点数组（必填，每个子节点包含完整配置和order字段）
2. **outputs字段已固定**，不需要设置value字段：
   - committed: 事务是否成功提交（布尔类型）
   - affectedTotal: 事务中所有操作影响的总行数（数字类型）
   - childResults: 所有子节点的执行结果数组（数组类型）
   - executionTime: 事务执行耗时（数字类型）
3. **子节点配置要求**：
   - name: 子节点名称（必填）
   - type: 节点类型（必填，只支持dbCreate、dbUpdate、dbDelete）
   - desc: 节点描述（必填）
   - order: 执行顺序（必填，从1开始）
   - inputs: 节点输入参数（可选）
   - outputs: 节点输出参数（必填）
   - configs: 节点配置（必填，包含table和sql）
4. **重要提示**：
   - 子节点的order必须唯一且连续，从1开始
   - 子节点间可以通过$.节点名.inputs.字段名引用事务节点的输入参数
   - 避免生成过多的子节点，建议不超过4个子节点
   - 确保JSON格式正确，避免截断"""
        
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
{special_requirements}

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

## 输出格式
请直接输出完整的JSON节点配置，不要包含任何额外的说明文字：

```json
{{
  "name": "NodeName",
  "type": "{node_type}",
  "desc": "节点描述",
  "inputs": {{}},
  "outputs": {{}},
  "configs": {{}},
  "nextNodes": []
}}
```

请确保输出的JSON格式完全正确，可以直接解析使用。
**特别注意**: 节点名称必须使用英文且以大写字母开头，采用PascalCase格式，如 "QuerySupplier", "CreateUser", "CheckUserExists"。确保节点名称唯一，不与其他节点重复。"""
        
        return base_prompt
    
    async def _generate_individual_nodes(self, node_prompts: List[Dict[str, Any]], user_requirement: str) -> List[Dict[str, Any]]:
        """逐个生成节点配置"""
        generated_nodes = []
        
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
            node_prompt = prompt_info["generation_prompt"]
            
            # 在提示词中添加节点名称上下文
            enhanced_prompt = self._enhance_prompt_with_node_context(node_prompt, all_node_names, i)
            
            logger.info(f"生成节点 {i+1}/{len(node_prompts)}: {node_type}")
            
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
                validated_config = self._validate_node_config(node_config, node_type)
                
                # 添加到结果中
                generated_nodes.append({
                    "node_type": node_type,
                    "node_config": validated_config,
                    "generation_info": {
                        "prompt_used": enhanced_prompt,
                        "raw_response": response,
                        "validation_applied": True
                    }
                })
                
                logger.info(f"成功生成节点: {validated_config.get('name', 'unknown')}")
                
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
        
        return generated_nodes
    
    def _enhance_prompt_with_node_context(self, base_prompt: str, all_node_names: List[str], current_index: int) -> str:
        """增强提示词，添加节点名称上下文"""
        
        # 获取前面已生成的节点名称
        previous_node_names = all_node_names[:current_index]
        remaining_node_names = all_node_names[current_index:]
        
        context_info = f"""
## 节点名称上下文

**已生成的节点名称**:
{', '.join(previous_node_names) if previous_node_names else '无'}

**当前和后续节点名称**:
{', '.join(remaining_node_names) if remaining_node_names else '无'}

**数据引用要求**:
- 只能引用已生成的节点名称: {', '.join(previous_node_names) if previous_node_names else '无'}
- 必须使用完整的节点名称，不能使用简化或虚构的名称
- 如果是第一个节点，可以使用 workflowStart 节点作为数据源
- 引用格式: $.NodeName.outputs.fieldName 或 $.NodeName.inputs.fieldName

**特别注意**:
- 节点名称必须以大写字母开头，采用PascalCase格式，如 "QueryUser", "CreateOrder", "CheckUserExists"
- 节点名称必须唯一，不能与已生成的节点名称重复
- 禁止使用不存在的节点名称，如 "StartNode", "ValidateSupplier", "CheckProduct" 等
- 必须使用建议的节点名称，确保引用的准确性
- 如果需要引用其他节点的数据，请使用上述 "已生成的节点名称" 中的名称
"""
        
        # 将上下文信息添加到基础提示词中
        enhanced_prompt = base_prompt + context_info
        
        return enhanced_prompt
    
    def _get_max_tokens_for_node_type(self, node_type: str) -> int:
        """根据节点类型获取最大token数"""
        token_limits = {
            "transaction": 3000,  # 事务节点需要更多tokens
            "batch": 2500,        # 批处理节点需要更多tokens
            "chatWithLLM": 2000,  # LLM节点需要更多tokens
            "code": 2000,         # 代码节点需要更多tokens
            "condition": 1500,    # 条件节点
            "http": 1500,         # HTTP节点
            "workflow": 1500,     # 工作流节点
            "dbQuery": 1500,      # 数据库查询节点
            "dbCreate": 1500,     # 数据库创建节点
            "dbUpdate": 1500,     # 数据库更新节点
            "dbDelete": 1500,     # 数据库删除节点
            "workflowStart": 1000,  # 开始节点
            "workflowEnd": 1000,    # 结束节点
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
                "inputs": {},
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
                # 对于workflowStart和workflowEnd节点的configs/outputs字段，不产生警告
                should_warn = True
                if expected_type in ["workflowStart", "workflowEnd"]:
                    if field in ["configs", "outputs"]:
                        should_warn = False
                
                if should_warn:
                    logger.warning(f"节点配置缺少字段 {field}，将使用默认值")
                
                if field == "inputs":
                    node_config[field] = {}
                elif field == "outputs":
                    # 根据节点类型设置默认outputs
                    if expected_type == "workflowStart":
                        node_config[field] = {}  # workflowStart不产生输出数据
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
                
        # 特殊处理：确保workflowEnd节点的nextNodes正确
        if expected_type == "workflowEnd":
            if node_config.get("nextNodes") != ["end"]:
                logger.info(f"修正workflowEnd节点的nextNodes为['end']")
                node_config["nextNodes"] = ["end"]
                
            # 确保workflowEnd节点有必需的输出字段
            required_outputs = ["code", "data", "message"]
            outputs = node_config.get("outputs", {})
            for output_field in required_outputs:
                if output_field not in outputs:
                    logger.warning(f"workflowEnd节点缺少必需输出字段: {output_field}，添加默认配置")
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
    
    def _create_fallback_node(self, node_type: str, node_info: Dict[str, Any]) -> Dict[str, Any]:
        """创建后备节点配置"""
        fallback_node = {
            "name": node_info.get("suggested_name", f"Default{node_type.title()}"),
            "type": node_type,
            "desc": node_info.get("purpose", f"默认{node_type}节点"),
            "inputs": {},
            "outputs": {},
            "configs": {},
            "nextNodes": []
        } 
        
        # 根据节点类型设置特定的默认配置
        if node_type == "workflowEnd":
            fallback_node["nextNodes"] = ["end"]
            fallback_node["outputs"] = {
                "code": {
                    "type": "number",
                    "value": "200",
                    "desc": "HTTP状态码"
                },
                "data": {
                    "type": "string",
                    "value": "操作成功",
                    "desc": "响应数据"
                },
                "message": {
                    "type": "string",
                    "value": "操作完成",
                    "desc": "响应消息"
                }
            }
        elif node_type == "dbQuery":
            fallback_node["outputs"] = {
                "affected": {
                    "type": "number",
                    "desc": "查询返回的行数"
                },
                "data": {
                    "type": "array",
                    "desc": "查询结果数据"
                }
            }
            fallback_node["configs"] = {
                "table": "default_table",
                "sql": "SELECT * FROM default_table"
            }
        elif node_type == "dbCreate":
            fallback_node["outputs"] = {
                "affected": {
                    "type": "number",
                    "desc": "影响的行数"
                },
                "insertId": {
                    "type": "string",
                    "desc": "新插入记录的ID"
                }
            }
            fallback_node["configs"] = {
                "table": "default_table",
                "sql": "INSERT INTO default_table (field) VALUES (value)"
            }
        elif node_type == "dbUpdate":
            fallback_node["outputs"] = {
                "affected": {
                    "type": "number",
                    "desc": "影响的行数"
                }
            }
            fallback_node["configs"] = {
                "table": "default_table",
                "sql": "UPDATE default_table SET field = value WHERE condition"
            }
        elif node_type == "dbDelete":
            fallback_node["outputs"] = {
                "affected": {
                    "type": "number",
                    "desc": "影响的行数"
                }
            }
            fallback_node["configs"] = {
                "table": "default_table",
                "sql": "DELETE FROM default_table WHERE condition"
            }
        elif node_type == "http":
            fallback_node["outputs"] = {
                "code": {
                    "type": "number",
                    "desc": "HTTP状态码"
                },
                "data": {
                    "type": "object",
                    "desc": "响应数据"
                }
            }
            fallback_node["configs"] = {
                "method": "GET",
                "url": "https://api.example.com",
                "bodyType": "none"
            }
        elif node_type == "chatWithLLM":
            fallback_node["outputs"] = {
                "thinking": {
                    "type": "string",
                    "desc": "AI思考过程"
                },
                "response": {
                    "type": "string",
                    "desc": "AI生成的回复"
                },
                "tokens": {
                    "type": "object",
                    "desc": "Token使用情况"
                }
            }
            fallback_node["configs"] = {
                "modelId": "gpt-3.5-turbo"
            }
        elif node_type == "condition":
            # condition节点不需要outputs和nextNodes字段
            if "outputs" in fallback_node:
                del fallback_node["outputs"]
            if "nextNodes" in fallback_node:
                del fallback_node["nextNodes"]
            fallback_node["configs"] = {
                "conditionGroups": [],
                "defaultNextNode": ""
            }
        elif node_type == "batch":
            fallback_node["outputs"] = {
                "totalProcessed": {
                    "type": "number",
                    "desc": "处理的总数量"
                },
                "successCount": {
                    "type": "number",
                    "desc": "成功处理的数量"
                },
                "failureCount": {
                    "type": "number",
                    "desc": "失败处理的数量"
                },
                "aggregatedResult": {
                    "type": "object",
                    "desc": "聚合结果"
                },
                "executionTime": {
                    "type": "number",
                    "desc": "执行耗时"
                }
            }
            fallback_node["configs"] = {
                "mapConfig": {
                    "dataSource": "$.BatchNode.inputs.dataList"
                },
                "reduceConfig": {
                    "strategy": "collect"
                },
                "child": {}
            }
        elif node_type == "transaction":
            fallback_node["outputs"] = {
                "committed": {
                    "type": "boolean",
                    "desc": "事务是否成功提交"
                },
                "affectedTotal": {
                    "type": "number",
                    "desc": "影响的总行数"
                },
                "childResults": {
                    "type": "array",
                    "desc": "子节点执行结果"
                },
                "executionTime": {
                    "type": "number",
                    "desc": "执行耗时"
                }
            }
            fallback_node["configs"] = {
                "children": []
            }
        
        return fallback_node 