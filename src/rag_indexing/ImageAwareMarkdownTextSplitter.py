from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownTextSplitter,
    MarkdownHeaderTextSplitter
)
from typing import List, Dict, Any, Optional, Callable

from rag_indexing.ImageAwareTextSplitterMixin import ImageAwareTextSplitterMixin


class ImageAwareMarkdownTextSplitter(
    ImageAwareTextSplitterMixin,
    MarkdownTextSplitter
):
    """
    基于 MarkdownTextSplitter 的图片感知版本
    推荐用于 Markdown 文档
    """

    def __init__(
            self,
            chunk_size: int = 1000,
            chunk_overlap: int = 200,
            image_merge_threshold: int = 100,
            merge_strategy: str = "contextual",
            **kwargs
    ):
        ImageAwareTextSplitterMixin.__init__(
            self,
            image_merge_threshold=image_merge_threshold,
            merge_strategy=merge_strategy
        )

        MarkdownTextSplitter.__init__(
            self,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            **kwargs
        )

    def split_text(self, text: str) -> List[str]:
        """重写分割方法"""
        processed_text, placeholder_map = self._preprocess_text(text)
        chunks = super().split_text(processed_text)
        final_chunks = self._postprocess_chunks(chunks, placeholder_map)
        return final_chunks