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

// XAIProvider xAI提供商实现
type XAIProvider struct {
	httpClient *http.Client
}

// NewXAIProvider 创建xAI提供商
func NewXAIProvider() *XAIProvider {
	return &XAIProvider{
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// GetProviderType 获取提供商类型
func (p *XAIProvider) GetProviderType() ModelType {
	return ModelTypeXAI
}

// Chat 聊天对话
func (p *XAIProvider) Chat(ctx context.Context, config *ModelConfig, request *ChatRequest) (*ChatResponse, error) {
	if config.BaseURL == "" {
		config.BaseURL = "https://api.x.ai/v1"
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

// CalculateTokens 计算token消耗 (简单估算，与OpenAI类似)
func (p *XAIProvider) CalculateTokens(ctx context.Context, config *ModelConfig, request *TokenCalculateRequest) (*TokenCalculateResponse, error) {
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
func (p *XAIProvider) ValidateConfig(config *ModelConfig) error {
	if config.APIKey == "" {
		return fmt.Errorf("API key is required")
	}
	if config.ModelName == "" {
		return fmt.Errorf("model name is required")
	}
	return nil
}

// GetModels 获取支持的模型列表
func (p *XAIProvider) GetModels(ctx context.Context, config *ModelConfig) ([]string, error) {
	if config.BaseURL == "" {
		config.BaseURL = "https://api.x.ai/v1"
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
		// 返回xAI的Grok模型
		if strings.Contains(model.ID, "grok") {
			models = append(models, model.ID)
		}
	}

	return models, nil
}
