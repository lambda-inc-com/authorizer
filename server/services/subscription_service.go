package services

import (
	"context"
	"time"

	"github.com/authorizerdev/authorizer/server/db"
	"github.com/authorizerdev/authorizer/server/db/models"
)

// SubscriptionService 订阅服务
type SubscriptionService struct{}

// UserSubscription 用户订阅信息
type UserSubscription struct {
	HasValidSubscription bool   `json:"has_valid_subscription"`
	RequiresUserAPIKey   bool   `json:"requires_user_api_key"`
	ProductName          string `json:"product_name,omitempty"`
	ExpiresAt            int64  `json:"expires_at,omitempty"`
}

// NewSubscriptionService 创建订阅服务实例
func NewSubscriptionService() *SubscriptionService {
	return &SubscriptionService{}
}

// CheckUserSubscription 检查用户的订阅状态
func (s *SubscriptionService) CheckUserSubscription(ctx context.Context, userID string) (*UserSubscription, error) {
	// 获取用户所有已支付的订单
	orders, err := db.Provider.GetOrdersByUserIDAndStatus(ctx, userID, "paid", 100, 0)
	if err != nil {
		return &UserSubscription{
			HasValidSubscription: false,
			RequiresUserAPIKey:   true,
		}, err
	}

	now := time.Now()
	var validOrder *models.Order

	// 查找当前时间内有效的订单
	for _, order := range orders {
		if !order.SubscribeTo.IsZero() && order.SubscribeTo.After(now) {
			validOrder = order
			break
		}
	}

	if validOrder == nil {
		return &UserSubscription{
			HasValidSubscription: false,
			RequiresUserAPIKey:   true,
		}, nil
	}

	// 获取商品信息
	product, err := db.Provider.GetProductByID(ctx, validOrder.ProductID)
	if err != nil {
		return &UserSubscription{
			HasValidSubscription: false,
			RequiresUserAPIKey:   true,
		}, err
	}

	// 根据商品ID判断是否需要用户自己的API key
	requiresUserAPIKey := (product.ID == "a") // A商品需要用户自己配置API key

	return &UserSubscription{
		HasValidSubscription: true,
		RequiresUserAPIKey:   requiresUserAPIKey,
		ProductName:          product.Name,
		ExpiresAt:            validOrder.SubscribeTo.Unix(),
	}, nil
}

// CanUseSystemAPIKey 检查用户是否可以使用系统的API key
func (s *SubscriptionService) CanUseSystemAPIKey(ctx context.Context, userID string) (bool, error) {
	subscription, err := s.CheckUserSubscription(ctx, userID)
	if err != nil {
		return false, err
	}

	// 用户有有效订阅且不需要自己的API key（即B、C商品）
	return subscription.HasValidSubscription && !subscription.RequiresUserAPIKey, nil
}

// MustUseUserAPIKey 检查用户是否必须使用自己的API key
func (s *SubscriptionService) MustUseUserAPIKey(ctx context.Context, userID string) (bool, error) {
	subscription, err := s.CheckUserSubscription(ctx, userID)
	if err != nil {
		return false, err
	}

	// 用户有有效订阅但需要自己的API key（即A商品）
	return subscription.HasValidSubscription && subscription.RequiresUserAPIKey, nil
}

// HasValidSubscription 检查用户是否有有效订阅
func (s *SubscriptionService) HasValidSubscription(ctx context.Context, userID string) (bool, error) {
	subscription, err := s.CheckUserSubscription(ctx, userID)
	if err != nil {
		return false, err
	}

	return subscription.HasValidSubscription, nil
}
