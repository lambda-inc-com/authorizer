package routes

import (
	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"

	"github.com/authorizerdev/authorizer/server/handlers"
	"github.com/authorizerdev/authorizer/server/middlewares"
)

// InitRouter initializes gin router
func InitRouter(log *logrus.Logger) *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	router := gin.New()

	router.Use(middlewares.Logger(log), gin.Recovery())
	router.Use(middlewares.GinContextToContextMiddleware())
	router.Use(middlewares.CORSMiddleware())
	router.Use(middlewares.ClientCheckMiddleware())

	router.GET("/", handlers.RootHandler())
	router.GET("/health", handlers.HealthHandler())
	router.POST("/graphql", handlers.GraphqlHandler())
	router.GET("/playground", handlers.PlaygroundHandler())
	router.GET("/oauth_login/:oauth_provider", handlers.OAuthLoginHandler())
	router.GET("/oauth_callback/:oauth_provider", handlers.OAuthCallbackHandler())
	router.POST("/oauth_callback/:oauth_provider", handlers.OAuthCallbackHandler())
	router.GET("/verify_email", handlers.VerifyEmailHandler())
	// OPEN ID routes
	router.GET("/.well-known/openid-configuration", handlers.OpenIDConfigurationHandler())
	router.GET("/.well-known/jwks.json", handlers.JWKsHandler())
	router.GET("/authorize", handlers.AuthorizeHandler())
	router.GET("/userinfo", handlers.UserInfoHandler())
	router.GET("/logout", handlers.LogoutHandler())
	router.POST("/oauth/token", handlers.TokenHandler())
	router.POST("/oauth/revoke", handlers.RevokeRefreshTokenHandler())

	router.LoadHTMLGlob("/templates/*")
	// login page app related routes.
	app := router.Group("/app")
	{
		app.Static("/favicon_io", "/app/favicon_io")
		app.Static("/build", "/app/build")
		app.GET("/", handlers.AppHandler())
		app.GET("/:page", handlers.AppHandler())
	}

	// dashboard related routes
	dashboard := router.Group("/dashboard")
	{
		dashboard.Static("/favicon_io", "/dashboard/favicon_io")
		dashboard.Static("/build", "/dashboard/build")
		dashboard.Static("/public", "/dashboard/public")
		dashboard.GET("/", handlers.DashboardHandler())
		dashboard.GET("/:page", handlers.DashboardHandler())
	}

	// 商品、订单、支付接口
	productGroup := router.Group("/products")
	productGroup.Use(middlewares.AuthMiddleware())
	{
		productGroup.GET("/", handlers.ListProducts)
		productGroup.GET("/:product_id/price", handlers.GetProductPrice)
		productGroup.GET("/demo/pricing", handlers.CalculatePriceDemo)
	}

	orderGroup := router.Group("/orders")
	orderGroup.Use(middlewares.AuthMiddleware())
	{
		orderGroup.POST("/", handlers.CreateOrder)
		orderGroup.GET("/", handlers.ListOrders)
	}

	paymentGroup := router.Group("/payments")
	paymentGroup.Use(middlewares.AuthMiddleware())
	{
		paymentGroup.POST("/:order_id", handlers.PayOrder)
	}

	// 订阅状态相关路由
	subscriptionGroup := router.Group("/subscription")
	subscriptionGroup.Use(middlewares.AuthMiddleware())
	{
		subscriptionGroup.GET("/status", handlers.GetUserSubscriptionHandler())
	}

	// 积分相关路由
	pointsGroup := router.Group("/points")
	pointsGroup.Use(middlewares.AuthMiddleware())
	{
		pointsGroup.GET("/me", handlers.GetUserPoints)
		pointsGroup.POST("/consume", handlers.ConsumePoints)
		pointsGroup.GET("/usage-log", handlers.ListPointUsage)
		pointsGroup.GET("/status", handlers.GetPointsStatusHandler())
		pointsGroup.GET("/recharge-recommendation", handlers.RechargeRecommendationHandler())
	}

	// LLM 相关路由
	llm := router.Group("/llm")
	{
		llm.GET("/demo", handlers.LLMDemoHandler())
		llm.GET("/providers", handlers.LLMProvidersHandler())
		llm.GET("/models", handlers.LLMModelsHandler())
		llm.GET("/available-models", handlers.GetAvailableModelsHandler())

		// 需要认证的接口
		llm.Use(middlewares.AuthMiddleware())
		llm.POST("/chat", handlers.ChatHandler())
		llm.POST("/calculate-tokens", handlers.CalculateTokensHandler())

		// 用户LLM配置接口
		llm.POST("/user-configs", handlers.AddUserLLMConfigHandler())
		llm.GET("/user-configs", handlers.GetUserLLMConfigsHandler())
		llm.PUT("/user-configs/:config_id", handlers.UpdateUserLLMConfigHandler())
		llm.DELETE("/user-configs/:config_id", handlers.DeleteUserLLMConfigHandler())
		llm.POST("/user-configs/:config_id/set-default", handlers.SetDefaultUserLLMConfigHandler())
	}

	// 打印所有注册的路由
	log.Info("=== 注册的路由列表 ===")
	routes := router.Routes()
	for _, route := range routes {
		log.Infof("%-8s %s", route.Method, route.Path)
	}
	log.Infof("总共注册了 %d 个路由", len(routes))
	log.Info("=== 路由列表结束 ===")

	return router
}
