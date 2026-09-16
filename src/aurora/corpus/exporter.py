"""CorpusExporter implementations for Phase C."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import time

from aurora.interfaces.corpus import ICorpusExporter
from aurora.models.training_corpus import ExportFormat, ExportResult, SerializedCorpus


class JSONLExporter(ICorpusExporter):
    """Exports serialized training samples as a JSON Lines (.jsonl) file atomically."""

    def export(self, serialized_corpus: SerializedCorpus, output_path: str) -> ExportResult:
        """Writes serialized corpus samples to the output file path atomically."""
        start_time = time.perf_counter()
        tmp_path = output_path + ".tmp"

        parent_dir = os.path.dirname(os.path.abspath(output_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        sha256_hash = hashlib.sha256()
        bytes_written = 0
        doc_count = len(serialized_corpus.documents)
        sample_count = 0

        # Open in binary write mode to guarantee exact byte control and LF newlines
        with open(tmp_path, "wb") as f:
            for doc in serialized_corpus.documents:
                for sample in doc.samples:
                    sample_count += 1
                    # Ensure stable field ordering via sort_keys
                    line_str = json.dumps(sample.model_dump(), sort_keys=True, ensure_ascii=False) + "\n"
                    line_bytes = line_str.encode("utf-8")

                    f.write(line_bytes)

                    # Compute checksum from the exact UTF-8 bytes written to disk
                    sha256_hash.update(line_bytes)
                    bytes_written += len(line_bytes)

        # Atomically replace target file to prevent partial write visibility
        os.replace(tmp_path, output_path)

        duration = time.perf_counter() - start_time

        return ExportResult(
            output_path=output_path,
            format=ExportFormat.JSONL,
            documents_exported=doc_count,
            samples_exported=sample_count,
            bytes_written=bytes_written,
            checksum=sha256_hash.hexdigest(),
            export_timestamp=datetime.now(timezone.utc),
            export_duration=timedelta(seconds=duration),
        )
