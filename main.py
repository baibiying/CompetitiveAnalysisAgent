from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from agent import analyze_product
import shutil
import os

app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # 直接将图片路径传递给AI agent，让大模型识别产品名和价格
    result = analyze_product(temp_path)
    os.remove(temp_path)
    return JSONResponse(content=result)