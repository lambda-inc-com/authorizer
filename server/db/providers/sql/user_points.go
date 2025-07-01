package sql

import (
	"context"
	"time"

	"github.com/authorizerdev/authorizer/server/db/models"
)

// AddUserPoints 添加用户积分账户
func (p *provider) AddUserPoints(ctx context.Context, userPoints *models.UserPoints) (*models.UserPoints, error) {
	userPoints.UpdatedAt = time.Now()

	result := p.db.Create(&userPoints)
	if result.Error != nil {
		return userPoints, result.Error
	}

	return userPoints, nil
}

// UpdateUserPoints 更新用户积分账户
func (p *provider) UpdateUserPoints(ctx context.Context, userPoints *models.UserPoints) (*models.UserPoints, error) {
	userPoints.UpdatedAt = time.Now()

	result := p.db.Save(&userPoints)
	if result.Error != nil {
		return userPoints, result.Error
	}

	return userPoints, nil
}

// DeleteUserPoints 删除用户积分账户
func (p *provider) DeleteUserPoints(ctx context.Context, userID string) error {
	result := p.db.Where("user_id = ?", userID).Delete(&models.UserPoints{})
	if result.Error != nil {
		return result.Error
	}

	return nil
}

// GetUserPointsByUserID 根据用户ID获取积分账户
func (p *provider) GetUserPointsByUserID(ctx context.Context, userID string) (*models.UserPoints, error) {
	var userPoints *models.UserPoints
	result := p.db.Where("user_id = ?", userID).First(&userPoints)
	if result.Error != nil {
		return nil, result.Error
	}

	return userPoints, nil
}

// GetOrCreateUserPoints 获取或创建用户积分账户
func (p *provider) GetOrCreateUserPoints(ctx context.Context, userID string) (*models.UserPoints, error) {
	userPoints, err := p.GetUserPointsByUserID(ctx, userID)
	if err != nil {
		// 如果不存在，创建新的积分账户
		userPoints = &models.UserPoints{
			UserID:      userID,
			Points:      0,
			TotalEarned: 0,
			UpdatedAt:   time.Now(),
		}
		return p.AddUserPoints(ctx, userPoints)
	}

	return userPoints, nil
}

// AddPointsToUser 给用户增加积分
func (p *provider) AddPointsToUser(ctx context.Context, userID string, points int) (*models.UserPoints, error) {
	userPoints, err := p.GetOrCreateUserPoints(ctx, userID)
	if err != nil {
		return nil, err
	}

	userPoints.Points += points
	if points > 0 {
		userPoints.TotalEarned += points
	}
	userPoints.UpdatedAt = time.Now()

	result := p.db.Save(&userPoints)
	if result.Error != nil {
		return userPoints, result.Error
	}

	return userPoints, nil
}

// ConsumeUserPoints 消耗用户积分
func (p *provider) ConsumeUserPoints(ctx context.Context, userID string, points int) (*models.UserPoints, error) {
	userPoints, err := p.GetUserPointsByUserID(ctx, userID)
	if err != nil {
		return nil, err
	}

	if userPoints.Points < points {
		return nil, err
	}

	userPoints.Points -= points
	userPoints.UpdatedAt = time.Now()

	result := p.db.Save(&userPoints)
	if result.Error != nil {
		return userPoints, result.Error
	}

	return userPoints, nil
}

// GetTopUsersByPoints 获取积分排行榜
func (p *provider) GetTopUsersByPoints(ctx context.Context, limit int) ([]*models.UserPoints, error) {
	var userPoints []*models.UserPoints
	result := p.db.Order("points DESC").Limit(limit).Find(&userPoints)
	if result.Error != nil {
		return nil, result.Error
	}

	return userPoints, nil
}

// GetUserPointsStatistics 获取用户积分统计信息
func (p *provider) GetUserPointsStatistics(ctx context.Context) (map[string]interface{}, error) {
	var totalUsers int64
	var totalPoints int64
	var totalEarned int64

	// 获取总用户数
	result := p.db.Model(&models.UserPoints{}).Count(&totalUsers)
	if result.Error != nil {
		return nil, result.Error
	}

	// 获取总积分
	result = p.db.Model(&models.UserPoints{}).Select("COALESCE(SUM(points), 0)").Scan(&totalPoints)
	if result.Error != nil {
		return nil, result.Error
	}

	// 获取总获得积分
	result = p.db.Model(&models.UserPoints{}).Select("COALESCE(SUM(total_earned), 0)").Scan(&totalEarned)
	if result.Error != nil {
		return nil, result.Error
	}

	return map[string]interface{}{
		"total_users":  totalUsers,
		"total_points": totalPoints,
		"total_earned": totalEarned,
		"average_points": func() float64 {
			if totalUsers > 0 {
				return float64(totalPoints) / float64(totalUsers)
			}
			return 0
		}(),
	}, nil
}
