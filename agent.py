import os
import openai
import base64
import json
import re
from retrievers import ChromaRetriever

def get_openai_client():
    """获取OpenAI客户端"""
    os.environ['MOONSHOT_API_KEY'] = "sk-XgFQs9dC5L5ynGZyVODjin1dFMhnNtM3OqdMCLfO5qSDuYco"
    client = openai.OpenAI(
        api_key=os.environ.get("MOONSHOT_API_KEY"),
        base_url="https://api.moonshot.cn/v1"
    )
    return client

def get_fruit_data():
    """获取水果数据"""
    with open('./fruit_data.json', 'r', encoding='utf-8') as f:
        fruit_data = json.load(f)
    return fruit_data

def get_vector_db(fruit_data):
    """获取向量数据库"""
    vector_db = ChromaRetriever(collection_name="fruit",model_name='all-MiniLM-L6-v2')
    vector_db.add_document(fruit_data)
    return vector_db

def extract_product_info_from_image(image_path):
    """从图片中提取产品信息"""
    client = get_openai_client()
    model = "kimi-thinking-preview"
    
    # 读取图片为base64编码
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:image/jpeg;base64,{image_base64}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": (
                "你是一个专业的产品鉴别分析师，请从用户上传的图片中识别出产品名称、价格以及价格分析。"
                "最终以JSON格式返回，字段包括：product_name, price"
            )},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        "请识别图片中的产品名称和价格，并进行价格分析，注意价格单位"
                        "请对该产品进行详细分析，分析内容包括：\n"
                        "1. 价格分析，注意价格单位；\n"
                        "最终以JSON格式返回，字段包括：product_name, price, price_analysis。"
                    )},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ],
        temperature=0.7
    )
    result = response.choices[0].message.content

    # 尝试直接解析为JSON
    try:
        data = json.loads(result)
    except Exception:
        # 若不是标准JSON，尝试用正则提取
        product_name = re.search(r'"?product_name"?\s*[:：]\s*"?([^",\n]+)', result)
        price = re.search(r'"?price"?\s*[:：]\s*"?([\d.]+)', result)
        price_analysis = re.search(r'"?price_analysis"?\s*[:：]\s*"?([^",\n]+)', result)
        data = {
            "product_name": product_name.group(1) if product_name else None,
            "price": price.group(1) if price else None,
            "price_analysis": price_analysis.group(1) if price_analysis else None,
        }
    
    return data

def perform_final_analysis(product_name, price, price_analysis=None, image_url=None):
    """执行最终的产品分析"""
    client = get_openai_client()
    model = "kimi-thinking-preview"
    
    fruit_data = get_fruit_data()
    vector_db = get_vector_db(fruit_data)
    bg = vector_db.search(product_name)
    
    # 构建用户消息内容
    user_content = [
        {"type": "text", "text": (
            f"请对该产品{product_name}进行详细分析，该产品价格为{price}"
            + (f", 价格分析为{price_analysis}" if price_analysis else "")
            + "。需要分析的内容包括：\n"
            "1. 价格分析（与市场价对比、是否合理）；\n"
            "2. 与其他类似产品的优势分析；\n"
            "3. 与其他类似产品的劣势分析；\n"
            "4. 适合这类产品的用户画像分析。\n"
            "每个分析部分只用一句话，且每句话限15个字以内，不要写成自然段。"
            "最终以JSON格式返回，字段包括：product_name, price, description, is_overpriced, price_analysis, advantage_analysis, disadvantage_analysis, user_profile_analysis, analysis。"
        )}
    ]
    
    # 如果有图片，添加图片内容
    if image_url:
        user_content.append({"type": "image_url", "image_url": {"url": image_url}})

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": (
                "你是一个专业的产品价格分析师。请根据用户输入的产品名称和价格，查询产品的详细描述，并判断该价格是否超出市场公允价格。"
                "请对该产品进行详细分析，分析内容包括：\n"
                "1. 价格分析（与市场价对比、是否合理）；\n"
                "2. 与其他类似产品的优势分析；\n"
                "3. 与其他类似产品的劣势分析；\n"
                "4. 适合这类产品的用户画像分析。\n"
                "每个分析部分只用一句话，且每句话限15个字以内，不要写成自然段。"
                "最终以JSON格式返回，字段包括：product_name, price, description, is_overpriced, price_analysis, advantage_analysis, disadvantage_analysis, user_profile_analysis, analysis。"
            )},
            {
                "role": "user",
                "background": f"近一年类似水果产品的品种和价格为：{bg}, 其中价格单位为元/斤",
                "content": user_content
            }
        ],
        temperature=0.7
    )
    result = response.choices[0].message.content

    # 尝试直接解析为JSON
    try:
        data = json.loads(result)
    except Exception:
        # 若不是标准JSON，尝试用正则提取
        product_name = re.search(r'"?product_name"?\s*[:：]\s*"?([^",\n]+)', result)
        price = re.search(r'"?price"?\s*[:：]\s*"?([\d.]+)', result)
        description = re.search(r'"?description"?\s*[:：]\s*"?([^",\n]+)', result)
        is_overpriced = re.search(r'"?is_overpriced"?\s*[:：]\s*"?([^",\n]+)', result)
        price_analysis = re.search(r'"?price_analysis"?\s*[:：]\s*"?([^",\n]+)', result)
        advantage_analysis = re.search(r'"?advantage_analysis"?\s*[:：]\s*"?([^",\n]+)', result)
        disadvantage_analysis = re.search(r'"?disadvantage_analysis"?\s*[:：]\s*"?([^",\n]+)', result)
        user_profile_analysis = re.search(r'"?user_profile_analysis"?\s*[:：]\s*"?([^",\n]+)', result)
        analysis = re.search(r'"?analysis"?\s*[:：]\s*"?([^\n}]+)', result)
        data = {
            "product_name": product_name.group(1) if product_name else None,
            "price": price.group(1) if price else None,
            "description": description.group(1) if description else None,
            "is_overpriced": is_overpriced.group(1) if is_overpriced else None,
            "price_analysis": price_analysis.group(1) if price_analysis else None,
            "advantage_analysis": advantage_analysis.group(1) if advantage_analysis else None,
            "disadvantage_analysis": disadvantage_analysis.group(1) if disadvantage_analysis else None,
            "user_profile_analysis": user_profile_analysis.group(1) if user_profile_analysis else None,
            "analysis": analysis.group(1) if analysis else result
        }
    return data

def analyze_product(image_path):
    """分析产品（图片输入）"""
    # 从图片中提取产品信息
    product_info = extract_product_info_from_image(image_path)
    product_name = product_info['product_name']
    price = product_info['price']
    price_analysis = product_info.get('price_analysis')
    
    print(f"提取的产品名: {product_name}")
    
    # 读取图片为base64编码（用于最终分析）
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:image/jpeg;base64,{image_base64}"
    
    # 执行最终分析
    return perform_final_analysis(product_name, price, price_analysis, image_url)

def analyze_product_text(product_name, price):
    """分析产品（文本输入）"""
    # 执行最终分析（无图片）
    return perform_final_analysis(product_name, price) 