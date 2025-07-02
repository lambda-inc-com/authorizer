"""
简化的工作流生成提示词模板
"""

def get_workflow_system_prompt():
    """工作流生成系统提示词"""
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
    """构建用户提示词"""
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