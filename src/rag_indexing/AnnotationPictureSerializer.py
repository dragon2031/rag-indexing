from typing import Any, Optional

from docling_core.transforms.serializer.base import (
    BaseDocSerializer,
    SerializationResult,
)
from docling_core.transforms.serializer.common import create_ser_result
from docling_core.transforms.serializer.markdown import (
    MarkdownParams,
    MarkdownPictureSerializer,
)
from docling_core.types.doc.document import (
    DoclingDocument,
    ImageRefMode,
    PictureDescriptionData,
    PictureItem,
)
from typing_extensions import override


class AnnotationPictureSerializer(MarkdownPictureSerializer):
    """
    结构化标记法的图片序列化器
    将图片描述包装在 <!-- IMAGE_START --> 和 <!-- IMAGE_END --> 之间
    """
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.sys_prompt="""
你是一个专业的文档数字化专家和数据分析师。
你的任务是精确地阅读文档中提取的图片，并将其内容转换为适合嵌入 Markdown 文档的文本格式。
你需要重点关注数据的准确性、专业术语的正确性以及排版的整洁性。
"""
        self.usr_prompt="""
请分析附带的图片，并根据图片内容类型生成对应的 Markdown 文本，用于替换原文档中的图片占位符。

请严格遵循以下处理逻辑：

### 1. 判断图片类型
首先判断图片的主要内容类型：
- **A. 数据表格 (Table)**：含有明显的行列结构，用于展示具体数值。
- **B. 统计图表 (Chart)**：包含折线图、柱状图、饼图等，用于展示趋势或占比。
- **C. 复合图片 (Composite)**：一张图中包含多个子图表或“左图右表”。
- **D. 普通图片 (General Image)**：照片、示意图、流程图等非数据类图片。

### 2. 根据类型执行转换策略

#### 若为 A. 数据表格：
- **完整转录**：请使用标准的 Markdown 表格格式 (`| head | head |`) 完整转录图中所有文字和数字。
- **保持结构**：尽量保持原有的行列关系。如果存在复杂的合并单元格，请在 Markdown 中尽量用合理的文本方式表达，或者将其拆解为扁平化表格。
- **准确性优先**：严禁修改、猜测模糊不清的数字。如果某处绝对无法辨认，请用 `[不可辨认]` 标记。

#### 若为 B. 统计图表：
- 请生成一段结构化的描述，包含：标题、图例与轴含义、核心数据/趋势总结（这也是最关键的）、以及数据来源。

#### 若为 C. 复合图片：
- 请按从左到右、从上到下的顺序，分别对每个子部分应用上述 A 或 B 的策略。
- 使用三级标题 `###` 区分不同的子部分。

#### 若为 D. 普通图片：
- 提供一段简洁的文字描述，说明图片里的主要内容及其作用。

### 3. 输出格式约束
- **仅输出转换后的 Markdown 内容**，不要包含任何开场白或结束语。
"""


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
        text_parts: list[str] = []

        # 1. 复用父类的基础序列化逻辑
        parent_res = super().serialize(
            item=item,
            doc_serializer=doc_serializer,
            doc=doc,
            **kwargs,
        )
        text_parts.append(parent_res.text)

        # 2. 如果有图片描述注解，使用结构化标记包装
        if item.annotations:
            for annotation in item.annotations:
                if isinstance(annotation, PictureDescriptionData):
                    # 构建结构化的图片描述块
                    structured_description = self._build_structured_description(
                        annotation=annotation,
                        item=item
                    )
                    text_parts.append(structured_description)

        # 3. 拼接结果
        text_res = (separator or "\n").join(text_parts)
        return create_ser_result(text=text_res, span_source=item)

    def _build_structured_description(
            self,
            annotation: PictureDescriptionData,
            item: PictureItem
    ) -> str:
        """
        构建结构化的图片描述块

        格式:
        <!-- IMAGE_START -->
        **[图片描述]**
        - 图片类型: XXX
        - 主要内容: XXX
        - 关键元素: XXX
        <!-- IMAGE_END -->
        """
        description_text = annotation.text.strip()

        # 方案A: 完整结构化格式 (推荐)
        structured_block = f"""
                        <!-- IMAGE_START -->
                        **[图片描述]**
                        - 图片类型: {self._infer_image_type(item)}
                        - 主要内容: {description_text}
                        - 关键元素: {self._extract_key_elements(description_text)}
                        <!-- IMAGE_END -->
                        """

        return structured_block

    def _infer_image_type(self, item: PictureItem) -> str:
        """
        推断图片类型 (可以根据实际情况扩展)
        """
        # 这里可以根据 item 的属性或文件名推断类型
        # 示例逻辑:
        if hasattr(item, 'image_type'):
            return item.image_type

        # 默认分类
        return "图表/示意图"

    def _extract_key_elements(self, description: str) -> str:
        """
        从描述中提取关键元素
        简单实现: 提取前50字作为关键点
        可以用NLP进一步优化
        """
        # 简单截取
        if len(description) > 50:
            return description[:50] + "..."
        return description
