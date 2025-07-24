from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from ocr import extract_product_info
from agent import analyze_product
import shutil
import os

app = FastAPI()

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    product_name, price = extract_product_info(temp_path)
    result = analyze_product(product_name, price)
    os.remove(temp_path)
    return JSONResponse(content=result) 