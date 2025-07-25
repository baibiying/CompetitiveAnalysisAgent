from fastapi import FastAPI, File, UploadFile, Body
from fastapi.responses import JSONResponse
from agent import analyze_product
import shutil
import os
from agent import analyze_product_text

app = FastAPI()

@app.post("/analyze_image")
async def analyze_image(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # 直接将图片路径传递给AI agent，让大模型识别产品名和价格
    result = analyze_product(temp_path)
    os.remove(temp_path)
    return JSONResponse(content=result)

@app.post("/analyze_text")
async def analyze_text(payload: dict = Body(...)):
    # 期望payload包含product_name和price
    product_name = payload.get("product_name")
    price = payload.get("price")
    # analyze_product_text函数待在agent.py实现
    result = analyze_product_text(product_name, price)
    return JSONResponse(content=result)