import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"]  = "1"

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np


_model    = None
_index    = None
_texts    = None


_context_cache = {}

def _init_rag():
    global _model, _index, _texts

    if _model is not None:
        return

    print("Chargement RAG...")

    loader1 = PyPDFLoader(r"C:\Users\msi\PycharmProjects\PythonProject\rag_rgpd\CELEX_32016R0679_FR_TXT.pdf")
    loader2 = PyPDFLoader(r"C:\Users\msi\PycharmProjects\PythonProject\rag_rgpd\Donnée sensible _ CNIL.pdf")
    documents = loader1.load() + loader2.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=80,
        separators=["\nArticle ", "\nChapitre ", "\nSection ",
                    "\n\n", "\n", ". "]
    )
    chunks = splitter.split_documents(documents)

    _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    _texts = [chunk.page_content for chunk in chunks]

    embeddings = _model.encode(
        _texts,
        normalize_embeddings=True,
        batch_size=64,
        show_progress_bar=False,
    )
    embeddings = np.array(embeddings).astype('float32')

    _index = faiss.IndexFlatIP(embeddings.shape[1])
    _index.add(embeddings)

    print(f"RAG prêt — {len(_texts)} chunks, {_index.ntotal} vecteurs")

_context_cache = {}

def retrieve_context(column, table="", k=10, seuil=0.50):

    cache_key = f"{table}.{column}" if table else column

    if cache_key in _context_cache:
        return _context_cache[cache_key]

    _init_rag()

    query = f"""Quelle est la classification RGPD pour une donnée appelée "{column}" ?
Niveau de sensibilité, article applicable, mesures de protection."""

    query_embedding = _model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    query_embedding = np.array(query_embedding).astype('float32')

    scores, indices = _index.search(query_embedding, k)

    results = []
    for i, idx in enumerate(indices[0]):
        if scores[0][i] > seuil:
            results.append(_texts[idx])

    result = "\n---\n".join(results) if results else ""

    _context_cache[cache_key] = result

    return result