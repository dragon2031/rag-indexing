"""
Configuration management for RAG indexing project.

This module centralizes all configuration values to avoid magic numbers and strings
scattered throughout the codebase.
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
from langchain_core.runnables import chain
from langchain_core.messages import SystemMessage, HumanMessage


class ModelProvider(Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    LOCAL = "local"


@dataclass
class APIConfig:
    """API configuration for LLM services."""
    
    # Gemini API Configuration
    GEMINI_API_KEY: str = "AIzaSyDShbYrwu7UJgH0SsKgXn1DGPGmnRaFBaQleo"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    GEMINI_CHAT_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Alternative API key (if needed)
    ALTERNATIVE_API_KEY: str = "AIzaSyBvqydy0JtCypEPsoBAVXLqYKV6RRBSvGkleo"
    
    # API Request Settings
    DEFAULT_TIMEOUT: int = 90
    DEFAULT_TEMPERATURE: float = 0.3
    DEFAULT_MAX_TOKENS: int = 1500
    
    # Table Analysis Settings
    TABLE_TEMPERATURE: float = 0.3
    TABLE_MAX_TOKENS: int = 1500
    TABLE_TIMEOUT: int = 60


@dataclass
class PipelineConfig:
    """Pipeline processing configuration."""
    
    # OCR and Image Processing
    ENABLE_OCR: bool = True
    ENABLE_REMOTE_SERVICES: bool = True
    GENERATE_PICTURE_IMAGES: bool = True
    GENERATE_TABLE_IMAGES: bool = True
    DO_PICTURE_DESCRIPTION: bool = True
    
    # Image Scaling
    DEFAULT_IMAGE_SCALE: float = 2.0
    PPTX_IMAGE_SCALE: float = 4.0
    
    # VLM Options
    VLM_SKIP_SPECIAL_TOKENS: bool = False


@dataclass
class PromptConfig:
    """Prompt templates for various tasks."""
    
    # Picture Description Prompt
    PICTURE_DESCRIPTION_PROMPT: str = (
        "为这张图片生成一个简洁但详细的描述，"
        "专注于图片中的关键对象、场景和活动"
    )
    
    # VLM Picture Analysis Prompt
    VLM_PICTURE_PROMPT: str = (
        "你现在是一个图片扫描器，请以 markdown 格式为还原这张图片内容。"
        "如果你看到了图片、表格、图表等请务必不要忽视，"
        "使用占位符标识同时对其加以理解输出内容描述或概括。"
        "另外请直接输出 markdown 数据不要有多余的废话例如：这张图片展示了..."
    )
    
    # Table Analysis Prompt
    TABLE_ANALYSIS_PROMPT: str = (
        "请分析以下表格，并提供一个简洁但全面的解释。"
        "说明表格的主题、关键数据点、趋势或重要发现。"
        "直接输出解释内容，不要有多余的开场白。\n\n"
        "表格标题: {caption}"
    )

    SER_LLM_SYS_PROMPT: str="""
你是一个专业的文档数字化专家和数据分析师。
你的任务是精确地阅读文档中提取的图片，并将其内容转换为适合嵌入 Markdown 文档的文本格式。
你需要重点关注数据的准确性、专业术语的正确性以及排版的整洁性。
"""

    SERL_LLM_USER_PROMPT: str = """
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

    @chain
    def image_analysis_chain(inputs: dict) -> list[SystemMessage | HumanMessage]:
        """
        自定义的 LCEL 链节点，用于将输入的 base64 字符串包装成
        OpenAI Vision API 所需的多模态消息格式。
        """
        base64_image=inputs["base64_image"]
        mine_type=inputs["mine_type"]
        sys_prompt=inputs["sys_prompt"]
        usr_prompt=inputs["usr_prompt"]
        return [
            SystemMessage(content=sys_prompt),
            HumanMessage(
                content=[
                    # 1. 放入我们的文本指令
                    {"type": "text", "text": usr_prompt},
                    # 2. 放入图片数据
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mine_type};base64,{base64_image}"},
                    },
                ]
            ),
        ]


@dataclass
class OutputConfig:
    """Output file configuration."""
    
    # File Extensions
    MARKDOWN_EXT: str = ".md"
    HTML_EXT: str = ".html"
    
    # File Name Patterns
    TIME_FORMAT: str = "%H%M"
    MARKDOWN_SUFFIX: str = "_{time}.md"
    HTML_SUFFIX: str = "_{time}.html"
    SERIALIZED_SUFFIX: str = "_str_{time}.md"
    
    # Image Placeholder
    IMAGE_PLACEHOLDER: str = ""
    
    # Serialization Settings
    INCLUDE_MARKDOWN_TABLE: bool = True


@dataclass
class SerializerConfig:
    """Serializer-specific configuration."""
    
    # Comment Templates
    TABLE_CAPTION_TEMPLATE: str = "<!-- Table caption: {caption} -->"
    TABLE_METADATA_TEMPLATE: str = "<!-- Table metadata: {metadata} -->"
    PICTURE_DESCRIPTION_TEMPLATE: str = "<!-- Picture description: {description} -->"
    
    # Structured Block Templates
    PICTURE_BLOCK_TEMPLATE: str = """
<!-- IMAGE_START -->
**[图片描述]**
- 主要内容: {explanation}
<!-- IMAGE_END -->
"""
    TABLE_BLOCK_TEMPLATE: str = """
<!-- TABLE_START -->
**[图片描述]**
- 主要内容: {explanation}
<!-- TABLE_END -->
"""
    
    # Separator
    DEFAULT_SEPARATOR: str = "\n"


class Config:
    """
    Main configuration class that aggregates all config sections.
    
    Usage:
        from rag_indexing.config import Config
        
        config = Config()
        api_key = config.api.GEMINI_API_KEY
        timeout = config.api.DEFAULT_TIMEOUT
    """
    
    def __init__(
        self,
        api_config: Optional[APIConfig] = None,
        pipeline_config: Optional[PipelineConfig] = None,
        prompt_config: Optional[PromptConfig] = None,
        output_config: Optional[OutputConfig] = None,
        serializer_config: Optional[SerializerConfig] = None,
    ):
        self.api = api_config or APIConfig()
        self.pipeline = pipeline_config or PipelineConfig()
        self.prompt = prompt_config or PromptConfig()
        self.output = output_config or OutputConfig()
        self.serializer = serializer_config or SerializerConfig()
    
    @classmethod
    def from_env(cls) -> "Config":
        """
        Create configuration from environment variables.
        
        This method can be extended to read from environment variables
        or configuration files.
        """
        # TODO: Implement environment variable loading
        return cls()
    
    def update_api_key(self, api_key: str, provider: ModelProvider = ModelProvider.GEMINI):
        """Update API key for a specific provider."""
        if provider == ModelProvider.GEMINI:
            self.api.GEMINI_API_KEY = api_key
    
    def update_model(self, model: str, provider: ModelProvider = ModelProvider.GEMINI):
        """Update model name for a specific provider."""
        if provider == ModelProvider.GEMINI:
            self.api.GEMINI_MODEL = model


# Global default configuration instance
default_config = Config()
