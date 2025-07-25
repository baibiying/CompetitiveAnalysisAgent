from fastapi import FastAPI, File, UploadFile, Body
from fastapi.responses import JSONResponse
from agent import analyze_product
import shutil
import os
from agent import analyze_product_text
from functools import lru_cache
import hashlib

app = FastAPI()

# 用全局dict做图片缓存
image_cache = {}

# 文本分析缓存，key为(product_name, price)
@lru_cache(maxsize=128)
def cached_analyze_text(product_name, price):
    return analyze_product_text(product_name, price)

@app.post("/analyze_image")
async def analyze_image(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    with open(temp_path, "rb") as f:
        file_bytes = f.read()
    file_hash = hashlib.md5(file_bytes).hexdigest()
    if file_hash in image_cache:
        result = image_cache[file_hash]
    else:
        result = analyze_product(temp_path)
        image_cache[file_hash] = result
    os.remove(temp_path)
    return JSONResponse(content=result)

@app.post("/analyze_text")
async def analyze_text(payload: dict = Body(...)):
    # 期望payload包含product_name和price
    product_name = payload.get("product_name")
    price = payload.get("price")
    # analyze_product_text函数待在agent.py实现
    result = cached_analyze_text(product_name, price)
    return JSONResponse(content=result)