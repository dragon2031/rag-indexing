"""
Main module for the rag_indexing package.
"""
import os
import sys
from pathlib import Path
from docling.chunking import HierarchicalChunker
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker

from rag_indexing.chunker import Chunker
from src.rag_indexing.docling_loader import  DoclingLoader


def main():
    """Main function for the rag_indexing package."""
    print("Hello from rag_indexing!")
    proj_path = Path(sys.prefix).parent
    input_file_path = proj_path.__str__() + "/scratch/input/房地产行业周度观察diy.pptx"
    document = DoclingLoader(input_file_path).load_document()

    # Chunker(HybridChunker()).process(document)




if __name__ == "__main__":
    main()