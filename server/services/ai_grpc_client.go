package services

import (
	"context"
	"fmt"
	"io"
	"time"

	"github.com/authorizerdev/authorizer/server/proto"
	log "github.com/sirupsen/logrus"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// AIGRPCClient AI gRPC客户端
type AIGRPCClient struct {
	conn   *grpc.ClientConn
	client proto.AIStreamServiceClient
}

// NewAIGRPCClient 创建AI gRPC客户端
func NewAIGRPCClient(address string) (*AIGRPCClient, error) {
	// 建立gRPC连接
	conn, err := grpc.Dial(address, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, fmt.Errorf("连接AI gRPC服务失败: %w", err)
	}

	client := proto.NewAIStreamServiceClient(conn)

	return &AIGRPCClient{
		conn:   conn,
		client: client,
	}, nil
}

// Close 关闭连接
func (c *AIGRPCClient) Close() error {
	return c.conn.Close()
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
	stream, err := c.client.StreamChat(ctx, request)
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
	// 构建请求
	request := &proto.StreamWorkflowRequest{
		WorkflowName: "generate_workflow",
		UserId:       userID,
		Inputs:       inputs,
		Config:       map[string]string{},
	}

	// 发起流式调用
	stream, err := c.client.StreamWorkflowGenerate(ctx, request)
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
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	// 简单的连接测试
	// 这里可以实现一个专门的健康检查RPC
	// 暂时使用连接状态检查
	state := c.conn.GetState()
	if state.String() == "READY" || state.String() == "IDLE" {
		return nil
	}

	return fmt.Errorf("AI gRPC服务连接状态异常: %s", state.String())
}
