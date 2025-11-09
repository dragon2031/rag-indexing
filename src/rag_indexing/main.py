"""
Main module for the rag_indexing package.
"""
import os
import sys
from operator import index
from pathlib import Path
from docling.chunking import HierarchicalChunker
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from langchain_core.documents import Document

from rag_indexing.ImageAwareMarkdownHeaderTextSplitter import ImageAwareMarkdownHeaderTextSplitter
from rag_indexing.ImageAwareMarkdownTextSplitter import ImageAwareMarkdownTextSplitter
from rag_indexing.chunker import Chunker
from src.rag_indexing.docling_loader import  DoclingLoader


def main():
    """Main function for the rag_indexing package."""
    print("Hello from rag_indexing!")
    proj_path = Path(sys.prefix).parent
    input_file_path = proj_path.__str__() + "/scratch/input/房地产行业周度观察diy.pptx"

    res = DoclingLoader(input_file_path).load_document()

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    docs = ImageAwareMarkdownHeaderTextSplitter(headers_to_split_on).split_text(res)
    for index, doc in enumerate(docs):
        print(f"切分块: {index}")
        print(f"page content: {doc.page_content}")
        print(f"meta data: {doc.metadata}")
        print("-" * 50)  # 添加分隔线使输出更清晰
    # splitter = ImageAwareMarkdownTextSplitter()
    #
    #
    # documents = splitter.split_text(res)
    # # 优化后的代码
    # for index, doc in enumerate(documents):
    #     print(f"切分块: {index}")
    #     print(f"page content: {doc}")
    #     print(f"meta data: ")
    #     print("-" * 50)  # 添加分隔线使输出更清晰




    # Chunker(HybridChunker()).process(document)




if __name__ == "__main__":
    main()