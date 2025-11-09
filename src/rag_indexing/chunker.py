from docling.chunking import HierarchicalChunker
from docling_core.transforms.chunker import BaseChunker


class Chunker:
    """
    A class for chunking documents.
    """
    def __init__(self,spliter:BaseChunker):
        self.spliter = spliter

    def process(self, document:[]):
        chunker = self.spliter
        chunk = chunker.chunk(document)

        print("chunk result:")
        for e in chunk:
            print(e)

