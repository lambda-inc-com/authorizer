package models

import (
	"time"

	"github.com/shopspring/decimal"
)

type Order struct {
	ID            string          `json:"id" gorm:"primaryKey"`
	UserID        string          `json:"user_id" gorm:"index"`
	ProductID     string          `json:"product_id" gorm:"index"`
	Points        int             `json:"points"`
	Amount        decimal.Decimal `json:"amount" gorm:"type:decimal(10,2)"`
	Status        string          `json:"status"`       // pending, paid, cancelled
	PaymentType   string          `json:"payment_type"` // monthly, yearly, continuous
	PayCycle      string          `json:"pay_cycle"`    // month, year, onetime
	SubscribeFrom time.Time       `json:"subscribe_from"`
	SubscribeTo   time.Time       `json:"subscribe_to"`
	AutoRenew     bool            `json:"auto_renew"`
	CreatedAt     time.Time       `json:"created_at"`
	UpdatedAt     time.Time       `json:"updated_at"`
}
