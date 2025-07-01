package models

import (
	"encoding/json"
	"strings"

	"github.com/authorizerdev/authorizer/server/graph/model"
	"github.com/authorizerdev/authorizer/server/refs"
)

// Note: any change here should be reflected in providers/casandra/provider.go as it does not have model support in collection creation

// User model for db
type User struct {
	Key string `json:"_key,omitempty" bson:"_key,omitempty" cql:"_key,omitempty" dynamo:"key,omitempty"` // for arangodb
	ID  string `gorm:"primaryKey;type:char(36)" json:"_id" bson:"_id" cql:"id" dynamo:"id,hash"`

	Email                    *string `gorm:"index" json:"email" bson:"email" cql:"email" dynamo:"email" index:"email,hash"`
	EmailVerifiedAt          *int64  `json:"email_verified_at" bson:"email_verified_at" cql:"email_verified_at" dynamo:"email_verified_at"`
	Password                 *string `json:"password" bson:"password" cql:"password" dynamo:"password"`
	SignupMethods            string  `json:"signup_methods" bson:"signup_methods" cql:"signup_methods" dynamo:"signup_methods"`
	GivenName                *string `json:"given_name" bson:"given_name" cql:"given_name" dynamo:"given_name"`
	FamilyName               *string `json:"family_name" bson:"family_name" cql:"family_name" dynamo:"family_name"`
	MiddleName               *string `json:"middle_name" bson:"middle_name" cql:"middle_name" dynamo:"middle_name"`
	Nickname                 *string `json:"nickname" bson:"nickname" cql:"nickname" dynamo:"nickname"`
	Gender                   *string `json:"gender" bson:"gender" cql:"gender" dynamo:"gender"`
	Birthdate                *string `json:"birthdate" bson:"birthdate" cql:"birthdate" dynamo:"birthdate"`
	PhoneNumber              *string `gorm:"index" json:"phone_number" bson:"phone_number" cql:"phone_number" dynamo:"phone_number"`
	PhoneNumberVerifiedAt    *int64  `json:"phone_number_verified_at" bson:"phone_number_verified_at" cql:"phone_number_verified_at" dynamo:"phone_number_verified_at"`
	Picture                  *string `json:"picture" bson:"picture" cql:"picture" dynamo:"picture"`
	Roles                    string  `json:"roles" bson:"roles" cql:"roles" dynamo:"roles"`
	RevokedTimestamp         *int64  `json:"revoked_timestamp" bson:"revoked_timestamp" cql:"revoked_timestamp" dynamo:"revoked_timestamp"`
	IsMultiFactorAuthEnabled *bool   `json:"is_multi_factor_auth_enabled" bson:"is_multi_factor_auth_enabled" cql:"is_multi_factor_auth_enabled" dynamo:"is_multi_factor_auth_enabled"`
	UpdatedAt                int64   `json:"updated_at" bson:"updated_at" cql:"updated_at" dynamo:"updated_at"`
	CreatedAt                int64   `json:"created_at" bson:"created_at" cql:"created_at" dynamo:"created_at"`
	AppData                  *string `json:"app_data" bson:"app_data" cql:"app_data" dynamo:"app_data"`
}

type OneAPIUser struct {
	ID           int64   `gorm:"column:id;primaryKey;autoIncrement" json:"id"` // bigserial 主键
	UserId       string  `json:"user_id" gorm:"column:user_id;type:varchar(64);default:'default'"`
	Username     string  `gorm:"column:username;type:text;uniqueIndex" json:"username"`             // 唯一用户名
	Password     string  `gorm:"column:password;type:text;not null" json:"password"`                // 非空密码
	DisplayName  *string `gorm:"column:display_name;type:text" json:"display_name"`                 // 可空显示名
	Role         int64   `gorm:"column:role;type:bigint;default:1" json:"role"`                     // 角色，默认1
	Status       int64   `gorm:"column:status;type:bigint;default:1" json:"status"`                 // 状态，默认1
	Email        *string `gorm:"column:email;type:text;index" json:"email"`                         // 可空邮箱（带索引）
	GithubID     *string `gorm:"column:github_id;type:text;index" json:"github_id"`                 // GitHub ID（带索引）
	WechatID     *string `gorm:"column:wechat_id;type:text;index" json:"wechat_id"`                 // 微信ID（带索引）
	LarkID       *string `gorm:"column:lark_id;type:text;index" json:"lark_id"`                     // 飞书ID（带索引）
	OIDCID       *string `gorm:"column:oidc_id;type:text;index" json:"oidc_id"`                     // OIDC ID（带索引）
	AccessToken  *string `gorm:"column:access_token;type:char(32);uniqueIndex" json:"access_token"` // 唯一访问令牌
	Quota        int64   `gorm:"column:quota;type:bigint;default:0" json:"quota"`                   // 配额，默认0
	UsedQuota    int64   `gorm:"column:used_quota;type:bigint;default:0" json:"used_quota"`         // 已用配额，默认0
	RequestCount int64   `gorm:"column:request_count;type:bigint;default:0" json:"request_count"`   // 请求计数，默认0
	Group        string  `gorm:"column:group;type:varchar(32);default:'default'" json:"group"`      // 分组，默认'default'
	AffCode      *string `gorm:"column:aff_code;type:varchar(32);uniqueIndex" json:"aff_code"`      // 邀请码（唯一）
	InviterID    *int64  `gorm:"column:inviter_id;type:bigint;index" json:"inviter_id"`             // 邀请人ID（带索引）
}

func (OneAPIUser) TableName() string {
	return "users" //
}

func (user *User) AsAPIUser() *model.User {
	isEmailVerified := user.EmailVerifiedAt != nil
	isPhoneVerified := user.PhoneNumberVerifiedAt != nil
	appDataMap := make(map[string]interface{})
	json.Unmarshal([]byte(refs.StringValue(user.AppData)), &appDataMap)
	// id := user.ID
	// if strings.Contains(id, Collections.User+"/") {
	// 	id = strings.TrimPrefix(id, Collections.User+"/")
	// }
	return &model.User{
		ID:                       user.ID,
		Email:                    user.Email,
		EmailVerified:            isEmailVerified,
		SignupMethods:            user.SignupMethods,
		GivenName:                user.GivenName,
		FamilyName:               user.FamilyName,
		MiddleName:               user.MiddleName,
		Nickname:                 user.Nickname,
		PreferredUsername:        user.Email,
		Gender:                   user.Gender,
		Birthdate:                user.Birthdate,
		PhoneNumber:              user.PhoneNumber,
		PhoneNumberVerified:      &isPhoneVerified,
		Picture:                  user.Picture,
		Roles:                    strings.Split(user.Roles, ","),
		RevokedTimestamp:         user.RevokedTimestamp,
		IsMultiFactorAuthEnabled: user.IsMultiFactorAuthEnabled,
		CreatedAt:                refs.NewInt64Ref(user.CreatedAt),
		UpdatedAt:                refs.NewInt64Ref(user.UpdatedAt),
		AppData:                  appDataMap,
	}
}

func (user *User) ToMap() map[string]interface{} {
	res := map[string]interface{}{}
	data, _ := json.Marshal(user) // Convert to a json string
	json.Unmarshal(data, &res)    // Convert to a map
	return res
}
