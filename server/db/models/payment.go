package models

import (
	"time"

	"github.com/shopspring/decimal"
)

type Payment struct {
	ID        string          `json:"id" gorm:"primaryKey"`
	OrderID   string          `json:"order_id" gorm:"index"`
	UserID    string          `json:"user_id" gorm:"index"`
	Amount    decimal.Decimal `json:"amount" gorm:"type:decimal(10,2)"`
	Type      string          `json:"type"`    // onetime, subscription_month, subscription_year
	Channel   string          `json:"channel"` // mock, alipay, wechat, bank
	Status    string          `json:"status"`  // pending, success, failed
	PaidAt    time.Time       `json:"paid_at"`
	ExpiredAt time.Time       `json:"expired_at"`
	CreatedAt time.Time       `json:"created_at"`
}
