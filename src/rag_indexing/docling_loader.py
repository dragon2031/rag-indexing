import os
from datetime import datetime

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, PictureDescriptionApiOptions, \
    PictureDescriptionVlmOptions, granite_picture_description, VlmPipelineOptions, ConvertPipelineOptions, \
    smolvlm_picture_description
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions, ResponseFormat
from docling.document_converter import DocumentConverter, PdfFormatOption, PowerpointFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling_core.transforms.chunker.hierarchical_chunker import TripletTableSerializer
from docling_core.transforms.serializer.markdown import MarkdownDocSerializer, MarkdownParams
from docling_core.types import DoclingDocument
from docling_core.types.doc import PictureItem, ImageRefMode, TableItem
from shapely.affinity import scale

from rag_indexing.AnnotationPictureSerializer import AnnotationPictureSerializer
from rag_indexing.AnnotationTableSerializer import AnnotationTableSerializer
from rag_indexing.LLMTableSerializer import LLMTableSerializer


def openai_compatible_vlm_options(
        model: str,
        prompt: str,
        format: ResponseFormat,
        hostname_and_port,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        api_key: str = "",
        skip_special_tokens=False,
):
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    options = ApiVlmOptions(
        url=hostname_and_port,  # LM studio defaults to port 1234, VLLM to 8000
        params=dict(
            model=model
        ),
        headers=headers,
        prompt=prompt,
        timeout=90,
        scale=2.0,
        temperature=temperature,
        response_format=format,
    )
    return options


def vlm_p_options(base_url, api_key):
    """
    Returns the options for the VLM pipeline.
    """
    p_options = VlmPipelineOptions(
        enable_remote_services=True
        # do_picture_classification=True,
        # do_picture_description=True,

    )

    p_options.vlm_options = openai_compatible_vlm_options(
        model="gemini-2.5-flash",
        prompt="你现在是一个图片扫描器，请以 markdown 格式为还原这张图片内容。如果你看到了图片、表格、图表等请务必不要忽视，使用占位符标识同时对其加以理解输出内容描述或概括。另外请直接输出 markdown 数据不要有多余的废话例如：“这张图片展示了...”",
        format=ResponseFormat.MARKDOWN,
        hostname_and_port=base_url,
        api_key=api_key
    )

    return p_options


class DoclingLoader:
    """
    A class for loading documents from a directory.
    """

    def __init__(self, file_path):
        self.file_path = file_path

    def load_document(self):
        """
        Loads all documents from the directory.

        Returns:
            list: A list of documents.
        """

        api_key = "AIzaSyBvqydy0JtCypEPsoBAVXLqYKV6RRBSvGk"
        gemini_key = "AIzaSyDShbYrwu7UJgH0SsKgXn1DGPGmnRaFBaQ"
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        client_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        pdf_p_options = PdfPipelineOptions(
            enable_remote_services=True,
            do_ocr=True,
            generate_picture_images=True,
            do_picture_description=True,
            generate_table_images=True,
        )

        pdf_p_options.picture_description_options = PictureDescriptionApiOptions(
            url=base_url,
            params=dict(
                model="gemini-2.5-flash"
            ),
            headers={"Authorization": f"Bearer {gemini_key}"},
            prompt="为这张图片生成一个简洁但详细的描述，专注于图片中的关键对象、场景和活动",
            timeout=90
        )

        convt_p_options = ConvertPipelineOptions(
            enable_remote_services=True,
            do_ocr=True,
            generate_picture_images=True,
            do_picture_description=True,
            generate_table_images=True,
        )
        convt_p_options.picture_description_options.scale=4

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    # pipeline_options=vlm_p_options(base_url,api_key),
                    # pipeline_cls=VlmPipeline
                    pipeline_options=pdf_p_options
                ),
                InputFormat.PPTX: PowerpointFormatOption(
                    pipeline_options=convt_p_options,
                )

            }
        )

        res = converter.convert(self.file_path)
        print("pic/tbl annotation show::::::")
        for element, _level in res.document.iterate_items():
            if isinstance(element, PictureItem):
                print(
                    f"Picture {element.self_ref}\n"
                    f"Caption: {element.caption_text(doc=res.document)}\n"  # 标题
                    f"Annotations: {element.annotations}"
                )
            if isinstance(element, TableItem):
                print(
                    f"Table {element.self_ref}\n"
                    f"Cap   tion: {element.caption_text(doc=res.document)}\n"  # 标题
                    f"Annotations: {element.meta}"
                )

        print("diy serializer::::")

        # Option 1: Use LLM Table Serializer for intelligent table explanation
        llm_table_serializer = LLMTableSerializer(
            api_url=client_base_url,
            api_key=gemini_key,
            model="gemini-2.5-flash",
            include_markdown=True,  # Include both markdown table and explanation
        )

        # Option 2: Use simple annotation serializer (comment out one option)
        # table_serializer = AnnotationTableSerializer()

        serializer = MarkdownDocSerializer(
            doc=res.document,
            picture_serializer=AnnotationPictureSerializer(),
            table_serializer=llm_table_serializer,  # Use LLM serializer
            params=MarkdownParams(
                image_mode=ImageRefMode.PLACEHOLDER,
                image_placeholder=""
            )
        )
        ser_result = serializer.serialize()
        ser_text = ser_result.text

        self._save_document(res.document, doc_str=ser_text)

        return res.document

    def _save_document(self, document: DoclingDocument, doc_str: str = None):
        """
        Saves all documents to the directory.
        """
        output_dir = os.path.dirname(self.file_path)
        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        now = datetime.now()
        time_str = now.strftime("%H%M")
        md_path = os.path.join(output_dir, f"{base_name}_{time_str}.md")
        str_path = os.path.join(output_dir, f"{base_name}_str_{time_str}.md")

        html_path = os.path.join(output_dir, f"{base_name}_{time_str}.html")
        document.save_as_markdown(md_path)
        document.save_as_html(html_path)
        if doc_str:
            with open(str_path, "w") as f:
                f.write(doc_str)
