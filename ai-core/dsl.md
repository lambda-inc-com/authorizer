# 工作流结构
```json
{
  "name": "工作流名称",
  "desc": "工作流描述",
  "version": "1.0.0",
  "nodes": [
    {
      "name": "节点名称",
      "type": "节点类型",
      "desc": "节点描述",
      "inputs": {},
      "outputs": {},
      "configs": {},
      "nextNodes": []
    }
  ]
}
```

## 节点基本结构
每个节点都必须包含以下基本字段：

```json
{
  "name": "节点名称",
  "type": "节点类型", 
  "desc": "节点功能描述",
  "inputs": {},
  "outputs": {},
  "configs": {},
  "nextNodes": []
}
```

## 字段说明

### name *(必填)*
- 节点的唯一标识符
- 必须在整个工作流中唯一
- 使用PascalCase命名，如: "GetUserData", "SendEmail"
- 名称应具有描述性，能够表达节点的主要功能

### type *(必填)*
- 节点类型，决定节点的执行逻辑
- 可选值: "workflowStart", "workflowEnd", "dbQuery", "dbCreate", "dbUpdate", "dbDelete", "transaction", "batch", "http", "llm", "condition", "code", "workflow"
- 必须与具体节点的类型完全匹配

### desc *(可选)*
- 节点功能的详细描述
- 应该清楚说明节点做什么，处理什么数据
- 有助于理解工作流的业务逻辑

### inputs *(可选)*
输入参数定义，格式为键值对对象：
```json
{
  "参数名": {
    "type": "数据类型",
    "value": "数据来源引用",
    "desc": "参数描述"
  }
}
```

**数据类型**: string, number, boolean, object, array
**inputs中允许的数据来源**: 
- `$.节点名.outputs.字段名` - 引用指定节点输出
- 直接字符串值 - 静态数据
- **禁止**: 循环引用自身或形成引用环

### outputs *(必填)*
输出参数定义，定义节点执行后产生的数据：

**内置节点 outputs**：
以下节点类型有固定的输出结构，由系统自动生成，用户只需定义type和desc字段，不需要设置value字段：
- **HTTP节点**: 返回 code、data、message 字段
- **LLM节点**: 返回 thinking、response、tokens 字段  
- **数据库操作节点**: dbQuery返回affected、data；dbCreate返回affected、insertId；dbUpdate/dbDelete返回affected
- **Transaction节点**: 返回 committed、affectedTotal、childResults、executionTime 字段
- **Condition节点**: 无outputs字段

```json
{
  "code": {
    "type": "number",
    "desc": "HTTP状态码"
  },
  "data": {
    "type": "object", 
    "desc": "响应数据"
  }
}
```

**自定义节点 outputs（Code、Batch等）**：
用户需要完整定义包括value字段：
```json
{
  "result": {
    "type": "object",
    "value": "$testNode.inputs.testAttr",
    "desc": "执行结果"
  }
}
```

### configs *(必填)*
节点特定的配置参数，根据不同节点类型有不同的配置结构。
每种节点类型都有自己的配置规范，具体参考各节点的配置说明。

### nextNodes *(必填)*
定义当前节点执行完成后的流向：
- 数组格式: ["下一个节点名称"]
- 对于条件节点，不需要在此字段指定连接关系
- 对于结束节点，使用: ["end"]
- 可以连接多个节点实现并发执行

## JSON Path 数据引用

### 基本语法
- `$.节点名.inputs/outputs.字段名` - 引用节点数据
- `$.节点名.result.字段名` - 引用Code节点结果
- `$.currentItem.字段名` - 批处理中的当前项

### 高级语法
- 数组访问：`$.GetUsers.outputs.data[0].name`
- 条件过滤：`$.Users.outputs.data[?(@.status == 'active')]`
- 嵌套访问：`$.User.outputs.profile.email`

以下是各种节点类型的具体配置说明：


# 工作流开始节点 (Start Node)

## 功能说明
工作流开始节点，定义工作流的输入参数和触发方式，作为工作流的起始点。

## inputs 输入参数
用户自由配置，作为工作流的初始输入数据，所有工作流的输入参数都在该节点定义

## outputs 输出参数
此节点类型不产生输出数据

## configs 配置参数
此节点类型无需特殊配置

## 配置示例
```json
{
    "name": "Start",
    "type": "workflowStart",
    "desc": "工作流开始节点",
    "inputs": {
        "userId": {
            "type": "string",
            "value": "123",
            "desc": "用户ID"
        }
    },
    "nextNodes": [
        "ProcessUser"
    ]
}
```


# 工作流结束节点 (End Node)

## 功能说明
工作流结束节点，定义工作流的API响应输出结果，作为工作流的终止点。**必须返回标准的API响应格式**。

## inputs 输入参数
用户自由配置，通常用于接收前面节点的最终结果

## outputs 输出参数 *(必填)*
End节点必须定义标准的API响应格式，包含以下固定字段：

### 必需字段
- **code**: HTTP状态码（数字类型）
  - 成功操作: 200
  - 创建成功: 201
  - 客户端错误: 400
  - 未授权: 401
  - 禁止访问: 403
  - 资源未找到: 404
  - 服务器错误: 500

- **data**: 响应数据（字符串或对象类型）
  - 包含实际的业务数据
  - 可以是简单字符串（如ID、确认消息）
  - 也可以是复杂对象（如用户信息、列表数据）
  - 支持字符串、对象、数组等各种数据格式

- **message**: 响应消息（字符串类型）
  - 操作结果的描述信息
  - 成功消息或错误提示

### Data结构定义
data字段支持多种类型和定义方式：

#### 1. 字符串类型 - 简单数据
适用于ID、确认消息等简单场景：
```json
{
  "data": {
    "type": "string",
    "value": "$.CreateUser.outputs.insertId",
    "desc": "新创建的用户ID"
  }
}
```

#### 2. 对象类型 - 直接引用
当前面的节点已经返回了完整的数据结构时，直接引用即可：
```json
{
  "data": {
    "type": "object",
    "value": "$.ProcessResult.outputs.result",
    "desc": "业务处理结果（完整对象数据）"
  }
}
```

#### 3. 对象类型 - 组合模式
当需要从多个节点组合数据时，在properties中定义具体字段：
```json
{
  "data": {
    "type": "object",
    "desc": "分页查询结果",
    "properties": {
      "list": {
        "type": "array",
        "value": "$.QueryUsers.outputs.data",
        "desc": "用户列表数据"
      },
      "total": {
        "type": "number", 
        "value": "$.CountUsers.outputs.affected",
        "desc": "用户总数"
      }
    }
  }
}
```

### 支持的字段
- **type**: 数据类型 (string, number, boolean, object, array)
- **value**: 数据来源引用（可选，但data或其子级必须至少有一个）
- **desc**: 字段描述
- **properties**: 对象的属性定义（支持嵌套）
- **items**: 数组元素类型定义
- **enum**: 枚举值限制

## configs 配置参数
此节点类型无需特殊配置

## 常见响应格式

### 1. 字符串响应
适用于：简单确认、ID返回、状态消息
data为字符串类型

### 2. 单个对象响应
适用于：创建、更新、查询单个资源
data为对象类型

### 3. 列表响应
适用于：查询列表、分页数据
建议包含：list（数据数组）、total（总数）、page（页码）、pageSize（页大小）

### 4. 操作确认响应
适用于：删除、状态变更等操作
可以是简单字符串确认或包含操作结果的对象

## 配置示例

### 示例1: 字符串数据 - 简单ID返回
```json
{
  "name": "End",
  "type": "workflowEnd",
  "desc": "工作流结束节点 - 字符串数据",
  "outputs": {
    "code": {
      "type": "number",
      "value": "200",
      "desc": "HTTP状态码"
    },
    "data": {
      "type": "string",
      "value": "$.CreateUser.outputs.insertId",
      "desc": "新创建的用户ID"
    },
    "message": {
      "type": "string",
      "value": "操作成功",
      "desc": "响应消息"
    }
  }
}
```

### 示例2: 对象数据 - 直接引用完整数据
```json
{
  "name": "End",
  "type": "workflowEnd",
  "desc": "工作流结束节点",
  "outputs": {
    "code": {
      "type": "number",
      "value": "200",
      "desc": "HTTP状态码"
    },
    "data": {
      "type": "object",
      "value": "$.ProcessResult.outputs.result",
      "desc": "业务处理结果（完整对象数据）"
    },
    "message": {
      "type": "string",
      "value": "操作成功",
      "desc": "响应消息"
    }
  }
}
```

### 示例3: 组合模式 - 从多个节点组合数据
```json
{
  "name": "End",
  "type": "workflowEnd",
  "desc": "工作流结束节点 - 组合数据",
  "outputs": {
    "code": {
      "type": "number",
      "value": "200",
      "desc": "HTTP状态码"
    },
    "data": {
      "type": "object",
      "desc": "分页查询结果",
      "properties": {
        "list": {
          "type": "array",
          "value": "$.QueryUsers.outputs.data",
          "desc": "用户列表数据"
        },
        "total": {
          "type": "number",
          "value": "$.CountUsers.outputs.affected",
          "desc": "用户总数"
        },
        "page": {
          "type": "number",
          "value": "$.GetPage.outputs.page",
          "desc": "当前页码"
        },
        "pageSize": {
          "type": "number",
          "value": "10",
          "desc": "每页大小"
        }
      }
    },
    "message": {
      "type": "string",
      "value": "查询成功",
      "desc": "响应消息"
    }
  }
}
```

### 示例4: 创建操作 - 组合结果响应
```json
{
  "name": "End",
  "type": "workflowEnd",
  "desc": "工作流结束节点 - 创建操作",
  "outputs": {
    "code": {
      "type": "number",
      "value": "201",
      "desc": "HTTP状态码"
    },
    "data": {
      "type": "object",
      "desc": "创建结果",
      "properties": {
        "id": {
          "type": "string",
          "value": "$.CreateUser.outputs.insertId",
          "desc": "新创建的用户ID"
        },
        "createdAt": {
          "type": "string",
          "value": "$.GetCurrentTime.outputs.timestamp",
          "desc": "创建时间"
        }
      }
    },
    "message": {
      "type": "string",
      "value": "用户创建成功",
      "desc": "响应消息"
    }
  }
}
```

### 示例5: 删除操作 - 简单确认
```json
{
  "name": "End",
  "type": "workflowEnd",
  "desc": "工作流结束节点 - 删除操作",
  "outputs": {
    "code": {
      "type": "number",
      "value": "200",
      "desc": "HTTP状态码"
    },
    "data": {
      "type": "string",
      "value": "删除成功",
      "desc": "操作结果确认"
    },
    "message": {
      "type": "string",
      "value": "数据删除成功",
      "desc": "响应消息"
    }
  }
}
```

## 强制要求
1. **必须包含code、data、message三个字段**
2. **data或其子级必须至少有一个value引用**，确保有实际数据返回
3. **合理设置HTTP状态码**，与业务操作结果匹配
4. **明确定义数据类型**，使用type字段标明每个数据的类型

## 使用建议
1. **选择合适的类型**：根据业务场景选择string或object类型
2. **优先使用简单模式**：如果前置节点已经构建好完整数据，直接引用
3. **合理使用组合模式**：需要从多个节点收集数据时才使用properties
4. **字符串适用场景**：ID返回、简单确认消息、状态字符串等
5. **对象适用场景**：复杂数据结构、列表数据、多字段信息等
6. **避免过度嵌套**：保持结构简单清晰，便于理解和维护
7. **描述要准确**：desc字段要准确描述数据内容和用途
8. **类型要匹配**：type字段要与实际数据类型一致
9. **保持一致性**：所有API都应使用相同的响应结构



# 批量处理节点 (Batch Node)

## 功能说明
此节点用于实现Map-Reduce模式的批量数据处理，将数据源拆分为多个子项，对每个子项执行相同的操作，最后聚合结果。

## inputs 输入参数
用户自由配置，根据具体业务需求定义输入数据，通常包含需要批量处理的数据列表。

## outputs 输出参数
批量处理节点固定返回以下字段：
- **totalProcessed**: 处理的总数量（数字类型）
- **successCount**: 成功处理的数量（数字类型）
- **failureCount**: 失败处理的数量（数字类型）
- **aggregatedResult**: 根据reduce策略聚合的结果（任意类型）
- **executionTime**: 批处理执行耗时，单位毫秒（数字类型）

## configs 配置参数
节点特定的配置参数，详见下方配置参数部分

## 配置参数

### 基本配置
- **concurrency**: 并发数，默认1 *(可选)*
- **timeout**: 总超时时间（秒），默认60秒 *(可选)*
- **continueOnError**: 遇到错误是否继续处理，默认false *(可选)*

### Map配置 (mapConfig) *(必填)*
定义如何拆分数据和访问当前项：
- **dataSource**: 数据源路径，如 "$.BatchNode.inputs.dataList" *(必填)*
- **itemVariable**: 当前数据项变量名，默认"$.currentItem" *(可选)*
- **indexVariable**: 当前索引变量名，默认"$.currentIndex" *(可选)*

### Reduce配置 (reduceConfig) *(必填)*
定义如何合并结果：
- **strategy**: 聚合策略，支持 "sum", "count", "collect", "first", "last", "max", "min" *(必填)*
- **targetField**: 要聚合的字段名，如 "affected" *(可选)*
- **customLogic**: 自定义合并逻辑（JavaScript表达式）*(可选)*

## 聚合策略说明
- **sum**: 对指定字段求和
- **count**: 统计成功处理的数量
- **collect**: 收集所有结果到数组
- **first**: 返回第一个结果
- **last**: 返回最后一个结果
- **max**: 返回最大值
- **min**: 返回最小值

## 子节点配置 (child) *(必填)*
单个子节点定义，包含完整的节点配置：
- **name**: 子节点名称 *(必填)*
- **type**: 节点类型 (dbQuery, dbCreate, dbUpdate, dbDelete, code) *(必填)*
- **desc**: 节点描述 *(必填)*
- **inputs**: 节点输入参数 *(必填)*
- **outputs**: 节点输出参数 *(必填)*
- **configs**: 节点的具体配置 *(必填)*

## 数据访问模式
在子节点中可以使用以下变量访问数据：
- `$.currentItem` - 当前正在处理的数据项
- `$.currentIndex` - 当前数据项的索引
- `$.节点名.inputs.字段名` - 引用batch节点的输入参数

## 配置示例
```json
{
  "configs": {
    "concurrency": 3,
    "timeout": 120,
    "continueOnError": true,
    "mapConfig": {
      "dataSource": "$.BatchInsertUsers.inputs.userList",
      "itemVariable": "$.currentItem",
      "indexVariable": "$.currentIndex"
    },
    "reduceConfig": {
      "strategy": "sum",
      "targetField": "affected"
    }
  },
  "child": {
    "name": "InsertUser",
    "type": "dbCreate",
    "desc": "插入单个用户",
    "inputs": {
      "name": {
        "type": "string",
        "value": "$.currentItem.name",
        "desc": "用户名"
      },
      "email": {
        "type": "string",
        "value": "$.currentItem.email",
        "desc": "邮箱"
      }
    },
    "outputs": {
      "affected": {
        "type": "number",
        "desc": "影响的行数"
      },
      "insertId": {
        "type": "string",
        "desc": "新插入记录的ID"
      }
    },
    "configs": {
      "table": "users_table",
      "sql": "INSERT INTO users_table (name, email) VALUES ($.InsertUser.inputs.name, $.InsertUser.inputs.email)"
    }
  }
}
```

## 执行流程
1. **数据拆分**: 根据mapConfig.dataSource获取数据源并拆分为子项
2. **并发处理**: 按concurrency配置并发执行子节点操作
3. **结果收集**: 收集每个子项的执行结果
4. **数据聚合**: 根据reduceConfig策略聚合结果
5. **输出结果**: 返回统计信息和聚合结果

## 使用场景
- 批量数据插入：将用户列表批量插入数据库
- 批量数据更新：批量更新商品价格
- 批量数据验证：批量验证邮箱格式
- 批量API调用：批量调用外部服务

## 注意事项
1. 子节点必须是支持的类型：dbQuery, dbCreate, dbUpdate, dbDelete, code
2. 数据源必须是数组类型
3. 子节点的输入参数通过$.currentItem访问当前处理的数据项
4. 聚合策略需要根据实际业务需求选择合适的类型
5. 并发数过大可能影响系统性能，需根据实际情况调整
6. 建议为重要的批量操作设置适当的超时时间
7. child配置包含完整的节点定义，而不是简单的配置引用



# 条件判断节点 (Condition Node)

## 功能说明
此节点用于根据输入数据执行条件判断，决定工作流的下一步执行路径。支持复杂的条件逻辑组合。

## inputs 输入参数
用户自由配置，通常包含需要进行条件判断的数据字段

## outputs 输出参数
条件节点不产生数据输出，其作用是控制工作流的执行路径

## configs 配置参数
条件组配置，包括判断逻辑、操作符、期望值和跳转目标

## 配置参数

### 基本配置
- **conditionGroups**: 条件组列表 *(必填)*
- **groupRelationship**: 条件组之间的逻辑关系 (AND/OR) *(可选)*
- **defaultNextNode**: 默认跳转节点 *(可选)*

### 条件组配置 (conditionGroups)
- **conditions**: 单个条件组内的条件列表 *(必填)*
- **relationship**: 条件组内的逻辑关系 (AND/OR) *(必填)*
- **nextNode**: 条件满足时跳转的节点ID *(必填)*

### 单个条件配置
- **left**: 变量路径，如 "$.ConditionNode.inputs.userType" *(必填)*
- **operator**: 比较操作符 *(必填)*
- **right**: 期望值 *(必填)*

## 支持的操作符
- **equal** - 等于
- **notEqual** - 不等于
- **greaterThan** - 大于
- **greaterThanEqual** - 大于等于
- **lessThan** - 小于
- **lessThanEqual** - 小于等于
- **isNull** - 为空
- **isNotNull** - 不为空
- **include** - 包含
- **notInclude** - 不包含

## 核心要点
1. **顺序评估**：按顺序评估条件组，首个匹配的执行
2. **逻辑关系**：组内用relationship，组间用groupRelationship
3. **变量引用**：使用`$.节点名.inputs.字段名`格式
4. **默认分支**：设置defaultNextNode处理未匹配情况

## 配置示例
```json
{
  "conditionGroups": [{
    "conditions": [{
      "left": "$.CheckUser.inputs.userType",
      "operator": "equal", 
      "right": "vip"
    }],
    "relationship": "AND",
    "nextNode": "VipProcess"
  }],
  "defaultNextNode": "NormalProcess"
}
```



# 工作流节点 (Workflow Node)

## 功能说明
调用其他已定义的工作流，实现工作流复用和组合。

## configs 配置参数

### 基本配置
- **workflowId**: 目标工作流ID *(必填)*
- **version**: 工作流版本，默认latest *(可选)*

### 参数映射
- **inputMappings**: 输入参数映射 *(必填)*
  - sourceField: 数据来源，如 `$.PrevNode.outputs.data`
  - targetField: 目标工作流输入字段名
  - desc: 映射说明
- **outputMappings**: 输出参数映射 *(必填)*
  - sourceField: 子工作流输出字段名
  - targetField: 当前节点输出字段名
  - desc: 映射说明

### 执行控制 *(可选)*
- **maxDepth**: 最大嵌套深度，默认3，最大5
- **timeout**: 执行超时时间（秒）
- **allowFailure**: 子工作流失败是否继续，默认false
- **retryCount**: 重试次数，0-3次，默认0

## 配置示例
```json
{
  "workflowId": "order-processing",
  "version": "1.0.0",
  "inputMappings": [
    {
      "sourceField": "$.ValidateOrder.outputs.orderData",
      "targetField": "orderInfo",
      "desc": "传递订单数据"
    }
  ],
  "outputMappings": [
    {
      "sourceField": "processedOrder",
      "targetField": "result",
      "desc": "获取处理结果"
    }
  ],
  "timeout": 60,
  "retryCount": 2
}
```

## 输出字段
节点执行后自动生成：
- **自定义字段**: 根据outputMappings动态生成
- **executionStatus**: 执行状态(success/failed/timeout)
- **executionTime**: 执行耗时(毫秒)
- **executionMetadata**: 执行详情




# 数据库查询节点 (DbQuery Node)

## 功能说明
此节点用于执行数据库查询操作（SELECT），专门用于数据检索。

## inputs 输入参数
用户自由配置，根据具体业务需求定义输入数据

## outputs 输出参数
数据库查询节点固定返回以下字段：
- **affected**: 查询返回的行数（数字类型）
- **data**: 查询结果数据（数组类型）

## configs 配置参数
- **table**: 查询的表名称 *(必填)*
- **sql**: SQL 查询语句，支持变量引用 *(必填)*

## 变量引用
在 sql 字段中可以使用 JSON Path 格式引用数据：
- `$.节点名.inputs.字段名` - 引用当前节点输入参数
- `$.节点名.outputs.字段名` - 引用其他节点输出

## 注意事项
1. 只支持 SELECT 查询操作
2. 查询结果以数组形式返回，每个元素为一行记录
3. 字段名和表名会自动进行SQL注入防护
4. 支持数据库函数如 NOW()、COUNT() 等
5. 变量引用支持嵌套对象访问，如 `$.QueryUser.inputs.user.profile.email`
6. 合理使用 WHERE 条件和 LIMIT 子句优化查询性能



# 数据库创建节点 (DbCreate Node)

## 功能说明
此节点用于执行数据库插入操作（INSERT），专门用于数据创建。

## inputs 输入参数
用户自由配置，根据具体业务需求定义输入数据

## outputs 输出参数
数据库创建节点固定返回以下字段：
- **affected**: 影响的行数（数字类型）
- **insertId**: 新插入记录的ID（字符串类型）

## configs 配置参数
- **table**: 插入的表名称 *(必填)*
- **sql**: SQL 插入语句，支持变量引用 *(必填)*

## 变量引用
在 sql 字段中可以使用 JSON Path 格式引用数据：
- `$.节点名.inputs.字段名` - 引用当前节点输入参数
- `$.节点名.outputs.字段名` - 引用其他节点输出

## 注意事项
1. 只支持 INSERT 插入操作
2. insertId 字段返回新创建记录的主键ID
3. affected 字段通常为1，表示成功插入一条记录
4. 字段名和表名会自动进行SQL注入防护
5. 支持数据库函数如 NOW()、UUID() 等
6. 变量引用支持嵌套对象访问，如 `$.CreateUser.inputs.user.profile.email`
7. 确保必填字段都有对应的输入参数



# 数据库更新节点 (DbUpdate Node)

## 功能说明
此节点用于执行数据库更新操作（UPDATE），专门用于数据修改。

## inputs 输入参数
用户自由配置，根据具体业务需求定义输入数据

## outputs 输出参数
数据库更新节点固定返回以下字段：
- **affected**: 影响的行数（数字类型）

## configs 配置参数
- **table**: 更新的表名称 *(必填)*
- **sql**: SQL 更新语句，支持变量引用 *(必填)*

## 变量引用
在 sql 字段中可以使用 JSON Path 格式引用数据：
- `$.节点名.inputs.字段名` - 引用当前节点输入参数
- `$.节点名.outputs.字段名` - 引用其他节点输出

## 注意事项
1. 只支持 UPDATE 更新操作
2. affected 字段返回实际被更新的记录数量
3. 强烈建议 UPDATE 操作加 WHERE 条件，避免全表更新
4. 字段名和表名会自动进行SQL注入防护
5. 支持数据库函数如 NOW()、CONCAT() 等
6. 变量引用支持嵌套对象访问，如 `$.UpdateUser.inputs.user.profile.email`
7. WHERE 条件必须明确，确保只更新目标记录



# 数据库删除节点 (DbDelete Node)

## 功能说明
此节点用于执行数据库删除操作（DELETE），专门用于数据删除。

## inputs 输入参数
用户自由配置，根据具体业务需求定义输入数据

## outputs 输出参数
数据库删除节点固定返回以下字段：
- **affected**: 影响的行数（数字类型）

## configs 配置参数
- **table**: 删除的表名称 *(必填)*
- **sql**: SQL 删除语句，支持变量引用 *(必填)*

## 变量引用
在 sql 字段中可以使用 JSON Path 格式引用数据：
- `$.节点名.inputs.字段名` - 引用当前节点输入参数
- `$.节点名.outputs.字段名` - 引用其他节点输出

## 注意事项
1. 只支持 DELETE 删除操作
2. affected 字段返回实际被删除的记录数量
3. 强烈建议 DELETE 操作加 WHERE 条件，避免全表删除
4. 字段名和表名会自动进行SQL注入防护
5. 删除操作不可逆，请谨慎使用
6. 变量引用支持嵌套对象访问，如 `$.DeleteUser.inputs.user.profile.email`
7. WHERE 条件必须明确，确保只删除目标记录
8. 考虑使用软删除（更新状态字段）代替物理删除



# 数据库事务节点 (Transaction Node)

## 功能说明
此节点用于将多个数据库操作包装在一个事务中执行，保证原子性、一致性、隔离性和持久性（ACID特性）。

## inputs 输入参数
用户自由配置，根据具体业务需求定义输入数据

## outputs 输出参数
事务节点固定返回以下字段：
- **committed**: 事务是否成功提交（布尔类型）
- **affectedTotal**: 事务中所有操作影响的总行数（数字类型）
- **childResults**: 所有子节点的执行结果数组（数组类型）
- **executionTime**: 事务执行耗时，单位毫秒（数字类型）

## configs 配置参数
节点特定的配置参数，详见下方配置参数部分

## 配置参数

### 基本配置
- **isolation**: 事务隔离级别，默认READ_COMMITTED *(可选)*
- **timeout**: 事务超时时间（秒），默认60秒 *(可选)*

### 子节点配置 (children) *(必填)*
每个子节点都是完整的数据库操作节点定义：
- **name**: 子节点名称 *(必填)*
- **type**: 节点类型 (dbCreate, dbUpdate, dbDelete) *(必填)*
- **desc**: 节点描述 *(必填)*
- **order**: 执行顺序，从1开始 *(必填)*
- **inputs**: 节点输入参数 *(可选)*
- **outputs**: 节点输出参数 *(必填)*
- **configs**: 节点的具体配置 *(必填)*

## 隔离级别
- **READ_UNCOMMITTED**: 读未提交（最低隔离级别）
- **READ_COMMITTED**: 读已提交（默认级别）
- **REPEATABLE_READ**: 可重复读
- **SERIALIZABLE**: 串行化（最高隔离级别）

## 配置示例
```json
{
  "configs": {
    "isolation": "READ_COMMITTED",
    "timeout": 60
  },
  "children": [
    {
      "name": "CreateUser",
      "type": "dbCreate",
      "desc": "创建新用户",
      "order": 1,
      "inputs": {},
      "outputs": {
        "affected": {
          "type": "number",
          "desc": "影响的行数"
        },
        "insertId": {
          "type": "string",
          "desc": "新用户ID"
        }
      },
      "configs": {
        "table": "your_table_name",
        "data": {
          "name": "$.TransactionNode.inputs.userData.name",
          "email": "$.TransactionNode.inputs.userData.email",
          "status": "active"
        },
        "timeout": 30
      }
    },
    {
      "name": "CreateProfile",
      "type": "dbCreate",
      "desc": "创建用户档案",
      "order": 2,
      "inputs": {},
      "outputs": {
        "affected": {
          "type": "number",
          "desc": "影响的行数"
        },
        "insertId": {
          "type": "string",
          "desc": "档案ID"
        }
      },
      "configs": {
        "table": "related_table",
        "data": {
          "user_id": "$.CreateUser.outputs.insertId",
          "bio": "$.TransactionNode.inputs.userData.bio"
        },
        "timeout": 30
      }
    }
  ]
}
```

## 输出结果
事务节点的输出结果为内置字段，系统自动生成，不需要在DSL中配置value字段

## 子节点数据引用
在子节点配置中可以使用 JSON Path 格式引用：
- `$.节点名.inputs.字段名` - 引用事务节点的输入参数
- `$.节点名.outputs.字段名` - 引用其他子节点的输出

## 执行流程
1. **开启事务**: 根据isolation级别创建数据库事务
2. **顺序执行**: 按order顺序执行所有子节点
3. **结果收集**: 收集每个子节点的执行结果
4. **提交/回滚**: 全部成功则提交事务，任意失败则回滚

## 注意事项
1. 事务中的所有数据库操作要么全部成功，要么全部失败
2. 只支持数据库操作节点 (dbCreate, dbUpdate, dbDelete)
3. 子节点的order必须唯一且连续，从1开始
4. 长事务可能影响数据库性能，合理设置timeout
5. 子节点间的数据依赖要通过引用路径正确配置
6. 事务失败时会自动回滚所有已执行的操作
7. 建议将相关的数据库操作组合在同一个事务中
8. children数组包含完整的节点定义，而不是简单的配置引用


# 代码执行节点 (Code Node)

## 功能说明
执行自定义JavaScript代码，支持NPM依赖库引入，**仅用于其他专业节点无法实现的复杂业务逻辑处理、数据转换和计算**。

## 重要使用限制
**Code节点应该是最后的选择，优先使用专业节点**：
- ❌ **数据库操作**：使用dbQuery、dbCreate、dbUpdate、dbDelete节点，不要用code节点
- ❌ **HTTP请求**：使用http节点，不要在code中使用fetch/axios
- ❌ **简单条件判断**：使用condition节点，不要用code节点
- ❌ **批量处理**：使用batch节点，不要在code中写循环
- ❌ **事务操作**：使用transaction节点，不要用code节点
- ❌ **LLM调用**：使用llm节点，不要在code中调用LLM API

## Code节点适用场景
**仅在以下情况使用code节点**：
1. **复杂数据转换**：专业节点无法完成的数据结构转换和格式化
2. **复杂业务计算**：涉及多个算法、公式计算的业务逻辑
3. **复杂条件逻辑**：condition节点无法表达的复杂条件判断
4. **数据聚合分析**：需要复杂统计分析的数据处理
5. **外部库依赖**：需要使用特定NPM包的功能

## 设计原则
1. **单一职责**：每个code节点只完成一个明确的功能
2. **功能独立**：避免在一个code节点中混合多种不同类型的处理逻辑
3. **最小化原则**：能用专业节点实现的功能绝不使用code节点

## inputs 输入参数
用户自由配置，根据具体业务需求定义输入数据，每个字段将作为函数参数对象的属性传入

## outputs 输出参数  
用户自由配置，必须与函数返回值的结构完全一致，每个字段对应函数返回对象的同名属性

## configs 配置参数
- **file**: 代码文件配置 *(必填)*
  - **name**: 代码文件名(.js格式) *(必填)*
  - **content**: JavaScript代码内容 *(必填)*
- **dependencies**: NPM包依赖列表 *(可选)*

## 输入输出映射规范

### 1. 函数签名要求（强制约束）
```javascript
export default function main(inputs) {
    // inputs 是包含所有节点输入字段的对象
    // 必须返回对象，字段名与节点outputs中定义的字段名完全一致
    return {
        // 返回值字段必须匹配 outputs 定义
    };
}
```

**关键限制**：
- ✅ **必须使用 `export default`**：函数入口点必须是默认导出
- ✅ **函数名必须是 `main`**：固定的函数名称
- ✅ **必须返回对象**：不能返回基础类型（string、number、boolean等）
- ✅ **参数名必须是 `inputs`**：接收所有输入参数的对象

### 2. 输入参数映射
- 节点 `inputs` 中定义的每个字段，会作为函数 `inputs` 参数对象的属性
- 字段名必须完全一致，支持任意数据类型
- 示例：节点定义 `userId`、`userData`，函数中通过 `inputs.userId`、`inputs.userData` 访问

### 3. 输出结果映射  
- 函数返回值必须是对象类型
- 返回对象的字段名必须与节点 `outputs` 中定义的字段名完全一致
- outputs 中的 `value` 字段使用 `$.节点名.result.字段名` 格式引用
- 函数必须返回 outputs 中定义的所有字段

### 4. 引用规范
在其他节点中引用 code 节点的输出：
- `$.CodeNodeName.result.outputFieldName`
- 例如：`$.ProcessUserData.result.isValid`

## 代码编写要求（严格遵守）
1. **函数导出**: 必须使用 `export default function main(inputs)`，不允许其他导出方式
2. **返回值类型**: 必须返回对象类型，不能返回 string、number、boolean、array 等基础类型
3. **返回值完整性**: 必须返回包含所有 outputs 字段的对象，字段名完全匹配
4. **参数解构**: 推荐使用解构语法获取输入参数 `const { param1, param2 } = inputs;` 
5. **错误处理**: 必须包含 try-catch 错误处理，确保始终返回有效的对象结果
6. **类型安全**: 对输入参数进行类型检查和数据验证
7. **依赖管理**: 外部依赖必须在 dependencies 中声明

## 核心限制
1. **必须返回对象**：禁止返回string、number、boolean等基础类型
2. **固定函数签名**：`export default function main(inputs)`
3. **完整输出**：返回对象必须包含所有outputs定义的字段
4. **错误处理**：必须用try-catch确保始终返回有效结果

## 简单示例
```javascript
export default function main(inputs) {
    const { userId, userData } = inputs;
    const isValid = userData.age >= 18;
    
    return {
        isValid,
        errorMsg: isValid ? null : "年龄不符合要求"
    };
}
```



# HTTP请求节点 (HTTP Request Node)

## 功能说明
此节点用于发送HTTP请求，支持多种请求方法、参数类型和请求体格式。

## inputs 输入参数
用户自由配置，根据具体业务需求定义输入数据

## outputs 输出参数
HTTP节点固定返回以下字段：
- **code**: HTTP状态码（数字类型）
- **data**: 响应数据（对象类型）

## configs 配置参数
节点特定的配置参数，详见下方配置参数部分

## 配置参数

### 基本配置
- **method**: HTTP请求方法 (GET, POST, PUT, PATCH, DELETE) *(必填)*
- **url**: 请求URL，支持路径参数 :paramName *(必填)*
- **timeout**: 请求超时时间（秒），默认30秒 *(可选)*

### 路径参数 (params) *(可选)*
路径参数以键值对对象形式配置，key为参数名，value为参数值

### 查询参数 (queryParams) *(可选)*
查询参数以键值对对象形式配置，key为参数名，value为参数值

### 请求头 (headers) *(可选)*
请求头以键值对对象形式配置，key为头部名称，value为头部值

### 请求体配置
- **bodyType**: 请求体类型 (none, json, form-data, text) *(必填)*
- **body**: 请求体内容，字符串格式 *(可选)*

## 配置示例
```json
{
  "method": "POST",
  "url": "https://api.example.com/users/:userId/profile",
  "timeout": 30,
  "params": {
    "userId": "$.HttpRequest.inputs.userId"
  },
  "queryParams": {
    "format": "json",
    "version": "v1"
  },
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer $.HttpRequest.inputs.token"
  },
  "bodyType": "json",
  "body": "$.HttpRequest.inputs.userData"
}
```

## 输出结果说明
- **code**: HTTP状态码，用于判断请求是否成功
- **data**: HTTP响应数据，包含服务器返回的具体内容

## 变量引用
在参数值中可以使用 JSON Path 格式引用数据：
- `$.节点名.inputs.字段名` - 引用当前节点输入参数
- `$.节点名.outputs.字段名` - 引用其他节点输出

## 注意事项
1. URL中的路径参数用 :paramName 格式
2. 查询参数会自动编码
3. 建议设置合理的超时时间
4. POST/PUT请求需要配置适当的请求体
5. 敏感信息建议通过环境变量传递



# LLM对话节点 (ChatWithLLM Node)

## 功能说明
此节点用于与大型语言模型进行交互，支持多种模型参数配置和对话管理。

## inputs 输入参数
用户自由配置，根据具体业务需求定义输入数据

## outputs 输出参数
LLM节点固定返回以下字段：
- **thinking**: AI思考过程（字符串类型）
- **response**: AI生成的回复（字符串类型）
- **tokens**: Token使用情况（对象类型）

## configs 配置参数
节点特定的配置参数，详见下方配置参数部分

## 配置参数

### 基本配置
- **modelId**: 使用的模型ID *(必填)*
- **systemPrompt**: 系统提示词，定义AI的角色和行为 *(可选)*
- **temperature**: 温度参数 (0-2)，控制生成的随机性 *(可选)*
- **maxTokens**: 最大token数，限制响应长度 *(可选)*
- **topP**: Top-p参数 (0-1)，控制词汇选择范围 *(可选)*
- **frequencyPenalty**: 频率惩罚 (-2到2)，减少重复内容 *(可选)*
- **presencePenalty**: 存在惩罚 (-2到2)，鼓励话题多样性 *(可选)*

## 配置示例
```json
{
  "modelId": "gpt-4",
  "temperature": 0.7,
  "maxTokens": 1000,
  "topP": 0.9,
  "frequencyPenalty": 0,
  "presencePenalty": 0,
  "systemPrompt": "你是一个有用的AI助手。"
}
```

## 输入数据
- **userInput**: 用户输入内容，可以是字符串或消息数组

## 输出结果说明
- **thinking**: AI的思考过程和推理步骤
- **response**: AI最终生成的回复内容
- **tokens**: Token统计信息，包含输入、输出和总计token数

## 变量引用
在配置中可以使用 JSON Path 格式引用数据：
- `$.节点名.inputs.字段名` - 引用当前节点输入参数
- `$.节点名.outputs.字段名` - 引用其他节点输出

## 参数说明

### 温度 (Temperature)
- 0: 确定性输出，始终选择最可能的词
- 1: 平衡创造性和一致性
- 2: 高创造性，输出更加随机

### Top-P
- 0.1: 保守选择，输出更稳定
- 0.9: 标准设置，平衡多样性
- 1.0: 考虑所有可能的词汇

## 注意事项
1. 合理设置maxTokens以控制成本
2. systemPrompt对输出质量影响很大
3. 不同模型支持的参数可能有差异
4. 敏感信息不要包含在prompt中
5. 建议先测试参数组合的效果

