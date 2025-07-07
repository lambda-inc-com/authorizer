# 🚀 工作流生成系统 - 简单测试

## 📋 简介
这是一个简化的工作流生成测试工具，用户可以输入需求，系统会使用真实的LLM（默认Claude）生成工作流并保存为JSON文件。

## 🛠️ 配置步骤

### 1. 设置API密钥
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，添加您的 Claude API 密钥
# CLAUDE_API_KEY=your_actual_api_key_here
```

或者直接设置环境变量：
```bash
export CLAUDE_API_KEY=your_actual_api_key_here
```

### 2. 激活虚拟环境并安装依赖
```bash
# 激活虚拟环境
source .venv/bin/activate

# 确认依赖已安装
pip install anthropic openai python-dotenv
```

## 🎯 使用方法

### 运行测试
```bash
# 确保在 ai-core 目录下
python simple_test.py
```

### 输入需求示例
- "创建一个用户注册工作流"
- "设计一个订单处理流程"
- "建立一个数据备份工作流"
- "制作一个邮件发送工作流"

## 📁 输出结果

生成的工作流会保存在 `generated_workflows/` 目录下，文件名格式：
```
工作流名称_时间戳.json
```

例如：
```
generated_workflows/
├── 用户注册工作流_20240107_143022.json
├── 订单处理流程_20240107_143156.json
└── 数据备份工作流_20240107_143301.json
```

## 🔧 配置说明

### 当前配置
- **默认模型**: Claude 3 Sonnet
- **配置文件**: `../configs/llm/claude.json`
- **状态**: 已启用 (`is_enabled: true`)

### 切换模型
如需使用其他模型，可以：
1. 修改相应的配置文件中的 `is_enabled` 为 `true`
2. 同时将 Claude 的 `is_enabled` 设为 `false`
3. 设置对应的API密钥环境变量

## 🚨 注意事项
1. 确保API密钥有效且有足够的配额
2. 首次运行可能需要等待API响应
3. 如果生成失败，检查网络连接和API配置
4. 生成的工作流是基于AI理解的结果，可能需要人工审核

## 🆘 故障排除

### 常见问题
1. **API密钥错误**
   - 检查环境变量是否正确设置
   - 确认API密钥是否有效

2. **网络连接问题**
   - 确认网络畅通
   - 检查防火墙设置

3. **模块导入错误**
   - 确认在虚拟环境中运行
   - 检查依赖是否正确安装

### 日志查看
系统会在控制台输出详细的执行日志，包括：
- 初始化状态
- API调用过程
- 错误信息
- 生成结果 