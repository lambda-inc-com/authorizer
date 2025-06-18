package handlers

import (
	"context"
	"net/http"
	"strconv"
	"time"

	"github.com/authorizerdev/authorizer/server/db"
	"github.com/authorizerdev/authorizer/server/db/models"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

func CreateOrder(c *gin.Context) {
	userID := c.GetString("user_id")
	var req struct {
		ProductID   string `json:"product_id"`
		PaymentType string `json:"payment_type"` // monthly, yearly, continuous
		AutoRenew   bool   `json:"auto_renew"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}

	// 验证支付方式
	if req.PaymentType == "" {
		req.PaymentType = "monthly" // 默认按月
	}
	if req.PaymentType != "monthly" && req.PaymentType != "yearly" && req.PaymentType != "continuous" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "支付方式必须是: monthly, yearly, continuous"})
		return
	}

	ctx := context.Background()
	product, err := db.Provider.GetProductByID(ctx, req.ProductID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "商品不存在"})
		return
	}

	// 根据商品和支付方式计算最终价格
	amount := product.GetPrice(req.PaymentType)

	// 设置订阅周期
	payCycle := "month"
	if req.PaymentType == "yearly" {
		payCycle = "year"
	}

	var subFrom, subTo time.Time
	if product.Type == "subscription" {
		now := time.Now()
		subFrom = now
		switch req.PaymentType {
		case "monthly", "continuous":
			subTo = now.AddDate(0, 1, 0) // 1个月后
		case "yearly":
			subTo = now.AddDate(1, 0, 0) // 1年后
		}
	}

	order := &models.Order{
		ID:            uuid.NewString(),
		UserID:        userID,
		ProductID:     product.ID,
		Points:        product.Points,
		Amount:        amount,
		Status:        "pending",
		PaymentType:   req.PaymentType,
		PayCycle:      payCycle,
		SubscribeFrom: subFrom,
		SubscribeTo:   subTo,
		AutoRenew:     req.AutoRenew || req.PaymentType == "continuous", // 连续续订自动开启自动续费
		CreatedAt:     time.Now(),
		UpdatedAt:     time.Now(),
	}

	// 保存订单到数据库
	savedOrder, err := db.Provider.AddOrder(ctx, order)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建订单失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"order":   savedOrder,
		"message": "订单创建成功",
		"pricing_info": gin.H{
			"product_name": product.Name,
			"payment_type": req.PaymentType,
			"final_price":  amount,
			"points":       product.Points,
		},
	})
}

func ListOrders(c *gin.Context) {
	userID := c.GetString("user_id")
	ctx := context.Background()

	// 获取分页参数
	limitStr := c.DefaultQuery("limit", "10")
	offsetStr := c.DefaultQuery("offset", "0")

	limit, _ := strconv.Atoi(limitStr)
	offset, _ := strconv.Atoi(offsetStr)

	orders, err := db.Provider.GetOrdersByUserID(ctx, userID, limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取订单列表失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"orders": orders})
}
