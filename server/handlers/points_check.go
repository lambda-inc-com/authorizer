package handlers

import (
	"net/http"

	"github.com/authorizerdev/authorizer/server/db"
	"github.com/gin-gonic/gin"
	log "github.com/sirupsen/logrus"
)

// GetPointsStatusHandler 获取积分状态和充值提醒
func GetPointsStatusHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		userID := c.GetString("user_id")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Unauthorized",
			})
			return
		}

		userPoints, err := db.Provider.GetUserPointsByUserID(c.Request.Context(), userID)
		if err != nil {
			log.Errorf("Failed to get user points: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to get points status",
			})
			return
		}

		status := "sufficient"
		message := ""
		needRecharge := false

		if userPoints.Points <= 0 {
			status = "insufficient"
			message = "积分已用完，请充值后继续使用"
			needRecharge = true
		} else if userPoints.Points <= 100 {
			status = "low"
			message = "积分余额较低，建议充值"
			needRecharge = true
		} else if userPoints.Points <= 1000 {
			status = "medium"
			message = "积分余额中等，使用前会进行预计算检查"
		} else {
			status = "high"
			message = "积分余额充足，可直接使用服务"
		}

		c.JSON(http.StatusOK, gin.H{
			"points":        userPoints.Points,
			"status":        status,
			"message":       message,
			"need_recharge": needRecharge,
			"threshold_info": gin.H{
				"high_threshold": 1000,
				"low_threshold":  100,
				"description":    "积分>1000时直接放行，<=1000时进行预计算检查",
			},
		})
	})
}

// RechargeRecommendationHandler 充值建议API
func RechargeRecommendationHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		userID := c.GetString("user_id")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Unauthorized",
			})
			return
		}

		userPoints, err := db.Provider.GetUserPointsByUserID(c.Request.Context(), userID)
		if err != nil {
			log.Errorf("Failed to get user points: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to get points status",
			})
			return
		}

		// 充值建议
		recommendations := []gin.H{}

		if userPoints.Points <= 100 {
			recommendations = append(recommendations, gin.H{
				"amount":      2000,
				"description": "基础充值包",
				"reason":      "推荐充值2000积分，可使用约200次对话",
			})
		}

		if userPoints.Points <= 500 {
			recommendations = append(recommendations, gin.H{
				"amount":      5000,
				"description": "标准充值包",
				"reason":      "推荐充值5000积分，可使用约500次对话",
			})
		}

		recommendations = append(recommendations, gin.H{
			"amount":      10000,
			"description": "高级充值包",
			"reason":      "推荐充值10000积分，可使用约1000次对话，享受直接放行服务",
		})

		c.JSON(http.StatusOK, gin.H{
			"current_points":  userPoints.Points,
			"recommendations": recommendations,
			"usage_estimate":  "平均每次对话消耗约10积分",
			"recharge_products": gin.H{
				"message": "您也可以购买B/C商品享受不限积分的订阅服务",
				"products": []gin.H{
					{
						"id":   "b",
						"name": "B商品 - 系统服务版",
						"desc": "月费制，无需积分，直接使用",
					},
					{
						"id":   "c",
						"name": "C商品 - 高级服务版",
						"desc": "月费制，无需积分，包含更多功能",
					},
				},
			},
		})
	})
}
