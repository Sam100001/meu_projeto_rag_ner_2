import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List

# Caminho para o arquivo de contexto
CAMINHO_CONTEXTO = "data/contextos/jurisprudencia_responsabilidade_civil.txt"

# Configurações de chunk
CHUNK_SIZE = 1200       # tamanho do chunk em caracteres
CHUNK_OVERLAP = 250     # overlap para manter continuidade entre chunks
RETRIEVER_K = 5         # número de documentos retornados pelo retriever

def carregar_documentos(caminho: str) -> List:
    """
    Carrega o texto do arquivo e cria uma lista de documentos divididos em chunks.
    """
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Arquivo de contexto não encontrado: {caminho}")

    with open(caminho, "r", encoding="utf-8") as f:
        texto = f.read().strip()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    return splitter.create_documents([texto])

def criar_retriever() -> FAISS:
    """
    Cria e retorna um retriever FAISS configurado com embeddings HuggingFace.
    """
    device = os.getenv("EMBEDDINGS_DEVICE", "cpu")  # 'cpu' ou 'cuda'
    model_name = "BAAI/bge-m3"
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": device}
    )

    documentos = carregar_documentos(CAMINHO_CONTEXTO)
    vetorstore = FAISS.from_documents(documentos, embeddings)

    retriever = vetorstore.as_retriever(
        search_type="mmr",  # Maximal Marginal Relevance
        search_kwargs={
            "k": RETRIEVER_K,
            "lambda_mult": 0.5
        }
    )
    return retriever

# Lazy loading do retriever
_retriever_global = None

def get_retriever() -> FAISS:
    """
    Retorna o retriever global, criando se ainda não existir.
    """
    global _retriever_global
    if _retriever_global is None:
        _retriever_global = criar_retriever()
    return _retriever_global

def recuperar_contexto(query: str, k: int = RETRIEVER_K) -> str:
    """
    Recupera os k documentos mais relevantes para a query dada.
    Retorna um texto pronto para injetar no prompt.
    """
    retriever = get_retriever()
    documentos = retriever.get_relevant_documents(query)
    contexto = "\n".join(doc.page_content.strip() for doc in documentos[:k] if doc.page_content.strip())
    return contexto.strip()

def recuperar_contexto_injetado(texto_base: str, query: str) -> str:
    """
    Retorna o texto base com o contexto recuperado injetado no início.
    """
    contexto = recuperar_contexto(query)
    return f"{contexto}\n\n{texto_base}"
