import os
import openai
import base64
import json
import re
from retrievers import ChromaRetriever

os.environ['MOONSHOT_API_KEY'] = "sk-XgFQs9dC5L5ynGZyVODjin1dFMhnNtM3OqdMCLfO5qSDuYco"
def analyze_product(image_path):
    client = openai.OpenAI(
        api_key=os.environ.get("MOONSHOT_API_KEY"),
        base_url="https://api.moonshot.cn/v1"
    )
    model = "kimi-thinking-preview"  # 如有其他模型名可替换

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

    fruit_name = data['product_name']
    print(fruit_name)

    with open('./fruit_data.json', 'r', encoding='utf-8') as f:
        fruit_data = json.load(f)

    vector_db = ChromaRetriever(collection_name="fruit",model_name='all-MiniLM-L6-v2')
    vector_db.add_document(fruit_data)
    bg = vector_db.search(fruit_name)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": (
                "你是一个专业的产品价格分析师。请从用户上传的图片中识别出产品名称和价格，查询产品的详细描述，并判断该价格是否超出市场公允价格。"
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
                "content": [
                    {"type": "text", "text": (
                        f"请对该产品{fruit_name}进行详细分析，该产品价格为{data['price']}, 价格分析为{data['price_analysis']}。需要分析的内容包括：\n"
                        "1. 价格分析（与市场价对比、是否合理）；\n"
                        "2. 与其他类似产品的优势分析；\n"
                        "3. 与其他类似产品的劣势分析；\n"
                        "4. 适合这类产品的用户画像分析。\n"
                        "每个分析部分只用一句话，且每句话限15个字以内，不要写成自然段。"
                        "最终以JSON格式返回，字段包括：product_name, price, description, is_overpriced, price_analysis, advantage_analysis, disadvantage_analysis, user_profile_analysis, analysis。"
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