import os
from datetime import datetime
from typing import Optional

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
from hierarchical.postprocessor import ResultPostprocessor
from shapely.affinity import scale

from rag_indexing.AnnotationPictureSerializer import AnnotationPictureSerializer
from rag_indexing.AnnotationTableSerializer import AnnotationTableSerializer
from rag_indexing.LLMPictureSerializer import LLMPictureSerializer
from rag_indexing.LLMTableSerializer import LLMTableSerializer
from rag_indexing.config import Config, default_config


def openai_compatible_vlm_options(
        model: str,
        prompt: str,
        format: ResponseFormat,
        hostname_and_port: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: str = "",
        skip_special_tokens: Optional[bool] = None,
        config: Optional[Config] = None,
):
    """
    Create OpenAI-compatible VLM options.
    
    Args:
        model: Model name
        prompt: Prompt template
        format: Response format
        hostname_and_port: API endpoint
        temperature: Temperature (uses config default if not provided)
        max_tokens: Max tokens (uses config default if not provided)
        api_key: API key
        skip_special_tokens: Skip special tokens flag (uses config default if not provided)
        config: Configuration object
    """
    cfg = config or default_config
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    options = ApiVlmOptions(
        url=hostname_and_port,
        params=dict(model=model),
        headers=headers,
        prompt=prompt,
        timeout=cfg.api.DEFAULT_TIMEOUT,
        scale=cfg.pipeline.DEFAULT_IMAGE_SCALE,
        temperature=temperature or cfg.api.DEFAULT_TEMPERATURE,
        response_format=format,
    )
    return options


def vlm_p_options(base_url, api_key):
    """
    Returns the options for the VLM pipeline.
    """
    cfg = default_config
    
    p_options = VlmPipelineOptions(
        enable_remote_services=cfg.pipeline.ENABLE_REMOTE_SERVICES
    )

    p_options.vlm_options = openai_compatible_vlm_options(
        model=cfg.api.GEMINI_MODEL,
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

    def __init__(self, file_path: str, config: Optional[Config] = None):
        self.file_path = file_path
        self.config = config or default_config

    def load_document(self)->str:
        """
        Loads all documents from the directory.

        Returns:
            list: A list of documents.
        """
        cfg = self.config
        
        # Use configuration values
        api_key = cfg.api.ALTERNATIVE_API_KEY
        gemini_key = cfg.api.GEMINI_API_KEY
        base_url = cfg.api.GEMINI_CHAT_URL
        client_base_url = cfg.api.GEMINI_BASE_URL
        
        pdf_p_options = PdfPipelineOptions(
            enable_remote_services=cfg.pipeline.ENABLE_REMOTE_SERVICES,
            do_ocr=cfg.pipeline.ENABLE_OCR,
            generate_picture_images=cfg.pipeline.GENERATE_PICTURE_IMAGES,
            do_picture_description=cfg.pipeline.DO_PICTURE_DESCRIPTION,
            generate_table_images=cfg.pipeline.GENERATE_TABLE_IMAGES,
        )

        pdf_p_options.picture_description_options = PictureDescriptionApiOptions(
            url=base_url,
            params=dict(model=cfg.api.GEMINI_MODEL),
            headers={"Authorization": f"Bearer {gemini_key}"},
            prompt=cfg.prompt.PICTURE_DESCRIPTION_PROMPT,
            timeout=cfg.api.DEFAULT_TIMEOUT
        )

        convt_p_options = ConvertPipelineOptions(
            enable_remote_services=cfg.pipeline.ENABLE_REMOTE_SERVICES,
            do_ocr=cfg.pipeline.ENABLE_OCR,
            generate_picture_images=cfg.pipeline.GENERATE_PICTURE_IMAGES,
            do_picture_description=cfg.pipeline.DO_PICTURE_DESCRIPTION,
            generate_table_images=cfg.pipeline.GENERATE_TABLE_IMAGES,
        )
        convt_p_options.picture_description_options.scale = cfg.pipeline.PPTX_IMAGE_SCALE

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

        ResultPostprocessor(res).process()

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
            config=cfg
        )

        llm_pic_serializer=LLMPictureSerializer(
            api_url=client_base_url,
            api_key=gemini_key,
            config=cfg
        )

        # Option 2: Use simple annotation serializer (comment out one option)
        # table_serializer = AnnotationTableSerializer(config=cfg)

        serializer = MarkdownDocSerializer(
            doc=res.document,
            picture_serializer=llm_pic_serializer,
            table_serializer=llm_table_serializer,  # Use LLM serializer
            params=MarkdownParams(
                image_mode=ImageRefMode.PLACEHOLDER,
                image_placeholder=cfg.output.IMAGE_PLACEHOLDER
            )
        )
        ser_result = serializer.serialize()
        ser_text = ser_result.text



        self._save_document(res.document, doc_str=ser_text)

        return ser_text

    def _save_document(self, document: DoclingDocument, doc_str: str = None):
        """
        Saves all documents to the directory.
        """
        cfg = self.config
        output_dir = os.path.dirname(self.file_path)
        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        now = datetime.now()
        time_str = now.strftime(cfg.output.TIME_FORMAT)
        
        # Build file paths using config
        md_path = os.path.join(output_dir, f"{base_name}_{time_str}{cfg.output.MARKDOWN_EXT}")
        str_path = os.path.join(output_dir, f"{base_name}_str_{time_str}{cfg.output.MARKDOWN_EXT}")
        html_path = os.path.join(output_dir, f"{base_name}_{time_str}{cfg.output.HTML_EXT}")
        
        document.save_as_markdown(md_path)
        document.save_as_html(html_path)
        if doc_str:
            with open(str_path, "w") as f:
                f.write(doc_str)
