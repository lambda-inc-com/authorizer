from openai import OpenAI, APIConnectionError, APIError
import requests
import time

# 验证自定义API端点连通性
def test_endpoint_connection():
    api_url = "https://api.gptsapi.net/v1"
    try:
        # 尝试简单的HEAD请求检查服务可用性
        response = requests.head(api_url, timeout=5)
        print(f"端点 {api_url} 可用。状态码: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到端点 {api_url}: {str(e)}")
        print("\n请检查以下问题：")
        print("1. API端点URL是否正确？")
        print("2. 服务是否在线？")
        print("3. 您的网络是否有限制？")
        print("4. DNS解析是否正常？")
        return False

# 创建带错误处理的客户端
def create_client():
    try:
        client = OpenAI(
            base_url="https://api.gptsapi.net/v1",
            api_key="sk-ftr66c87a1ef49a6f5079dbaa6fd771d4bdf39817020XZK1"
        )
        return client
    except Exception as e:
        print(f"创建客户端失败: {str(e)}")
        return None

# 带重试机制的API调用函数
def safe_gpt_api_call(prompt, max_retries=3, backoff_factor=1):
    """带重试和指数退避的安全API调用"""
    # 首先检查端点连通性
    if not test_endpoint_connection():
        return "服务无法访问，请检查网络连接和端点URL"

    client = create_client()
    if not client:
        return "客户端初始化失败"

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "你是一个有帮助的AI助手"},
                    {"role": "user", "content": prompt}
                ],
                timeout=15  # 设置超时时间
            )
            return response.choices[0].message.content
        except APIConnectionError as e:
            wait_time = backoff_factor * (2 ** attempt)  # 指数退避
            print(f"❌ 连接错误 (尝试 {attempt+1}/{max_retries}): {str(e)}")
            print(f"等待 {wait_time}秒后重试...")
            time.sleep(wait_time)
        except APIError as e:
            return f"API返回错误: {str(e)}"
        except Exception as e:
            return f"未知错误: {str(e)}"

    return "所有重试失败，请稍后再试"

# 测试示例
if __name__ == "__main__":
    test_questions = [
        "海盗分金怎么样才可以赢",
    ]

    for question in test_questions:
        print(f"\n📨 问题: {question}")
        response = safe_gpt_api_call(
            prompt=question,
            max_retries=3,
            backoff_factor=1
        )
        print(f"💡 回复: {response}")
        print("-" * 60)