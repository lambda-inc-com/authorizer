# LLM 配置文件说明

本目录包含各大模型提供商的配置文件，用于系统级别的LLM服务配置。

## XAI 配置文件

### 1. xai.json - Grok Beta 模型
```json
{
  "provider": "xAI",
  "model_type": "xai", 
  "model_name": "grok-beta",
  "api_key": "${XAI_API_KEY}",
  "base_url": "https://api.x.ai/v1",
  "max_tokens": 4096,
  "is_enabled": false
}
```

### 2. xai-grok-vision.json - Grok Vision 模型
```json
{
  "provider": "xAI",
  "model_type": "xai",
  "model_name": "grok-vision-beta", 
  "api_key": "${XAI_API_KEY}",
  "base_url": "https://api.x.ai/v1",
  "max_tokens": 8192,
  "is_enabled": false
}
```

## 使用方法

1. **设置环境变量**:
   ```bash
   export XAI_API_KEY="your-xai-api-key"
   ```

2. **启用配置**:
   修改配置文件中的 `is_enabled` 为 `true`

3. **重启服务**:
   配置修改后需要重启服务才能生效

## 配置字段说明

- `provider`: 提供商名称 (xAI)
- `model_type`: 模型类型枚举 (xai)
- `model_name`: 具体模型名称
- `api_key`: API密钥（支持环境变量）
- `base_url`: API基础URL
- `max_tokens`: 最大token限制
- `token_ratio`: 输入输出token计费比例
- `is_enabled`: 是否启用该配置
- `extra`: 额外配置信息

## 注意事项

- API密钥通过环境变量设置，保护敏感信息
- 配置文件修改后需要重启服务
- Grok Vision模型支持图像理解功能
- 建议根据实际使用情况调整token限制 