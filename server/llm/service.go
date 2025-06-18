package llm

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/authorizerdev/authorizer/server/db"
	"github.com/authorizerdev/authorizer/server/llm/providers"
	log "github.com/sirupsen/logrus"
)

// LLMService 大模型服务接口
type LLMService interface {
	// GetProvider 获取指定类型的提供商
	GetProvider(modelType providers.ModelType) (providers.LLMProvider, error)

	// GetAvailableModels 获取可用模型列表
	GetAvailableModels(ctx context.Context) (map[string][]providers.ModelConfig, error)

	// Chat 统一聊天接口
	Chat(ctx context.Context, userID string, request *providers.ChatRequest) (*providers.ChatResponse, error)

	// CalculateAndConsumePoints 计算并消耗积分
	CalculateAndConsumePoints(ctx context.Context, userID string, request *providers.TokenCalculateRequest) (*providers.TokenCalculateResponse, error)

	// LoadConfigs 加载配置文件
	LoadConfigs() error
}

// Service LLM服务实现
type Service struct {
	providers map[providers.ModelType]providers.LLMProvider
	configs   map[string]*providers.ModelConfig // key: provider_model_name
}

// NewService 创建LLM服务
func NewService() *Service {
	service := &Service{
		providers: make(map[providers.ModelType]providers.LLMProvider),
		configs:   make(map[string]*providers.ModelConfig),
	}

	// 注册提供商
	service.providers[providers.ModelTypeOpenAI] = providers.NewOpenAIProvider()
	service.providers[providers.ModelTypeClaude] = providers.NewClaudeProvider()
	service.providers[providers.ModelTypeDeepSeek] = providers.NewDeepSeekProvider()

	return service
}

// GetProvider 获取指定类型的提供商
func (s *Service) GetProvider(modelType providers.ModelType) (providers.LLMProvider, error) {
	provider, exists := s.providers[modelType]
	if !exists {
		return nil, fmt.Errorf("provider %s not found", modelType)
	}
	return provider, nil
}

// GetAvailableModels 获取可用模型列表
func (s *Service) GetAvailableModels(ctx context.Context) (map[string][]providers.ModelConfig, error) {
	result := make(map[string][]providers.ModelConfig)

	for providerType := range s.providers {
		var providerModels []providers.ModelConfig

		for _, config := range s.configs {
			if config.ModelType == providerType && config.IsEnabled {
				providerModels = append(providerModels, *config)
			}
		}

		if len(providerModels) > 0 {
			result[string(providerType)] = providerModels
		}
	}

	return result, nil
}

// Chat 统一聊天接口
func (s *Service) Chat(ctx context.Context, userID string, request *providers.ChatRequest) (*providers.ChatResponse, error) {
	// 根据模型名称找到对应的配置
	var config *providers.ModelConfig
	for _, cfg := range s.configs {
		if cfg.ModelName == request.Model && cfg.IsEnabled {
			config = cfg
			break
		}
	}

	if config == nil {
		return nil, fmt.Errorf("model %s not found or not enabled", request.Model)
	}

	// 获取对应的提供商
	provider, err := s.GetProvider(config.ModelType)
	if err != nil {
		return nil, fmt.Errorf("get provider failed: %w", err)
	}

	// 预扣积分检查
	tokenReq := &providers.TokenCalculateRequest{
		Model:    request.Model,
		Messages: request.Messages,
	}

	tokenResp, err := provider.CalculateTokens(ctx, config, tokenReq)
	if err != nil {
		return nil, fmt.Errorf("calculate tokens failed: %w", err)
	}

	// 检查用户积分是否足够
	userPoints, err := db.Provider.GetUserPointsByUserID(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("get user points failed: %w", err)
	}

	if userPoints.Points < tokenResp.EstimatedPoints {
		return nil, fmt.Errorf("insufficient points: need %d, have %d", tokenResp.EstimatedPoints, userPoints.Points)
	}

	// 调用聊天接口
	response, err := provider.Chat(ctx, config, request)
	if err != nil {
		return nil, fmt.Errorf("chat request failed: %w", err)
	}

	// 根据实际消耗的token扣除积分
	actualPoints := response.Usage.TotalTokens
	if actualPoints == 0 {
		actualPoints = tokenResp.EstimatedPoints // 如果没有返回用量，使用预估值
	}

	// 消耗积分
	_, err = db.Provider.ConsumeUserPoints(ctx, userID, actualPoints)
	if err != nil {
		log.Errorf("Failed to consume points for user %s: %v", userID, err)
		// 注意：这里不返回错误，因为聊天已经成功，只是积分扣除失败
	}

	return response, nil
}

// CalculateAndConsumePoints 计算并消耗积分
func (s *Service) CalculateAndConsumePoints(ctx context.Context, userID string, request *providers.TokenCalculateRequest) (*providers.TokenCalculateResponse, error) {
	// 根据模型名称找到对应的配置
	var config *providers.ModelConfig
	for _, cfg := range s.configs {
		if cfg.ModelName == request.Model && cfg.IsEnabled {
			config = cfg
			break
		}
	}

	if config == nil {
		return nil, fmt.Errorf("model %s not found or not enabled", request.Model)
	}

	// 获取对应的提供商
	provider, err := s.GetProvider(config.ModelType)
	if err != nil {
		return nil, fmt.Errorf("get provider failed: %w", err)
	}

	// 计算token消耗
	tokenResp, err := provider.CalculateTokens(ctx, config, request)
	if err != nil {
		return nil, fmt.Errorf("calculate tokens failed: %w", err)
	}

	return tokenResp, nil
}

// LoadConfigs 加载配置文件
func (s *Service) LoadConfigs() error {
	configDir := "configs/llm"

	// 确保配置目录存在
	if err := os.MkdirAll(configDir, 0755); err != nil {
		return fmt.Errorf("create config directory failed: %w", err)
	}

	// 如果配置文件不存在，创建默认配置
	if err := s.createDefaultConfigs(configDir); err != nil {
		return fmt.Errorf("create default configs failed: %w", err)
	}

	// 加载所有配置文件
	return s.loadConfigsFromDir(configDir)
}

// createDefaultConfigs 创建默认配置文件
func (s *Service) createDefaultConfigs(configDir string) error {
	defaultConfigs := map[string]*providers.ModelConfig{
		"openai.json": {
			Provider:   "OpenAI",
			ModelType:  providers.ModelTypeOpenAI,
			ModelName:  "gpt-3.5-turbo",
			APIKey:     "${OPENAI_API_KEY}",
			BaseURL:    "https://api.openai.com/v1",
			MaxTokens:  4096,
			TokenRatio: map[string]int{"input": 1, "output": 1},
			IsEnabled:  false,
			Extra:      map[string]string{},
		},
		"claude.json": {
			Provider:   "Anthropic",
			ModelType:  providers.ModelTypeClaude,
			ModelName:  "claude-3-sonnet-20240229",
			APIKey:     "${CLAUDE_API_KEY}",
			BaseURL:    "https://api.anthropic.com/v1",
			MaxTokens:  4096,
			TokenRatio: map[string]int{"input": 1, "output": 1},
			IsEnabled:  false,
			Extra:      map[string]string{},
		},
		"deepseek.json": {
			Provider:   "DeepSeek",
			ModelType:  providers.ModelTypeDeepSeek,
			ModelName:  "deepseek-chat",
			APIKey:     "${DEEPSEEK_API_KEY}",
			BaseURL:    "https://api.deepseek.com/v1",
			MaxTokens:  4096,
			TokenRatio: map[string]int{"input": 1, "output": 1},
			IsEnabled:  false,
			Extra:      map[string]string{},
		},
	}

	for filename, config := range defaultConfigs {
		filePath := filepath.Join(configDir, filename)

		// 如果文件已存在，跳过
		if _, err := os.Stat(filePath); err == nil {
			continue
		}

		// 创建配置文件
		data, err := json.MarshalIndent(config, "", "  ")
		if err != nil {
			return fmt.Errorf("marshal config %s failed: %w", filename, err)
		}

		if err := os.WriteFile(filePath, data, 0644); err != nil {
			return fmt.Errorf("write config file %s failed: %w", filename, err)
		}

		log.Infof("Created default config file: %s", filePath)
	}

	return nil
}

// loadConfigsFromDir 从目录加载配置文件
func (s *Service) loadConfigsFromDir(configDir string) error {
	files, err := os.ReadDir(configDir)
	if err != nil {
		return fmt.Errorf("read config directory failed: %w", err)
	}

	for _, file := range files {
		if !file.IsDir() && filepath.Ext(file.Name()) == ".json" {
			filePath := filepath.Join(configDir, file.Name())

			if err := s.loadConfigFile(filePath); err != nil {
				log.Errorf("Failed to load config file %s: %v", filePath, err)
				continue
			}
		}
	}

	log.Infof("Loaded %d LLM configurations", len(s.configs))
	return nil
}

// loadConfigFile 加载单个配置文件
func (s *Service) loadConfigFile(filePath string) error {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return fmt.Errorf("read file failed: %w", err)
	}

	var config providers.ModelConfig
	if err := json.Unmarshal(data, &config); err != nil {
		return fmt.Errorf("unmarshal config failed: %w", err)
	}

	// 解析环境变量
	config.APIKey = os.ExpandEnv(config.APIKey)
	config.BaseURL = os.ExpandEnv(config.BaseURL)

	// 验证配置
	if provider, exists := s.providers[config.ModelType]; exists {
		if err := provider.ValidateConfig(&config); err != nil {
			return fmt.Errorf("validate config failed: %w", err)
		}
	}

	// 存储配置
	key := fmt.Sprintf("%s_%s", config.Provider, config.ModelName)
	s.configs[key] = &config

	log.Infof("Loaded config: %s (enabled: %v)", key, config.IsEnabled)
	return nil
}
