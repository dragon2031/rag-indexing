from typing import Any, Optional
import base64
import io
from PIL import Image

from docling_core.transforms.serializer.base import (
    BaseDocSerializer,
    BaseTableSerializer,
    SerializationResult,
)
from docling_core.transforms.serializer.common import create_ser_result
from docling_core.transforms.serializer.markdown import MarkdownTableSerializer
from docling_core.types.doc.document import DoclingDocument, TableItem
from typing_extensions import override
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


class LLMTableSerializer(BaseTableSerializer):
    """
    A table serializer that uses a multimodal LLM to generate natural language
    explanations of table content, preferring image input when available.
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        prompt_template: Optional[str] = None,
        include_markdown: bool = True,
        timeout: int = 60,
    ):
        """
        Initialize the LLM Table Serializer.

        Args:
            api_url: The API endpoint URL (e.g., OpenAI compatible endpoint)
            api_key: API key for authentication
            model: Model name to use
            prompt_template: Custom prompt template. Use {caption} as a placeholder.
                             If no image is available, {table_markdown} will be appended.
            include_markdown: Whether to include the original markdown table along with the explanation.
            timeout: Request timeout in seconds.
        """
        self.include_markdown = include_markdown

        # Initialize the LangChain client
        self.llm_client = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=api_url,
            temperature=0.3,
            max_tokens=1500,
            request_timeout=timeout,
        )

        # Default prompt template for multimodal input
        self.prompt_template = prompt_template or (
            "请分析以下表格，并提供一个简洁但全面的解释。"
            "说明表格的主题、关键数据点、趋势或重要发现。"
            "直接输出解释内容，不要有多余的开场白。\n\n"
            "表格标题: {caption}"
        )

        # Fallback markdown serializer
        self._markdown_serializer = MarkdownTableSerializer()

    def _call_llm(self, prompt: str, image: Optional[Image.Image] = None) -> str:
        """
        Call LLM API to generate table explanation, using multimodal input if an image is provided.

        Args:
            prompt: The text prompt to send to the LLM.
            image: A PIL Image object of the table, if available.

        Returns:
            LLM generated explanation text.
        """
        try:
            content = []
            
            # Add text prompt first
            content.append({"type": "text", "text": prompt})
            
            # Add image if available
            if image:
                # Convert PIL image to base64
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                })
            
            message = HumanMessage(content=content)
            
            response = self.llm_client.invoke([message])
            
            # Ensure we return a string
            return str(response.content).strip() if response.content else ""

        except Exception as e:
            print(f"Warning: LLM call failed for table explanation: {e}")
            return ""

    @override
    def serialize(
        self,
        *,
        item: TableItem,
        doc_serializer: BaseDocSerializer,
        doc: DoclingDocument,
        separator: Optional[str] = None,
        **kwargs: Any,
    ) -> SerializationResult:
        """
        Serialize table with LLM-generated explanation, preferring image analysis.

        Args:
            item: The table item to serialize.
            doc_serializer: The document serializer.
            doc: The document containing the table.
            separator: Separator for joining text parts.
            **kwargs: Additional arguments.

        Returns:
            Serialization result with table and explanation.
        """
        text_parts: list[str] = []
        llm_explanation = ""

        # Get table caption
        caption = item.caption_text(doc=doc) or "无标题"
        
        # Try to get table as an image first
        table_image = item.get_image(doc)

        if table_image:
            # Use image for explanation
            prompt = self.prompt_template.format(caption=caption)
            llm_explanation = self._call_llm(prompt, image=table_image)
        else:
            # Fallback to markdown text if no image is available
            print("Warning: No image found for table. Falling back to markdown text analysis.")
            markdown_res = self._markdown_serializer.serialize(
                item=item, doc_serializer=doc_serializer, doc=doc, **kwargs
            )
            table_markdown = markdown_res.text
            
            prompt = self.prompt_template.format(caption=caption)
            prompt += f"\n\n表格内容:\n{table_markdown}"
            llm_explanation = self._call_llm(prompt)

        # Get markdown representation for inclusion in the output if required
        # if self.include_markdown:
        #     markdown_res = self._markdown_serializer.serialize(
        #         item=item, doc_serializer=doc_serializer, doc=doc, **kwargs
        #     )
        #     text_parts.append(markdown_res.text)

        if llm_explanation:
            structured_block = f"""
                            <!-- TABLE_START -->
                            **[图片描述]**
                            - 主要内容: {llm_explanation}
                            <!-- TABLE_END -->
                            """
            text_parts.append(structured_block)

        # Add metadata if available
        if item.meta:
            meta_info = []
            for key, value in item.meta.items():
                if value:
                    meta_info.append(f"{key}: {value}")
            if meta_info:
                text_parts.append(f"<!-- Table metadata: {', '.join(meta_info)} -->")

        text_res = (separator or "\n").join(text_parts)
        return create_ser_result(text=text_res, span_source=item)
