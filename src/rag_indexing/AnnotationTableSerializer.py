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


class AnnotationTableSerializer(MarkdownTableSerializer):
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
            text_parts.append(f"<!-- Table caption: {caption} -->")

        # appending metadata/annotations:
        if item.meta:
            meta_info = []
            for key, value in item.meta.items():
                if value:
                    meta_info.append(f"{key}: {value}")
            if meta_info:
                text_parts.append(f"<!-- Table metadata: {', '.join(meta_info)} -->")

        text_res = (separator or "\n").join(text_parts)
        return create_ser_result(text=text_res, span_source=item)