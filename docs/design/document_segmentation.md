# Document Structural Segmentation Design

The document structural segmentation subsystem slices a `NormalizedDocument` into structural elements.

## Design Flow

1. **Initial State**: A single starting segment of type `METADATA` wrapping the full normalized text.
2. **Sequential Refinement**:
   - `HeaderSegmentationStep` extracts headers and splits the rest.
   - `CodeBlockSegmentationStep` extracts code blocks from the remaining unsegmented text.
   - `ParagraphSegmentationStep` splits the rest by double newlines into paragraphs.
3. **Hierarchy Builder**: Assigns parent/child links using a stack of active heading levels.
4. **Validation**: Assures that segments do not overlap and that their combined text reconstructs the original document exactly.
