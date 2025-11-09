from typing import Any, Optional

from docling_core.transforms.serializer.base import (
    BaseDocSerializer,
    SerializationResult,
)
from docling_core.transforms.serializer.common import create_ser_result
from docling_core.transforms.serializer.markdown import (
    MarkdownParams,
    MarkdownPictureSerializer, MarkdownTableSerializer,
)
from docling_core.types.doc.document import (
    DoclingDocument,
    ImageRefMode,
    PictureDescriptionData,
    TableItem,
)
from typing_extensions import override

from rag_indexing.config import Config, default_config


class AnnotationTableSerializer(MarkdownTableSerializer):
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Annotation Table Serializer.
        
        Args:
            config: Configuration object. If not provided, uses default_config.
        """
        super().__init__()
        self.config = config or default_config
    
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
        text_parts: list[str] = []

        # reusing the existing result:
        parent_res = super().serialize(
            item=item,
            doc_serializer=doc_serializer,
            doc=doc,
            **kwargs,
        )
        text_parts.append(parent_res.text)

        # appending table caption if exists:
        caption = item.caption_text(doc=doc)
        if caption:
            caption_text = self.config.serializer.TABLE_CAPTION_TEMPLATE.format(caption=caption)
            text_parts.append(caption_text)

        # appending metadata/annotations:
        if item.meta:
            meta_info = []
            for key, value in item.meta.items():
                if value:
                    meta_info.append(f"{key}: {value}")
            if meta_info:
                metadata_text = self.config.serializer.TABLE_METADATA_TEMPLATE.format(
                    metadata=', '.join(meta_info)
                )
                text_parts.append(metadata_text)

        sep = separator or self.config.serializer.DEFAULT_SEPARATOR
        text_res = sep.join(text_parts)
        return create_ser_result(text=text_res, span_source=item)