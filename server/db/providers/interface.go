package providers

import (
	"context"
	"time"

	"github.com/authorizerdev/authorizer/server/db/models"
	"github.com/shopspring/decimal"
)

// ProductProvider 商品数据操作接口
type ProductProvider interface {
	AddProduct(ctx context.Context, product *models.Product) (*models.Product, error)
	UpdateProduct(ctx context.Context, product *models.Product) (*models.Product, error)
	DeleteProduct(ctx context.Context, productID string) error
	GetProductByID(ctx context.Context, id string) (*models.Product, error)
	ListProducts(ctx context.Context, limit, offset int) ([]*models.Product, error)
	GetProductsByType(ctx context.Context, productType string) ([]*models.Product, error)
	GetProductPrice(ctx context.Context, productID, paymentType string) (decimal.Decimal, error)
}

// OrderProvider 订单数据操作接口
type OrderProvider interface {
	AddOrder(ctx context.Context, order *models.Order) (*models.Order, error)
	UpdateOrder(ctx context.Context, order *models.Order) (*models.Order, error)
	DeleteOrder(ctx context.Context, orderID string) error
	GetOrderByID(ctx context.Context, id string) (*models.Order, error)
	GetOrdersByUserID(ctx context.Context, userID string, limit, offset int) ([]*models.Order, error)
	GetOrdersByStatus(ctx context.Context, status string, limit, offset int) ([]*models.Order, error)
	GetOrdersByUserIDAndStatus(ctx context.Context, userID, status string, limit, offset int) ([]*models.Order, error)
	UpdateOrderStatus(ctx context.Context, orderID, status string) error
	GetExpiredOrders(ctx context.Context) ([]*models.Order, error)
}

// PaymentProvider 支付数据操作接口
type PaymentProvider interface {
	AddPayment(ctx context.Context, payment *models.Payment) (*models.Payment, error)
	UpdatePayment(ctx context.Context, payment *models.Payment) (*models.Payment, error)
	DeletePayment(ctx context.Context, paymentID string) error
	GetPaymentByID(ctx context.Context, id string) (*models.Payment, error)
	GetPaymentByOrderID(ctx context.Context, orderID string) (*models.Payment, error)
	GetPaymentsByUserID(ctx context.Context, userID string, limit, offset int) ([]*models.Payment, error)
	GetPaymentsByStatus(ctx context.Context, status string, limit, offset int) ([]*models.Payment, error)
	GetPaymentsByUserIDAndStatus(ctx context.Context, userID, status string, limit, offset int) ([]*models.Payment, error)
	UpdatePaymentStatus(ctx context.Context, paymentID, status string) error
	GetPaymentsByDateRange(ctx context.Context, startDate, endDate time.Time, limit, offset int) ([]*models.Payment, error)
	GetTotalPaymentAmount(ctx context.Context, userID string) (decimal.Decimal, error)
	GetExpiredPayments(ctx context.Context) ([]*models.Payment, error)
}

// UserPointsProvider 用户积分数据操作接口
type UserPointsProvider interface {
	AddUserPoints(ctx context.Context, userPoints *models.UserPoints) (*models.UserPoints, error)
	UpdateUserPoints(ctx context.Context, userPoints *models.UserPoints) (*models.UserPoints, error)
	DeleteUserPoints(ctx context.Context, userID string) error
	GetUserPointsByUserID(ctx context.Context, userID string) (*models.UserPoints, error)
	GetOrCreateUserPoints(ctx context.Context, userID string) (*models.UserPoints, error)
	AddPointsToUser(ctx context.Context, userID string, points int) (*models.UserPoints, error)
	ConsumeUserPoints(ctx context.Context, userID string, points int) (*models.UserPoints, error)
	GetTopUsersByPoints(ctx context.Context, limit int) ([]*models.UserPoints, error)
	GetUserPointsStatistics(ctx context.Context) (map[string]interface{}, error)
}

// PointUsageProvider 积分使用记录数据操作接口
type PointUsageProvider interface {
	AddPointUsage(ctx context.Context, pointUsage *models.PointUsage) (*models.PointUsage, error)
	UpdatePointUsage(ctx context.Context, pointUsage *models.PointUsage) (*models.PointUsage, error)
	DeletePointUsage(ctx context.Context, usageID string) error
	GetPointUsageByID(ctx context.Context, id string) (*models.PointUsage, error)
	GetPointUsagesByUserID(ctx context.Context, userID string, limit, offset int) ([]*models.PointUsage, error)
	GetPointUsagesByModelType(ctx context.Context, modelType string, limit, offset int) ([]*models.PointUsage, error)
	GetPointUsagesByUserIDAndModelType(ctx context.Context, userID, modelType string, limit, offset int) ([]*models.PointUsage, error)
	GetPointUsagesByDateRange(ctx context.Context, startDate, endDate time.Time, limit, offset int) ([]*models.PointUsage, error)
	GetTotalPointsConsumedByUser(ctx context.Context, userID string) (int, error)
	GetPointUsageStatistics(ctx context.Context) (map[string]interface{}, error)
	RecordPointUsage(ctx context.Context, userID, content string, amountConsumed int, modelType, modelName string) error
}
