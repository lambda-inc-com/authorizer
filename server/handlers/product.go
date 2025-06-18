package handlers

import (
	"context"
	"net/http"
	"strconv"
	"time"

	"github.com/authorizerdev/authorizer/server/db"
	"github.com/authorizerdev/authorizer/server/db/models"
	"github.com/gin-gonic/gin"
	"github.com/shopspring/decimal"
)

// 初始化商品数据到数据库
func InitProducts() error {
	ctx := context.Background()

	// 检查是否已经初始化过
	products, err := db.Provider.ListProducts(ctx, 10, 0)
	if err == nil && len(products) > 0 {
		return nil // 已经有数据，不需要重复初始化
	}

	// 初始化A、B商品
	initialProducts := []*models.Product{
		{
			ID:                "a",
			Name:              "A商品",
			Points:            4000,
			PricingMonthly:    decimal.NewFromFloat(39.9),  // 按月支付
			PricingYearly:     decimal.NewFromFloat(399.0), // 按年支付(相当于月费打8.3折)
			PricingContinuous: decimal.NewFromFloat(35.9),  // 连续续订月费(9折优惠)
			Type:              "subscription",
			Description:       "A商品支持多种支付方式",
			Image:             "",
			CreatedAt:         time.Now(),
			UpdatedAt:         time.Now(),
		},
		{
			ID:                "b",
			Name:              "B商品",
			Points:            6000,
			PricingMonthly:    decimal.NewFromFloat(59.9),  // 按月支付
			PricingYearly:     decimal.NewFromFloat(599.0), // 按年支付(相当于月费打8.3折)
			PricingContinuous: decimal.NewFromFloat(53.9),  // 连续续订月费(9折优惠)
			Type:              "subscription",
			Description:       "B商品支持多种支付方式",
			Image:             "",
			CreatedAt:         time.Now(),
			UpdatedAt:         time.Now(),
		},
	}

	for _, product := range initialProducts {
		_, err := db.Provider.AddProduct(ctx, product)
		if err != nil {
			return err
		}
	}

	return nil
}

func ListProducts(c *gin.Context) {
	ctx := context.Background()

	// 获取分页参数
	limitStr := c.DefaultQuery("limit", "10")
	offsetStr := c.DefaultQuery("offset", "0")

	limit, _ := strconv.Atoi(limitStr)
	offset, _ := strconv.Atoi(offsetStr)

	products, err := db.Provider.ListProducts(ctx, limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取商品列表失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"products": products})
}

func GetProductByID(id string) (*models.Product, error) {
	ctx := context.Background()
	return db.Provider.GetProductByID(ctx, id)
}

// GetProductPrice 获取商品在指定支付方式下的价格
func GetProductPrice(c *gin.Context) {
	productID := c.Param("product_id")
	paymentType := c.Query("payment_type") // monthly, yearly, continuous

	if paymentType == "" {
		paymentType = "monthly" // 默认按月
	}

	ctx := context.Background()
	product, err := db.Provider.GetProductByID(ctx, productID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "商品不存在"})
		return
	}

	price := product.GetPrice(paymentType)

	c.JSON(http.StatusOK, gin.H{
		"product_id":   productID,
		"payment_type": paymentType,
		"price":        price,
		"product":      product,
	})
}

// CalculatePriceDemo 价格计算演示接口
func CalculatePriceDemo(c *gin.Context) {
	ctx := context.Background()

	products, err := db.Provider.ListProducts(ctx, 100, 0)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取商品列表失败"})
		return
	}

	// 演示所有商品的不同支付方式价格
	result := gin.H{
		"message":  "商品价格计算演示",
		"products": []gin.H{},
	}

	paymentTypes := []string{"monthly", "yearly", "continuous"}

	for _, product := range products {
		productInfo := gin.H{
			"id":      product.ID,
			"name":    product.Name,
			"points":  product.Points,
			"pricing": gin.H{},
		}

		pricing := product.GetPricing()
		for _, paymentType := range paymentTypes {
			price := pricing[paymentType]
			productInfo["pricing"].(gin.H)[paymentType] = gin.H{
				"price":       price,
				"description": getPaymentTypeDescription(paymentType),
			}
		}

		result["products"] = append(result["products"].([]gin.H), productInfo)
	}

	c.JSON(http.StatusOK, result)
}

// getPaymentTypeDescription 获取支付方式描述
func getPaymentTypeDescription(paymentType string) string {
	switch paymentType {
	case "monthly":
		return "按月支付，标准价格"
	case "yearly":
		return "按年支付，相当于月费打8.3折"
	case "continuous":
		return "连续续订，月费9折优惠，自动续费"
	default:
		return "未知支付方式"
	}
}
