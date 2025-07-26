from fastapi import FastAPI, File, UploadFile, Body
from fastapi.responses import JSONResponse
from agent import analyze_product
import shutil
import os
from agent import analyze_product_text
from functools import lru_cache
import hashlib
import asyncio
import aiofiles


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
    
    # 异步写入文件
    async with aiofiles.open(temp_path, "wb") as buffer:
        await buffer.write(await file.read())
    
    # 异步读取文件
    async with aiofiles.open(temp_path, "rb") as f:
        file_bytes = await f.read()
    
    file_hash = hashlib.md5(file_bytes).hexdigest()
    
    if file_hash in image_cache:
        result = image_cache[file_hash]
    else:
        # 将同步的AI分析函数包装在线程池中执行
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyze_product, temp_path)
        image_cache[file_hash] = result
    
    # 异步删除文件
    await asyncio.to_thread(os.remove, temp_path)
    return JSONResponse(content=result)

@app.post("/analyze_text")
async def analyze_text(payload: dict = Body(...)):
    # 期望payload包含product_name和price
    product_name = payload.get("product_name")
    price = payload.get("price")
    # analyze_product_text函数待在agent.py实现
    # 将同步函数包装在线程池中执行
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, cached_analyze_text, product_name, price)
    return JSONResponse(content=result)