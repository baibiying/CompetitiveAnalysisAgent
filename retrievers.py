from typing import List, Dict, Any, Optional, Union
from sentence_transformers import SentenceTransformer
import nltk
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import chromadb
from chromadb.config import Settings
import pickle
from nltk.tokenize import word_tokenize
import os
import json
import jieba
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

def simple_tokenize(text):
    return word_tokenize(text)

class ChromaRetriever:
    """Vector database retrieval using ChromaDB"""
    def __init__(self, collection_name: str = "memories",model_name: str = "all-MiniLM-L6-v2", persist_directory: str = "./user_memories/persist_dir"):
        if persist_directory is not None:
            self.client = chromadb.Client(Settings(allow_reset=True, persist_directory=persist_directory))
        else:
            self.client = chromadb.Client(Settings(allow_reset=True))
        self.embedding_function = SentenceTransformerEmbeddingFunction(model_name=model_name)
        self.collection = self.client.get_or_create_collection(name=collection_name,embedding_function=self.embedding_function)

    def add_document(self, fruit_data):
        """
        批量添加fruit_data.json中的水果数据到向量库。
        doc_id: 可忽略或作为批次ID
        fruit_data: List[Dict]，每个dict包含'大类'、'品种'、'价格'
        """
        documents = []
        metadatas = []
        ids = []
        for idx, item in enumerate(fruit_data):
            # 以大类+品种为唯一ID
            fruit_id = f"{item['大类']}_{item['品种']}"
            doc_text = f"大类：{item['大类']}，品种：{item['品种']}，价格：{item['价格']}"
            documents.append(doc_text)
            metadatas.append(item)
            ids.append(fruit_id)
        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)

    def delete_document(self, doc_id: str):
        self.collection.delete(ids=[doc_id])

    def search(self, query: str, k: int = 5):
        # 预处理：去除空格、全角转半角
        def normalize(text):
            if not isinstance(text, str):
                return ''
            return text.replace(' ', '').replace('　', '').lower()
        norm_query = normalize(query)
        all_data = self.collection.get()
        exact_hits = []
        fuzzy_hits = []
        # 预处理：去除空格、全角转半角，保留中文分词所需的基本形式
        def normalize(text):
            if not isinstance(text, str):
                return ''
            # 只去除全角空格，保留半角空格用于可能的分词
            return text.replace('　', '').strip()
        
        # 分词处理函数
        def get_keywords(text):
            if not text:
                return []
            # 精确模式分词
            return list(jieba.cut(text, cut_all=False))
        
        norm_query = normalize(query)
        query_keywords = get_keywords(norm_query)
        all_data = self.collection.get()
        
        exact_hits = []
        fuzzy_hits = []
        keyword_hits = []  # 新增：关键词匹配
        
        if 'metadatas' in all_data:
            for item in all_data['metadatas']:
                pn = normalize(item.get('品种', ''))
                cat = normalize(item.get('大类', ''))
                item_keywords = get_keywords(pn) + get_keywords(cat)
                
                # 精确匹配
                if norm_query == pn or norm_query == cat:
                    exact_hits.append(item)
                # 双向模糊匹配（解决"麒麟瓜"匹配"麒麟西瓜"的问题）
                elif (norm_query in pn or norm_query in cat or 
                    pn in norm_query or cat in norm_query):
                    fuzzy_hits.append(item)
                # 关键词匹配（至少匹配一个分词）
                elif any(keyword in item_keywords for keyword in query_keywords):
                    keyword_hits.append(item)
    
        # 结果优先级：精确匹配 > 双向模糊匹配 > 关键词匹配 > 向量检索
        if exact_hits:
            return exact_hits[:k]
        if fuzzy_hits:
            return fuzzy_hits[:k]
        if keyword_hits:
            return keyword_hits[:k]
        # 否则用向量检索
        results = self.collection.query(query_texts=[query], n_results=k)
        hits = []
        if 'metadatas' in results and results['metadatas'] and len(results['metadatas']) > 0:
            for meta in results['metadatas'][0]:
                hits.append(meta)
        return hits
