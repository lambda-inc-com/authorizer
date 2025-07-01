package sql

import (
	"context"
	"time"

	"github.com/authorizerdev/authorizer/server/db/models"
	"github.com/google/uuid"
	"github.com/shopspring/decimal"
)

// AddProduct 添加商品
func (p *provider) AddProduct(ctx context.Context, product *models.Product) (*models.Product, error) {
	if product.ID == "" {
		product.ID = uuid.New().String()
	}

	product.CreatedAt = time.Now()
	product.UpdatedAt = time.Now()

	result := p.db.Create(&product)
	if result.Error != nil {
		return product, result.Error
	}

	return product, nil
}

// UpdateProduct 更新商品
func (p *provider) UpdateProduct(ctx context.Context, product *models.Product) (*models.Product, error) {
	product.UpdatedAt = time.Now()

	result := p.db.Save(&product)
	if result.Error != nil {
		return product, result.Error
	}

	return product, nil
}

// DeleteProduct 删除商品
func (p *provider) DeleteProduct(ctx context.Context, productID string) error {
	result := p.db.Where("id = ?", productID).Delete(&models.Product{})
	if result.Error != nil {
		return result.Error
	}

	return nil
}

// GetProductByID 根据ID获取商品
func (p *provider) GetProductByID(ctx context.Context, id string) (*models.Product, error) {
	var product *models.Product
	result := p.db.Where("id = ?", id).First(&product)
	if result.Error != nil {
		return nil, result.Error
	}

	return product, nil
}

// ListProducts 获取商品列表
func (p *provider) ListProducts(ctx context.Context, limit, offset int) ([]*models.Product, error) {
	var products []*models.Product
	result := p.db.Limit(limit).Offset(offset).Order("created_at DESC").Find(&products)
	if result.Error != nil {
		return nil, result.Error
	}

	return products, nil
}

// GetProductsByType 根据类型获取商品列表
func (p *provider) GetProductsByType(ctx context.Context, productType string) ([]*models.Product, error) {
	var products []*models.Product
	result := p.db.Where("type = ?", productType).Order("created_at DESC").Find(&products)
	if result.Error != nil {
		return nil, result.Error
	}

	return products, nil
}

// GetProductPrice 获取商品指定支付方式的价格
func (p *provider) GetProductPrice(ctx context.Context, productID, paymentType string) (decimal.Decimal, error) {
	product, err := p.GetProductByID(ctx, productID)
	if err != nil {
		return decimal.Zero, err
	}

	return product.GetPrice(paymentType), nil
}
