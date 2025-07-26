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
from person_desicion import desicion


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

@app.post("/recommend_fruits")
async def recommend_fruits(payload: dict = Body(...)):
    """
    根据预算、特殊要求和可选水果列表推荐水果
    
    期望payload包含:
    - budget: 预算金额 (string)
    - special_remark: 特殊要求 (string) 
    - available_fruits: 可选水果列表 (list)
    """
    try:
        budget = payload.get("budget")
        special_remark = payload.get("special_remark")
        available_fruits = payload.get("available_fruits")
        
        # 参数验证
        if not budget:
            return JSONResponse(
                status_code=400,
                content={"error": "缺少必要参数: budget"}
            )
        if not special_remark:
            return JSONResponse(
                status_code=400,
                content={"error": "缺少必要参数: special_remark"}
            )
        if not available_fruits or not isinstance(available_fruits, list):
            return JSONResponse(
                status_code=400,
                content={"error": "缺少必要参数: available_fruits (必须是列表)"}
            )
        
        # 调用person_desicion.py的desicion方法（同步函数异步包装）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, desicion, budget, special_remark, available_fruits)
        
        return JSONResponse(content={
            "success": True,
            "data": result,
            "input": {
                "budget": budget,
                "special_remark": special_remark,
                "available_fruits": available_fruits
            }
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"推荐失败: {str(e)}"
            }
        )