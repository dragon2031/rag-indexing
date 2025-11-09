from typing import Any, Optional
from PIL import Image

from docling_core.transforms.serializer.base import (
    BaseDocSerializer,
    BasePictureSerializer,
    SerializationResult,
)
from docling_core.transforms.serializer.common import create_ser_result
from docling_core.transforms.serializer.markdown import MarkdownPictureSerializer
from docling_core.types.doc.document import DoclingDocument, PictureItem
from typing_extensions import override
from langchain_openai import ChatOpenAI

from rag_indexing.config import Config, default_config
from rag_indexing.llm_utils import call_llm, call_llm_chain


class LLMPictureSerializer(BasePictureSerializer):
    """
    A picture serializer that uses a multimodal LLM to generate natural language
    descriptions of picture content, using image input.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        prompt_template: Optional[str] = None,
        timeout: Optional[int] = None,
        config: Optional[Config] = None,
    ):
        """
        Initialize the LLM Picture Serializer.

        Args:
            api_url: The API endpoint URL (e.g., OpenAI compatible endpoint)
            api_key: API key for authentication
            model: Model name to use
            prompt_template: Custom prompt template.
            timeout: Request timeout in seconds.
            config: Configuration object. If not provided, uses default_config.
        """
        # Use provided config or default
        cfg = config or default_config
        
        final_api_url = api_url or cfg.api.GEMINI_BASE_URL
        final_api_key = api_key or cfg.api.GEMINI_API_KEY
        final_model = model or cfg.api.GEMINI_MODEL
        final_timeout = timeout or cfg.api.DEFAULT_TIMEOUT

        # Initialize the LangChain client
        self.llm_client = ChatOpenAI(
            model=final_model,
            api_key=final_api_key,
            base_url=final_api_url,
            temperature=cfg.api.DEFAULT_TEMPERATURE,
            max_tokens=cfg.api.DEFAULT_MAX_TOKENS,
            request_timeout=final_timeout,
        )

        # Use provided prompt or default from config
        self.prompt_template = prompt_template or cfg.prompt.PICTURE_DESCRIPTION_PROMPT

        # Fallback markdown serializer
        self._markdown_serializer = MarkdownPictureSerializer()
        
        # Store config for later use
        self.config = cfg



    @override
    def serialize(
        self,
        *,
        item: PictureItem,
        doc_serializer: BaseDocSerializer,
        doc: DoclingDocument,
        separator: Optional[str] = None,
        **kwargs: Any,
    ) -> SerializationResult:
        """
        Serialize picture with LLM-generated description.

        Args:
            item: The picture item to serialize.
            doc_serializer: The document serializer.
            doc: The document containing the picture.
            separator: Separator for joining text parts.
            **kwargs: Additional arguments.

        Returns:
            Serialization result with picture and description.
        """
        text_parts: list[str] = []
        llm_description = ""

        # Try to get picture as an image
        picture_image = item.get_image(doc)

        if picture_image:
            # Use image for description
            prompt = self.prompt_template
            llm_description = call_llm_chain(self.llm_client, self.config.prompt, image=picture_image)
        else:
            print("Warning: No image found for picture. Skipping LLM description.")

        # Add LLM description if available
        if llm_description:
            desc_text = self.config.serializer.PICTURE_BLOCK_TEMPLATE.format(
                explanation=llm_description
            )
            text_parts.append(desc_text)

        text_res = (separator or "\n").join(text_parts)
        return create_ser_result(text=text_res, span_source=item)
