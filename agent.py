from langchain.agents import initialize_agent, Tool
from langchain_community.tools.serpapi.tool import SerpAPIWrapper
from langchain.llms import OpenAI
import os

def analyze_product(product_name, price):
    # 需要设置OPENAI_API_KEY和SERPAPI_API_KEY环境变量
    llm = OpenAI(temperature=0)
    search = SerpAPIWrapper()
    tools = [Tool(name="Search", func=search.run, description="Search the web for product info")]
    agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=False)
    prompt = (
        f"产品名称：{product_name}\n"
        f"标价：{price}元\n"
        "请查询该产品的详细描述、市场合理价格，并判断当前价格是否偏贵，给出详细分析。"
    )
    result = agent.run(prompt)
    return {
        "product_name": product_name,
        "input_price": price,
        "analysis": result
    } 