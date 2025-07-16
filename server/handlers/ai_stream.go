package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/authorizerdev/authorizer/server/db"
	"github.com/authorizerdev/authorizer/server/db/models"
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
	Requirement string                 `json:"requirement" binding:"required"`
	Config      map[string]interface{} `json:"config,omitempty"`
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

		ctx := c.Request.Context()

		// 创建订阅服务
		subscriptionService := services.NewSubscriptionService()

		// 检查用户订阅状态
		subscription, err := subscriptionService.CheckUserSubscription(ctx, userID)
		if err != nil {
			log.Errorf("Failed to check user subscription for user %s: %v", userID, err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to check subscription status",
			})
			return
		}

		// 检查是否有有效订阅
		if !subscription.HasValidSubscription {
			c.JSON(http.StatusForbidden, gin.H{
				"error": "无有效订阅，请先购买订阅服务后再使用",
			})
			return
		}

		// 检查积分情况
		userPoints, err := db.Provider.GetUserPointsByUserID(ctx, userID)
		if err != nil {
			log.Errorf("Failed to get user points for user %s: %v", userID, err)
			userPoints = &models.UserPoints{Points: 0}
		}

		// 决策逻辑：
		// 1. A商品：必须使用用户API key，不消耗积分
		// 2. B、C商品：有积分时使用系统API key并扣积分，无积分时使用用户API key
		// 3. 如果需要用户API key但用户没有配置，则提示购买积分

		needConsumePoints := false
		useUserAPIKey := false
		var reason string

		if subscription.RequiresUserAPIKey {
			// A商品：必须使用用户API key，不消耗积分
			useUserAPIKey = true
			needConsumePoints = false
			reason = fmt.Sprintf("购买了%s，需要配置自己的API密钥", subscription.ProductName)
		} else {
			// B、C商品：根据积分情况决定
			if userPoints.Points > 0 {
				// 有积分时，使用系统API key并扣积分
				useUserAPIKey = false
				needConsumePoints = true
				reason = fmt.Sprintf("购买了%s且有积分，使用系统服务并扣积分", subscription.ProductName)
			} else {
				// 无积分时，必须使用用户API key
				useUserAPIKey = true
				needConsumePoints = false
				reason = fmt.Sprintf("购买了%s但无积分，需要使用自己的API密钥", subscription.ProductName)
			}
		}

		// 如果需要使用用户API key，检查用户是否有配置
		if useUserAPIKey {
			userConfigs, err := db.Provider.GetUserLLMConfigsByUserID(ctx, userID)
			if err != nil {
				log.Errorf("Failed to get user LLM configs for user %s: %v", userID, err)
				c.JSON(http.StatusInternalServerError, gin.H{
					"error": "Failed to get user API key configurations",
				})
				return
			}

			// 检查是否有对应模型的配置
			var hasModelConfig bool
			for _, uc := range userConfigs {
				if uc.ModelName == request.Model && uc.IsEnabled {
					hasModelConfig = true
					break
				}
			}

			if !hasModelConfig {
				c.JSON(http.StatusPaymentRequired, gin.H{
					"error":       fmt.Sprintf("%s，但您尚未配置%s模型的API密钥。请配置API密钥或购买积分后再试", reason, request.Model),
					"need_config": true,
					"model":       request.Model,
				})
				return
			}
		}

		log.Infof("User %s streaming chat decision: %s", userID, reason)

		// 如果需要消耗积分，进行预检查
		if needConsumePoints {
			// 如果积分 <= 1000，需要预计算检查
			if userPoints.Points <= 1000 {
				// 简单估算：假设每条消息消耗约10积分
				estimatedPoints := len(request.Messages) * 10
				if userPoints.Points < estimatedPoints {
					c.JSON(http.StatusPaymentRequired, gin.H{
						"error": fmt.Sprintf("积分不足：预计需要 %d 积分，当前剩余 %d 积分。请充值后再试", estimatedPoints, userPoints.Points),
					})
					return
				}
				log.Infof("User %s has %d points, estimated cost %d points, proceeding with streaming request", userID, userPoints.Points, estimatedPoints)
			} else {
				log.Infof("User %s has %d points (>1000), skipping pre-calculation", userID, userPoints.Points)
			}
		}

		// 设置SSE头
		c.Header("Content-Type", "text/event-stream")
		c.Header("Cache-Control", "no-cache")
		c.Header("Connection", "keep-alive")
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Headers", "Cache-Control")

		// 🎯 添加更多防缓冲头
		c.Header("X-Accel-Buffering", "no")      // 防止nginx缓冲
		c.Header("Transfer-Encoding", "chunked") // 使用chunked编码
		c.Writer.WriteHeaderNow()                // 立即发送头部

		// 🎯 立即发送一个初始事件以建立连接
		flusher := c.Writer.(http.Flusher)
		c.Writer.WriteString(": connected\n\n") // SSE注释，不会被客户端处理但建立连接
		flusher.Flush()

		// 创建响应通道
		responseChan := make(chan *services.StreamChatResponse)

		// 启动gRPC流式调用
		streamCtx, cancel := context.WithTimeout(ctx, 10*time.Minute)
		defer cancel()

		err = h.grpcClient.StreamChat(streamCtx, userID, request.Model, request.Messages, responseChan)
		if err != nil {
			log.Errorf("启动流式聊天失败: %v", err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to start streaming chat",
			})
			return
		}

		// 流式发送响应
		var totalTokensUsed int32 = 0
		var totalPointsConsumed int32 = 0

		for response := range responseChan {
			// 累计token和积分使用
			totalTokensUsed += response.TokensUsed
			totalPointsConsumed += response.PointsConsumed

			// 将响应转换为JSON
			jsonData, err := json.Marshal(response)
			if err != nil {
				log.Errorf("序列化响应失败: %v", err)
				continue
			}

			// 发送SSE事件
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(jsonData)))
			flusher.Flush()

			// 如果完成或出错，进行积分扣除
			if response.IsComplete || response.Error != "" {
				// 如果需要消耗积分，进行实际扣除
				if needConsumePoints {
					actualPoints := int(totalPointsConsumed)
					if actualPoints == 0 {
						// 如果没有返回积分消耗，使用token数量估算
						actualPoints = int(totalTokensUsed)
						if actualPoints == 0 {
							actualPoints = 10 // 默认消耗10积分，避免0消耗
						}
					}

					// 获取最新的用户积分（可能在请求期间有变化）
					latestUserPoints, err := db.Provider.GetUserPointsByUserID(ctx, userID)
					if err != nil {
						log.Errorf("Failed to get user points for consumption for user %s: %v", userID, err)
						break // 聊天成功，但积分获取失败，直接结束
					}

					// 检查积分是否足够扣除
					if latestUserPoints.Points < actualPoints {
						log.Errorf("User %s insufficient points for actual consumption: need %d, have %d", userID, actualPoints, latestUserPoints.Points)
						// 积分不足，扣除所有剩余积分并记录使用日志
						if latestUserPoints.Points > 0 {
							content := fmt.Sprintf("AI流式聊天对话 - %s (积分不足，扣除剩余积分)", request.Model)
							err = db.Provider.RecordPointUsage(ctx, userID, content, latestUserPoints.Points, "ai_stream", request.Model)
							if err != nil {
								log.Errorf("Failed to record remaining points usage for user %s: %v", userID, err)
							} else {
								log.Infof("Recorded usage and consumed all remaining %d points for user %s", latestUserPoints.Points, userID)
							}
						}
					} else {
						// 消耗实际积分并记录使用日志
						content := fmt.Sprintf("AI流式聊天对话 - %s", request.Model)
						err = db.Provider.RecordPointUsage(ctx, userID, content, actualPoints, "ai_stream", request.Model)
						if err != nil {
							log.Errorf("Failed to record %d points usage for user %s: %v", actualPoints, userID, err)
						} else {
							log.Infof("Successfully recorded usage and consumed %d points for user %s", actualPoints, userID)
						}
					}
				}
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

		// 先读取原始请求体
		body, err := c.GetRawData()
		if err != nil {
			log.Errorf("读取请求体失败，用户ID: %s，错误: %v", userID, err)
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Failed to read request body",
			})
			return
		}

		var request StreamWorkflowRequest
		if err := json.Unmarshal(body, &request); err != nil {
			log.Errorf("JSON解析失败，用户ID: %s，错误: %v", userID, err)
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid request format: " + err.Error(),
			})
			return
		}

		// 验证必填字段
		if request.Requirement == "" {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "requirement field is required",
			})
			return
		}

		ctx := c.Request.Context()

		// 创建订阅服务
		subscriptionService := services.NewSubscriptionService()

		// 检查用户订阅状态
		subscription, err := subscriptionService.CheckUserSubscription(ctx, userID)
		if err != nil {
			log.Errorf("Failed to check user subscription for user %s: %v", userID, err)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to check subscription status",
			})
			return
		}

		// 检查是否有有效订阅
		if !subscription.HasValidSubscription {
			c.JSON(http.StatusForbidden, gin.H{
				"error": "无有效订阅，请先购买订阅服务后再使用",
			})
			return
		}

		// 检查积分情况
		userPoints, err := db.Provider.GetUserPointsByUserID(ctx, userID)
		if err != nil {
			log.Errorf("Failed to get user points for user %s: %v", userID, err)
			userPoints = &models.UserPoints{Points: 0}
		}

		// 决策逻辑：
		// 1. A商品：必须使用用户API key，不消耗积分
		// 2. B、C商品：有积分时使用系统API key并扣积分，无积分时使用用户API key
		// 3. 如果需要用户API key但用户没有配置，则提示购买积分

		needConsumePoints := false
		useUserAPIKey := false
		var reason string

		if subscription.RequiresUserAPIKey {
			// A商品：必须使用用户API key，不消耗积分
			useUserAPIKey = true
			needConsumePoints = false
			reason = fmt.Sprintf("购买了%s，需要配置自己的API密钥", subscription.ProductName)
		} else {
			// B、C商品：根据积分情况决定
			if userPoints.Points > 0 {
				// 有积分时，使用系统API key并扣积分
				useUserAPIKey = false
				needConsumePoints = true
				reason = fmt.Sprintf("购买了%s且有积分，使用系统服务并扣积分", subscription.ProductName)
			} else {
				// 无积分时，必须使用用户API key
				useUserAPIKey = true
				needConsumePoints = false
				reason = fmt.Sprintf("购买了%s但无积分，需要使用自己的API密钥", subscription.ProductName)
			}
		}

		// 如果需要使用用户API key，检查用户是否有配置
		if useUserAPIKey {
			userConfigs, err := db.Provider.GetUserLLMConfigsByUserID(ctx, userID)
			if err != nil {
				log.Errorf("Failed to get user LLM configs for user %s: %v", userID, err)
				c.JSON(http.StatusInternalServerError, gin.H{
					"error": "Failed to get user API key configurations",
				})
				return
			}

			// 对于工作流生成，我们需要检查是否有任何可用的模型配置
			var hasAnyConfig bool
			for _, uc := range userConfigs {
				if uc.IsEnabled {
					hasAnyConfig = true
					break
				}
			}

			if !hasAnyConfig {
				c.JSON(http.StatusPaymentRequired, gin.H{
					"error":       fmt.Sprintf("%s，但您尚未配置任何LLM模型的API密钥。请配置API密钥或购买积分后再试", reason),
					"need_config": true,
				})
				return
			}
		}

		log.Infof("User %s workflow generation decision: %s", userID, reason)

		// 如果需要消耗积分，进行预检查
		if needConsumePoints {
			// 工作流生成通常消耗较多积分，预估100积分
			estimatedPoints := 100
			if userPoints.Points <= 1000 && userPoints.Points < estimatedPoints {
				c.JSON(http.StatusPaymentRequired, gin.H{
					"error": fmt.Sprintf("积分不足：工作流生成预计需要 %d 积分，当前剩余 %d 积分。请充值后再试", estimatedPoints, userPoints.Points),
				})
				return
			}
			log.Infof("User %s has %d points, estimated cost %d points, proceeding with workflow generation", userID, userPoints.Points, estimatedPoints)
		}

		// 设置SSE头
		c.Header("Content-Type", "text/event-stream")
		c.Header("Cache-Control", "no-cache")
		c.Header("Connection", "keep-alive")
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Headers", "Cache-Control")

		// 🎯 添加更多防缓冲头
		c.Header("X-Accel-Buffering", "no")      // 防止nginx缓冲
		c.Header("Transfer-Encoding", "chunked") // 使用chunked编码
		c.Writer.WriteHeaderNow()                // 立即发送头部

		// 🎯 立即发送一个初始事件以建立连接
		flusher := c.Writer.(http.Flusher)
		c.Writer.WriteString(": connected\n\n") // SSE注释，不会被客户端处理但建立连接
		flusher.Flush()

		// 创建响应通道
		responseChan := make(chan *services.StreamWorkflowResponse)

		// 构建输入参数
		inputs := map[string]string{
			"requirement": request.Requirement,
		}
		for k, v := range request.Config {
			// 安全的类型转换：将 interface{} 转换为 string
			if str, ok := v.(string); ok {
				inputs[k] = str
			} else {
				// 如果不是 string 类型，使用 fmt.Sprintf 转换
				inputs[k] = fmt.Sprintf("%v", v)
			}
		}

		// 启动gRPC流式调用 - 增加超时时间以适应线上环境和复杂工作流生成
		streamCtx, cancel := context.WithTimeout(ctx, 30*time.Minute)
		defer cancel()

		err = h.grpcClient.StreamWorkflowGenerate(streamCtx, userID, inputs, responseChan)
		if err != nil {
			log.Errorf("启动流式工作流生成失败: %v", err)

			// 发送错误信息到客户端
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n",
				`{"error":"工作流生成服务暂时不可用，请稍后重试","is_complete":true,"workflow_id":""}`))
			c.Writer.(http.Flusher).Flush()
			return
		}

		// 流式发送响应
		var totalOutputLength int

		for response := range responseChan {
			// 累计输出内容长度（用于估算token消耗）
			totalOutputLength += len(response.StepOutput)

			// 将响应转换为JSON
			jsonData, err := json.Marshal(response)
			if err != nil {
				log.Errorf("序列化响应失败: %v", err)
				continue
			}

			// 发送SSE事件
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(jsonData)))
			flusher.Flush()

			// 如果完成或出错，进行积分扣除
			if response.IsComplete || response.Error != "" {
				// 如果需要消耗积分，进行实际扣除
				if needConsumePoints {
					// 根据实际内容长度估算token消耗
					// 估算规则：输入需求长度 + 输出内容长度，每4个字符约等于1个token
					inputLength := len(request.Requirement)
					totalLength := inputLength + totalOutputLength
					estimatedTokens := totalLength / 4
					if estimatedTokens < 10 {
						estimatedTokens = 10 // 最少10个token
					}

					// 积分消耗 = token数量 * 2 (这里可以根据实际情况调整倍数)
					actualPoints := estimatedTokens * 2

					if response.Error != "" {
						// 如果出错，减半扣除积分
						actualPoints = actualPoints / 2
					}

					// 获取最新的用户积分（可能在请求期间有变化）
					latestUserPoints, err := db.Provider.GetUserPointsByUserID(ctx, userID)
					if err != nil {
						log.Errorf("Failed to get user points for consumption for user %s: %v", userID, err)
						break // 工作流生成成功，但积分获取失败，直接结束
					}

					// 检查积分是否足够扣除
					if latestUserPoints.Points < actualPoints {
						log.Errorf("User %s insufficient points for actual consumption: need %d, have %d", userID, actualPoints, latestUserPoints.Points)
						// 积分不足，扣除所有剩余积分并记录使用日志
						if latestUserPoints.Points > 0 {
							content := fmt.Sprintf("AI流式工作流生成 - %s (积分不足，扣除剩余积分)", request.Requirement)
							err = db.Provider.RecordPointUsage(ctx, userID, content, latestUserPoints.Points, "ai_workflow", "workflow_generation")
							if err != nil {
								log.Errorf("Failed to record remaining points usage for user %s: %v", userID, err)
							} else {
								log.Infof("Recorded usage and consumed all remaining %d points for user %s", latestUserPoints.Points, userID)
							}
						}
					} else {
						// 消耗实际积分并记录使用日志
						content := fmt.Sprintf("AI流式工作流生成 - %s (估算%d tokens)", request.Requirement, estimatedTokens)
						err = db.Provider.RecordPointUsage(ctx, userID, content, actualPoints, "ai_workflow", "workflow_generation")
						if err != nil {
							log.Errorf("Failed to record %d points usage for user %s: %v", actualPoints, userID, err)
						} else {
							log.Infof("Successfully recorded usage and consumed %d points for user %s (estimated %d tokens)", actualPoints, userID, estimatedTokens)
						}
					}
				}
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
		ctx := c.Request.Context()

		// 检查gRPC连接
		err := h.grpcClient.HealthCheck(ctx)
		if err != nil {
			log.Errorf("AI gRPC服务健康检查失败: %v", err)
			c.JSON(http.StatusServiceUnavailable, gin.H{
				"status":  "unhealthy",
				"message": "AI gRPC服务不可用",
				"error":   err.Error(),
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"status":    "healthy",
			"message":   "AI流式服务正常运行",
			"timestamp": time.Now().Format(time.RFC3339),
			"services": gin.H{
				"grpc": "connected",
				"streaming": gin.H{
					"chat":              "/ai/stream/chat",
					"workflow_generate": "/ai/stream/workflow/generate",
				},
			},
		})
	})
}
