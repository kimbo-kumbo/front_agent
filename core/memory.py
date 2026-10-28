# core/memory.py
import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

QDRANT_HOST = "qdrant" if os.path.exists("/app") else "localhost"
client = QdrantClient(host=QDRANT_HOST, port=6333)

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def get_collection_name(project_name: str) -> str:
    """Генерирует безопасное имя коллекции для Qdrant."""
    # Qdrant любит латиницу и дефисы
    safe_name = "".join(c if c.isalnum() else "_" for c in project_name).lower()
    return f"proj_{safe_name}"

def init_project_db(project_name: str):
    """Создает коллекцию для конкретного проекта, если ее нет."""
    collection_name = get_collection_name(project_name)
    collections = client.get_collections().collections
    if not any(c.name == collection_name for c in collections):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
        )

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

def index_file(project_name: str, file_path: str, content: str):
    """Индексирует файл в коллекцию конкретного проекта."""
    collection_name = get_collection_name(project_name)
    init_project_db(project_name) # На всякий случай создаем коллекцию
    
    # Удаляем старые записи для этого файла
    client.delete(
        collection_name=collection_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key="file_path", match=models.MatchValue(value=file_path))]
            )
        )
    )
    
    chunks = chunk_text(content)
    points = []
    
    for i, chunk in enumerate(chunks):
        vector = model.encode(chunk).tolist()
        points.append(models.PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={"file_path": file_path, "chunk_index": i, "text": chunk}
        ))
        
    if points:
        client.upsert(collection_name=collection_name, points=points)

def search_knowledge(project_name: str, query: str, limit: int = 3) -> str:
    """Ищет в базе конкретного проекта."""
    collection_name = get_collection_name(project_name)
    query_vector = model.encode(query).tolist()
    
    try:
        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
    except Exception:
        return f"База знаний для проекта '{project_name}' пуста или не создана."
    
    if not results:
        return "Ничего не найдено."
        
    result_str = []
    for res in results:
        result_str.append(f"=== Файл: {res.payload['file_path']} ===\n{res.payload['text']}\n")
    return "\n".join(result_str)