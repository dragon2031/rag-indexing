import os
import json
from pathlib import Path
from typing import List, Dict, Any
import sys
from datetime import datetime

# 导入 docling
from docling.document_converter import DocumentConverter, ExcelFormatOption, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    VlmExtractionPipelineOptions,
    VlmPipelineOptions,
    PictureDescriptionApiOptions
)
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions, ResponseFormat, AnyUrl
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling.pipeline.extraction_vlm_pipeline import ExtractionVlmPipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.pipeline.simple_pipeline import SimplePipeline



def vlm_options(
        model: str,
        prompt: str,
        format: ResponseFormat,
        scheme_and_host,
        api_key: str = "",
):
    """创建 VLM API 选项（用于 VlmPipeline）"""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    options = ApiVlmOptions(
        url=AnyUrl(f"{scheme_and_host}/chat/completions"),
        params=dict(
            model=model,
        ),
        headers=headers,
        prompt=prompt,
        timeout=600,
        scale=2.0,
        temperature=1,
        response_format=format,
    )
    return options


def picture_description_options(
        model: str,
        scheme_and_host: str,
        api_key: str = "",
        prompt: str = "详细描述这张图片的内容，包括图片中的文字、图表、数据等信息。",
        timeout: float = 600,
        batch_size: int = 8,
        scale: float = 2.0,
):
    """创建图片描述选项（用于 PdfPipelineOptions）"""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    options = PictureDescriptionApiOptions(
        url=AnyUrl(f"{scheme_and_host}/v1/chat/completions"),
        params=dict(
            model=model,
        ),
        headers=headers,
        prompt=prompt,
        timeout=timeout,
        batch_size=batch_size,
        scale=scale,
    )
    return options


def convert_document_with_docling(
        doc_path: str,
        vlm_mode: str = "picture_description"
) -> Dict[str, Any]:
    """
    使用 Docling 转换文档，支持 VLM 处理图片

    Args:
        doc_path: 文档路径
        vlm_mode: VLM 模式（仅对 PDF 有效）
            - "picture_description": 标准 PDF 处理 + VLM 图片描述（推荐）
            - "full_page": 使用 VLM 处理整个页面（包括文本和图片）
    """
    doc_file = Path(doc_path)
    file_ext = doc_file.suffix.lower()

    print(f"\n[转换] 使用 Docling 转换文档: {doc_file.name}")
    print(f"文件类型: {file_ext}")
    if file_ext == '.pdf':
        print(f"VLM 模式: {vlm_mode}")
    print("-" * 60)

    try:
        # api_key = os.getenv("EMBEDDING_API_KEY", "")
        api_key = "AIzaSyDShbYrwu7UJgH0SsKgXn1DGPGmnRaFBaQ"
        # scheme_and_host = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        scheme_and_host = "https://generativelanguage.googleapis.com/v1beta/openai"

        # XLSX 文件使用简单处理
        if file_ext == '.xlsx':
            print("使用VlmPipeline方式：Excel 文件处理")

            # pipeline_options = VlmExtractionPipelineOptions(
            #     enable_remote_services=True,
            # )
            # pipeline_options.vlm_options = vlm_options(
            #     model="qwen3-vl-plus",
            #     scheme_and_host=scheme_and_host,
            #     prompt="OCR the full page to markdown. Include all text, tables, and describe images in detail.",
            #     format=ResponseFormat.MARKDOWN,
            #     api_key=api_key,
            # )

            # 使用 VLM Pipeline
            converter = DocumentConverter(
                format_options={
                    InputFormat.XLSX: ExcelFormatOption(

                        pipeline_cls=SimplePipeline  # VLM 处理管道
                    )
                }
            )
        elif vlm_mode == "picture_description":
            # 方式一：标准 PDF 处理 + VLM 图片描述（推荐）
            # 优点：保持标准 PDF 处理能力（OCR、表格提取等），同时用 VLM 增强图片理解
            print("使用方式：标准 PDF 处理 + VLM 图片描述")

            pipeline_options = PdfPipelineOptions()

            # 启用标准 PDF 处理功能
            pipeline_options.do_ocr = True
            pipeline_options.do_table_structure = True
            pipeline_options.enable_remote_services = True

            # 启用图片处理相关选项
            pipeline_options.generate_picture_images = True  # 生成图片图像
            pipeline_options.do_picture_description = True  # 启用图片描述

            # 配置 VLM 图片描述选项
            pipeline_options.picture_description_options = picture_description_options(
                model="gemini-2.5-flash",
                scheme_and_host=scheme_and_host,
                api_key=api_key,
                prompt="详细描述这张图片的内容，包括图片中的文字、图表、数据等信息。如果图片中包含文字，请完整提取。",
            )

            # 使用标准的 PDF Pipeline
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options,
                        pipeline_cls=StandardPdfPipeline  # 标准 PDF 处理管道
                    ),
                    InputFormat.XLSX: ExcelFormatOption(
                        pipeline_cls=SimplePipeline
                    )
                }
            )

        elif vlm_mode == "full_page":
            # 方式二：使用 VLM 处理整个页面
            # 优点：可以处理复杂布局、混合内容等
            # 缺点：可能不如标准流程稳定，处理速度较慢
            print("使用方式：VLM 完整页面处理")

            pipeline_options = VlmPipelineOptions(
                enable_remote_services=True,
            )
            pipeline_options.vlm_options = vlm_options(
                model="gemini-2.5-flash",
                scheme_and_host=scheme_and_host,
                prompt="OCR the full page to markdown. Include all text, tables, and describe images in detail.",
                format=ResponseFormat.MARKDOWN,
                api_key=api_key,
            )

            # 使用 VLM Pipeline
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options,
                        pipeline_cls=VlmPipeline  # VLM 处理管道
                    )
                }
            )
        else:
            raise ValueError(f"不支持的 vlm_mode: {vlm_mode}，可选值: 'picture_description', 'full_page'")

        # 转换文档
        result = converter.convert(doc_path)

        # 导出为 Markdown
        markdown_content = result.document.export_to_markdown()

        # 导出为 JSON（获取结构化信息）
        json_content = result.document.export_to_dict()

        print(f"✓ 文档转换成功")
        print(f"  - Markdown 长度: {len(markdown_content)} 字符")
        print(f"  - JSON 键: {list(json_content.keys())}")

        return {
            "success": True,
            "markdown": markdown_content,
            "json": json_content,
            "result": result
        }
    except Exception as e:
        print(f"✗ 文档转换失败: {e}")
        return {"success": False, "error": str(e)}


def get_documents_from_folder(folder_path: str = "docs", extensions: List[str] = None,include_files_name:List[str] = None) -> List[Path]:
    """
    从文件夹中获取指定扩展名的文件

    Args:
        folder_path: 文件夹路径
        extensions: 文件扩展名列表，例如 ['.pdf', '.xlsx']

    Returns:
        文件路径列表
    """
    if extensions is None:
        extensions = ['.pdf', '.xlsx']

    folder = Path(folder_path)
    if not folder.exists():
        print(f"错误: 文件夹不存在: {folder_path}")
        return []

    documents = []
    for ext in extensions:
        documents.extend(folder.glob(f"*{ext}"))
        documents.extend(folder.glob(f"*{ext.upper()}"))

    if include_files_name:
        documents = [doc for doc in documents if doc.name in include_files_name]
    # 去重并排序
    documents = sorted(set(documents))
    return documents


def main():
    """主函数 - 批量处理 docs 文件夹下的文档"""
    print("=" * 60)
    print("Docling 批量文档转换工具")
    print("=" * 60)

    # 获取所有需要处理的文档
    proj_path = Path(sys.prefix).parent
    input_file_folder = proj_path.__str__() + "/scratch/input"
    output_file_folder = proj_path.__str__() + "/scratch/output"
    docs_folder = "docs"
    documents = get_documents_from_folder(input_file_folder, extensions=['.pdf', '.xlsx'],include_files_name=['房地产行业周度观察diy.pdf'])

    if not documents:
        print(f"\n错误: 在 {input_file_folder} 文件夹下未找到 PDF 或 XLSX 文件")
        return

    print(f"\n找到 {len(documents)} 个文档:")
    for i, doc in enumerate(documents, 1):
        print(f"  {i}. {doc.name}")

    # 统计信息
    success_count = 0
    fail_count = 0
    processed_files = []

    try:
        # 批量处理每个文档
        for idx, doc_path in enumerate(documents, 1):
            print("\n" + "=" * 60)
            print(f"[{idx}/{len(documents)}] 处理文档: {doc_path.name}")
            print("=" * 60)

            try:
                # 根据文件类型选择处理模式
                # PDF 文件可以使用 VLM 模式，XLSX 文件自动使用简单模式
                if doc_path.suffix.lower() == '.pdf':
                    vlm_mode = "picture_description"
                else:
                    vlm_mode = "picture_description"  # 对于非 PDF 文件，此参数会被忽略

                # 步骤 1: Docling 文档转换
                docling_result = convert_document_with_docling(str(doc_path), vlm_mode=vlm_mode)

                if not docling_result["success"]:
                    print(f"\n✗ 文档 {doc_path.name} 转换失败")
                    fail_count += 1
                    continue

                success_count += 1

                # 保存转换结果
                save_results(
                    docling_result["markdown"],
                    docling_result["json"],
                    doc_name=doc_path.name,
                    output_dir=output_file_folder
                )

                # 文档分块处理（可选）
                # chunker = HybridChunker()
                # chunk_iter = chunker.chunk(dl_doc=docling_result["result"].document)
                # chunk_count = sum(1 for _ in chunk_iter)
                # print(f"✓ 文档分块完成，共 {chunk_count} 个块")

                processed_files.append({
                    "file": doc_path.name,
                    "status": "success",
                    "markdown_length": len(docling_result["markdown"])
                })

            except Exception as e:
                print(f"\n✗ 处理文档 {doc_path.name} 时出错: {e}")
                import traceback
                traceback.print_exc()
                fail_count += 1
                processed_files.append({
                    "file": doc_path.name,
                    "status": "failed",
                    "error": str(e)
                })

        # 打印处理结果汇总
        print("\n" + "=" * 60)
        print("批量处理完成")
        print("=" * 60)
        print(f"总计: {len(documents)} 个文档")
        print(f"成功: {success_count} 个")
        print(f"失败: {fail_count} 个")

        if processed_files:
            print("\n处理详情:")
            for file_info in processed_files:
                status_icon = "✓" if file_info["status"] == "success" else "✗"
                print(f"  {status_icon} {file_info['file']}")
                if file_info["status"] == "success":
                    print(f"      Markdown 长度: {file_info['markdown_length']} 字符")
                else:
                    print(f"      错误: {file_info.get('error', '未知错误')}")

    except KeyboardInterrupt:
        print("\n\n用户中断")
        print(f"已处理: {success_count} 个成功, {fail_count} 个失败")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ 批量处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def save_results(markdown_content: str, json_content: Dict, doc_name: str, output_dir: str = "output"):
    """保存转换结果"""
    print(f"\n[保存] 保存转换结果: {doc_name}")
    print("-" * 60)

    try:
        # 创建输出目录
        Path(output_dir).mkdir(exist_ok=True)

        # 生成文件名（去掉扩展名，添加时间戳）
        base_name = Path(doc_name).stem
        timestamp = datetime.now().strftime("%d%H%M%S")

        # 保存 Markdown
        md_path = Path(output_dir) / f"{base_name}_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"✓ Markdown 已保存: {md_path}")

        # # 保存 JSON
        # json_path = Path(output_dir) / f"{base_name}_{timestamp}.json"
        # with open(json_path, "w", encoding="utf-8") as f:
        #     json.dump(json_content, f, ensure_ascii=False, indent=2)
        # print(f"✓ JSON 已保存: {json_path}")

    except Exception as e:
        print(f"✗ 保存结果失败: {e}")


if __name__ == "__main__":
    main()

