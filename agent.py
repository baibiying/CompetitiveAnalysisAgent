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

def convert_to_jin(price_str):
    """将价格字符串换算为斤为单位，返回float价格和换算说明"""
    import re
    if not isinstance(price_str, str):
        return price_str, None
    # 识别数字和单位
    match = re.search(r"(\d+\.?\d*)\s*([\u4e00-\u9fa5a-zA-Z/]+)", price_str)
    if not match:
        return price_str, None
    value = float(match.group(1))
    unit = match.group(2)
    # 常见单位换算
    if '公斤' in unit or 'kg' in unit or '千克' in unit:
        return value * 2, '已由公斤换算为斤'
    if '克' in unit and '千克' not in unit:
        return value / 500, '已由克换算为斤'
    if '两' in unit:
        return value / 10, '已由两换算为斤'
    if '斤' in unit:
        return value, None
    # 兜底：如果单位未知，直接返回原值
    return value, f'未知单位{unit}，未换算'

def postprocess_price(data):
    """根据price_unit和total_weight自动换算为每斤单价"""
    price = data.get('price')
    price_unit = data.get('price_unit')
    total_weight = data.get('total_weight')
    try:
        price = float(price)
    except Exception:
        return data
    if price and price_unit:
        try:
            if '公斤' in price_unit or 'kg' in price_unit or '千克' in price_unit:
                data['price'] = round(price * 2, 2)
                data['price_unit'] = '元/斤'
                data['convert_note'] = '已由公斤换算为斤'
            elif '克' in price_unit and '千克' not in price_unit:
                data['price'] = round(price / 500, 2)
                data['price_unit'] = '元/斤'
                data['convert_note'] = '已由克换算为斤'
            elif '两' in price_unit:
                data['price'] = round(price / 10, 2)
                data['price_unit'] = '元/斤'
                data['convert_note'] = '已由两换算为斤'
            elif ('总价' in price_unit or '元' == price_unit) and total_weight:
                try:
                    data['price'] = round(price / float(total_weight), 2)
                    data['price_unit'] = '元/斤'
                    data['convert_note'] = '已由总价/重量换算为斤单价'
                except Exception:
                    pass
        except Exception:
            pass
    return data

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
                "你是一个专业的水果鉴别分析师，请从用户上传的图片中识别出水果名称、水果的新鲜程度、价格, 价格单位, 如果图片显示的是总价请同时返回总重量。"
                "最终以JSON格式返回，字段包括：product_name, fresh_level, price, price_unit, total_weight"
            )},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        "请识别图片中的产品名称和价格，并进行价格分析，注意价格单位, 如果图片里面显示的是总价而不是每斤的价格，则需要将总价和总重量都提取出来，并换算成斤为单位的单价价格显示在返回值里面；\n"
                        "2. 新鲜程度，范围0-5，5为最新鲜，0为最不新鲜；\n"
                        "最终以JSON格式返回，字段包括：product_name, fresh_level, price, price_unit, total_weight"
                    )},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ],
        temperature=0.7
    )
    result = response.choices[0].message.content
    print("[LOG] LLM raw output (image):", result)

    # 尝试直接解析为JSON
    try:
        data = json.loads(result)
    except Exception:
        # 若不是标准JSON，尝试用正则提取
        product_name = re.search(r'"?product_name"?\s*[:：]\s*"?([^",\n]+)', result)
        price = re.search(r'"?price"?\s*[:：]\s*"?([\d.]+)', result)
        price_unit= re.search(r'"?price_unit"?\s*[:：]\s*"?([^",\n]+)', result)
        fresh_level = re.search(r'"?fresh_level"?\s*[:：]\s*"?([^",\n]+)', result)
        total_weight = re.search(r'"?total_weight"?\s*[:：]\s*"?([^",\n]+)', result)
        data = {
            "product_name": product_name.group(1) if product_name else None,
            "price": price.group(1) if price else None,
            "price_unit": price_unit.group(1) if price_unit else None,
            "fresh_level": fresh_level.group(1) if fresh_level else None,
            "total_weight": total_weight.group(1) if total_weight else None
        }
        print("[LOG] 正则提取失败，原始内容:", result)
    print("[LOG] Parsed data (image):", data)
    # 自动换算为每斤单价
    data = postprocess_price(data)
    print("[LOG] Postprocessed data (image):", data)
    return data

def perform_final_analysis(product_name, price, price_unit=None, image_url=None, fresh_level=None):
    """执行最终的产品分析"""
    client = get_openai_client()
    model = "kimi-thinking-preview"
    
    fruit_data = get_fruit_data()
    vector_db = get_vector_db(fruit_data)
    bg = vector_db.search(product_name)
    
    print(f"[LOG] Final analysis input: product_name={product_name}, price={price}, price_unit={price_unit}, fresh_level={fresh_level}")

    # 构建用户消息内容
    user_content = [
        {"type": "text", "text": (
            f"请对该产品{product_name}进行详细分析，该产品价格为{price}"
            + (f", 价格分析为{price_unit}" if price_unit else "")
            + "。需要分析的内容包括：\n"
            "1. 价格分析（与市场价对比、是否合理）；\n"
            "2. 与其他类似产品的优势分析；\n"
            "3. 与其他类似产品的劣势分析；\n"
            "4. 适合这类产品的用户画像分析。\n"
            "每个分析部分只用一句话，且每句话限15个字以内，不要写成自然段。"
            "最终以JSON格式返回，字段包括：product_name, price, description, is_overpriced, price_unit, advantage_analysis, disadvantage_analysis, user_profile_analysis, analysis。"
        )}
    ]
    
    # 如果有图片，添加图片内容
    if image_url:
        user_content.append({"type": "image_url", "image_url": {"url": image_url}})

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": (
                "你是一个专业的产品价格分析师。"
            )},
            {
                "role": "user",
                "background": f"近一年类似水果产品的品种和价格为：{bg}, 其中价格单位为元/斤",
                "content": [
                    {"type": "text", "text": (
                        f"请对该产品{product_name}进行详细分析，该产品价格为{price}, 价格分析为{price_unit}, 新鲜程度为{fresh_level}。需要分析的内容包括：\n"
                        "1. 价格分析（与市场价对比、是否合理）；\n"
                        "2. 该产品的甜度、酸度、水分、脆度（范围0-5）；\n"
                        "3. 与其他类似产品的优势分析；\n"
                        "4. 与其他类似产品的劣势分析；\n"
                        "5. 适合这类产品的用户画像分析。\n"
                        "每个分析部分只用一句话，且每句话限25个字以内，不要写成自然段。"
                        "最终以JSON格式返回，字段包括：product_name, price, fresh_level, sweet_level, sour_level, water_level, crisp_level, description, is_overpriced, price_unit, advantage_analysis, disadvantage_analysis, user_profile_analysis, analysis。"
                    )},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ],
        temperature=0.7
    )
    result = response.choices[0].message.content
    print("[LOG] LLM raw output (final analysis):", result)

    # 尝试直接解析为JSON
    try:
        data = json.loads(result)
    except Exception:
        # 若不是标准JSON，尝试用正则提取
        product_name = re.search(r'"?product_name"?\s*[:：]\s*"?([^",\n]+)', result)
        price = re.search(r'"?price"?\s*[:：]\s*"?([\d.]+)', result)
        fresh_level = re.search(r'"?fresh_level"?\s*[:：]\s*"?([^",\n]+)', result)
        sweet_level = re.search(r'"?sweet_level"?\s*[:：]\s*"?([^",\n]+)', result)
        sour_level = re.search(r'"?sour_level"?\s*[:：]\s*"?([^",\n]+)', result)
        water_level = re.search(r'"?water_level"?\s*[:：]\s*"?([^",\n]+)', result)
        crisp_level = re.search(r'"?crisp_level"?\s*[:：]\s*"?([^",\n]+)', result)
        description = re.search(r'"?description"?\s*[:：]\s*"?([^",\n]+)', result)
        is_overpriced = re.search(r'"?is_overpriced"?\s*[:：]\s*"?([^",\n]+)', result)
        price_unit = re.search(r'"?price_unit"?\s*[:：]\s*"?([^",\n]+)', result)
        advantage_analysis = re.search(r'"?advantage_analysis"?\s*[:：]\s*"?([^",\n]+)', result)
        disadvantage_analysis = re.search(r'"?disadvantage_analysis"?\s*[:：]\s*"?([^",\n]+)', result)
        user_profile_analysis = re.search(r'"?user_profile_analysis"?\s*[:：]\s*"?([^",\n]+)', result)
        analysis = re.search(r'"?analysis"?\s*[:：]\s*"?([^\n}]+)', result)
        data = {
            "product_name": product_name.group(1) if product_name else None,
            "price": price.group(1) if price else None,
            "fresh_level": fresh_level.group(1) if fresh_level else None,
            "sweet_level": sweet_level.group(1) if sweet_level else None,
            "sour_level": sour_level.group(1) if sour_level else None,
            "water_level": water_level.group(1) if water_level else None,
            "crisp_level": crisp_level.group(1) if crisp_level else None,
            "description": description.group(1) if description else None,
            "is_overpriced": is_overpriced.group(1) if is_overpriced else None,
            "price_unit": price_unit.group(1) if price_unit else None,
            "advantage_analysis": advantage_analysis.group(1) if advantage_analysis else None,
            "disadvantage_analysis": disadvantage_analysis.group(1) if disadvantage_analysis else None
        }
        print("[LOG] 正则提取失败 (final analysis)，原始内容:", result)
    print("[LOG] Parsed data (final analysis):", data)
    return data

def parse_price(price):
    """从带单位的价格字符串中提取数字部分"""
    import re
    if isinstance(price, (int, float)):
        return float(price)
    if isinstance(price, str):
        match = re.search(r"(\d+\.?\d*)", price)
        if match:
            return float(match.group(1))
    return None

def analyze_product(image_path):
    """分析产品（图片输入）"""
    # 从图片中提取产品信息
    product_info = extract_product_info_from_image(image_path)
    product_name = product_info['product_name']
    price = product_info['price']
    price_unit = product_info.get('price_unit')
    fresh_level = product_info.get('fresh_level')
    print(f"提取的产品名: {product_name}")
    
    # 读取图片为base64编码（用于最终分析）
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:image/jpeg;base64,{image_base64}"
    
    # 执行最终分析
    return perform_final_analysis(product_name, price, price_unit, image_url, fresh_level)

def analyze_product_text(product_name, price):
    """分析产品（文本输入，价格必须以斤为单位的字符串）"""
    if not (isinstance(price, str) and price.strip().endswith('斤')):
        raise ValueError('价格必须是以“斤”为单位的字符串，如“10.5元/斤”')
    price_num = parse_price(price)
    return perform_final_analysis(product_name, price_num) 