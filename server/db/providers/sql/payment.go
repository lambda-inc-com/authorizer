package sql

import (
	"context"
	"time"

	"github.com/authorizerdev/authorizer/server/db/models"
	"github.com/google/uuid"
	"github.com/shopspring/decimal"
)

// AddPayment 添加支付记录
func (p *provider) AddPayment(ctx context.Context, payment *models.Payment) (*models.Payment, error) {
	if payment.ID == "" {
		payment.ID = uuid.New().String()
	}

	payment.CreatedAt = time.Now()

	result := p.db.Create(&payment)
	if result.Error != nil {
		return payment, result.Error
	}

	return payment, nil
}

// UpdatePayment 更新支付记录
func (p *provider) UpdatePayment(ctx context.Context, payment *models.Payment) (*models.Payment, error) {
	result := p.db.Save(&payment)
	if result.Error != nil {
		return payment, result.Error
	}

	return payment, nil
}

// DeletePayment 删除支付记录
func (p *provider) DeletePayment(ctx context.Context, paymentID string) error {
	result := p.db.Where("id = ?", paymentID).Delete(&models.Payment{})
	if result.Error != nil {
		return result.Error
	}

	return nil
}

// GetPaymentByID 根据ID获取支付记录
func (p *provider) GetPaymentByID(ctx context.Context, id string) (*models.Payment, error) {
	var payment *models.Payment
	result := p.db.Where("id = ?", id).First(&payment)
	if result.Error != nil {
		return nil, result.Error
	}

	return payment, nil
}

// GetPaymentByOrderID 根据订单ID获取支付记录
func (p *provider) GetPaymentByOrderID(ctx context.Context, orderID string) (*models.Payment, error) {
	var payment *models.Payment
	result := p.db.Where("order_id = ?", orderID).First(&payment)
	if result.Error != nil {
		return nil, result.Error
	}

	return payment, nil
}

// GetPaymentsByUserID 根据用户ID获取支付记录列表
func (p *provider) GetPaymentsByUserID(ctx context.Context, userID string, limit, offset int) ([]*models.Payment, error) {
	var payments []*models.Payment
	result := p.db.Where("user_id = ?", userID).Limit(limit).Offset(offset).Order("created_at DESC").Find(&payments)
	if result.Error != nil {
		return nil, result.Error
	}

	return payments, nil
}

// GetPaymentsByStatus 根据状态获取支付记录列表
func (p *provider) GetPaymentsByStatus(ctx context.Context, status string, limit, offset int) ([]*models.Payment, error) {
	var payments []*models.Payment
	result := p.db.Where("status = ?", status).Limit(limit).Offset(offset).Order("created_at DESC").Find(&payments)
	if result.Error != nil {
		return nil, result.Error
	}

	return payments, nil
}

// GetPaymentsByUserIDAndStatus 根据用户ID和状态获取支付记录列表
func (p *provider) GetPaymentsByUserIDAndStatus(ctx context.Context, userID, status string, limit, offset int) ([]*models.Payment, error) {
	var payments []*models.Payment
	result := p.db.Where("user_id = ? AND status = ?", userID, status).Limit(limit).Offset(offset).Order("created_at DESC").Find(&payments)
	if result.Error != nil {
		return nil, result.Error
	}

	return payments, nil
}

// UpdatePaymentStatus 更新支付状态
func (p *provider) UpdatePaymentStatus(ctx context.Context, paymentID, status string) error {
	result := p.db.Model(&models.Payment{}).Where("id = ?", paymentID).Update("status", status)
	if result.Error != nil {
		return result.Error
	}

	return nil
}

// GetPaymentsByDateRange 根据日期范围获取支付记录
func (p *provider) GetPaymentsByDateRange(ctx context.Context, startDate, endDate time.Time, limit, offset int) ([]*models.Payment, error) {
	var payments []*models.Payment
	result := p.db.Where("paid_at BETWEEN ? AND ?", startDate, endDate).Limit(limit).Offset(offset).Order("paid_at DESC").Find(&payments)
	if result.Error != nil {
		return nil, result.Error
	}

	return payments, nil
}

// GetTotalPaymentAmount 获取总支付金额
func (p *provider) GetTotalPaymentAmount(ctx context.Context, userID string) (decimal.Decimal, error) {
	var total decimal.Decimal
	result := p.db.Model(&models.Payment{}).Where("user_id = ? AND status = ?", userID, "success").Select("COALESCE(SUM(amount), 0)").Scan(&total)
	if result.Error != nil {
		return decimal.Zero, result.Error
	}

	return total, nil
}

// GetExpiredPayments 获取过期的支付记录
func (p *provider) GetExpiredPayments(ctx context.Context) ([]*models.Payment, error) {
	var payments []*models.Payment
	now := time.Now()
	result := p.db.Where("status = ? AND expired_at <= ? AND expired_at != ?", "success", now, time.Time{}).Find(&payments)
	if result.Error != nil {
		return nil, result.Error
	}

	return payments, nil
}
