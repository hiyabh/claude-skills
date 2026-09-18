"""Extractors: input file → list of paragraphs."""
from .docx_x import extract_docx
from .pdf_x import extract_pdf
from .old_doc import extract_old_doc

__all__ = ["extract_docx", "extract_pdf", "extract_old_doc"]
