package models

import (
	"time"

	"github.com/shopspring/decimal"
)

type Product struct {
	ID                string          `json:"id" gorm:"primaryKey"`
	Name              string          `json:"name"`
	Points            int             `json:"points"`
	PricingMonthly    decimal.Decimal `json:"pricing_monthly" gorm:"type:decimal(10,2)"`    // 按月支付价格
	PricingYearly     decimal.Decimal `json:"pricing_yearly" gorm:"type:decimal(10,2)"`     // 按年支付价格
	PricingContinuous decimal.Decimal `json:"pricing_continuous" gorm:"type:decimal(10,2)"` // 连续续订价格
	Type              string          `json:"type"`                                         // normal, subscription
	Description       string          `json:"description"`
	Image             string          `json:"image"`
	CreatedAt         time.Time       `json:"created_at"`
	UpdatedAt         time.Time       `json:"updated_at"`
}

// GetPrice 根据支付方式获取价格
func (p *Product) GetPrice(paymentType string) decimal.Decimal {
	switch paymentType {
	case "monthly":
		return p.PricingMonthly
	case "yearly":
		return p.PricingYearly
	case "continuous":
		return p.PricingContinuous
	default:
		return p.PricingMonthly // 默认按月价格
	}
}

// GetPricing 获取价格信息（为了兼容性）
func (p *Product) GetPricing() map[string]decimal.Decimal {
	return map[string]decimal.Decimal{
		"monthly":    p.PricingMonthly,
		"yearly":     p.PricingYearly,
		"continuous": p.PricingContinuous,
	}
}
