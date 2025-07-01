package models

import "time"

type UserPoints struct {
	UserID      string    `json:"user_id" gorm:"primaryKey"`
	Points      int       `json:"points"`       // 当前可用积分
	TotalEarned int       `json:"total_earned"` // 历史累计获得积分
	UpdatedAt   time.Time `json:"updated_at"`
}
