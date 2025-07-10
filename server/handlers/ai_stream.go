package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/authorizerdev/authorizer/server/services"
	"github.com/gin-gonic/gin"
	log "github.com/sirupsen/logrus"
)

// AIStreamHandler AI流式处理器
type AIStreamHandler struct {
	grpcClient *services.AIGRPCClient
}

// NewAIStreamHandler 创建AI流式处理器
func NewAIStreamHandler(grpcClient *services.AIGRPCClient) *AIStreamHandler {
	return &AIStreamHandler{
		grpcClient: grpcClient,
	}
}

// StreamChatRequest 流式聊天请求
type StreamChatRequest struct {
	Model       string              `json:"model" binding:"required"`
	Messages    []map[string]string `json:"messages" binding:"required"`
	Temperature float64             `json:"temperature,omitempty"`
	MaxTokens   int                 `json:"max_tokens,omitempty"`
}

// StreamWorkflowRequest 流式工作流请求
type StreamWorkflowRequest struct {
	Requirement string            `json:"requirement" binding:"required"`
	Config      map[string]string `json:"config,omitempty"`
}

// StreamChatHandler 流式聊天接口
func (h *AIStreamHandler) StreamChatHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		// 验证用户身份
		userID := c.GetString("user_id")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Unauthorized",
			})
			return
		}

		var request StreamChatRequest
		if err := c.ShouldBindJSON(&request); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request format: " + err.Error(),
			})
			return
		}

		// 设置SSE头
		c.Header("Content-Type", "text/event-stream")
		c.Header("Cache-Control", "no-cache")
		c.Header("Connection", "keep-alive")
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Headers", "Cache-Control")

		// 创建响应通道
		responseChan := make(chan *services.StreamChatResponse)

		// 启动gRPC流式调用
		ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Minute)
		defer cancel()

		err := h.grpcClient.StreamChat(ctx, userID, request.Model, request.Messages, responseChan)
		if err != nil {
			log.Errorf("启动流式聊天失败: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to start streaming chat",
			})
			return
		}

		// 流式发送响应
		flusher := c.Writer.(http.Flusher)

		for response := range responseChan {
			// 将响应转换为JSON
			jsonData, err := json.Marshal(response)
			if err != nil {
				log.Errorf("序列化响应失败: %v", err)
				continue
			}

			// 发送SSE事件
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(jsonData)))
			flusher.Flush()

			// 如果完成或出错，退出
			if response.IsComplete || response.Error != "" {
				break
			}
		}
	})
}

// StreamWorkflowGenerateHandler 流式工作流生成接口
func (h *AIStreamHandler) StreamWorkflowGenerateHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		// 验证用户身份
		userID := c.GetString("user_id")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Unauthorized",
			})
			return
		}

		var request StreamWorkflowRequest
		if err := c.ShouldBindJSON(&request); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request format: " + err.Error(),
			})
			return
		}

		// 设置SSE头
		c.Header("Content-Type", "text/event-stream")
		c.Header("Cache-Control", "no-cache")
		c.Header("Connection", "keep-alive")
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Headers", "Cache-Control")

		// 创建响应通道
		responseChan := make(chan *services.StreamWorkflowResponse)

		// 构建输入参数
		inputs := map[string]string{
			"requirement": request.Requirement,
		}
		for k, v := range request.Config {
			inputs[k] = v
		}

		// 启动gRPC流式调用
		ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Minute)
		defer cancel()

		err := h.grpcClient.StreamWorkflowGenerate(ctx, userID, inputs, responseChan)
		if err != nil {
			log.Errorf("启动流式工作流生成失败: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to start streaming workflow generation",
			})
			return
		}

		// 流式发送响应
		flusher := c.Writer.(http.Flusher)

		for response := range responseChan {
			// 将响应转换为JSON
			jsonData, err := json.Marshal(response)
			if err != nil {
				log.Errorf("序列化响应失败: %v", err)
				continue
			}

			// 发送SSE事件
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(jsonData)))
			flusher.Flush()

			// 如果完成或出错，退出
			if response.IsComplete || response.Error != "" {
				break
			}
		}
	})
}

// WebSocketChatHandler WebSocket流式聊天（可选实现）
func (h *AIStreamHandler) WebSocketChatHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		// WebSocket实现...
		// 这里可以使用gorilla/websocket等库实现WebSocket版本
		c.JSON(http.StatusNotImplemented, gin.H{
			"message": "WebSocket chat not implemented yet",
		})
	})
}

// HealthCheckHandler 健康检查
func (h *AIStreamHandler) HealthCheckHandler() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
		defer cancel()

		err := h.grpcClient.HealthCheck(ctx)
		if err != nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{
				"status": "unhealthy",
				"error":  err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"status": "healthy",
		})
	})
}
