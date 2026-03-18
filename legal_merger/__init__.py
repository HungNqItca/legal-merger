"""
legal_merger — Package hợp nhất văn bản pháp lý Việt Nam.

Public API:
    merge_legal_documents(base_file, amendment_files, output_file, ...)
    DocumentParser, AmendmentParser, MergeEngine
    OutputWriter, ComparisonTableBuilder
    Node, Amendment, NodeType, OperationType
    read_file, clean_page_artifacts
"""

from .models import (
    Node, Amendment, ComparisonRow,
    NodeType, OperationType,
)
from .page_cleaner import read_file, clean_page_artifacts, extract_title
from .document_parser import DocumentParser
from .amendment_parser import AmendmentParser
from .merge_engine import MergeEngine
from .output_writer import OutputWriter
from .comparison_builder import ComparisonTableBuilder
from .orchestrator import merge_legal_documents

__all__ = [
    "merge_legal_documents",
    "DocumentParser", "AmendmentParser", "MergeEngine",
    "OutputWriter", "ComparisonTableBuilder",
    "Node", "Amendment", "ComparisonRow",
    "NodeType", "OperationType",
    "read_file", "clean_page_artifacts", "extract_title",
]
