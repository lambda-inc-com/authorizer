package sql

import (
	"context"
	"time"

	"github.com/authorizerdev/authorizer/server/db/models"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

// AddUserLLMConfig 添加用户LLM配置
func (p *provider) AddUserLLMConfig(ctx context.Context, config *models.UserLLMConfig) (*models.UserLLMConfig, error) {
	if config.ID == "" {
		config.ID = uuid.New().String()
	}

	config.CreatedAt = time.Now().Unix()
	config.UpdatedAt = time.Now().Unix()

	// 如果设置为默认配置，先取消其他默认配置
	if config.IsDefault {
		err := p.db.Model(&models.UserLLMConfig{}).
			Where("user_id = ? AND is_default = ?", config.UserID, true).
			Update("is_default", false).Error
		if err != nil {
			return nil, err
		}
	}

	result := p.db.Create(&config)
	if result.Error != nil {
		return nil, result.Error
	}

	return config, nil
}

// UpdateUserLLMConfig 更新用户LLM配置
func (p *provider) UpdateUserLLMConfig(ctx context.Context, config *models.UserLLMConfig) (*models.UserLLMConfig, error) {
	config.UpdatedAt = time.Now().Unix()

	// 如果设置为默认配置，先取消其他默认配置
	if config.IsDefault {
		err := p.db.Model(&models.UserLLMConfig{}).
			Where("user_id = ? AND is_default = ? AND id != ?", config.UserID, true, config.ID).
			Update("is_default", false).Error
		if err != nil {
			return nil, err
		}
	}

	result := p.db.Save(&config)
	if result.Error != nil {
		return nil, result.Error
	}

	return config, nil
}

// DeleteUserLLMConfig 删除用户LLM配置
func (p *provider) DeleteUserLLMConfig(ctx context.Context, configID string) error {
	result := p.db.Where("id = ?", configID).Delete(&models.UserLLMConfig{})
	return result.Error
}

// GetUserLLMConfigByID 根据ID获取用户LLM配置
func (p *provider) GetUserLLMConfigByID(ctx context.Context, id string) (*models.UserLLMConfig, error) {
	var config models.UserLLMConfig
	result := p.db.Where("id = ?", id).First(&config)
	if result.Error != nil {
		return nil, result.Error
	}
	return &config, nil
}

// GetUserLLMConfigsByUserID 获取用户的所有LLM配置
func (p *provider) GetUserLLMConfigsByUserID(ctx context.Context, userID string) ([]*models.UserLLMConfig, error) {
	var configs []*models.UserLLMConfig
	result := p.db.Where("user_id = ?", userID).Order("created_at DESC").Find(&configs)
	if result.Error != nil {
		return nil, result.Error
	}
	return configs, nil
}

// GetUserLLMConfigByUserIDAndProvider 根据用户ID和提供商获取LLM配置
func (p *provider) GetUserLLMConfigByUserIDAndProvider(ctx context.Context, userID, provider string) (*models.UserLLMConfig, error) {
	var config models.UserLLMConfig
	result := p.db.Where("user_id = ? AND provider = ? AND is_enabled = ?", userID, provider, true).First(&config)
	if result.Error != nil {
		return nil, result.Error
	}
	return &config, nil
}

// GetDefaultUserLLMConfig 获取用户的默认LLM配置
func (p *provider) GetDefaultUserLLMConfig(ctx context.Context, userID string) (*models.UserLLMConfig, error) {
	var config models.UserLLMConfig
	result := p.db.Where("user_id = ? AND is_default = ? AND is_enabled = ?", userID, true, true).First(&config)
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			// 如果没有默认配置，返回第一个启用的配置
			result = p.db.Where("user_id = ? AND is_enabled = ?", userID, true).First(&config)
			if result.Error != nil {
				return nil, result.Error
			}
		} else {
			return nil, result.Error
		}
	}
	return &config, nil
}

// SetDefaultUserLLMConfig 设置默认的用户LLM配置
func (p *provider) SetDefaultUserLLMConfig(ctx context.Context, userID, configID string) error {
	// 先取消所有默认配置
	err := p.db.Model(&models.UserLLMConfig{}).
		Where("user_id = ? AND is_default = ?", userID, true).
		Update("is_default", false).Error
	if err != nil {
		return err
	}

	// 设置新的默认配置
	err = p.db.Model(&models.UserLLMConfig{}).
		Where("id = ? AND user_id = ?", configID, userID).
		Update("is_default", true).Error
	if err != nil {
		return err
	}

	return nil
}

// GetUserLLMConfigsByModelType 根据模型类型获取用户LLM配置
func (p *provider) GetUserLLMConfigsByModelType(ctx context.Context, userID, modelType string) ([]*models.UserLLMConfig, error) {
	var configs []*models.UserLLMConfig
	result := p.db.Where("user_id = ? AND model_type = ? AND is_enabled = ?", userID, modelType, true).
		Order("is_default DESC, created_at DESC").Find(&configs)
	if result.Error != nil {
		return nil, result.Error
	}
	return configs, nil
}
