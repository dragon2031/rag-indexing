"""
Utility functions for LLM-based serializers.
"""
import base64
import io
from typing import Optional
from PIL import Image
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from rag_indexing.config import PromptConfig


def call_llm(
    llm_client: ChatOpenAI,
    prompt: str,
    image: Optional[Image.Image] = None
) -> str:
    """
    Call LLM API to generate content, using multimodal input if an image is provided.

    Args:
        llm_client: The LangChain ChatOpenAI client instance.
        prompt: The text prompt to send to the LLM.
        image: A PIL Image object, if available.

    Returns:
        LLM generated text.
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
        
        response = llm_client.invoke([message])
        
        # Ensure we return a string
        return str(response.content).strip() if response.content else ""

    except Exception as e:
        print(f"Warning: LLM call failed: {e}")
        return ""

def call_llm_chain(
    llm_client: ChatOpenAI,
    prompt_cfg: PromptConfig,
    image: Optional[Image.Image] = None)-> str:

    img_base64=''
    if image:
        # Convert PIL image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    # Build the chain first, then invoke it
    chain = PromptConfig.image_analysis_chain | llm_client
    response = chain.invoke({
        "base64_image": img_base64,
        "mine_type": 'image/png',
        "sys_prompt": prompt_cfg.SER_LLM_SYS_PROMPT,
        "usr_prompt": prompt_cfg.SERL_LLM_USER_PROMPT
    })
    # Ensure we return a string
    return str(response.content).strip() if response.content else ""