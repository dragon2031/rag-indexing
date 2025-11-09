from typing import Any, Optional
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

from rag_indexing.config import Config, default_config
from rag_indexing.llm_utils import call_llm, call_llm_chain


class LLMTableSerializer(BaseTableSerializer):
    """
    A table serializer that uses a multimodal LLM to generate natural language
    explanations of table content, preferring image input when available.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        prompt_template: Optional[str] = None,
        include_markdown: Optional[bool] = None,
        timeout: Optional[int] = None,
        config: Optional[Config] = None,
    ):
        """
        Initialize the LLM Table Serializer.

        Args:
            api_url: The API endpoint URL (e.g., OpenAI compatible endpoint)
            api_key: API key for authentication
            model: Model name to use
            prompt_template: Custom prompt template. Use {caption} as a placeholder.
            include_markdown: Whether to include the original markdown table along with the explanation.
            timeout: Request timeout in seconds.
            config: Configuration object. If not provided, uses default_config.
        """
        # Use provided config or default
        cfg = config or default_config
        
        # Use provided values or fall back to config
        self.include_markdown = include_markdown if include_markdown is not None else cfg.output.INCLUDE_MARKDOWN_TABLE
        
        final_api_url = api_url or cfg.api.GEMINI_BASE_URL
        final_api_key = api_key or cfg.api.GEMINI_API_KEY
        final_model = model or cfg.api.GEMINI_MODEL
        final_timeout = timeout or cfg.api.TABLE_TIMEOUT

        # Initialize the LangChain client
        self.llm_client = ChatOpenAI(
            model=final_model,
            api_key=final_api_key,
            base_url=final_api_url,
            temperature=cfg.api.TABLE_TEMPERATURE,
            max_tokens=cfg.api.TABLE_MAX_TOKENS,
            request_timeout=final_timeout,
        )

        # Use provided prompt or default from config
        self.prompt_template = prompt_template or cfg.prompt.TABLE_ANALYSIS_PROMPT

        # Fallback markdown serializer
        self._markdown_serializer = MarkdownTableSerializer()
        
        # Store config for later use
        self.config = cfg

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
            llm_explanation = call_llm_chain(self.llm_client, self.config.prompt, image=table_image)
        else:
            # Fallback to markdown text if no image is available
            print("Warning: No image found for table. Falling back to markdown text analysis.")
            markdown_res = self._markdown_serializer.serialize(
                item=item, doc_serializer=doc_serializer, doc=doc, **kwargs
            )
            table_markdown = markdown_res.text
            
            prompt = self.prompt_template.format(caption=caption)
            prompt += f"\n\n表格内容:\n{table_markdown}"
            llm_explanation = call_llm(self.llm_client, prompt)

        # Get markdown representation for inclusion in the output if required
        # if self.include_markdown:
        #     markdown_res = self._markdown_serializer.serialize(
        #         item=item, doc_serializer=doc_serializer, doc=doc, **kwargs
        #     )
        #     text_parts.append(markdown_res.text)

        if llm_explanation:
            structured_block = self.config.serializer.TABLE_BLOCK_TEMPLATE.format(
                explanation=llm_explanation
            )
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
