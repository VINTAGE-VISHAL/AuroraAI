import os
import sys

# Resolve repository root dynamically
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from aurora.config.settings import Settings
from aurora.core.metrics import MetricsCollector
from aurora.ingestion.file_scanner import FileScanner
from aurora.ingestion.source_registry import SourceRegistry
from aurora.ingestion.document_loader import DocumentLoader
from aurora.ingestion.pdf_extractor import PDFExtractor
from aurora.normalization.pipeline import NormalizationPipeline
from aurora.normalization.models import NormalizationContext
from aurora.segmentation.pipeline import SegmentationPipeline
from aurora.corpus.pipeline import CorpusPipeline
from aurora.core.pipeline import PipelineContext
from aurora.extraction.models import ExtractedDocument as LegacyExtractedDocument

def main():
    raw_dir = os.path.join(REPO_ROOT, "data", "raw", "OOSE")
    output_path = os.path.join(REPO_ROOT, "data", "corpus", "oose_training.jsonl")
    
    if not os.path.exists(raw_dir):
        print(f"ERROR: Raw directory does not exist: {raw_dir}")
        print("Please create this directory and place your OOSE PDF files inside it.")
        return
        
    raw_files = [f for f in os.listdir(raw_dir) if f.endswith(".pdf")]
    if not raw_files:
        print(f"ERROR: No PDF files found in {raw_dir}")
        return
        
    print(f"Found {len(raw_files)} OOSE raw PDFs. Ingesting...")
    
    scanner = FileScanner()
    registry = SourceRegistry()
    metrics = MetricsCollector()
    loader = DocumentLoader(metrics)
    extractor = PDFExtractor()
    
    registry.refresh(scanner, raw_dir, {".pdf"})
    documents = registry.list_documents()
    
    extracted_docs = []
    for doc in documents:
        raw_doc = loader.load(doc)
        ext_doc = extractor.extract(raw_doc)
        extracted_docs.append(ext_doc)
        
    legacy_extracted_docs = []
    for ext in extracted_docs:
        legacy_doc = LegacyExtractedDocument(
            doc_id=ext.doc_id,
            text="\n\n".join(ext.pages),
            metadata=ext.metadata,
            provenance=ext.provenance,
            artifact=ext.artifact,
        )
        legacy_extracted_docs.append(legacy_doc)
        
    print("Normalizing and segmenting...")
    normalizer = NormalizationPipeline()
    context = NormalizationContext()
    normalized_docs = [normalizer.execute(doc, context).result for doc in legacy_extracted_docs]
    
    segmenter = SegmentationPipeline()
    pipeline_context = PipelineContext()
    structured_docs = [segmenter.execute(doc, pipeline_context).result for doc in normalized_docs]
    
    clean_structured_docs = []
    for s_doc in structured_docs:
        filtered = [seg for seg in s_doc.segments if seg.text.strip()]
        if filtered:
            s_doc_copy = s_doc.model_copy(update={"segments": filtered})
            clean_structured_docs.append(s_doc_copy)
            
    print("Serializing using instruction-tuning strategy...")
    settings = Settings()
    settings.corpus.output_path = output_path
    settings.corpus.serializer_type = "instruction"
    
    corpus_pipeline = CorpusPipeline(settings)
    result = corpus_pipeline.run(clean_structured_docs)
    
    print("\n" + "="*50)
    print("OOSE DATASET PREPARATION COMPLETE")
    print("="*50)
    print(f"Clean Samples generated: {result.export_result.samples_exported}")
    print(f"Output Dataset path:     {result.export_result.output_path}")
    print(f"Validation Status:       {result.validation_result.passed}")
    print("="*50)

if __name__ == "__main__":
    main()
