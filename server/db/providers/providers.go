package providers

import (
	"context"
	"time"

	"github.com/authorizerdev/authorizer/server/db/models"
	"github.com/authorizerdev/authorizer/server/graph/model"
	"github.com/shopspring/decimal"
)

type Provider interface {
	// AddUser to save user information in database
	AddUser(ctx context.Context, user *models.User) (*models.User, error)
	// UpdateUser to update user information in database
	UpdateUser(ctx context.Context, user *models.User) (*models.User, error)
	// DeleteUser to delete user information from database
	DeleteUser(ctx context.Context, user *models.User) error
	// ListUsers to get list of users from database
	ListUsers(ctx context.Context, pagination *model.Pagination) (*model.Users, error)
	// GetUserByEmail to get user information from database using email address
	GetUserByEmail(ctx context.Context, email string) (*models.User, error)
	// GetUserByPhoneNumber to get user information from database using phone number
	GetUserByPhoneNumber(ctx context.Context, phoneNumber string) (*models.User, error)
	// GetUserByID to get user information from database using user ID
	GetUserByID(ctx context.Context, id string) (*models.User, error)
	// UpdateUsers to update multiple users, with parameters of user IDs slice
	// If ids set to nil / empty all the users will be updated
	UpdateUsers(ctx context.Context, data map[string]interface{}, ids []string) error

	// AddVerificationRequest to save verification request in database
	AddVerificationRequest(ctx context.Context, verificationRequest *models.VerificationRequest) (*models.VerificationRequest, error)
	// GetVerificationRequestByToken to get verification request from database using token
	GetVerificationRequestByToken(ctx context.Context, token string) (*models.VerificationRequest, error)
	// GetVerificationRequestByEmail to get verification request by email from database
	GetVerificationRequestByEmail(ctx context.Context, email string, identifier string) (*models.VerificationRequest, error)
	// ListVerificationRequests to get list of verification requests from database
	ListVerificationRequests(ctx context.Context, pagination *model.Pagination) (*model.VerificationRequests, error)
	// DeleteVerificationRequest to delete verification request from database
	DeleteVerificationRequest(ctx context.Context, verificationRequest *models.VerificationRequest) error

	// AddSession to save session information in database
	AddSession(ctx context.Context, session *models.Session) error
	// DeleteSession to delete session information from database
	DeleteSession(ctx context.Context, userId string) error

	// AddEnv to save environment information in database
	AddEnv(ctx context.Context, env *models.Env) (*models.Env, error)
	// UpdateEnv to update environment information in database
	UpdateEnv(ctx context.Context, env *models.Env) (*models.Env, error)
	// GetEnv to get environment information from database
	GetEnv(ctx context.Context) (*models.Env, error)

	// AddWebhook to add webhook
	AddWebhook(ctx context.Context, webhook *models.Webhook) (*model.Webhook, error)
	// UpdateWebhook to update webhook
	UpdateWebhook(ctx context.Context, webhook *models.Webhook) (*model.Webhook, error)
	// ListWebhook to list webhook
	ListWebhook(ctx context.Context, pagination *model.Pagination) (*model.Webhooks, error)
	// GetWebhookByID to get webhook by id
	GetWebhookByID(ctx context.Context, webhookID string) (*model.Webhook, error)
	// GetWebhookByEventName to get webhook by event_name
	GetWebhookByEventName(ctx context.Context, eventName string) ([]*model.Webhook, error)
	// DeleteWebhook to delete webhook
	DeleteWebhook(ctx context.Context, webhook *model.Webhook) error

	// AddWebhookLog to add webhook log
	AddWebhookLog(ctx context.Context, webhookLog *models.WebhookLog) (*model.WebhookLog, error)
	// ListWebhookLogs to list webhook logs
	ListWebhookLogs(ctx context.Context, pagination *model.Pagination, webhookID string) (*model.WebhookLogs, error)

	// AddEmailTemplate to add EmailTemplate
	AddEmailTemplate(ctx context.Context, emailTemplate *models.EmailTemplate) (*model.EmailTemplate, error)
	// UpdateEmailTemplate to update EmailTemplate
	UpdateEmailTemplate(ctx context.Context, emailTemplate *models.EmailTemplate) (*model.EmailTemplate, error)
	// ListEmailTemplate to list EmailTemplate
	ListEmailTemplate(ctx context.Context, pagination *model.Pagination) (*model.EmailTemplates, error)
	// GetEmailTemplateByID to get EmailTemplate by id
	GetEmailTemplateByID(ctx context.Context, emailTemplateID string) (*model.EmailTemplate, error)
	// GetEmailTemplateByEventName to get EmailTemplate by event_name
	GetEmailTemplateByEventName(ctx context.Context, eventName string) (*model.EmailTemplate, error)
	// DeleteEmailTemplate to delete EmailTemplate
	DeleteEmailTemplate(ctx context.Context, emailTemplate *model.EmailTemplate) error

	// UpsertOTP to add or update otp
	UpsertOTP(ctx context.Context, otp *models.OTP) (*models.OTP, error)
	// GetOTPByEmail to get otp for a given email address
	GetOTPByEmail(ctx context.Context, emailAddress string) (*models.OTP, error)
	// GetOTPByPhoneNumber to get otp for a given phone number
	GetOTPByPhoneNumber(ctx context.Context, phoneNumber string) (*models.OTP, error)
	// DeleteOTP to delete otp
	DeleteOTP(ctx context.Context, otp *models.OTP) error

	// AddAuthenticator adds a new authenticator document to the database.
	// If the authenticator doesn't have an ID, a new one is generated.
	// The created document is returned, or an error if the operation fails.
	AddAuthenticator(ctx context.Context, totp *models.Authenticator) (*models.Authenticator, error)
	// UpdateAuthenticator updates an existing authenticator document in the database.
	// The updated document is returned, or an error if the operation fails.
	UpdateAuthenticator(ctx context.Context, totp *models.Authenticator) (*models.Authenticator, error)
	// GetAuthenticatorDetailsByUserId retrieves details of an authenticator document based on user ID and authenticator type.
	// If found, the authenticator document is returned, or an error if not found or an error occurs during the retrieval.
	GetAuthenticatorDetailsByUserId(ctx context.Context, userId string, authenticatorType string) (*models.Authenticator, error)

	// Product operations
	AddProduct(ctx context.Context, product *models.Product) (*models.Product, error)
	UpdateProduct(ctx context.Context, product *models.Product) (*models.Product, error)
	DeleteProduct(ctx context.Context, productID string) error
	GetProductByID(ctx context.Context, id string) (*models.Product, error)
	ListProducts(ctx context.Context, limit, offset int) ([]*models.Product, error)
	GetProductsByType(ctx context.Context, productType string) ([]*models.Product, error)
	GetProductPrice(ctx context.Context, productID, paymentType string) (decimal.Decimal, error)

	// Order operations
	AddOrder(ctx context.Context, order *models.Order) (*models.Order, error)
	UpdateOrder(ctx context.Context, order *models.Order) (*models.Order, error)
	DeleteOrder(ctx context.Context, orderID string) error
	GetOrderByID(ctx context.Context, id string) (*models.Order, error)
	GetOrdersByUserID(ctx context.Context, userID string, limit, offset int) ([]*models.Order, error)
	GetOrdersByStatus(ctx context.Context, status string, limit, offset int) ([]*models.Order, error)
	GetOrdersByUserIDAndStatus(ctx context.Context, userID, status string, limit, offset int) ([]*models.Order, error)
	UpdateOrderStatus(ctx context.Context, orderID, status string) error
	GetExpiredOrders(ctx context.Context) ([]*models.Order, error)

	// Payment operations
	AddPayment(ctx context.Context, payment *models.Payment) (*models.Payment, error)
	UpdatePayment(ctx context.Context, payment *models.Payment) (*models.Payment, error)
	DeletePayment(ctx context.Context, paymentID string) error
	GetPaymentByID(ctx context.Context, id string) (*models.Payment, error)
	GetPaymentByOrderID(ctx context.Context, orderID string) (*models.Payment, error)
	GetPaymentsByUserID(ctx context.Context, userID string, limit, offset int) ([]*models.Payment, error)
	GetPaymentsByStatus(ctx context.Context, status string, limit, offset int) ([]*models.Payment, error)
	GetPaymentsByUserIDAndStatus(ctx context.Context, userID, status string, limit, offset int) ([]*models.Payment, error)
	UpdatePaymentStatus(ctx context.Context, paymentID, status string) error
	GetPaymentsByDateRange(ctx context.Context, startDate, endDate time.Time, limit, offset int) ([]*models.Payment, error)
	GetTotalPaymentAmount(ctx context.Context, userID string) (decimal.Decimal, error)
	GetExpiredPayments(ctx context.Context) ([]*models.Payment, error)

	// UserPoints operations
	AddUserPoints(ctx context.Context, userPoints *models.UserPoints) (*models.UserPoints, error)
	UpdateUserPoints(ctx context.Context, userPoints *models.UserPoints) (*models.UserPoints, error)
	DeleteUserPoints(ctx context.Context, userID string) error
	GetUserPointsByUserID(ctx context.Context, userID string) (*models.UserPoints, error)
	GetOrCreateUserPoints(ctx context.Context, userID string) (*models.UserPoints, error)
	AddPointsToUser(ctx context.Context, userID string, points int) (*models.UserPoints, error)
	ConsumeUserPoints(ctx context.Context, userID string, points int) (*models.UserPoints, error)
	GetTopUsersByPoints(ctx context.Context, limit int) ([]*models.UserPoints, error)
	GetUserPointsStatistics(ctx context.Context) (map[string]interface{}, error)

	// PointUsage operations
	AddPointUsage(ctx context.Context, pointUsage *models.PointUsage) (*models.PointUsage, error)
	UpdatePointUsage(ctx context.Context, pointUsage *models.PointUsage) (*models.PointUsage, error)
	DeletePointUsage(ctx context.Context, usageID string) error
	GetPointUsageByID(ctx context.Context, id string) (*models.PointUsage, error)
	GetPointUsagesByUserID(ctx context.Context, userID string, limit, offset int) ([]*models.PointUsage, error)
	GetPointUsagesByModelType(ctx context.Context, modelType string, limit, offset int) ([]*models.PointUsage, error)
	GetPointUsagesByUserIDAndModelType(ctx context.Context, userID, modelType string, limit, offset int) ([]*models.PointUsage, error)
	GetPointUsagesByDateRange(ctx context.Context, startDate, endDate time.Time, limit, offset int) ([]*models.PointUsage, error)
	GetTotalPointsConsumedByUser(ctx context.Context, userID string) (int, error)
	GetPointUsageStatistics(ctx context.Context) (map[string]interface{}, error)
	RecordPointUsage(ctx context.Context, userID, content string, amountConsumed int, modelType, modelName string) error
}
