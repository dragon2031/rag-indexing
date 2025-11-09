from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

from rag_indexing.ImageAwareTextSplitterMixin import ImageAwareTextSplitterMixin


class ImageAwareMarkdownHeaderTextSplitter(
    ImageAwareTextSplitterMixin,
    MarkdownHeaderTextSplitter
):
    """
    基于 MarkdownHeaderTextSplitter 的图片感知版本
    推荐用于按标题层级分割的场景
    """

    def __init__(
            self,
            headers_to_split_on: List[tuple],
            image_merge_threshold: int = 100,
            merge_strategy: str = "contextual",
            **kwargs
    ):
        ImageAwareTextSplitterMixin.__init__(
            self,
            image_merge_threshold=image_merge_threshold,
            merge_strategy=merge_strategy
        )

        MarkdownHeaderTextSplitter.__init__(
            self,
            headers_to_split_on=headers_to_split_on,
            **kwargs
        )

    # def split_text_old(self, text: str) -> List[Document]:
    #     """重写分割方法（返回 Document）"""
    #     processed_text, placeholder_map = self._preprocess_text(text)
    #
    #     # 调用父类分割（返回 Document 列表）
    #     docs = super().split_text(processed_text)
    #
    #     # 后处理每个 Document 的内容
    #     for doc in docs:
    #         chunks = self._postprocess_chunks([doc.page_content], placeholder_map)
    #         if not chunks:
    #             continue
    #         first_chunk = processed_chunks.pop(0)
    #         final_docs.append(Document(page_content=first_chunk, metadata=doc.metadata))
    #
    #         # 如果产生了额外的块（通常是独立的图片块），为它们创建新的 Document
    #         # 这些新 Document 继承父块的元数据（如标题信息）
    #         for extra_chunk in processed_chunks:
    #             final_docs.append(Document(page_content=extra_chunk, metadata=doc.metadata.copy()))
    #
    #         if chunks:
    #             doc.page_content = chunks[0]
    #
    #     return docs

    def split_text(self, text: str) -> List[Document]:
        """
        重写分割方法（返回 Document）
        [BUG修复版本]
        """
        processed_text, placeholder_map = self._preprocess_text(text)

        # 1. 调用父类分割（返回 Document 列表）
        initial_docs = super().split_text(processed_text)

        # 如果没有图片，直接返回，避免不必要的处理
        if not placeholder_map:
            return initial_docs

        # 2. 创建一个新的列表来存放最终结果
        final_docs: List[Document] = []

        # 3. 后处理每个 Document 的内容
        for doc in initial_docs:
            # 对每个 doc 的内容进行后处理，这可能返回多个文本块
            processed_chunks = self._postprocess_chunks([doc.page_content], placeholder_map)

            if not processed_chunks:
                continue

            # 4. 根据返回的文本块列表，生成新的 Document
            # 第一个块可以重用原始 doc 的元数据
            first_chunk = processed_chunks.pop(0)
            final_docs.append(Document(page_content=first_chunk, metadata=doc.metadata))

            # 如果产生了额外的块（通常是独立的图片块），为它们创建新的 Document
            # 这些新 Document 继承父块的元数据（如标题信息）
            for extra_chunk in processed_chunks:
                final_docs.append(Document(page_content=extra_chunk, metadata=doc.metadata.copy()))

        return final_docs

