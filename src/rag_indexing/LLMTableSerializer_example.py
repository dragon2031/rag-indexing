"""
Example usage of LLMTableSerializer

This example shows how to use the LLM-powered table serializer
to generate intelligent explanations of table content.
"""

from rag_indexing.LLMTableSerializer import LLMTableSerializer

# Example 1: Basic usage with Gemini API
def example_gemini():
    serializer = LLMTableSerializer(
        api_url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        api_key="YOUR_GEMINI_API_KEY",
        model="gemini-2.0-flash-exp",
        include_markdown=True,
    )
    return serializer


# Example 2: Custom prompt template
def example_custom_prompt():
    custom_prompt = """
    Analyze this table and provide:
    1. Main topic and purpose
    2. Key insights or trends
    3. Notable data points
    
    Table Title: {caption}
    
    Table Content:
    {table_markdown}
    """
    
    serializer = LLMTableSerializer(
        api_url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        api_key="YOUR_API_KEY",
        model="gemini-2.0-flash-exp",
        prompt_template=custom_prompt,
        include_markdown=True,
    )
    return serializer


# Example 3: OpenAI compatible API (e.g., local LLM)
def example_local_llm():
    serializer = LLMTableSerializer(
        api_url="http://localhost:8000/v1/chat/completions",
        api_key="not-needed",
        model="llama-3.1-8b",
        include_markdown=False,  # Only output explanation, no markdown table
        timeout=60,
    )
    return serializer


# Example 4: Use in DoclingLoader
def example_in_loader():
    """
    In your docling_loader.py, use it like this:
    
    from rag_indexing.LLMTableSerializer import LLMTableSerializer
    
    llm_table_serializer = LLMTableSerializer(
        api_url=base_url,
        api_key=gemini_key,
        model="gemini-2.0-flash-exp",
        include_markdown=True,
    )
    
    serializer = MarkdownDocSerializer(
        doc=res.document,
        picture_serializer=AnnotationPictureSerializer(),
        table_serializer=llm_table_serializer,
        params=MarkdownParams(
            image_mode=ImageRefMode.PLACEHOLDER,
            image_placeholder="<image-leo>"
        )
    )
    """
    pass


if __name__ == "__main__":
    print("LLMTableSerializer Examples")
    print("=" * 50)
    print("\nSee the example functions above for usage patterns.")
    print("\nKey features:")
    print("- Generates natural language explanations of tables")
    print("- Supports any OpenAI-compatible API")
    print("- Customizable prompts")
    print("- Optional markdown table inclusion")
    print("- Graceful fallback on API errors")
