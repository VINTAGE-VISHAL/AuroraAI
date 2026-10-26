"""Runtime text preprocessing and recursive overlapping chunker implementation."""

import hashlib
import re
from typing import List, Optional, Tuple

from aurora.core.exceptions import InvalidChunkingConfigError
from aurora.interfaces.runtime_chunker import IRuntimeChunker
from aurora.models.file_metadata import ExtractedFileResponse
from aurora.models.runtime_chunk import ChunkingConfig, ChunkingResult, DocumentChunk


class RuntimeChunker(IRuntimeChunker):
    """Production runtime text preprocessing and recursive chunker.
    
    1. Normalizes whitespace and line breaks without destroying markdown structure,
       code blocks, lists, or paragraph boundaries.
    2. Chunks documents using natural boundaries (double newline, single newline, sentences, words).
    3. Preserves PDF page attribution when per-page text is present.
    4. Enforces configurable chunk_size, chunk_overlap, and min_chunk_size with strict validation.
    5. Produces deterministic chunk_id, offsets, and non-empty chunks.
    """

    DEFAULT_SEPARATORS: List[str] = [
        "\n\n",   # Paragraph / block boundary
        "\n",     # Line / list item boundary
        ". ",     # Sentence boundary
        "? ",     # Question sentence boundary
        "! ",     # Exclamation sentence boundary
        "; ",     # Clause boundary
        ", ",     # Sub-clause boundary
        " ",      # Word boundary
        "",       # Character fallback
    ]

    def __init__(self, default_config: Optional[ChunkingConfig] = None) -> None:
        self.default_config = default_config or ChunkingConfig()

    def normalize_text(self, text: str) -> str:
        """Cleans irrelevant whitespace while preserving paragraphs, headings, and code blocks.
        
        - Normalizes Windows (\\r\\n) and legacy Mac (\\r) line endings to Unix (\\n).
        - Strips trailing whitespace per line.
        - Compresses runs of 3+ newlines to standard double newlines (\\n\\n).
        - Strips non-printable control characters except tab and newline.
        """
        if not text:
            return ""

        # Normalize line endings
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        # Strip non-printable ASCII control characters (keep \t, \n)
        normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", normalized)

        # Strip trailing horizontal whitespace from every line
        lines = [line.rstrip(" \t") for line in normalized.split("\n")]
        joined = "\n".join(lines)

        # Compress excessive blank lines (3 or more newlines become 2)
        joined = re.sub(r"\n{3,}", "\n\n", joined)

        return joined.strip()

    def validate_config(self, config: ChunkingConfig) -> None:
        """Validates chunking configuration constraints."""
        if config.chunk_size <= 0:
            raise InvalidChunkingConfigError(
                f"chunk_size must be positive, got {config.chunk_size}"
            )
        if config.chunk_overlap < 0:
            raise InvalidChunkingConfigError(
                f"chunk_overlap cannot be negative, got {config.chunk_overlap}"
            )
        if config.chunk_overlap >= config.chunk_size:
            raise InvalidChunkingConfigError(
                f"chunk_overlap ({config.chunk_overlap}) must be strictly less than chunk_size ({config.chunk_size})"
            )
        if config.min_chunk_size <= 0:
            raise InvalidChunkingConfigError(
                f"min_chunk_size must be positive, got {config.min_chunk_size}"
            )
        if config.min_chunk_size > config.chunk_size:
            raise InvalidChunkingConfigError(
                f"min_chunk_size ({config.min_chunk_size}) cannot exceed chunk_size ({config.chunk_size})"
            )

    def _split_text_recursive(
        self,
        text: str,
        separators: List[str],
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[Tuple[str, int, int]]:
        """Splits text recursively using the hierarchical separators.
        
        Returns list of tuples: (chunk_text, start_char_offset, end_char_offset).
        """
        if not text:
            return []

        # Find the highest priority separator present in the text
        selected_sep = separators[-1]
        for sep in separators:
            if sep == "":
                selected_sep = ""
                break
            if sep in text:
                selected_sep = sep
                break

        # Split text into elements by the selected separator
        if selected_sep == "":
            splits = list(text)
        else:
            splits = text.split(selected_sep)

        docs: List[Tuple[str, int, int]] = []
        current_doc: List[str] = []
        current_len = 0
        running_offset = 0

        for s in splits:
            element = s + (selected_sep if selected_sep != "" else "")
            element_len = len(element)

            if current_len + element_len > chunk_size and current_doc:
                chunk_str = "".join(current_doc).strip()
                if chunk_str:
                    # Calculate offsets
                    c_start = text.find(chunk_str, max(0, running_offset - current_len - 10))
                    if c_start == -1:
                        c_start = running_offset - current_len
                    c_end = c_start + len(chunk_str)
                    docs.append((chunk_str, c_start, c_end))

                # Handle overlap by keeping tail elements
                overlap_accum: List[str] = []
                overlap_len = 0
                for item in reversed(current_doc):
                    if overlap_len + len(item) <= chunk_overlap:
                        overlap_accum.insert(0, item)
                        overlap_len += len(item)
                    else:
                        break
                current_doc = overlap_accum
                current_len = overlap_len

            current_doc.append(element)
            current_len += element_len
            running_offset += element_len

        # Append remaining accumulated elements
        if current_doc:
            chunk_str = "".join(current_doc).strip()
            if chunk_str:
                c_start = text.find(chunk_str, max(0, len(text) - len(chunk_str) - 20))
                if c_start == -1:
                    c_start = max(0, len(text) - len(chunk_str))
                c_end = c_start + len(chunk_str)
                docs.append((chunk_str, c_start, c_end))

        # Check if any resulting chunk is still larger than chunk_size (and can be further split)
        final_chunks: List[Tuple[str, int, int]] = []
        next_separators = separators[separators.index(selected_sep) + 1:] if selected_sep in separators else []

        for c_text, c_start, c_end in docs:
            if len(c_text) > chunk_size and next_separators:
                sub_chunks = self._split_text_recursive(
                    c_text,
                    next_separators,
                    chunk_size,
                    chunk_overlap,
                )
                for sc_text, sc_rel_start, sc_rel_end in sub_chunks:
                    final_chunks.append((
                        sc_text,
                        c_start + sc_rel_start,
                        c_start + sc_rel_end,
                    ))
            else:
                final_chunks.append((c_text, c_start, c_end))

        return final_chunks

    def chunk_extracted_document(
        self,
        extracted: ExtractedFileResponse,
        config: Optional[ChunkingConfig] = None,
    ) -> ChunkingResult:
        """Processes extracted document into overlapping chunks with page and offset attribution."""
        cfg = config or self.default_config
        self.validate_config(cfg)

        file_id = extracted.file_id
        filename = extracted.filename
        raw_chunks: List[dict] = []

        # Case 1: Multi-page PDF with per-page text
        if extracted.extension.lower() == ".pdf" and extracted.pages:
            for page_idx, page_raw in enumerate(extracted.pages):
                normalized_page = self.normalize_text(page_raw)
                if not normalized_page:
                    continue

                page_num = page_idx + 1
                page_splits = self._split_text_recursive(
                    normalized_page,
                    self.DEFAULT_SEPARATORS,
                    cfg.chunk_size,
                    cfg.chunk_overlap,
                )

                for c_text, c_start, c_end in page_splits:
                    c_text = c_text.strip()
                    if not c_text:
                        continue
                    raw_chunks.append({
                        "text": c_text,
                        "source_page": page_num,
                        "start_char": c_start,
                        "end_char": c_end,
                    })

        # Case 2: Monolithic document (TXT, DOCX, Markdown, or PDF without page splits)
        else:
            normalized_full = self.normalize_text(extracted.text)
            if normalized_full:
                splits = self._split_text_recursive(
                    normalized_full,
                    self.DEFAULT_SEPARATORS,
                    cfg.chunk_size,
                    cfg.chunk_overlap,
                )
                for c_text, c_start, c_end in splits:
                    c_text = c_text.strip()
                    if not c_text:
                        continue
                    raw_chunks.append({
                        "text": c_text,
                        "source_page": None,  # Page attribution cannot be determined reliably
                        "start_char": c_start,
                        "end_char": c_end,
                    })

        # Post-process: merge tiny residual chunks (if len < min_chunk_size and previous chunk exists from same page)
        filtered_chunks: List[dict] = []
        for rc in raw_chunks:
            if filtered_chunks and len(rc["text"]) < cfg.min_chunk_size:
                prev = filtered_chunks[-1]
                # Merge if from same page
                if prev.get("source_page") == rc.get("source_page"):
                    merged_text = prev["text"] + " " + rc["text"]
                    prev["text"] = merged_text
                    prev["end_char"] = rc["end_char"]
                    continue
            filtered_chunks.append(rc)

        total_chunks = len(filtered_chunks)
        document_chunks: List[DocumentChunk] = []

        for idx, item in enumerate(filtered_chunks):
            chunk_text = item["text"]
            # Deterministic chunk ID generated from file_id, page, index, and text content hash
            page_tag = f"p{item['source_page']}" if item["source_page"] is not None else "p0"
            content_digest = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:8]
            chunk_id = f"{file_id}_{page_tag}_c{idx:04d}_{content_digest}"

            token_estimate = max(1, len(chunk_text.split()))

            doc_chunk = DocumentChunk(
                chunk_id=chunk_id,
                file_id=file_id,
                filename=filename,
                text=chunk_text,
                chunk_index=idx,
                total_chunks=total_chunks,
                source_page=item["source_page"],
                start_char=item["start_char"],
                end_char=item["end_char"],
                char_count=len(chunk_text),
                token_estimate=token_estimate,
            )
            document_chunks.append(doc_chunk)

        total_chars = sum(c.char_count for c in document_chunks)
        return ChunkingResult(
            file_id=file_id,
            filename=filename,
            chunks=document_chunks,
            total_chunks=total_chunks,
            total_characters=total_chars,
            has_content=total_chunks > 0,
        )
