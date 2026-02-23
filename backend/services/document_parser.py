"""使用 LangChain 解析并切片文档"""
import os
import tempfile

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


async def parse_and_split(filename: str, file_bytes: bytes) -> tuple[str, int]:
    """
    解析文件内容并切片，返回 (全文本, 切片数量)
    支持 .docx/.pdf/.md/.txt 及其他纯文本格式
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        if ext in ("docx", "doc"):
            loader = Docx2txtLoader(tmp_path)
        elif ext == "pdf":
            loader = PyPDFLoader(tmp_path)
        elif ext in ("md", "markdown"):
            # 延迟导入，避免未安装 unstructured 时报错
            from langchain_community.document_loaders import UnstructuredMarkdownLoader
            loader = UnstructuredMarkdownLoader(tmp_path)
        else:
            # txt / csv / json / xml / html 等纯文本
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(tmp_path, encoding="utf-8", autodetect_encoding=True)

        docs = loader.load()
        full_text = "\n\n".join(d.page_content for d in docs)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        chunks = splitter.split_text(full_text)

        if not chunks:
            return full_text or f"[无法提取文本内容: {filename}]", 1

        content = "\n\n".join(chunks)
        return content, len(chunks)
    finally:
        os.unlink(tmp_path)
