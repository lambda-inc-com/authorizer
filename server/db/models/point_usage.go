package models

import "time"

type PointUsage struct {
	ID             string    `json:"id" gorm:"primaryKey"`
	UserID         string    `json:"user_id" gorm:"index"`
	Content        string    `json:"content"`         // 使用场景描述，如："购买商品X", "下载文档Y"
	AmountConsumed int       `json:"amount_consumed"` // 本次消耗的积分数量
	ModelType      string    `json:"model_type"`      // 关联的模型类型，如："product", "document", "feature"
	ModelName      string    `json:"model_name"`      // 关联的模型名称，如："A商品", "高级文档", "AI服务"
	CreatedAt      time.Time `json:"created_at"`
}
