package providers

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// ModelType 模型类型枚举
type ModelType string

const (
	ModelTypeOpenAI   ModelType = "openai"
	ModelTypeClaude   ModelType = "claude"
	ModelTypeDeepSeek ModelType = "deepseek"
)

// ChatMessage 聊天消息结构
type ChatMessage struct {
	Role    string `json:"role"`    // system, user, assistant
	Content string `json:"content"` // 消息内容
}

// ChatRequest 聊天请求结构
type ChatRequest struct {
	Model       string        `json:"model"`                 // 模型名称，如 "gpt-3.5-turbo"
	Messages    []ChatMessage `json:"messages"`              // 对话消息
	MaxTokens   int           `json:"max_tokens,omitempty"`  // 最大token数
	Temperature float64       `json:"temperature,omitempty"` // 温度参数
	Stream      bool          `json:"stream,omitempty"`      // 是否流式输出
}

// ChatResponse 聊天响应结构
type ChatResponse struct {
	ID      string `json:"id"`
	Object  string `json:"object"`
	Created int64  `json:"created"`
	Model   string `json:"model"`
	Choices []struct {
		Index   int `json:"index"`
		Message struct {
			Role    string `json:"role"`
			Content string `json:"content"`
		} `json:"message"`
		FinishReason string `json:"finish_reason"`
	} `json:"choices"`
	Usage TokenUsage `json:"usage"`
}

// TokenUsage token使用统计
type TokenUsage struct {
	PromptTokens     int `json:"prompt_tokens"`     // 输入token数
	CompletionTokens int `json:"completion_tokens"` // 输出token数
	TotalTokens      int `json:"total_tokens"`      // 总token数
}

// ModelConfig 模型配置
type ModelConfig struct {
	Provider   string            `json:"provider"`    // 提供商名称
	ModelType  ModelType         `json:"model_type"`  // 模型类型
	ModelName  string            `json:"model_name"`  // 模型名称
	APIKey     string            `json:"api_key"`     // API密钥
	BaseURL    string            `json:"base_url"`    // API基础URL
	MaxTokens  int               `json:"max_tokens"`  // 最大token限制
	TokenRatio map[string]int    `json:"token_ratio"` // token计费比例，input:output
	IsEnabled  bool              `json:"is_enabled"`  // 是否启用
	Extra      map[string]string `json:"extra"`       // 额外配置参数
}

// TokenCalculateRequest token计算请求
type TokenCalculateRequest struct {
	Model    string        `json:"model"`    // 模型名称
	Messages []ChatMessage `json:"messages"` // 消息内容
}

// TokenCalculateResponse token计算响应
type TokenCalculateResponse struct {
	EstimatedTokens int `json:"estimated_tokens"` // 预估token数
	EstimatedPoints int `json:"estimated_points"` // 预估积分消耗
}

// LLMProvider 大模型提供商接口
type LLMProvider interface {
	// GetProviderType 获取提供商类型
	GetProviderType() ModelType

	// Chat 聊天对话
	Chat(ctx context.Context, config *ModelConfig, request *ChatRequest) (*ChatResponse, error)

	// CalculateTokens 计算token消耗
	CalculateTokens(ctx context.Context, config *ModelConfig, request *TokenCalculateRequest) (*TokenCalculateResponse, error)

	// ValidateConfig 验证配置
	ValidateConfig(config *ModelConfig) error

	// GetModels 获取支持的模型列表
	GetModels(ctx context.Context, config *ModelConfig) ([]string, error)
}

// OpenAIProvider OpenAI提供商实现
type OpenAIProvider struct {
	httpClient *http.Client
}

// NewOpenAIProvider 创建OpenAI提供商
func NewOpenAIProvider() *OpenAIProvider {
	return &OpenAIProvider{
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// GetProviderType 获取提供商类型
func (p *OpenAIProvider) GetProviderType() ModelType {
	return ModelTypeOpenAI
}

// Chat 聊天对话
func (p *OpenAIProvider) Chat(ctx context.Context, config *ModelConfig, request *ChatRequest) (*ChatResponse, error) {
	if config.BaseURL == "" {
		config.BaseURL = "https://api.openai.com/v1"
	}

	url := fmt.Sprintf("%s/chat/completions", config.BaseURL)

	// 转换请求格式
	requestBody := map[string]interface{}{
		"model":    request.Model,
		"messages": request.Messages,
	}

	if request.MaxTokens > 0 {
		requestBody["max_tokens"] = request.MaxTokens
	}
	if request.Temperature > 0 {
		requestBody["temperature"] = request.Temperature
	}
	if request.Stream {
		requestBody["stream"] = request.Stream
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return nil, fmt.Errorf("marshal request failed: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("create request failed: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", config.APIKey))

	resp, err := p.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(body))
	}

	var response ChatResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("decode response failed: %w", err)
	}

	return &response, nil
}

// CalculateTokens 计算token消耗 (简单估算，实际应该用tiktoken)
func (p *OpenAIProvider) CalculateTokens(ctx context.Context, config *ModelConfig, request *TokenCalculateRequest) (*TokenCalculateResponse, error) {
	totalLength := 0
	for _, message := range request.Messages {
		// 简单按字符数估算，实际应该用更准确的token计算
		totalLength += len(message.Content)
	}

	// 英文一般4个字符约等于1个token，中文1个字符约等于1.5个token
	// 这里简化处理，按平均1.2倍估算
	estimatedTokens := int(float64(totalLength) * 1.2 / 4)

	// 1 token = 1 积分
	estimatedPoints := estimatedTokens

	return &TokenCalculateResponse{
		EstimatedTokens: estimatedTokens,
		EstimatedPoints: estimatedPoints,
	}, nil
}

// ValidateConfig 验证配置
func (p *OpenAIProvider) ValidateConfig(config *ModelConfig) error {
	if config.APIKey == "" {
		return fmt.Errorf("API key is required")
	}
	if config.ModelName == "" {
		return fmt.Errorf("model name is required")
	}
	return nil
}

// GetModels 获取支持的模型列表
func (p *OpenAIProvider) GetModels(ctx context.Context, config *ModelConfig) ([]string, error) {
	if config.BaseURL == "" {
		config.BaseURL = "https://api.openai.com/v1"
	}

	url := fmt.Sprintf("%s/models", config.BaseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("create request failed: %w", err)
	}

	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", config.APIKey))

	resp, err := p.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(body))
	}

	var modelsResp struct {
		Data []struct {
			ID string `json:"id"`
		} `json:"data"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&modelsResp); err != nil {
		return nil, fmt.Errorf("decode response failed: %w", err)
	}

	models := make([]string, 0, len(modelsResp.Data))
	for _, model := range modelsResp.Data {
		// 只返回GPT模型
		if strings.Contains(model.ID, "gpt") {
			models = append(models, model.ID)
		}
	}

	return models, nil
}
