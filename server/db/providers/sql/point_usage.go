package sql

import (
	"context"
	"time"

	"github.com/authorizerdev/authorizer/server/db/models"
	"github.com/google/uuid"
)

// AddPointUsage 添加积分使用记录
func (p *provider) AddPointUsage(ctx context.Context, pointUsage *models.PointUsage) (*models.PointUsage, error) {
	if pointUsage.ID == "" {
		pointUsage.ID = uuid.New().String()
	}

	pointUsage.CreatedAt = time.Now()

	result := p.db.Create(&pointUsage)
	if result.Error != nil {
		return pointUsage, result.Error
	}

	return pointUsage, nil
}

// UpdatePointUsage 更新积分使用记录
func (p *provider) UpdatePointUsage(ctx context.Context, pointUsage *models.PointUsage) (*models.PointUsage, error) {
	result := p.db.Save(&pointUsage)
	if result.Error != nil {
		return pointUsage, result.Error
	}

	return pointUsage, nil
}

// DeletePointUsage 删除积分使用记录
func (p *provider) DeletePointUsage(ctx context.Context, usageID string) error {
	result := p.db.Where("id = ?", usageID).Delete(&models.PointUsage{})
	if result.Error != nil {
		return result.Error
	}

	return nil
}

// GetPointUsageByID 根据ID获取积分使用记录
func (p *provider) GetPointUsageByID(ctx context.Context, id string) (*models.PointUsage, error) {
	var pointUsage *models.PointUsage
	result := p.db.Where("id = ?", id).First(&pointUsage)
	if result.Error != nil {
		return nil, result.Error
	}

	return pointUsage, nil
}

// GetPointUsagesByUserID 根据用户ID获取积分使用记录列表
func (p *provider) GetPointUsagesByUserID(ctx context.Context, userID string, limit, offset int) ([]*models.PointUsage, error) {
	var pointUsages []*models.PointUsage
	result := p.db.Where("user_id = ?", userID).Limit(limit).Offset(offset).Order("created_at DESC").Find(&pointUsages)
	if result.Error != nil {
		return nil, result.Error
	}

	return pointUsages, nil
}

// GetPointUsagesByModelType 根据模型类型获取积分使用记录列表
func (p *provider) GetPointUsagesByModelType(ctx context.Context, modelType string, limit, offset int) ([]*models.PointUsage, error) {
	var pointUsages []*models.PointUsage
	result := p.db.Where("model_type = ?", modelType).Limit(limit).Offset(offset).Order("created_at DESC").Find(&pointUsages)
	if result.Error != nil {
		return nil, result.Error
	}

	return pointUsages, nil
}

// GetPointUsagesByUserIDAndModelType 根据用户ID和模型类型获取积分使用记录列表
func (p *provider) GetPointUsagesByUserIDAndModelType(ctx context.Context, userID, modelType string, limit, offset int) ([]*models.PointUsage, error) {
	var pointUsages []*models.PointUsage
	result := p.db.Where("user_id = ? AND model_type = ?", userID, modelType).Limit(limit).Offset(offset).Order("created_at DESC").Find(&pointUsages)
	if result.Error != nil {
		return nil, result.Error
	}

	return pointUsages, nil
}

// GetPointUsagesByDateRange 根据日期范围获取积分使用记录
func (p *provider) GetPointUsagesByDateRange(ctx context.Context, startDate, endDate time.Time, limit, offset int) ([]*models.PointUsage, error) {
	var pointUsages []*models.PointUsage
	result := p.db.Where("created_at BETWEEN ? AND ?", startDate, endDate).Limit(limit).Offset(offset).Order("created_at DESC").Find(&pointUsages)
	if result.Error != nil {
		return nil, result.Error
	}

	return pointUsages, nil
}

// GetTotalPointsConsumedByUser 获取用户总消耗积分
func (p *provider) GetTotalPointsConsumedByUser(ctx context.Context, userID string) (int, error) {
	var total int
	result := p.db.Model(&models.PointUsage{}).Where("user_id = ?", userID).Select("COALESCE(SUM(amount_consumed), 0)").Scan(&total)
	if result.Error != nil {
		return 0, result.Error
	}

	return total, nil
}

// GetPointUsageStatistics 获取积分使用统计信息
func (p *provider) GetPointUsageStatistics(ctx context.Context) (map[string]interface{}, error) {
	var totalUsages int64
	var totalConsumed int64

	// 获取总使用记录数
	result := p.db.Model(&models.PointUsage{}).Count(&totalUsages)
	if result.Error != nil {
		return nil, result.Error
	}

	// 获取总消耗积分
	result = p.db.Model(&models.PointUsage{}).Select("COALESCE(SUM(amount_consumed), 0)").Scan(&totalConsumed)
	if result.Error != nil {
		return nil, result.Error
	}

	// 获取各模型类型的使用统计
	var modelTypeStats []struct {
		ModelType     string `json:"model_type"`
		Count         int64  `json:"count"`
		TotalConsumed int64  `json:"total_consumed"`
	}

	result = p.db.Model(&models.PointUsage{}).
		Select("model_type, COUNT(*) as count, COALESCE(SUM(amount_consumed), 0) as total_consumed").
		Group("model_type").
		Scan(&modelTypeStats)
	if result.Error != nil {
		return nil, result.Error
	}

	return map[string]interface{}{
		"total_usages":     totalUsages,
		"total_consumed":   totalConsumed,
		"model_type_stats": modelTypeStats,
		"average_consumed": func() float64 {
			if totalUsages > 0 {
				return float64(totalConsumed) / float64(totalUsages)
			}
			return 0
		}(),
	}, nil
}

// RecordPointUsage 记录积分使用（事务性操作）
func (p *provider) RecordPointUsage(ctx context.Context, userID, content string, amountConsumed int, modelType, modelName string) error {
	// 开始事务
	tx := p.db.Begin()
	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
		}
	}()

	// 检查用户积分是否足够
	var userPoints models.UserPoints
	result := tx.Where("user_id = ?", userID).First(&userPoints)
	if result.Error != nil {
		tx.Rollback()
		return result.Error
	}

	if userPoints.Points < amountConsumed {
		tx.Rollback()
		return result.Error
	}

	// 扣除积分
	userPoints.Points -= amountConsumed
	userPoints.UpdatedAt = time.Now()
	result = tx.Save(&userPoints)
	if result.Error != nil {
		tx.Rollback()
		return result.Error
	}

	// 记录使用记录
	pointUsage := &models.PointUsage{
		ID:             uuid.New().String(),
		UserID:         userID,
		Content:        content,
		AmountConsumed: amountConsumed,
		ModelType:      modelType,
		ModelName:      modelName,
		CreatedAt:      time.Now(),
	}

	result = tx.Create(&pointUsage)
	if result.Error != nil {
		tx.Rollback()
		return result.Error
	}

	// 提交事务
	return tx.Commit().Error
}
