"""CorpusValidator implementation for Phase C."""

import hashlib
from aurora.core.exceptions import InterfaceError
from aurora.interfaces.corpus import ICorpusValidator
from aurora.models.training_corpus import CorpusValidationResult, TrainingCorpus


class CorpusValidator(ICorpusValidator):
    """Validates the self-consistency and invariants of a TrainingCorpus."""

    def validate(self, corpus: TrainingCorpus) -> CorpusValidationResult:
        """Executes strict internal validations across 7 distinct contracts, returning the validation report."""
        struct_ok = self._validate_structure(corpus)
        dup_ok = self._validate_duplicates(corpus)
        trace_ok = self._validate_traceability(corpus)
        order_ok = self._validate_ordering(corpus)
        comp_ok = self._validate_completeness(corpus)
        det_id_ok = self._validate_deterministic_ids(corpus)
        meta_ok = self._validate_metadata(corpus)

        passed = struct_ok and comp_ok and order_ok and dup_ok and trace_ok and det_id_ok and meta_ok

        if not passed:
            raise InterfaceError("Corpus validation failed. One or more invariants were violated.")

        return CorpusValidationResult(
            passed=passed,
            samples_checked=sum(len(d.samples) for d in corpus.documents),
            documents_checked=len(corpus.documents),
            completeness=comp_ok,
            ordering=order_ok,
            duplication=dup_ok,
            traceability=trace_ok,
            deterministic_ids=det_id_ok,
            metadata=meta_ok,
            structural_integrity=struct_ok,
        )

    def _validate_structure(self, corpus: TrainingCorpus) -> bool:
        """Validates basic corpus structural integrity (presence of docs/samples and sequence contiguity)."""
        if not corpus.documents:
            raise InterfaceError("Structural Integrity failed: Corpus contains no documents.")

        for doc in corpus.documents:
            if not doc.samples:
                raise InterfaceError(f"Structural Integrity failed: Document '{doc.doc_id}' has no samples.")

            # Validate that sequence numbers start at 1 and are contiguous
            seqs = [sample.sequence_number for sample in doc.samples]
            expected_seqs = list(range(1, len(doc.samples) + 1))
            if seqs != expected_seqs:
                raise InterfaceError(
                    f"Structural Integrity failed: Sequence numbers must be contiguous and start at 1 for doc '{doc.doc_id}'. Got: {seqs}"
                )

        return True

    def _validate_completeness(self, corpus: TrainingCorpus) -> bool:
        """Validates that all samples contain non-empty text."""
        for doc in corpus.documents:
            for sample in doc.samples:
                if not sample.text or not sample.text.strip():
                    raise InterfaceError(
                        f"Completeness failed: Sample '{sample.sample_id}' has empty text content."
                    )
        return True

    def _validate_ordering(self, corpus: TrainingCorpus) -> bool:
        """Validates ordering invariants (sequence numbers start at 1 and are contiguous)."""
        for doc in corpus.documents:
            seqs = [sample.sequence_number for sample in doc.samples]
            expected_seqs = list(range(1, len(doc.samples) + 1))
            if seqs != expected_seqs:
                raise InterfaceError(
                    f"Ordering failed: Sequence numbers not contiguous in doc '{doc.doc_id}'."
                )
        return True

    def _validate_duplicates(self, corpus: TrainingCorpus) -> bool:
        """Validates that no sample IDs, document IDs, or source segments are duplicated."""
        seen_corpus_sample_ids = set()
        seen_document_ids = set()
        seen_global_seg_ids = set()

        for doc in corpus.documents:
            # Check duplicate document IDs
            if doc.doc_id in seen_document_ids:
                raise InterfaceError(f"Duplicate failed: Duplicate document ID '{doc.doc_id}' found in corpus.")
            seen_document_ids.add(doc.doc_id)

            for sample in doc.samples:
                # Global sample ID uniqueness
                if sample.sample_id in seen_corpus_sample_ids:
                    raise InterfaceError(f"Duplicate failed: Duplicate sample ID '{sample.sample_id}'.")
                seen_corpus_sample_ids.add(sample.sample_id)

                # Segment reuse checks across entire corpus
                for seg_id in sample.traceability.source_segment_ids:
                    if seg_id in seen_global_seg_ids:
                        raise InterfaceError(
                            f"Duplicate failed: Segment ID '{seg_id}' reused across corpus."
                        )
                    seen_global_seg_ids.add(seg_id)

        return True

    def _validate_traceability(self, corpus: TrainingCorpus) -> bool:
        """Validates traceability links within the corpus (sorted pages and consistent document mapping)."""
        for doc in corpus.documents:
            for sample in doc.samples:
                trace = sample.traceability
                
                # Check document reference consistency
                if trace.doc_id != doc.doc_id:
                    raise InterfaceError(
                        f"Traceability failed: Doc ID mismatch. Sample trace has '{trace.doc_id}', "
                        f"document has '{doc.doc_id}'."
                    )

                # Check sorted and unique page numbers
                if trace.page_numbers != sorted(trace.page_numbers):
                    raise InterfaceError(
                        f"Traceability failed: Page numbers not sorted for sample '{sample.sample_id}'."
                    )
                if len(trace.page_numbers) != len(set(trace.page_numbers)):
                    raise InterfaceError(
                        f"Traceability failed: Page numbers contain duplicates for sample '{sample.sample_id}'."
                    )

        return True

    def _validate_deterministic_ids(self, corpus: TrainingCorpus) -> bool:
        """Validates that sample IDs match recomputed values."""
        for doc in corpus.documents:
            for sample in doc.samples:
                trace = sample.traceability
                heading_id_str = trace.heading_segment_id or ""
                ordered_ids_str = "".join(trace.source_segment_ids)
                hash_input = f"{doc.doc_id}{heading_id_str}{ordered_ids_str}"
                recomputed_id = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

                if sample.sample_id != recomputed_id:
                    raise InterfaceError(
                        f"Deterministic IDs failed: ID mismatch for sample. "
                        f"Expected {recomputed_id}, got {sample.sample_id}."
                    )

        return True

    def _validate_metadata(self, corpus: TrainingCorpus) -> bool:
        """Validates internal consistency of sample metadata."""
        for doc in corpus.documents:
            for sample in doc.samples:
                trace = sample.traceability
                meta = sample.metadata

                # Check consistency of child segment count based on heading segment presence
                if trace.heading_segment_id:
                    expected_child_count = len(trace.source_segment_ids) - 1
                else:
                    expected_child_count = len(trace.source_segment_ids)
                    if meta.heading_level is not None:
                        raise InterfaceError(
                            f"Metadata failed: Introductory sample must have None heading_level. "
                            f"Got {meta.heading_level}."
                        )

                if meta.child_count != expected_child_count:
                    raise InterfaceError(
                        f"Metadata failed: Child count mismatch for sample '{sample.sample_id}'. "
                        f"Expected {expected_child_count}, got {meta.child_count}."
                    )

        return True
