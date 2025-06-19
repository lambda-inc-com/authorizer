package handlers

import (
	"net/http"

	"github.com/authorizerdev/authorizer/server/db"
	"github.com/authorizerdev/authorizer/server/db/models"
	"github.com/gin-gonic/gin"
	log "github.com/sirupsen/logrus"
)

// UserLLMConfigRequest 用户LLM配置请求
type UserLLMConfigRequest struct {
	Provider  string `json:"provider" binding:"required"`   // 提供商名称
	ModelType string `json:"model_type" binding:"required"` // 模型类型
	ModelName string `json:"model_name" binding:"required"` // 模型名称
	APIKey    string `json:"api_key" binding:"required"`    // API密钥
	BaseURL   string `json:"base_url"`                      // API基础URL
	MaxTokens int    `json:"max_tokens"`                    // 最大token限制
	IsEnabled bool   `json:"is_enabled"`                    // 是否启用
	IsDefault bool   `json:"is_default"`                    // 是否为默认配置
}

// AddUserLLMConfigHandler 添加用户LLM配置
func AddUserLLMConfigHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		userID := c.GetString("user_id")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Unauthorized",
			})
			return
		}

		var request UserLLMConfigRequest
		if err := c.ShouldBindJSON(&request); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request format: " + err.Error(),
			})
			return
		}

		config := &models.UserLLMConfig{
			UserID:    userID,
			Provider:  request.Provider,
			ModelType: request.ModelType,
			ModelName: request.ModelName,
			APIKey:    request.APIKey,
			BaseURL:   request.BaseURL,
			MaxTokens: request.MaxTokens,
			IsEnabled: request.IsEnabled,
			IsDefault: request.IsDefault,
		}

		// 设置默认值
		if config.MaxTokens == 0 {
			config.MaxTokens = 4096
		}

		result, err := db.Provider.AddUserLLMConfig(c.Request.Context(), config)
		if err != nil {
			log.Errorf("Failed to add user LLM config: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to add LLM configuration",
			})
			return
		}

		// 隐藏API密钥的敏感信息
		result.APIKey = "***"

		c.JSON(http.StatusCreated, gin.H{
			"config": result,
		})
	})
}

// UpdateUserLLMConfigHandler 更新用户LLM配置
func UpdateUserLLMConfigHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		userID := c.GetString("user_id")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Unauthorized",
			})
			return
		}

		configID := c.Param("config_id")
		if configID == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Config ID is required",
			})
			return
		}

		// 检查配置是否属于当前用户
		existingConfig, err := db.Provider.GetUserLLMConfigByID(c.Request.Context(), configID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Configuration not found",
			})
			return
		}

		if existingConfig.UserID != userID {
			c.JSON(http.StatusForbidden, gin.H{
				"error": "Permission denied",
			})
			return
		}

		var request UserLLMConfigRequest
		if err := c.ShouldBindJSON(&request); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request format: " + err.Error(),
			})
			return
		}

		// 更新配置
		existingConfig.Provider = request.Provider
		existingConfig.ModelType = request.ModelType
		existingConfig.ModelName = request.ModelName
		existingConfig.APIKey = request.APIKey
		existingConfig.BaseURL = request.BaseURL
		existingConfig.MaxTokens = request.MaxTokens
		existingConfig.IsEnabled = request.IsEnabled
		existingConfig.IsDefault = request.IsDefault

		result, err := db.Provider.UpdateUserLLMConfig(c.Request.Context(), existingConfig)
		if err != nil {
			log.Errorf("Failed to update user LLM config: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to update LLM configuration",
			})
			return
		}

		// 隐藏API密钥的敏感信息
		result.APIKey = "***"

		c.JSON(http.StatusOK, gin.H{
			"config": result,
		})
	})
}

// DeleteUserLLMConfigHandler 删除用户LLM配置
func DeleteUserLLMConfigHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		userID := c.GetString("user_id")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Unauthorized",
			})
			return
		}

		configID := c.Param("config_id")
		if configID == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Config ID is required",
			})
			return
		}

		// 检查配置是否属于当前用户
		existingConfig, err := db.Provider.GetUserLLMConfigByID(c.Request.Context(), configID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Configuration not found",
			})
			return
		}

		if existingConfig.UserID != userID {
			c.JSON(http.StatusForbidden, gin.H{
				"error": "Permission denied",
			})
			return
		}

		err = db.Provider.DeleteUserLLMConfig(c.Request.Context(), configID)
		if err != nil {
			log.Errorf("Failed to delete user LLM config: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to delete LLM configuration",
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "Configuration deleted successfully",
		})
	})
}

// GetUserLLMConfigsHandler 获取用户的所有LLM配置
func GetUserLLMConfigsHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		userID := c.GetString("user_id")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Unauthorized",
			})
			return
		}

		configs, err := db.Provider.GetUserLLMConfigsByUserID(c.Request.Context(), userID)
		if err != nil {
			log.Errorf("Failed to get user LLM configs: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to get LLM configurations",
			})
			return
		}

		// 隐藏API密钥的敏感信息
		for _, config := range configs {
			config.APIKey = "***"
		}

		c.JSON(http.StatusOK, gin.H{
			"configs": configs,
		})
	})
}

// SetDefaultUserLLMConfigHandler 设置默认的用户LLM配置
func SetDefaultUserLLMConfigHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		userID := c.GetString("user_id")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Unauthorized",
			})
			return
		}

		configID := c.Param("config_id")
		if configID == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Config ID is required",
			})
			return
		}

		// 检查配置是否属于当前用户
		existingConfig, err := db.Provider.GetUserLLMConfigByID(c.Request.Context(), configID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Configuration not found",
			})
			return
		}

		if existingConfig.UserID != userID {
			c.JSON(http.StatusForbidden, gin.H{
				"error": "Permission denied",
			})
			return
		}

		err = db.Provider.SetDefaultUserLLMConfig(c.Request.Context(), userID, configID)
		if err != nil {
			log.Errorf("Failed to set default user LLM config: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to set default LLM configuration",
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "Default configuration set successfully",
		})
	})
}
