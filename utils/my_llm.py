# from chromadb.api.segment import rate_limit
from langchain_core.messages import HumanMessage
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from utils.env_utils import BAILIAN_API_KEY, BAILIAN_BASE_URL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LOCAL_BASE_URL, \
    XIAOAI_API_KEY, XIAOAI_BASE_URL

# llm = ChatOpenAI(
#     model="qwen-flash",  # 或 qwen-turbo、qwen-max；qwen3-omni-flash-realtime 仅支持 WebSocket，不支持 Chat Completions
#     temperature=0.6,
#     api_key=BAILIAN_API_KEY,
#     base_url=BAILIAN_BASE_URL
# )

llm = ChatOpenAI(
    model="deepseek-chat",
    temperature=0.6,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)

# 速率控制
# rate_limiter = InMemoryRateLimiter(
#     requests_per_second= 0.1,
#     check_every_n_seconds=0.1,
#     max_bucket_size=10
# )

from langchain_openai import ChatOpenAI

autoal_llm = ChatOpenAI(  # 调用私有化部署的大模型 (全模态的大模型)
    model='qwen-omni-3b',
    base_url=LOCAL_BASE_URL,
    api_key="EMPTY",           # 本地部署一般随便写
    temperature=0.7,
)


xiaoai_llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.6,
    api_key=XIAOAI_API_KEY,
    base_url=XIAOAI_BASE_URL
)

embedding = OpenAIEmbeddings(
    api_key=XIAOAI_API_KEY,
    base_url=XIAOAI_BASE_URL,
    model="text-embedding-3-large",
)


def test_ping():
    resp = xiaoai_llm.invoke([
        HumanMessage(content="南京有什么好玩的？")
    ])

    print(resp.content)

if __name__ == '__main__':
    test_ping()
