package handlers

import (
	"context"
	"net/http"
	"time"

	"github.com/authorizerdev/authorizer/server/db"
	"github.com/authorizerdev/authorizer/server/db/models"
	"github.com/authorizerdev/authorizer/server/services"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

func PayOrder(c *gin.Context) {
	userID := c.GetString("user_id")
	orderID := c.Param("order_id")
	ctx := context.Background()

	// 从数据库获取订单
	order, err := db.Provider.GetOrderByID(ctx, orderID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "订单不存在"})
		return
	}

	// 验证订单属于当前用户
	if order.UserID != userID {
		c.JSON(http.StatusForbidden, gin.H{"error": "无权限访问此订单"})
		return
	}

	if order.Status != "pending" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "订单状态不可支付"})
		return
	}

	// mock支付逻辑
	order.Status = "paid"
	order.UpdatedAt = time.Now()

	payType := "onetime"
	var payExpired time.Time

	// 根据支付方式设置支付类型和到期时间
	switch order.PaymentType {
	case "monthly":
		payType = "subscription_month"
		payExpired = time.Now().AddDate(0, 1, 0)
	case "yearly":
		payType = "subscription_year"
		payExpired = time.Now().AddDate(1, 0, 0)
	case "continuous":
		payType = "subscription_continuous"
		payExpired = time.Now().AddDate(0, 1, 0) // 连续续订按月计费
	default:
		payType = "onetime"
	}

	payment := &models.Payment{
		ID:        uuid.NewString(),
		OrderID:   order.ID,
		UserID:    userID,
		Amount:    order.Amount,
		Type:      payType,
		Channel:   "mock",
		Status:    "success",
		PaidAt:    time.Now(),
		ExpiredAt: payExpired,
		CreatedAt: time.Now(),
	}

	// 保存支付记录
	savedPayment, err := db.Provider.AddPayment(ctx, payment)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "支付记录保存失败"})
		return
	}

	// 连续续订或自动续费：自动延长到期时间
	if order.AutoRenew || order.PaymentType == "continuous" {
		order.SubscribeTo = payExpired
	}

	// 更新订单状态
	_, err = db.Provider.UpdateOrder(ctx, order)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "订单状态更新失败"})
		return
	}

	// 积分到账逻辑
	if order.Points > 0 {
		_, err = db.Provider.AddPointsToUser(ctx, userID, order.Points)
		if err != nil {
			// 积分添加失败不影响支付成功，只记录日志
			// 可以考虑后续补偿机制
		}
	}

	c.JSON(http.StatusOK, gin.H{"payment": savedPayment})
}

func GetUserPoints(c *gin.Context) {
	userID := c.GetString("user_id")
	ctx := context.Background()

	// 获取用户积分
	userPoints, err := db.Provider.GetOrCreateUserPoints(ctx, userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取用户积分失败"})
		return
	}

	// 获取用户订阅信息
	subscriptionService := services.NewSubscriptionService()
	subscription, err := subscriptionService.CheckUserSubscription(ctx, userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取用户订阅信息失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"user_points":  userPoints,
		"subscription": subscription,
	})
}
