"""
基于 LangChain 现成 Splitter 的图片感知增强
保留 LangChain 的所有强大功能，只添加图片处理能力
"""

import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class ImageBlock:
    """图片块数据结构"""
    content: str  # 原始内容（含标记）
    clean_text: str  # 清理后的文本
    start: int  # 起始位置
    end: int  # 结束位置
    metadata: Dict[str, Any]  # 元数据


class ImageAwareTextSplitterMixin:
    """
    图片感知的 Mixin 类
    可以混入任何 LangChain TextSplitter

    核心思路：
    1. 预处理：识别并标记图片块
    2. 委托：调用原 splitter 的分割逻辑
    3. 后处理：恢复图片块并优化
    """

    def __init__(
            self,
            image_merge_threshold: int = 100,
            merge_strategy: str = "contextual",
            **kwargs
    ):
        """
        Args:
            image_merge_threshold: 图片描述长度阈值
            merge_strategy: 合并策略
                - "contextual": 智能合并（推荐）
                - "separate": 总是独立
                - "inline": 总是内联
        """
        self.image_merge_threshold = image_merge_threshold
        self.merge_strategy = merge_strategy
        self.image_pattern = re.compile(
            r'<!--\s*IMAGE_START\s*-->.*?<!--\s*IMAGE_END\s*-->',
            re.DOTALL | re.IGNORECASE
        )

    def _extract_image_blocks(self, text: str) -> List[ImageBlock]:
        """提取所有图片块"""
        blocks = []
        for match in self.image_pattern.finditer(text):
            raw_content = match.group(0)
            clean_text = self._clean_image_content(raw_content)
            metadata = self._parse_image_metadata(raw_content)

            blocks.append(ImageBlock(
                content=raw_content,
                clean_text=clean_text,
                start=match.start(),
                end=match.end(),
                metadata=metadata
            ))
        return blocks

    def _clean_image_content(self, content: str) -> str:
        """清理图片内容"""
        text = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        text = re.sub(r'\*\*\[图片描述\]\*\*', '', text)
        text = re.sub(r'^[-*]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*|__', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    def _parse_image_metadata(self, content: str) -> Dict[str, Any]:
        """解析图片元数据"""
        metadata = {}
        patterns = {
            'type': r'图片类型[：:]\s*([^\n]+)',
            'main_content': r'主要内容[：:]\s*([^\n]+)',
            'key_elements': r'关键元素[：:]\s*([^\n]+)',
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                metadata[key] = match.group(1).strip()
        return metadata

    def _preprocess_text(self, text: str) -> tuple[str, Dict[str, ImageBlock]]:
        """
        预处理：用占位符替换图片块

        Returns:
            (处理后的文本, 占位符映射)
        """
        image_blocks = self._extract_image_blocks(text)
        if not image_blocks:
            return text, {}

        placeholder_map = {}
        modified_text = text

        for i, block in enumerate(image_blocks):
            placeholder = f"\n__IMAGE_BLOCK_{i}__\n"
            placeholder_map[placeholder.strip()] = block
            modified_text = modified_text.replace(block.content, placeholder)

        return modified_text, placeholder_map

    def _postprocess_chunks(
            self,
            chunks: List[str],
            placeholder_map: Dict[str, ImageBlock]
    ) -> List[str]:
        """
        后处理：根据策略恢复图片块
        """
        if not placeholder_map:
            return chunks

        if self.merge_strategy == "inline":
            return self._restore_inline(chunks, placeholder_map)
        elif self.merge_strategy == "separate":
            return self._restore_separate(chunks, placeholder_map)
        else:  # contextual
            return self._restore_contextual(chunks, placeholder_map)

    def _restore_inline(
            self,
            chunks: List[str],
            placeholder_map: Dict[str, ImageBlock]
    ) -> List[str]:
        """策略：总是内联"""
        result = []
        for chunk in chunks:
            processed = chunk
            for placeholder, block in placeholder_map.items():
                if placeholder in chunk:
                    # 使用简洁的内联格式
                    inline_text = f"\n\n📷 **图片**: {block.clean_text}\n\n"
                    processed = processed.replace(placeholder, inline_text)
            result.append(processed.strip())
        return result

    def _restore_separate(
            self,
            chunks: List[str],
            placeholder_map: Dict[str, ImageBlock]
    ) -> List[str]:
        """策略：总是独立"""
        result = []
        for chunk in chunks:
            has_placeholder = False
            for placeholder, block in placeholder_map.items():
                if placeholder in chunk:
                    has_placeholder = True
                    # 移除占位符，前后文本分开
                    parts = chunk.split(placeholder)
                    for part in parts:
                        if part.strip():
                            result.append(part.strip())
                    # 图片独立成块
                    result.append(f"[IMAGE]\n{block.clean_text}")
                    break

            if not has_placeholder:
                result.append(chunk.strip())

        return [c for c in result if c]

    # def _restore_contextual_old(
    #         self,
    #         chunks: List[str],
    #         placeholder_map: Dict[str, ImageBlock]
    # ) -> List[str]:
    #     """策略：智能决策"""
    #     result = []
    #
    #     for chunk in chunks:
    #         has_image = any(p in chunk for p in placeholder_map.keys())
    #
    #         if not has_image:
    #             result.append(chunk.strip())
    #             continue
    #
    #         # 找到包含的图片块
    #         for placeholder, block in placeholder_map.items():
    #             if placeholder not in chunk:
    #                 continue
    #
    #             # 决策：合并还是独立
    #             should_merge = len(block.clean_text) < self.image_merge_threshold
    #
    #             if should_merge:
    #                 # 合并：内联格式
    #                 inline_text = f"\n\n📷 **图片**: {block.clean_text}\n\n"
    #                 chunk = chunk.replace(placeholder, inline_text)
    #             else:
    #                 # 独立：分成多个chunk
    #                 parts = chunk.split(placeholder)
    #                 for part in parts:
    #                     if part.strip():
    #                         result.append(part.strip())
    #                 result.append(f"[IMAGE]\n{block.clean_text}")
    #                 chunk = ""  # 标记已处理
    #                 break
    #
    #         if chunk.strip():
    #             result.append(chunk.strip())
    #
    #     return [c for c in result if c]
    #
    # # In ImageAwareTextSplitterMixin class

    def _restore_contextual(
            self,
            chunks: List[str],
            placeholder_map: Dict[str, ImageBlock]
    ) -> List[str]:
        """
        策略：智能决策
        [BUG修复版本 - 支持单个 chunk 内有多个占位符]
        """
        final_chunks = []
        # 编译一个正则表达式来一次性找到所有占位符
        # 这比循环 placeholder_map 更高效且能保证顺序
        placeholder_regex = re.compile(f"({'|'.join(re.escape(p) for p in placeholder_map.keys())})")

        for chunk in chunks:
            # 查找当前 chunk 中的所有占位符匹配项
            matches = list(placeholder_regex.finditer(chunk))

            # 如果没有图片，直接添加并继续
            if not matches:
                if chunk.strip():
                    final_chunks.append(chunk.strip())
                continue

            # 按顺序处理文本和图片
            current_pos = 0
            pending_text = ""

            for match in matches:
                placeholder = match.group(1)
                block = placeholder_map[placeholder]

                # 1. 添加占位符之前的文本
                text_before = chunk[current_pos:match.start()].strip()
                if text_before:
                    pending_text += " " + text_before if pending_text else text_before

                # 2. 决策：合并还是独立
                should_merge = len(block.clean_text) < self.image_merge_threshold

                if should_merge:
                    # 合并：将图片内联格式附加到待处理文本中
                    inline_text = f"\n\n📷 **图片**: {block.clean_text}\n\n"
                    pending_text += inline_text
                else:
                    # 独立：
                    # a) 先将之前累积的文本作为一个 chunk
                    if pending_text.strip():
                        final_chunks.append(pending_text.strip())
                        pending_text = ""  # 重置
                    # b) 将图片本身作为一个独立的 chunk
                    final_chunks.append(f"[IMAGE]\n{block.clean_text}")

                # 3. 更新游标位置
                current_pos = match.end()

            # 处理最后一个占位符之后的剩余文本
            remaining_text = chunk[current_pos:].strip()
            if remaining_text:
                pending_text += " " + remaining_text if pending_text else remaining_text

            # 添加最后累积的文本（如果存在）
            if pending_text.strip():
                final_chunks.append(pending_text.strip())

        return [c for c in final_chunks if c]