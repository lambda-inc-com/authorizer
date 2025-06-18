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

// DeepSeekProvider DeepSeek提供商实现
type DeepSeekProvider struct {
	httpClient *http.Client
}

// NewDeepSeekProvider 创建DeepSeek提供商
func NewDeepSeekProvider() *DeepSeekProvider {
	return &DeepSeekProvider{
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// GetProviderType 获取提供商类型
func (p *DeepSeekProvider) GetProviderType() ModelType {
	return ModelTypeDeepSeek
}

// Chat 聊天对话
func (p *DeepSeekProvider) Chat(ctx context.Context, config *ModelConfig, request *ChatRequest) (*ChatResponse, error) {
	if config.BaseURL == "" {
		config.BaseURL = "https://api.deepseek.com/v1"
	}

	url := fmt.Sprintf("%s/chat/completions", config.BaseURL)

	// DeepSeek使用OpenAI兼容的API格式
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

// CalculateTokens 计算token消耗
func (p *DeepSeekProvider) CalculateTokens(ctx context.Context, config *ModelConfig, request *TokenCalculateRequest) (*TokenCalculateResponse, error) {
	totalLength := 0
	for _, message := range request.Messages {
		totalLength += len(message.Content)
	}

	// DeepSeek的token计算，中文友好
	estimatedTokens := int(float64(totalLength) * 1.0 / 3) // DeepSeek对中文更友好

	// 1 token = 1 积分
	estimatedPoints := estimatedTokens

	return &TokenCalculateResponse{
		EstimatedTokens: estimatedTokens,
		EstimatedPoints: estimatedPoints,
	}, nil
}

// ValidateConfig 验证配置
func (p *DeepSeekProvider) ValidateConfig(config *ModelConfig) error {
	if config.APIKey == "" {
		return fmt.Errorf("API key is required")
	}
	if config.ModelName == "" {
		return fmt.Errorf("model name is required")
	}
	return nil
}

// GetModels 获取支持的模型列表
func (p *DeepSeekProvider) GetModels(ctx context.Context, config *ModelConfig) ([]string, error) {
	if config.BaseURL == "" {
		config.BaseURL = "https://api.deepseek.com/v1"
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
		// 如果API调用失败，返回默认模型列表
		return []string{
			"deepseek-chat",
			"deepseek-coder",
		}, nil
	}

	var modelsResp struct {
		Data []struct {
			ID string `json:"id"`
		} `json:"data"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&modelsResp); err != nil {
		// 解析失败，返回默认模型列表
		return []string{
			"deepseek-chat",
			"deepseek-coder",
		}, nil
	}

	models := make([]string, 0, len(modelsResp.Data))
	for _, model := range modelsResp.Data {
		// 只返回deepseek模型
		if strings.Contains(model.ID, "deepseek") {
			models = append(models, model.ID)
		}
	}

	return models, nil
}
