# Price AI Agent

基于LangChain的产品价格分析AI后端，支持图片输入。

## 依赖安装

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
uvicorn main:app --reload
```

## API 使用

### 图片分析接口
POST `/analyze_image`，参数为图片（multipart/form-data, 字段名file）。

curl -X POST "http://127.0.0.1:8000/analyze_image" -F "file=@fruit.jpg"

### 文字分析接口
POST `/analyze_text`，参数为JSON（字段包括product_name和price）。

curl -X POST "http://127.0.0.1:8000/analyze_text" -H "Content-Type: application/json" -d '{"product_name": "苹果", "price": 10.5}'

