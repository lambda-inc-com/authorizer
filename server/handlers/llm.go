package handlers

import (
	"net/http"
	"strconv"

	"github.com/authorizerdev/authorizer/server/llm"
	"github.com/authorizerdev/authorizer/server/llm/providers"
	"github.com/gin-gonic/gin"
	log "github.com/sirupsen/logrus"
)

// LLMService 全局LLM服务实例
var LLMService llm.LLMService

// InitLLMService 初始化LLM服务
func InitLLMService() error {
	LLMService = llm.NewService()
	return LLMService.LoadConfigs()
}

// GetAvailableModelsHandler 获取可用模型列表
func GetAvailableModelsHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		models, err := LLMService.GetAvailableModels(c.Request.Context())
		if err != nil {
			log.Errorf("Failed to get available models: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to get available models",
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"models": models,
		})
	})
}

// ChatHandler 聊天接口
func ChatHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		// 验证用户身份
		userID := c.GetString("user_id")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Unauthorized",
			})
			return
		}

		var request providers.ChatRequest
		if err := c.ShouldBindJSON(&request); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request format: " + err.Error(),
			})
			return
		}

		// 验证请求
		if request.Model == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Model is required",
			})
			return
		}

		if len(request.Messages) == 0 {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Messages are required",
			})
			return
		}

		// 调用聊天服务
		response, err := LLMService.Chat(c.Request.Context(), userID, &request)
		if err != nil {
			log.Errorf("Chat request failed for user %s: %v", userID, err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, response)
	})
}

// CalculateTokensHandler 计算Token消耗
func CalculateTokensHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		// 验证用户身份
		userID := c.GetString("user_id")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Unauthorized",
			})
			return
		}

		var request providers.TokenCalculateRequest
		if err := c.ShouldBindJSON(&request); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request format: " + err.Error(),
			})
			return
		}

		// 验证请求
		if request.Model == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Model is required",
			})
			return
		}

		if len(request.Messages) == 0 {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Messages are required",
			})
			return
		}

		// 计算token消耗
		response, err := LLMService.CalculateAndConsumePoints(c.Request.Context(), userID, &request)
		if err != nil {
			log.Errorf("Calculate tokens failed for user %s: %v", userID, err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, response)
	})
}

// LLMModelsHandler 获取LLM模型列表（支持分页）
func LLMModelsHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		// 获取分页参数
		page := 1
		limit := 10

		if p := c.Query("page"); p != "" {
			if parsed, err := strconv.Atoi(p); err == nil && parsed > 0 {
				page = parsed
			}
		}

		if l := c.Query("limit"); l != "" {
			if parsed, err := strconv.Atoi(l); err == nil && parsed > 0 && parsed <= 100 {
				limit = parsed
			}
		}

		// 获取提供商过滤参数
		provider := c.Query("provider")

		models, err := LLMService.GetAvailableModels(c.Request.Context())
		if err != nil {
			log.Errorf("Failed to get models: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to get models",
			})
			return
		}

		// 过滤和分页处理
		var allModels []gin.H
		for providerName, configs := range models {
			if provider != "" && providerName != provider {
				continue
			}

			for _, config := range configs {
				allModels = append(allModels, gin.H{
					"provider":   config.Provider,
					"model_type": config.ModelType,
					"model_name": config.ModelName,
					"max_tokens": config.MaxTokens,
					"is_enabled": config.IsEnabled,
					"base_url":   config.BaseURL,
				})
			}
		}

		// 计算分页
		total := len(allModels)
		start := (page - 1) * limit
		end := start + limit

		if start >= total {
			allModels = []gin.H{}
		} else if end > total {
			allModels = allModels[start:]
		} else {
			allModels = allModels[start:end]
		}

		c.JSON(http.StatusOK, gin.H{
			"models": allModels,
			"pagination": gin.H{
				"page":     page,
				"limit":    limit,
				"total":    total,
				"has_next": end < total,
				"has_prev": page > 1,
			},
		})
	})
}

// LLMProvidersHandler 获取支持的提供商列表
func LLMProvidersHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		providers := []gin.H{
			{
				"name":        "OpenAI",
				"type":        "openai",
				"description": "OpenAI GPT模型，支持GPT-3.5、GPT-4等",
				"models":      []string{"gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"},
			},
			{
				"name":        "Anthropic",
				"type":        "claude",
				"description": "Anthropic Claude模型，支持Claude-3系列",
				"models":      []string{"claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"},
			},
			{
				"name":        "DeepSeek",
				"type":        "deepseek",
				"description": "DeepSeek模型，中文友好的大语言模型",
				"models":      []string{"deepseek-chat", "deepseek-coder"},
			},
		}

		c.JSON(http.StatusOK, gin.H{
			"providers": providers,
		})
	})
}

// LLMDemoHandler 演示接口
func LLMDemoHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"message": "LLM服务演示",
			"features": []string{
				"支持OpenAI、Claude、DeepSeek等多个大模型提供商",
				"灵活的配置文件管理，每个厂商独立配置",
				"基于Token的积分消耗系统，1 Token = 1 积分",
				"实时的Token预计算和积分检查",
				"统一的聊天接口，自动适配不同厂商API格式",
			},
			"usage": gin.H{
				"models":           "GET /llm/models - 获取可用模型列表",
				"providers":        "GET /llm/providers - 获取支持的提供商",
				"chat":             "POST /llm/chat - 聊天对话",
				"calculate_tokens": "POST /llm/calculate-tokens - 计算Token消耗",
			},
			"config_path": "configs/llm/",
			"supported_env_vars": []string{
				"OPENAI_API_KEY",
				"CLAUDE_API_KEY",
				"DEEPSEEK_API_KEY",
			},
		})
	})
}
