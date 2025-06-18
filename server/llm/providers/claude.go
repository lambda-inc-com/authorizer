package providers

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// ClaudeProvider Claude提供商实现
type ClaudeProvider struct {
	httpClient *http.Client
}

// NewClaudeProvider 创建Claude提供商
func NewClaudeProvider() *ClaudeProvider {
	return &ClaudeProvider{
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// GetProviderType 获取提供商类型
func (p *ClaudeProvider) GetProviderType() ModelType {
	return ModelTypeClaude
}

// Chat 聊天对话
func (p *ClaudeProvider) Chat(ctx context.Context, config *ModelConfig, request *ChatRequest) (*ChatResponse, error) {
	if config.BaseURL == "" {
		config.BaseURL = "https://api.anthropic.com/v1"
	}

	url := fmt.Sprintf("%s/messages", config.BaseURL)

	// Claude API格式转换
	claudeRequest := map[string]interface{}{
		"model":      request.Model,
		"messages":   request.Messages,
		"max_tokens": 4096, // Claude需要max_tokens参数
	}

	if request.MaxTokens > 0 {
		claudeRequest["max_tokens"] = request.MaxTokens
	}
	if request.Temperature > 0 {
		claudeRequest["temperature"] = request.Temperature
	}
	if request.Stream {
		claudeRequest["stream"] = request.Stream
	}

	jsonData, err := json.Marshal(claudeRequest)
	if err != nil {
		return nil, fmt.Errorf("marshal request failed: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("create request failed: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-api-key", config.APIKey)
	req.Header.Set("anthropic-version", "2023-06-01")

	resp, err := p.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(body))
	}

	// Claude API响应格式转换为通用格式
	var claudeResp struct {
		ID      string `json:"id"`
		Type    string `json:"type"`
		Role    string `json:"role"`
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
		Model string `json:"model"`
		Usage struct {
			InputTokens  int `json:"input_tokens"`
			OutputTokens int `json:"output_tokens"`
		} `json:"usage"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&claudeResp); err != nil {
		return nil, fmt.Errorf("decode response failed: %w", err)
	}

	// 转换为通用格式
	response := &ChatResponse{
		ID:      claudeResp.ID,
		Object:  "chat.completion",
		Created: time.Now().Unix(),
		Model:   claudeResp.Model,
		Choices: []struct {
			Index   int `json:"index"`
			Message struct {
				Role    string `json:"role"`
				Content string `json:"content"`
			} `json:"message"`
			FinishReason string `json:"finish_reason"`
		}{
			{
				Index: 0,
				Message: struct {
					Role    string `json:"role"`
					Content string `json:"content"`
				}{
					Role:    "assistant",
					Content: claudeResp.Content[0].Text,
				},
				FinishReason: "stop",
			},
		},
		Usage: TokenUsage{
			PromptTokens:     claudeResp.Usage.InputTokens,
			CompletionTokens: claudeResp.Usage.OutputTokens,
			TotalTokens:      claudeResp.Usage.InputTokens + claudeResp.Usage.OutputTokens,
		},
	}

	return response, nil
}

// CalculateTokens 计算token消耗
func (p *ClaudeProvider) CalculateTokens(ctx context.Context, config *ModelConfig, request *TokenCalculateRequest) (*TokenCalculateResponse, error) {
	totalLength := 0
	for _, message := range request.Messages {
		totalLength += len(message.Content)
	}

	// Claude的token计算相对复杂，这里简化处理
	estimatedTokens := int(float64(totalLength) * 1.3 / 4) // Claude相对消耗更多token

	// 1 token = 1 积分
	estimatedPoints := estimatedTokens

	return &TokenCalculateResponse{
		EstimatedTokens: estimatedTokens,
		EstimatedPoints: estimatedPoints,
	}, nil
}

// ValidateConfig 验证配置
func (p *ClaudeProvider) ValidateConfig(config *ModelConfig) error {
	if config.APIKey == "" {
		return fmt.Errorf("API key is required")
	}
	if config.ModelName == "" {
		return fmt.Errorf("model name is required")
	}
	return nil
}

// GetModels 获取支持的模型列表
func (p *ClaudeProvider) GetModels(ctx context.Context, config *ModelConfig) ([]string, error) {
	// Claude API暂时不提供模型列表接口，返回常用模型
	return []string{
		"claude-3-opus-20240229",
		"claude-3-sonnet-20240229",
		"claude-3-haiku-20240307",
		"claude-2.1",
		"claude-2.0",
	}, nil
}
