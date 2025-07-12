package services

import (
	"context"
	"errors"
	"fmt"
	"io"
	"sync"
	"time"

	"github.com/authorizerdev/authorizer/server/proto"
	log "github.com/sirupsen/logrus"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/status"
)

// AIGRPCClient AI gRPC客户端
type AIGRPCClient struct {
	conn            *grpc.ClientConn
	client          proto.AIStreamServiceClient
	address         string
	mu              sync.RWMutex
	lastHealthCheck time.Time
}

// NewAIGRPCClient 创建AI gRPC客户端
func NewAIGRPCClient(address string) (*AIGRPCClient, error) {
	client := &AIGRPCClient{
		address: address,
	}

	err := client.connect()
	if err != nil {
		return nil, err
	}

	// 启动连接健康检查
	go client.healthCheckLoop()

	return client, nil
}

// connect 建立gRPC连接
func (c *AIGRPCClient) connect() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	// 配置gRPC连接选项 - 针对线上环境优化
	opts := []grpc.DialOption{
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithKeepaliveParams(keepalive.ClientParameters{
			Time:                10 * time.Second, // 减少到10秒发送一次keepalive
			Timeout:             3 * time.Second,  // 3秒keepalive超时
			PermitWithoutStream: true,             // 允许没有流时发送keepalive
		}),
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(100*1024*1024), // 100MB接收限制
			grpc.MaxCallSendMsgSize(100*1024*1024), // 100MB发送限制
		),
		// 添加连接状态监控
		grpc.WithConnectParams(grpc.ConnectParams{
			MinConnectTimeout: 5 * time.Second,
		}),
	}

	// 建立gRPC连接
	conn, err := grpc.Dial(c.address, opts...)
	if err != nil {
		return fmt.Errorf("连接AI gRPC服务失败: %w", err)
	}

	// 等待连接就绪
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	for {
		state := conn.GetState()
		if state == connectivity.Ready {
			break
		}
		if state == connectivity.TransientFailure || state == connectivity.Shutdown {
			conn.Close()
			return fmt.Errorf("连接失败，状态: %v", state)
		}
		if !conn.WaitForStateChange(ctx, state) {
			conn.Close()
			return fmt.Errorf("连接超时")
		}
	}

	c.conn = conn
	c.client = proto.NewAIStreamServiceClient(conn)
	c.lastHealthCheck = time.Now()

	log.Infof("成功连接到AI gRPC服务: %s", c.address)
	return nil
}

// healthCheckLoop 健康检查循环
func (c *AIGRPCClient) healthCheckLoop() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		if err := c.HealthCheck(context.Background()); err != nil {
			log.Warnf("gRPC健康检查失败: %v，尝试重连", err)
			if err := c.reconnect(); err != nil {
				log.Errorf("gRPC重连失败: %v", err)
			}
		}
	}
}

// reconnect 重新连接
func (c *AIGRPCClient) reconnect() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.conn != nil {
		c.conn.Close()
	}

	return c.connect()
}

// Close 关闭连接
func (c *AIGRPCClient) Close() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

// StreamChatResponse 流式聊天响应结构
type StreamChatResponse struct {
	Content        string `json:"content"`
	IsComplete     bool   `json:"is_complete"`
	ModelUsed      string `json:"model_used"`
	TokensUsed     int32  `json:"tokens_used"`
	PointsConsumed int32  `json:"points_consumed"`
	FinishReason   string `json:"finish_reason"`
	Error          string `json:"error,omitempty"`
}

// StreamWorkflowResponse 流式工作流响应结构
type StreamWorkflowResponse struct {
	WorkflowID   string            `json:"workflow_id"`
	Status       string            `json:"status"`
	CurrentStep  string            `json:"current_step"`
	StepOutput   string            `json:"step_output"`
	Progress     float32           `json:"progress"`
	IsComplete   bool              `json:"is_complete"`
	FinalOutputs map[string]string `json:"final_outputs,omitempty"`
	Error        string            `json:"error,omitempty"`
}

// StreamChat 流式聊天
func (c *AIGRPCClient) StreamChat(ctx context.Context, userID, modelName string, messages []map[string]string, responseChan chan<- *StreamChatResponse) error {
	return c.streamChatWithRetry(ctx, userID, modelName, messages, responseChan, 3)
}

// streamChatWithRetry 带重试的流式聊天
func (c *AIGRPCClient) streamChatWithRetry(ctx context.Context, userID, modelName string, messages []map[string]string, responseChan chan<- *StreamChatResponse, maxRetries int) error {
	var lastErr error

	for retry := 0; retry <= maxRetries; retry++ {
		if retry > 0 {
			log.Warnf("流式聊天重试第 %d 次", retry)
			// 重试前等待
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(time.Duration(retry) * time.Second):
			}
		}

		err := c.doStreamChat(ctx, userID, modelName, messages, responseChan)
		if err == nil {
			return nil
		}

		lastErr = err

		// 检查是否是可重试的错误
		if !isRetryableError(err) {
			break
		}

		// 检查连接状态并尝试重连
		if c.shouldReconnect(err) {
			if reconnectErr := c.reconnect(); reconnectErr != nil {
				log.Errorf("重连失败: %v", reconnectErr)
			}
		}
	}

	return fmt.Errorf("流式聊天失败，已重试 %d 次: %w", maxRetries, lastErr)
}

// doStreamChat 执行流式聊天
func (c *AIGRPCClient) doStreamChat(ctx context.Context, userID, modelName string, messages []map[string]string, responseChan chan<- *StreamChatResponse) error {
	// 构建请求
	var protoMessages []*proto.StreamChatMessage
	for _, msg := range messages {
		protoMessages = append(protoMessages, &proto.StreamChatMessage{
			Role:    msg["role"],
			Content: msg["content"],
		})
	}

	request := &proto.StreamChatRequest{
		ModelName:  modelName,
		UserId:     userID,
		Messages:   protoMessages,
		Parameters: map[string]string{},
	}

	// 发起流式调用
	c.mu.RLock()
	client := c.client
	c.mu.RUnlock()

	stream, err := client.StreamChat(ctx, request)
	if err != nil {
		return fmt.Errorf("启动流式聊天失败: %w", err)
	}

	// 处理流式响应
	go func() {
		defer close(responseChan)

		for {
			response, err := stream.Recv()
			if err == io.EOF {
				log.Debug("流式聊天完成")
				break
			}
			if err != nil {
				log.Errorf("接收流式聊天响应失败: %v", err)
				// 发送错误响应
				responseChan <- &StreamChatResponse{
					Error:      err.Error(),
					IsComplete: true,
				}
				break
			}

			// 转换响应格式并发送
			streamResponse := &StreamChatResponse{
				Content:        response.Content,
				IsComplete:     response.IsComplete,
				ModelUsed:      response.ModelUsed,
				TokensUsed:     response.TokensUsed,
				PointsConsumed: response.PointsConsumed,
				FinishReason:   response.FinishReason,
				Error:          response.Error,
			}

			responseChan <- streamResponse

			// 如果完成，退出循环
			if response.IsComplete {
				break
			}
		}
	}()

	return nil
}

// StreamWorkflowGenerate 流式工作流生成
func (c *AIGRPCClient) StreamWorkflowGenerate(ctx context.Context, userID string, inputs map[string]string, responseChan chan<- *StreamWorkflowResponse) error {
	return c.streamWorkflowGenerateWithRetry(ctx, userID, inputs, responseChan, 3)
}

// streamWorkflowGenerateWithRetry 带重试的流式工作流生成
func (c *AIGRPCClient) streamWorkflowGenerateWithRetry(ctx context.Context, userID string, inputs map[string]string, responseChan chan<- *StreamWorkflowResponse, maxRetries int) error {
	var lastErr error

	for retry := 0; retry <= maxRetries; retry++ {
		if retry > 0 {
			log.Warnf("流式工作流生成重试第 %d 次", retry)
			// 重试前等待
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(time.Duration(retry) * time.Second):
			}
		}

		err := c.doStreamWorkflowGenerate(ctx, userID, inputs, responseChan)
		if err == nil {
			return nil
		}

		lastErr = err

		// 检查是否是可重试的错误
		if !isRetryableError(err) {
			break
		}

		// 检查连接状态并尝试重连
		if c.shouldReconnect(err) {
			if reconnectErr := c.reconnect(); reconnectErr != nil {
				log.Errorf("重连失败: %v", reconnectErr)
			}
		}
	}

	return fmt.Errorf("流式工作流生成失败，已重试 %d 次: %w", maxRetries, lastErr)
}

// doStreamWorkflowGenerate 执行流式工作流生成
func (c *AIGRPCClient) doStreamWorkflowGenerate(ctx context.Context, userID string, inputs map[string]string, responseChan chan<- *StreamWorkflowResponse) error {
	// 构建请求
	request := &proto.StreamWorkflowRequest{
		WorkflowName: "generate_workflow",
		UserId:       userID,
		Inputs:       inputs,
		Config:       map[string]string{},
	}

	// 发起流式调用
	c.mu.RLock()
	client := c.client
	c.mu.RUnlock()

	stream, err := client.StreamWorkflowGenerate(ctx, request)
	if err != nil {
		return fmt.Errorf("启动流式工作流生成失败: %w", err)
	}

	// 处理流式响应
	go func() {
		defer close(responseChan)

		for {
			response, err := stream.Recv()
			if err == io.EOF {
				log.Debug("流式工作流生成完成")
				break
			}
			if err != nil {
				log.Errorf("接收流式工作流生成响应失败: %v", err)
				// 发送错误响应
				responseChan <- &StreamWorkflowResponse{
					Error:      err.Error(),
					IsComplete: true,
				}
				break
			}

			// 转换响应格式并发送
			streamResponse := &StreamWorkflowResponse{
				WorkflowID:   response.WorkflowId,
				Status:       response.Status,
				CurrentStep:  response.CurrentStep,
				StepOutput:   response.StepOutput,
				Progress:     response.Progress,
				IsComplete:   response.IsComplete,
				FinalOutputs: response.FinalOutputs,
				Error:        response.Error,
			}

			responseChan <- streamResponse

			// 如果完成，退出循环
			if response.IsComplete {
				break
			}
		}
	}()

	return nil
}

// HealthCheck 健康检查
func (c *AIGRPCClient) HealthCheck(ctx context.Context) error {
	// 设置超时
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	c.mu.RLock()
	defer c.mu.RUnlock()

	if c.conn == nil {
		return fmt.Errorf("连接未初始化")
	}

	// 检查连接状态
	state := c.conn.GetState()
	if state == connectivity.Ready || state == connectivity.Idle {
		c.lastHealthCheck = time.Now()
		return nil
	}

	return fmt.Errorf("AI gRPC服务连接状态异常: %s", state.String())
}

// isRetryableError 判断是否是可重试的错误
func isRetryableError(err error) bool {
	if err == nil {
		return false
	}

	// 检查 gRPC 状态码
	if st, ok := status.FromError(err); ok {
		switch st.Code() {
		case codes.DeadlineExceeded, codes.Unavailable, codes.ResourceExhausted, codes.Aborted, codes.Canceled:
			return true
		}
	}

	// 检查连接相关错误
	if errors.Is(err, context.DeadlineExceeded) || errors.Is(err, context.Canceled) {
		return true
	}

	return false
}

// shouldReconnect 判断是否应该重新连接
func (c *AIGRPCClient) shouldReconnect(err error) bool {
	if err == nil {
		return false
	}

	// 检查 gRPC 状态码
	if st, ok := status.FromError(err); ok {
		switch st.Code() {
		case codes.Unavailable, codes.DeadlineExceeded, codes.Canceled:
			return true
		}
	}

	// 检查连接状态
	c.mu.RLock()
	defer c.mu.RUnlock()

	if c.conn != nil {
		state := c.conn.GetState()
		if state == connectivity.TransientFailure || state == connectivity.Shutdown {
			return true
		}
	}

	return false
}
