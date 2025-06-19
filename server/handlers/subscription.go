package handlers

import (
	"net/http"

	"github.com/authorizerdev/authorizer/server/services"
	"github.com/gin-gonic/gin"
	log "github.com/sirupsen/logrus"
)

// GetUserSubscriptionHandler 获取用户订阅状态
func GetUserSubscriptionHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		userID := c.GetString("user_id")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Unauthorized",
			})
			return
		}

		subscriptionService := services.NewSubscriptionService()
		subscription, err := subscriptionService.CheckUserSubscription(c.Request.Context(), userID)
		if err != nil {
			log.Errorf("Failed to check user subscription: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to check subscription status",
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"subscription": subscription,
		})
	})
}
