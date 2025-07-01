package sql

import (
	"context"
	"time"

	"github.com/authorizerdev/authorizer/server/db/models"
	"github.com/google/uuid"
)

// AddOrder 添加订单
func (p *provider) AddOrder(ctx context.Context, order *models.Order) (*models.Order, error) {
	if order.ID == "" {
		order.ID = uuid.New().String()
	}

	order.CreatedAt = time.Now()
	order.UpdatedAt = time.Now()

	result := p.db.Create(&order)
	if result.Error != nil {
		return order, result.Error
	}

	return order, nil
}

// UpdateOrder 更新订单
func (p *provider) UpdateOrder(ctx context.Context, order *models.Order) (*models.Order, error) {
	order.UpdatedAt = time.Now()

	result := p.db.Save(&order)
	if result.Error != nil {
		return order, result.Error
	}

	return order, nil
}

// DeleteOrder 删除订单
func (p *provider) DeleteOrder(ctx context.Context, orderID string) error {
	result := p.db.Where("id = ?", orderID).Delete(&models.Order{})
	if result.Error != nil {
		return result.Error
	}

	return nil
}

// GetOrderByID 根据ID获取订单
func (p *provider) GetOrderByID(ctx context.Context, id string) (*models.Order, error) {
	var order *models.Order
	result := p.db.Where("id = ?", id).First(&order)
	if result.Error != nil {
		return nil, result.Error
	}

	return order, nil
}

// GetOrdersByUserID 根据用户ID获取订单列表
func (p *provider) GetOrdersByUserID(ctx context.Context, userID string, limit, offset int) ([]*models.Order, error) {
	var orders []*models.Order
	result := p.db.Where("user_id = ?", userID).Limit(limit).Offset(offset).Order("created_at DESC").Find(&orders)
	if result.Error != nil {
		return nil, result.Error
	}

	return orders, nil
}

// GetOrdersByStatus 根据状态获取订单列表
func (p *provider) GetOrdersByStatus(ctx context.Context, status string, limit, offset int) ([]*models.Order, error) {
	var orders []*models.Order
	result := p.db.Where("status = ?", status).Limit(limit).Offset(offset).Order("created_at DESC").Find(&orders)
	if result.Error != nil {
		return nil, result.Error
	}

	return orders, nil
}

// GetOrdersByUserIDAndStatus 根据用户ID和状态获取订单列表
func (p *provider) GetOrdersByUserIDAndStatus(ctx context.Context, userID, status string, limit, offset int) ([]*models.Order, error) {
	var orders []*models.Order
	result := p.db.Where("user_id = ? AND status = ?", userID, status).Limit(limit).Offset(offset).Order("created_at DESC").Find(&orders)
	if result.Error != nil {
		return nil, result.Error
	}

	return orders, nil
}

// UpdateOrderStatus 更新订单状态
func (p *provider) UpdateOrderStatus(ctx context.Context, orderID, status string) error {
	result := p.db.Model(&models.Order{}).Where("id = ?", orderID).Updates(map[string]interface{}{
		"status":     status,
		"updated_at": time.Now(),
	})

	if result.Error != nil {
		return result.Error
	}

	return nil
}

// GetExpiredOrders 获取过期的订单（用于自动续费）
func (p *provider) GetExpiredOrders(ctx context.Context) ([]*models.Order, error) {
	var orders []*models.Order
	now := time.Now()
	result := p.db.Where("status = ? AND auto_renew = ? AND subscribe_to <= ?", "paid", true, now).Find(&orders)
	if result.Error != nil {
		return nil, result.Error
	}

	return orders, nil
}
