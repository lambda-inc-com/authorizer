package models

// UserLLMConfig 用户自定义LLM配置
type UserLLMConfig struct {
	ID        string `gorm:"primaryKey;type:char(36)" json:"id" bson:"_id" cql:"id" dynamo:"id,hash"`
	UserID    string `gorm:"index;type:char(36)" json:"user_id" bson:"user_id" cql:"user_id" dynamo:"user_id"`
	Provider  string `json:"provider" bson:"provider" cql:"provider" dynamo:"provider"`         // 提供商名称，如 "OpenAI", "xAI", "Claude"
	ModelType string `json:"model_type" bson:"model_type" cql:"model_type" dynamo:"model_type"` // 模型类型
	ModelName string `json:"model_name" bson:"model_name" cql:"model_name" dynamo:"model_name"` // 模型名称
	APIKey    string `json:"api_key" bson:"api_key" cql:"api_key" dynamo:"api_key"`             // 用户的API密钥
	BaseURL   string `json:"base_url" bson:"base_url" cql:"base_url" dynamo:"base_url"`         // API基础URL
	MaxTokens int    `json:"max_tokens" bson:"max_tokens" cql:"max_tokens" dynamo:"max_tokens"` // 最大token限制
	IsEnabled bool   `json:"is_enabled" bson:"is_enabled" cql:"is_enabled" dynamo:"is_enabled"` // 是否启用
	IsDefault bool   `json:"is_default" bson:"is_default" cql:"is_default" dynamo:"is_default"` // 是否为默认配置
	CreatedAt int64  `json:"created_at" bson:"created_at" cql:"created_at" dynamo:"created_at"`
	UpdatedAt int64  `json:"updated_at" bson:"updated_at" cql:"updated_at" dynamo:"updated_at"`
}
