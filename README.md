# Price AI Agent

基于LangChain的产品价格分析AI后端，支持图片输入。

## 依赖安装

```bash
pip install -r requirements.txt
```

## API Key 配置

需要设置环境变量：
- `OPENAI_API_KEY`：OpenAI API Key
- `SERPAPI_API_KEY`：SerpAPI Key（用于联网搜索）

可在命令行运行：
```bash
export OPENAI_API_KEY=你的key
export SERPAPI_API_KEY=你的key
```

## 启动服务

```bash
uvicorn main:app --reload
```

## API 使用

POST `/analyze`，参数为图片（multipart/form-data, 字段名file）。

curl -X POST "http://127.0.0.1:8000/analyze" -F "file=@fruit.jpg"

返回：产品名、输入价格、AI分析结果。 