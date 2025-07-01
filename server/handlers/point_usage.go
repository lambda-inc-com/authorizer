package handlers

import (
	"context"
	"net/http"
	"strconv"

	"github.com/authorizerdev/authorizer/server/db"
	"github.com/gin-gonic/gin"
)

// ConsumePoints 模拟消耗积分的接口
func ConsumePoints(c *gin.Context) {
	userID := c.GetString("user_id")

	var req struct {
		AmountConsumed int    `json:"amount_consumed"`
		Content        string `json:"content"`
		ModelType      string `json:"model_type"`
		ModelName      string `json:"model_name"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}

	if req.AmountConsumed <= 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "消耗积分数量必须大于0"})
		return
	}

	ctx := context.Background()

	// 使用事务性积分消耗操作
	err := db.Provider.RecordPointUsage(ctx, userID, req.Content, req.AmountConsumed, req.ModelType, req.ModelName)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "积分不足或操作失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "积分消耗成功"})
}

// ListPointUsage 查询用户的积分使用日志
func ListPointUsage(c *gin.Context) {
	userID := c.GetString("user_id")
	ctx := context.Background()

	// 获取分页参数
	limitStr := c.DefaultQuery("limit", "10")
	offsetStr := c.DefaultQuery("offset", "0")

	limit, _ := strconv.Atoi(limitStr)
	offset, _ := strconv.Atoi(offsetStr)

	usages, err := db.Provider.GetPointUsagesByUserID(ctx, userID, limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取积分使用记录失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"usage_log": usages})
}
