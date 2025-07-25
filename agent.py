import os
import openai
import base64
import json
import re
from retrievers import ChromaRetriever
from openai.types.chat.chat_completion import Choice
from typing import Dict, Any
import json
import os
import time
import datetime
from typing import Dict, Any
from openai import OpenAI
from openai.types.chat.chat_completion import Choice
import re
import ast

def get_openai_client():
    """获取OpenAI客户端"""
    os.environ['MOONSHOT_API_KEY'] = "sk-RuAYrlEMOl4dTcqsbAQ6QEVFkHulSrE1llQvS7qJEKS67VTp"
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
                        "1. 请识别图片中的产品名称(product_name:str)和价格(price:float)，并进行价格分析，注意价格单位(price_unit:str), 如果图片里面显示的是总价而不是每斤的价格，则需要将总价和总重量(total_weight:float)都提取出来，并换算成斤为单位的单价价格显示在返回值里面；\n"
                        "2. 新鲜程度(fresh_level:float)，范围0-5，5为最新鲜，0为最不新鲜；\n"
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
    # nutrition_analysis字段转为JSON对象
    nutrition = data.get("nutrition_analysis")
    if isinstance(nutrition, str):
        try:
            data["nutrition_analysis"] = json.loads(nutrition)
        except Exception:
            pass
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
    
    # 如果有图片，添加图片内容

    prices = search_price(product_name)

    print(f"prices type: {prices}")

    price_trend =ast.literal_eval(prices)

    print(f"当前市场价是: {price_trend}")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": (
                "你是一个专业的产品价格分析师。"
            )},
            {
                "role": "user",
                "background": f"近一年类似水果产品的品种和价格为：{bg}, 其中价格单位为元/斤。",
                "content": [
                    {"type": "text", "text": (
                        f"请对该产品(product_name:str):{product_name}进行详细分析，该产品价格为(price:float):{price}, 价格分析为(price_unit:str):{price_unit}, 新鲜程度为(fresh_level:int):{fresh_level}。需要分析的内容包括：\n"
                        f"1. 价格分析(price_analysis:str)（根据市场价预估合理的市场价区间（market_price_range:str）、与市场价对比、是否合理（is_overpriced:str; 偏高/略高/合理/略低/偏低））。已知：当前市场价是: {price_trend[-1]}，如果产品价格超出当前市场价区间最大值每斤1块钱以上，就认为产品溢价\n"
                        "2. 该产品的甜度(sweet_level:float)、酸度(sour_level:float)、水分(water_level:float)、脆度(crisp_level:float)（范围0-5）；\n"
                        "3. 与其他类似产品的优势分析(advantage_analysis:str), 包括分析品牌独特性在哪里\n"
                        "4. 与其他类似产品的劣势分析(disadvantage_analysis:str)；\n"
                        "5. 营养成分分析(nutrition_analysis:str), 营养成分和相应的营养成分含量，形式如”维生素a-100mg-维生素b-200mg-维生素c-300mg“。\n"
                        "6. 产品整体描述（description:str）\n"
                        "营养成分分析最多35个字，其他分析部分限15个字以内。"
                        "最终以JSON格式返回，字段包括：product_name, price, masket_price_range, is_overpriced, fresh_level, sweet_level, sour_level, water_level, crisp_level, description, price_analysis, price_unit, advantage_analysis, disadvantage_analysis, nutrition_analysis"
                    )},
                   # {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ],
        temperature=0.7
    )
    result = response.choices[0].message.content
    print("[LOG] LLM raw output (final analysis):", result)

    try:
        data = json.loads(result)
        print("[LOG] data content:", data)
    except Exception as e:
        print("[LOG] LLM原始输出:", result)
        # 若不是标准JSON，尝试用正则提取主要字段
        product_name = re.search(r'"?product_name"?\s*[:：]\s*"?([^",\n]+)', result)
        price = re.search(r'"?price"?\s*[:：]\s*"?([\d.]+)', result)
        market_price_range = re.search(r'"?market_price_range"?\s*[:：]\s*"?([^",\n]+)', result)
        is_overpriced = re.search(r'"?is_overpriced"?\s*[:：]\s*"?([^",\n]+)', result)
        fresh_level = re.search(r'"?fresh_level"?\s*[:：]\s*"?([^",\n]+)', result)
        sweet_level = re.search(r'"?sweet_level"?\s*[:：]\s*"?([^",\n]+)', result)
        sour_level = re.search(r'"?sour_level"?\s*[:：]\s*"?([^",\n]+)', result)
        water_level = re.search(r'"?water_level"?\s*[:：]\s*"?([^",\n]+)', result)
        crisp_level = re.search(r'"?crisp_level"?\s*[:：]\s*"?([^",\n]+)', result)
        description = re.search(r'"?description"?\s*[:：]\s*"?([^",\n]+)', result)
        price_analysis = re.search(r'"?price_analysis"?\s*[:：]\s*"?([^",\n]+)', result)
        price_unit = re.search(r'"?price_unit"?\s*[:：]\s*"?([^",\n]+)', result)
        advantage_analysis = re.search(r'"?advantage_analysis"?\s*[:：]\s*"?([^",\n]+)', result)
        disadvantage_analysis = re.search(r'"?disadvantage_analysis"?\s*[:：]\s*"?([^",\n]+)', result)
        nutrition_analysis = re.search(r'"?nutrition_analysis"?\s*[:：]\s*"?([^",\n]+)', result)
        data = {
            "product_name": product_name.group(1) if product_name else None,
            "price": price.group(1) if price else None,
            "market_price_range": market_price_range.group(1) if market_price_range else None,
            "is_overpriced": is_overpriced.group(1) if is_overpriced else None,
            "fresh_level": fresh_level.group(1) if fresh_level else None,
            "sweet_level": sweet_level.group(1) if sweet_level else None,
            "sour_level": sour_level.group(1) if sour_level else None,
            "water_level": water_level.group(1) if water_level else None,
            "crisp_level": crisp_level.group(1) if crisp_level else None,
            "description": description.group(1) if description else None,
            "price_analysis": price_analysis.group(1) if price_analysis else None,
            "price_unit": price_unit.group(1) if price_unit else None,
            "advantage_analysis": advantage_analysis.group(1) if advantage_analysis else None,
            "disadvantage_analysis": disadvantage_analysis.group(1) if disadvantage_analysis else None,
            "nutrition_analysis": nutrition_analysis.group(1) if nutrition_analysis else None
        }
        print("[LOG] data content with regex fallback:", data)
    print(f"当前市场价是: {price_trend[-1]}")
    data['price_trend'] = str(price_trend)
    nutrition_ls = data['nutrition_analysis'].split('-')
    nutrition_dict = {}
    for i in range(0, len(nutrition_ls), 2):
    # 检查是否有对应的值
        if i + 1 < len(nutrition_ls):
            key = nutrition_ls[i].strip()
            value = nutrition_ls[i + 1].strip()
            nutrition_dict[key] = value
        else:
            # 如果没有对应的值，可以记录一个特殊的值（例如 None 或空字符串）
            key = nutrition_ls[i].strip()
            nutrition_dict[key] = None
    data['nutrition_analysis'] = nutrition_dict

    '''
    # nutrition_analysis字段转为JSON对象
    nutrition = data.get("nutrition_analysis")
    if isinstance(nutrition, str):
        try:
            data["nutrition_analysis"] = json.loads(nutrition)
        except Exception:
            pass '''

    print("[LOG] Final response data:", data)
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


# 定义搜索工具的具体实现
def search_impl(arguments: Dict[str, Any]) -> Any:
    return arguments

# 定义聊天函数
def chat(messages) -> Choice:
    client = get_openai_client()
    completion = client.chat.completions.create(
        model="kimi-k2-0711-preview",  # 使用Kimi模型
        messages=messages,
        temperature=0.6,
        tools=[
            {
                "type": "builtin_function",  # 使用内置函数
                "function": {
                    "name": "$web_search",  # 使用内置的联网搜索功能
                },
            }
        ]
    )

    return completion.choices[0]

def extract_answer(text):
    # 先尝试英文标签
    match = re.search(r"<answer>(.*?)</answer>", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # 再尝试中文标签
    match = re.search(r"<回答>(.*?)</回答>", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def clean_json_str(s):
    import re
    s = s.strip()
    # 去除 ```json ... ``` 或 ``` ... ```
    s = re.sub(r"^```(?:json)?", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"```$", "", s).strip()
    return s

# 主函数
def search_price(fruit_name):
    today = datetime.date.today()
    today_str = f"{today.year}年{today.month}月{today.day}日"
    messages = [
        {"role": "system", "content": "你是水果市场价格分析专家，请根据用户的问题，分析水果市场价格，并给出分析结果。"},
    ]
    # 初始提问
    messages.append({
        "role": "user",
        "content": (
            f"你的任务是联网搜索近6个月浙江省{fruit_name}正常价格数据，返回近6个月{fruit_name}的正常价格（单位：元/斤），按时间顺序组成一个列表，索引值最大的对应最新价格。输出仅需列表，不要有任何其他内容。\n"
            "请按照以下步骤完成任务：\n"
            f"1. 联网搜索近6个月浙江省{fruit_name}价格数据，当前时间为{today_str}\n"
            f"2. 仔细分析价格数据，从中提取近6个月浙江省{fruit_name}的正常市场价格信息。\n"
            "3. 按照时间顺序对价格信息进行排序，确保索引值最大的对应最新价格。\n"
            "4. 形成一个仅包含价格的列表。\n"
            "\n"
            "在<思考>标签中详细阐述你从数据中提取价格、排序等步骤的思维过程。然后在<回答>标签中输出最终的价格列表。\n"
            "<思考>\n"
            "[在此详细说明你的思维过程]\n"
            "</思考>\n"
            "<回答>\n"
            "[在此输出最终的价格列表]\n"
            "</回答>"
        )
    })
    finish_reason = None
    while finish_reason is None or finish_reason == "tool_calls":
        choice = chat(messages)
        finish_reason = choice.finish_reason
        if finish_reason == "tool_calls":  # 判断当前返回内容是否包含 tool_calls
            messages.append(choice.message)  # 将模型返回的 assistant 消息添加到上下文中
            for tool_call in choice.message.tool_calls:  # 处理每个工具调用
                tool_call_name = tool_call.function.name
                tool_call_arguments = json.loads(tool_call.function.arguments)  # 反序列化参数
                if tool_call_name == "$web_search":
                    tool_result = search_impl(tool_call_arguments)
                else:
                    tool_result = f"Error: unable to find tool by name '{tool_call_name}'"
                # 将工具执行结果添加到消息中
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call_name,
                    "content": json.dumps(tool_result),
                })
    answer = extract_answer(choice.message.content)
    return answer