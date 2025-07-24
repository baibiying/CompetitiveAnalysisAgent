from PIL import Image
import pytesseract
import re

def extract_product_info(image_path):
    text = pytesseract.image_to_string(Image.open(image_path), lang='chi_sim+eng')
    # 简单正则提取产品名和价格（可根据实际图片格式优化）
    name_match = re.search(r"产品名[:：]?\s*([\u4e00-\u9fa5A-Za-z0-9]+)", text)
    price_match = re.search(r"价格[:：]?\s*([0-9]+(\.[0-9]{1,2})?)", text)
    product_name = name_match.group(1) if name_match else ""
    price = float(price_match.group(1)) if price_match else 0.0
    return product_name, price 