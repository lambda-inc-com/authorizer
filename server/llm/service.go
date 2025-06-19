package llm

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/authorizerdev/authorizer/server/db"
	"github.com/authorizerdev/authorizer/server/db/models"
	"github.com/authorizerdev/authorizer/server/llm/providers"
	"github.com/authorizerdev/authorizer/server/services"
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
	service.providers[providers.ModelTypeXAI] = providers.NewXAIProvider()

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
	// 创建订阅服务
	subscriptionService := services.NewSubscriptionService()

	// 检查用户订阅状态
	subscription, err := subscriptionService.CheckUserSubscription(ctx, userID)
	if err != nil {
		log.Errorf("Failed to check user subscription: %v", err)
	}

	var config *providers.ModelConfig
	var useUserConfig bool = false
	var reason string = ""

	// 决策逻辑：
	// 1. 如果用户有有效订阅且有积分 -> 使用系统API key
	// 2. 如果用户有有效订阅且无积分 -> 必须使用用户API key
	// 3. 如果用户无有效订阅 -> 则无法使用程序

	if !subscription.HasValidSubscription {
		// 无有效订阅，直接拒绝
		return nil, fmt.Errorf("无有效订阅，请先购买订阅服务后再使用")
	}

	// 有有效订阅，检查积分情况
	userPoints, err := db.Provider.GetUserPointsByUserID(ctx, userID)
	if err != nil {
		log.Errorf("Failed to get user points: %v", err)
		userPoints = &models.UserPoints{Points: 0}
	}

	if userPoints.Points > 0 {
		// 有订阅且有积分，使用系统API key并扣积分
		useUserConfig = false
		reason = fmt.Sprintf("购买了%s且有积分，使用系统服务", subscription.ProductName)
	} else {
		// 有订阅但无积分，必须使用用户API key
		useUserConfig = true
		reason = fmt.Sprintf("购买了%s但积分不足，需要配置自己的API密钥", subscription.ProductName)
	}

	if useUserConfig {
		// 查找用户是否有对应模型的自定义配置
		userConfigs, err := db.Provider.GetUserLLMConfigsByUserID(ctx, userID)
		if err != nil {
			return nil, fmt.Errorf("%s，但获取用户LLM配置失败: %w", reason, err)
		}

		// 根据模型名称找到匹配的用户配置
		var userConfig *models.UserLLMConfig
		for _, uc := range userConfigs {
			if uc.ModelName == request.Model && uc.IsEnabled {
				userConfig = uc
				break
			}
		}

		if userConfig == nil {
			return nil, fmt.Errorf("%s，请配置%s模型的API密钥", reason, request.Model)
		}

		// 转换用户配置为ModelConfig
		config = &providers.ModelConfig{
			Provider:  userConfig.Provider,
			ModelType: providers.ModelType(userConfig.ModelType),
			ModelName: userConfig.ModelName,
			APIKey:    userConfig.APIKey,
			BaseURL:   userConfig.BaseURL,
			MaxTokens: userConfig.MaxTokens,
			IsEnabled: userConfig.IsEnabled,
		}
		log.Infof("User %s using own API key for model %s: %s", userID, request.Model, reason)
	} else {
		// 使用系统配置
		for _, cfg := range s.configs {
			if cfg.ModelName == request.Model && cfg.IsEnabled {
				config = cfg
				break
			}
		}

		if config == nil {
			return nil, fmt.Errorf("model %s not found or not enabled", request.Model)
		}
		log.Infof("User %s using system API key for model %s: %s", userID, request.Model, reason)
	}

	// 获取对应的提供商
	provider, err := s.GetProvider(config.ModelType)
	if err != nil {
		return nil, fmt.Errorf("get provider failed: %w", err)
	}

	// 如果使用系统配置且需要扣积分，进行积分检查
	needConsumePoints := !useUserConfig && subscription.HasValidSubscription
	if needConsumePoints {

		// 如果积分 <= 1000，需要预计算检查
		if userPoints.Points <= 1000 {
			tokenReq := &providers.TokenCalculateRequest{
				Model:    request.Model,
				Messages: request.Messages,
			}

			tokenResp, err := provider.CalculateTokens(ctx, config, tokenReq)
			if err != nil {
				return nil, fmt.Errorf("calculate tokens failed: %w", err)
			}

			if userPoints.Points < tokenResp.EstimatedPoints {
				return nil, fmt.Errorf("积分不足：预计需要 %d 积分，当前剩余 %d 积分。请充值后再试", tokenResp.EstimatedPoints, userPoints.Points)
			}
			log.Infof("User %s has %d points, estimated cost %d points, proceeding with request", userID, userPoints.Points, tokenResp.EstimatedPoints)
		} else {
			log.Infof("User %s has %d points (>1000), skipping pre-calculation", userID, userPoints.Points)
		}
	}

	// 调用聊天接口
	response, err := provider.Chat(ctx, config, request)
	if err != nil {
		return nil, fmt.Errorf("chat request failed: %w", err)
	}

	// 如果需要扣积分
	if needConsumePoints {
		actualPoints := response.Usage.TotalTokens
		if actualPoints == 0 {
			// 如果没有返回用量，重新计算
			tokenReq := &providers.TokenCalculateRequest{
				Model:    request.Model,
				Messages: request.Messages,
			}
			tokenResp, _ := provider.CalculateTokens(ctx, config, tokenReq)
			if tokenResp != nil {
				actualPoints = tokenResp.EstimatedPoints
			} else {
				actualPoints = 10 // 默认消耗10积分，避免0消耗
			}
		}

		// 获取最新的用户积分（可能在请求期间有变化）
		latestUserPoints, err := db.Provider.GetUserPointsByUserID(ctx, userID)
		if err != nil {
			log.Errorf("Failed to get user points for consumption for user %s: %v", userID, err)
			return response, nil // 聊天成功，但积分获取失败，返回结果
		}

		// 检查积分是否足够扣除
		if latestUserPoints.Points < actualPoints {
			log.Errorf("User %s insufficient points for actual consumption: need %d, have %d", userID, actualPoints, latestUserPoints.Points)
			// 积分不足，扣除所有剩余积分
			if latestUserPoints.Points > 0 {
				_, err = db.Provider.ConsumeUserPoints(ctx, userID, latestUserPoints.Points)
				if err != nil {
					log.Errorf("Failed to consume remaining points for user %s: %v", userID, err)
				} else {
					log.Infof("Consumed all remaining %d points for user %s", latestUserPoints.Points, userID)
				}
			}
		} else {
			// 消耗实际积分
			_, err = db.Provider.ConsumeUserPoints(ctx, userID, actualPoints)
			if err != nil {
				log.Errorf("Failed to consume %d points for user %s: %v", actualPoints, userID, err)
			} else {
				log.Infof("Successfully consumed %d points for user %s", actualPoints, userID)
			}
		}
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
		"xai.json": {
			Provider:   "xAI",
			ModelType:  providers.ModelTypeXAI,
			ModelName:  "grok-beta",
			APIKey:     "${XAI_API_KEY}",
			BaseURL:    "https://api.x.ai/v1",
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
