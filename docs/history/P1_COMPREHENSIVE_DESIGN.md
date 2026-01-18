# P1 Phase Implementation Design (Tasks 5-10)

**Status**: Design Phase - Ready for Implementation
**Date**: January 18, 2026
**Scope**: Document Search, API Manager Enhancements, Chat History, CEP Engine, Admin Dashboard, Testing Infrastructure

---

## Executive Summary

This document outlines the comprehensive design for P1 Phase tasks (5-10), which enhance production readiness with critical features:

1. **Task 5**: Document Search Enhancement (Multi-format, OCR, Access Control)
2. **Task 6**: API Manager Enhancements (Versioning, SQL Validation, Rollback)
3. **Task 7**: Chat History Enhancement (Auto-titles, Token Tracking, Export)
4. **Task 8**: CEP Engine Integration (Bytewax, Multi-channel Notifications, Scheduling)
5. **Task 9**: Admin Dashboard (User Monitoring, Resource Monitoring, Settings UI)
6. **Task 10**: Testing Infrastructure (Unit, Integration, E2E, CI/CD)

**Total Effort**: 8-15 weeks
**Parallel Path**: Tasks 5, 6, 9 can proceed in parallel; 7, 8, 10 dependent on infrastructure

---

## Part 1: Task 5 - Document Search Enhancement

### 5.1 Overview

**Current State**:
- Basic PDF upload (`api/routes/documents.py`)
- Vector embeddings (pgvector, 1536 dimensions)
- Simple text chunking

**Target State**:
- Multi-format support (PDF, DOCX, XLSX, PPTX, Images with OCR)
- Async background processing
- Enhanced search metadata tracking
- Per-document access control
- Chunk versioning for incremental updates

### 5.2 Technical Architecture

#### 5.2.1 Backend Components

**New Module**: `app/modules/document_processor/`

```
document_processor/
├── models.py                    # Extended document models
├── router.py                    # Document endpoints
├── services/
│   ├── document_service.py      # Document lifecycle
│   ├── format_processor.py      # Multi-format processing (PDF, DOCX, XLSX, PPTX)
│   ├── ocr_processor.py         # OCR processing (Tesseract/EasyOCR)
│   ├── chunk_service.py         # Intelligent chunking
│   ├── embedding_service.py     # Vector embeddings (OpenAI API)
│   └── search_service.py        # Advanced search
├── crud.py                      # Database operations
└── tasks/
    └── document_processing_task.py  # RQ background job

# New Models
TbDocument (extend existing):
  - format: "pdf" | "docx" | "xlsx" | "pptx" | "image"
  - processing_status: "queued" | "processing" | "chunks_created" | "embedded" | "done" | "failed"
  - processing_progress: 0-100
  - total_chunks: int
  - error_details: JSONB (if failed)
  - metadata: JSONB {
      pages: int,
      word_count: int,
      extraction_method: "pdf_text" | "pdf_image" | "ocr",
      language: "en" | "ko" | ...
    }
  - created_by: FK tb_user
  - created_at, updated_at, deleted_at: TIMESTAMP
  - access_control_id: FK to ResourcePermission

TbDocumentChunk (extend existing):
  - chunk_version: int (for incremental updates)
  - chunk_type: "text" | "table" | "image" | "mixed"
  - position_in_doc: int
  - page_number: int (PDF/PPTX)
  - slide_number: int (PPTX)
  - table_data: JSONB (for structured data)
  - source_hash: varchar (for change detection)
  - relevance_score: float (for search results)
  - metadata: JSONB {
      chunk_language: "en" | "ko",
      contains_tables: bool,
      contains_images: bool,
      processing_time_ms: int
    }

TbDocumentSearchLog:
  - search_id: UUID (PK)
  - user_id: FK
  - query: text
  - filter_criteria: JSONB
  - results_count: int
  - execution_time_ms: int
  - created_at: TIMESTAMP

TbDocumentAccess:
  - access_id: UUID (PK)
  - document_id: FK
  - user_id | role_id: FK (either user or role)
  - access_type: "read" | "download" | "share"
  - expires_at: TIMESTAMP (optional)
  - granted_by: FK tb_user
  - created_at: TIMESTAMP
```

#### 5.2.2 Format Processing Pipeline

```python
# format_processor.py

class DocumentProcessor:
    def process(self, file_path: str, format: str) -> dict:
        """Main entry point"""

        if format == "pdf":
            return self._process_pdf(file_path)
        elif format == "docx":
            return self._process_docx(file_path)
        elif format == "xlsx":
            return self._process_xlsx(file_path)
        elif format == "pptx":
            return self._process_pptx(file_path)
        elif format == "image":
            return self._process_image(file_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _process_pdf(self, file_path: str) -> dict:
        """
        Strategy:
        1. Use pypdf or pdfminer for text extraction
        2. If text extraction fails/low confidence -> use pdf2image + OCR
        3. Detect tables with tabula-py
        4. Return structured pages with text + images + tables
        """
        pages = []
        pdf_document = pdf.open(file_path)

        for page_num, page in enumerate(pdf_document):
            # Try direct text extraction
            text = page.extract_text()

            if len(text) < 50:  # Low confidence
                # Fall back to OCR
                image = pdf2image.convert_from_path(file_path, page_numbers=[page_num])[0]
                text = pytesseract.image_to_string(image)

            # Extract tables
            tables = tabula.read_pdf(file_path, pages=[page_num+1])

            pages.append({
                "page_num": page_num,
                "text": text,
                "tables": [t.to_dict() for t in tables],
                "image": image_base64 if needed
            })

        return {"pages": pages, "metadata": {"page_count": len(pages)}}

    def _process_docx(self, file_path: str) -> dict:
        """Extract from docx using python-docx"""
        doc = Document(file_path)
        pages = []
        current_page = {"text": "", "tables": []}

        for element in doc.element.body:
            if element.tag.endswith("p"):
                current_page["text"] += element.text + "\n"
            elif element.tag.endswith("tbl"):
                table_data = extract_table(element)
                current_page["tables"].append(table_data)

        return {"pages": [current_page], "metadata": {...}}

    def _process_xlsx(self, file_path: str) -> dict:
        """Extract from Excel"""
        excel_file = pd.ExcelFile(file_path)
        sheets = []

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            sheets.append({
                "sheet_name": sheet_name,
                "columns": df.columns.tolist(),
                "data": df.to_dict(orient="records"),
                "summary": df.describe().to_dict()
            })

        return {"sheets": sheets, "metadata": {...}}

    def _process_pptx(self, file_path: str) -> dict:
        """Extract from PowerPoint"""
        prs = Presentation(file_path)
        slides = []

        for slide_num, slide in enumerate(prs.slides):
            slide_data = {"slide_num": slide_num, "shapes": []}

            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    slide_data["shapes"].append({"type": "text", "content": shape.text})
                elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    # Extract and OCR image
                    image = shape.image
                    ocr_text = pytesseract.image_to_string(image.blob)
                    slide_data["shapes"].append({"type": "image", "ocr_text": ocr_text})

            slides.append(slide_data)

        return {"slides": slides, "metadata": {...}}

    def _process_image(self, file_path: str) -> dict:
        """OCR on image"""
        image = Image.open(file_path)

        # Use EasyOCR for better Korean support
        reader = easyocr.Reader(["en", "ko"])
        results = reader.readtext(image)

        text = "\n".join([text for (bbox, text, confidence) in results])

        return {
            "pages": [{
                "page_num": 0,
                "text": text,
                "ocr_confidence": np.mean([conf for (_, _, conf) in results])
            }],
            "metadata": {"format": "image", "width": image.width, "height": image.height}
        }
```

#### 5.2.3 Intelligent Chunking Service

```python
# chunk_service.py

class ChunkingStrategy:
    """Multi-strategy chunking based on content type"""

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 512,
        overlap: int = 100,
        document_type: str = "general"
    ) -> List[str]:
        """
        Strategies:
        1. Sentence-based: Split on sentence boundaries
        2. Paragraph-based: Split on paragraphs (more semantic)
        3. Sliding window: Fixed size with overlap
        4. Smart boundaries: Detect logical breaks
        """

        # Use spacy for sentence segmentation
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)

        sentences = [sent.text for sent in doc.sents]

        # Group sentences into chunks
        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_tokens = len(sentence.split())

            if current_size + sentence_tokens > chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                # Add overlap from previous chunk
                if len(chunks) > 0:
                    overlap_sentences = " ".join(current_chunk[-2:])
                    current_chunk = [overlap_sentences]
                    current_size = len(overlap_sentences.split())

            current_chunk.append(sentence)
            current_size += sentence_tokens

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    @staticmethod
    def chunk_table(table_data: dict, chunk_size: int = 10) -> List[str]:
        """Chunk structured table data"""
        df = pd.DataFrame(table_data["data"])

        chunks = []
        for i in range(0, len(df), chunk_size):
            chunk_df = df.iloc[i:i+chunk_size]
            chunk_text = chunk_df.to_string()
            chunks.append(chunk_text)

        return chunks
```

#### 5.2.4 Advanced Search Service

```python
# search_service.py

class DocumentSearchService:

    async def search(
        self,
        query: str,
        filters: DocumentSearchFilters,
        top_k: int = 10
    ) -> List[SearchResult]:
        """
        1. Embed query using OpenAI embedding API
        2. Vector similarity search (pgvector)
        3. BM25 full-text search
        4. Hybrid: Combine vector + BM25 results
        5. Re-rank using LLM (optional)
        6. Apply access control filters
        """

        # 1. Embed query
        query_embedding = await self.embedding_service.embed(query)

        # 2. Vector search
        vector_results = await self._vector_search(
            query_embedding,
            top_k * 2,  # Get more for re-ranking
            filters
        )

        # 3. BM25 search (full-text)
        bm25_results = await self._bm25_search(query, top_k * 2, filters)

        # 4. Combine results (RRF - Reciprocal Rank Fusion)
        combined = self._combine_results(vector_results, bm25_results, top_k)

        # 5. Apply access control
        authorized = [r for r in combined if await self._check_access(r)]

        # 6. Log search
        await self.audit_log.log_search(query, len(authorized))

        return authorized[:top_k]

    async def _vector_search(self, embedding, top_k, filters) -> List[SearchResult]:
        """Use pgvector cosine similarity"""
        query = """
        SELECT
            chunk_id, document_id, chunk_text, embedding,
            1 - (embedding <=> $1) as similarity
        FROM tb_document_chunk
        WHERE document_id IN (
            SELECT document_id FROM TbDocument WHERE deleted_at IS NULL
        )
        AND 1 - (embedding <=> $1) > 0.5
        ORDER BY similarity DESC
        LIMIT $2
        """

        results = await db.fetch(query, embedding, top_k)
        return [SearchResult(**r) for r in results]

    async def _bm25_search(self, query, top_k, filters) -> List[SearchResult]:
        """Use PostgreSQL full-text search with BM25"""
        query_sql = """
        SELECT
            chunk_id, document_id, chunk_text,
            ts_rank(to_tsvector(chunk_text), plainto_tsquery($1)) as rank
        FROM tb_document_chunk
        WHERE to_tsvector(chunk_text) @@ plainto_tsquery($1)
        ORDER BY rank DESC
        LIMIT $2
        """

        results = await db.fetch(query_sql, query, top_k)
        return [SearchResult(**r) for r in results]

    @staticmethod
    def _combine_results(
        vector_results: List[SearchResult],
        bm25_results: List[SearchResult],
        top_k: int
    ) -> List[SearchResult]:
        """RRF: Reciprocal Rank Fusion"""
        scores = {}

        for rank, result in enumerate(vector_results, 1):
            scores[result.chunk_id] = scores.get(result.chunk_id, 0) + 1 / (60 + rank)

        for rank, result in enumerate(bm25_results, 1):
            scores[result.chunk_id] = scores.get(result.chunk_id, 0) + 1 / (60 + rank)

        # Re-fetch full results in score order
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]

        # Fetch full chunks
        combined = db.fetch(
            "SELECT * FROM tb_document_chunk WHERE chunk_id = ANY($1)",
            sorted_ids
        )

        return combined
```

#### 5.2.5 Background Processing (RQ Job)

```python
# tasks/document_processing_task.py

@job("document_processing")
async def process_document_async(document_id: str, file_path: str):
    """
    RQ Background Job:
    1. Extract content based on format
    2. Create chunks with metadata
    3. Generate embeddings (batch)
    4. Update document status
    5. Log metrics
    """
    document = await db.get(TbDocument, document_id)

    try:
        document.processing_status = "processing"
        document.processing_progress = 0
        await db.update(document)

        # Step 1: Process format
        processor = DocumentProcessor()
        extracted = processor.process(file_path, document.format)

        document.processing_progress = 20
        document.metadata = extracted["metadata"]
        await db.update(document)

        # Step 2: Create chunks
        chunking = ChunkingStrategy()
        chunks = []

        for page in extracted.get("pages", []):
            page_chunks = chunking.chunk_text(page["text"])
            chunks.extend([
                TbDocumentChunk(
                    document_id=document_id,
                    text=chunk,
                    page_number=page.get("page_num"),
                    chunk_type="text",
                    position_in_doc=i
                )
                for i, chunk in enumerate(page_chunks)
            ])

        document.processing_progress = 40
        document.total_chunks = len(chunks)
        await db.update(document)

        # Step 3: Batch embed chunks
        embedding_service = EmbeddingService()
        embeddings = await embedding_service.embed_batch(
            [c.text for c in chunks],
            batch_size=100  # OpenAI rate limits
        )

        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        await db.insert_many(chunks)

        document.processing_status = "embedded"
        document.processing_progress = 100
        await db.update(document)

    except Exception as e:
        document.processing_status = "failed"
        document.error_details = {"error": str(e)}
        await db.update(document)
        raise
```

#### 5.2.6 API Endpoints

```python
# router.py

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    current_user: TbUser = Depends(get_current_user)
):
    """
    Upload document for processing
    - Validate file format
    - Save to storage
    - Queue background processing
    """

    # Validate format
    allowed_formats = ["pdf", "docx", "xlsx", "pptx", "jpg", "png"]
    file_ext = file.filename.split(".")[-1].lower()

    if file_ext not in allowed_formats:
        raise HTTPException(400, f"Unsupported format: {file_ext}")

    # Save file
    file_path = f"/tmp/documents/{uuid4()}.{file_ext}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Create document record
    doc = TbDocument(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        filename=file.filename,
        format=file_ext,
        content_type=file.content_type,
        processing_status="queued"
    )

    await db.insert(doc)

    # Queue background job
    job = queue.enqueue(
        "document_processing_task.process_document_async",
        document_id=str(doc.id),
        file_path=file_path
    )

    return ResponseEnvelope(
        data={
            "document_id": str(doc.id),
            "status": "queued",
            "job_id": job.id
        }
    )


@router.post("/documents/search")
async def search_documents(
    request: SearchDocumentRequest,
    current_user: TbUser = Depends(get_current_user)
):
    """
    Advanced document search
    - Hybrid vector + BM25
    - Filters: date, author, document type
    - Access control
    """

    search_service = DocumentSearchService()

    filters = DocumentSearchFilters(
        tenant_id=current_user.tenant_id,
        date_from=request.date_from,
        date_to=request.date_to,
        document_types=request.types
    )

    results = await search_service.search(
        query=request.query,
        filters=filters,
        top_k=request.top_k or 10
    )

    return ResponseEnvelope(data={"results": results})


@router.get("/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    current_user: TbUser = Depends(get_current_user)
):
    """Get all chunks for a document (with permission check)"""

    # Check access
    doc = await db.get(TbDocument, document_id)
    if not await check_resource_permission(doc.id, "read"):
        raise HTTPException(403, "Access denied")

    chunks = await db.fetch(
        "SELECT * FROM tb_document_chunk WHERE document_id = $1 ORDER BY chunk_index",
        document_id
    )

    return ResponseEnvelope(data={"chunks": chunks})


@router.post("/documents/{document_id}/share")
async def share_document(
    document_id: str,
    request: ShareDocumentRequest,
    current_user: TbUser = Depends(require_role(UserRole.MANAGER))
):
    """
    Share document with user/role
    - Create TbDocumentAccess record
    - Set expiration (optional)
    """

    access = TbDocumentAccess(
        document_id=document_id,
        user_id=request.user_id if request.share_type == "user" else None,
        role_id=request.role_id if request.share_type == "role" else None,
        access_type=request.access_type,
        expires_at=request.expires_at,
        granted_by=current_user.id
    )

    await db.insert(access)

    # Log
    await audit_log.log(
        resource_type="document",
        resource_id=document_id,
        action="share",
        actor=current_user.id
    )

    return ResponseEnvelope(data={"access_id": str(access.id)})
```

### 5.3 Frontend Components

#### 5.3.1 Document Upload Component

```typescript
// apps/web/src/components/documents/DocumentUploader.tsx

export function DocumentUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);

      return authenticatedFetch("/documents/upload", {
        method: "POST",
        body: formData,
        onUploadProgress: (progress) => {
          setUploadProgress(Math.round((progress.loaded / progress.total) * 100));
        }
      });
    },
    onSuccess: (data) => {
      toast.success("Document uploaded successfully");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    }
  });

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  return (
    <div
      className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer"
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
    >
      <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
      <p className="text-lg font-medium">Drag and drop your documents</p>
      <p className="text-sm text-gray-500">
        Supported: PDF, DOCX, XLSX, PPTX, Images (JPG, PNG)
      </p>

      {file && (
        <div className="mt-4">
          <p className="font-medium">{file.name}</p>
          {uploading && (
            <Progress value={uploadProgress} className="mt-2" />
          )}
        </div>
      )}

      <Button
        onClick={() => uploadMutation.mutate(file!)}
        disabled={!file || uploading}
        className="mt-4"
      >
        Upload
      </Button>
    </div>
  );
}
```

#### 5.3.2 Advanced Search Component

```typescript
// apps/web/src/components/documents/DocumentSearchPanel.tsx

export function DocumentSearchPanel() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({
    dateFrom: null,
    dateTo: null,
    types: [] as string[]
  });

  const searchQuery = useQuery({
    queryKey: ["document-search", query, filters],
    queryFn: () => authenticatedFetch("/documents/search", {
      method: "POST",
      body: JSON.stringify({ query, ...filters })
    }),
    enabled: query.length > 2
  });

  return (
    <div className="space-y-4">
      <div>
        <Input
          placeholder="Search documents..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="flex gap-4">
        <DatePicker
          label="From"
          value={filters.dateFrom}
          onChange={(date) => setFilters({...filters, dateFrom: date})}
        />
        <DatePicker
          label="To"
          value={filters.dateTo}
          onChange={(date) => setFilters({...filters, dateTo: date})}
        />

        <Select
          multiple
          placeholder="Document types"
          options={[
            { label: "PDF", value: "pdf" },
            { label: "Word", value: "docx" },
            { label: "Excel", value: "xlsx" },
            { label: "PowerPoint", value: "pptx" }
          ]}
          value={filters.types}
          onChange={(types) => setFilters({...filters, types})}
        />
      </div>

      <div className="space-y-2">
        {searchQuery.data?.results?.map((result) => (
          <DocumentSearchResult key={result.chunk_id} result={result} />
        ))}
      </div>
    </div>
  );
}
```

### 5.4 Database Migrations

```python
# alembic/versions/0036_document_enhancements.py

def upgrade():
    op.create_table(
        'tb_document_chunk',
        sa.Column('chunk_id', GUID(), nullable=False),
        sa.Column('document_id', GUID(), sa.ForeignKey('tb_document.id')),
        sa.Column('chunk_version', sa.Integer(), default=1),
        sa.Column('chunk_type', sa.String(), nullable=False),
        sa.Column('position_in_doc', sa.Integer()),
        sa.Column('page_number', sa.Integer()),
        sa.Column('chunk_text', sa.Text()),
        sa.Column('embedding', Vector(1536)),
        sa.Column('relevance_score', sa.Float()),
        sa.Column('metadata', JSONB()),
        sa.PrimaryKeyConstraint('chunk_id'),
        sa.Index('ix_document_chunk_document_id', 'document_id'),
        sa.Index('ix_document_chunk_embedding', 'embedding', postgresql_using='hnsw')
    )

    op.add_column('tb_document', sa.Column('format', sa.String()))
    op.add_column('tb_document', sa.Column('processing_status', sa.String()))
    op.add_column('tb_document', sa.Column('processing_progress', sa.Integer()))
    op.add_column('tb_document', sa.Column('total_chunks', sa.Integer()))
    op.add_column('tb_document', sa.Column('metadata', JSONB()))

    op.create_table(
        'tb_document_access',
        sa.Column('access_id', GUID(), primary_key=True),
        sa.Column('document_id', GUID(), sa.ForeignKey('tb_document.id')),
        sa.Column('user_id', GUID(), sa.ForeignKey('tb_user.id'), nullable=True),
        sa.Column('role_id', GUID(), sa.ForeignKey('tb_role.id'), nullable=True),
        sa.Column('access_type', sa.String()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('granted_by', GUID(), sa.ForeignKey('tb_user.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), default=datetime.utcnow),
    )
```

---

## Part 2: Task 6 - API Manager Enhancements

### 6.1 Overview

**Current State**:
- Basic dynamic API creation (SQL, Python, Workflow modes)
- No version management
- No SQL validation

**Target State**:
- Version control with change history
- SQL validation and performance analysis
- Rollback functionality
- Permission management per API
- Test execution and monitoring

### 6.2 Technical Architecture

#### 6.2.1 Extended Data Models

```python
# app/modules/api_manager/models.py (extend existing ApiDefinition)

class ApiDefinition(SQLModel, table=True):
    __tablename__ = "tb_api_definition"

    # Existing fields...
    id: UUID
    scope: str  # "system" | "custom"
    name: str
    method: str
    path: str
    logic: str
    is_enabled: bool

    # New fields
    version: int = 1  # Current version
    description: Optional[str]
    input_schema: dict  # JSON schema validation
    output_schema: dict  # JSON schema for response

    # SQL validation
    sql_analysis: Optional[dict] = Field(default_factory=dict)  # {"tables": [...], "performance": {...}}
    last_validation_at: Optional[datetime]
    validation_status: str = "pending"  # pending, valid, invalid

    # Permissions
    owner_id: UUID
    permission_level: str = "private"  # private, team, public

    # Metadata
    tags: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)  # Other API IDs
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

class ApiDefinitionVersion(SQLModel, table=True):
    __tablename__ = "tb_api_definition_version"

    version_id: UUID = Field(primary_key=True)
    api_id: UUID = Field(foreign_key="tb_api_definition.id")
    version_number: int

    # Full snapshot of API at this version
    snapshot: dict  # {name, method, path, logic, input_schema, output_schema, ...}

    # Change info
    change_type: str  # "create", "update", "publish", "rollback"
    change_description: Optional[str]
    changed_fields: List[str]  # Which fields changed

    # Validation info
    sql_analysis: Optional[dict]
    validation_status: str

    # Created by
    created_by: UUID
    created_at: datetime

class ApiTest(SQLModel, table=True):
    __tablename__ = "tb_api_test"

    test_id: UUID = Field(primary_key=True)
    api_id: UUID = Field(foreign_key="tb_api_definition.id")
    name: str
    description: Optional[str]

    # Test data
    input_data: dict  # Test parameters
    expected_output: dict  # Expected result

    # Test results
    last_run_at: Optional[datetime]
    last_result: str  # "pass", "fail", "error"
    last_error: Optional[str]

    is_enabled: bool = True
    created_at: datetime

class ApiExecutionLog(SQLModel, table=True):
    __tablename__ = "tb_api_execution_log"

    execution_id: UUID = Field(primary_key=True)
    api_id: UUID = Field(foreign_key="tb_api_definition.id")
    version: int

    # Request
    request_params: dict
    request_trace_id: str

    # Response
    status_code: int
    response_data: dict
    execution_time_ms: int

    # Performance
    row_count: Optional[int]  # For DB queries
    memory_used_mb: Optional[float]

    # Created by
    called_by: UUID
    created_at: datetime
```

#### 6.2.2 SQL Validator Service

```python
# app/modules/api_manager/services/sql_validator.py

class SQLValidator:
    """Validates SQL queries for safety and performance"""

    async def validate(self, sql: str) -> ValidationResult:
        """
        1. Check for dangerous operations (DROP, TRUNCATE, etc.)
        2. Parse query for tables and columns
        3. Check if user has access to tables
        4. Analyze query plan for performance
        5. Return recommendations
        """

        result = ValidationResult()

        # 1. Security check
        dangerous_keywords = ["DROP", "TRUNCATE", "DELETE FROM", "ALTER", "EXEC"]
        for keyword in dangerous_keywords:
            if keyword in sql.upper():
                result.is_safe = False
                result.errors.append(f"Dangerous keyword: {keyword}")

        if not result.is_safe:
            return result

        # 2. Parse query
        try:
            parsed = sqlparse.parse(sql)
            stmt = parsed[0]

            # Extract tables
            tables = self._extract_tables(stmt)
            result.metadata["tables"] = tables

            # Extract columns
            columns = self._extract_columns(stmt)
            result.metadata["columns"] = columns

        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Parse error: {str(e)}")
            return result

        # 3. Check access
        for table in tables:
            # Check if table is in allowed list
            if not self._is_table_allowed(table):
                result.errors.append(f"Access denied to table: {table}")
                result.is_safe = False

        # 4. Analyze query plan
        try:
            plan = await self._analyze_query_plan(sql)
            result.metadata["query_plan"] = plan

            # Check for performance issues
            if plan.get("estimated_cost") > 10000:
                result.warnings.append("High query cost (may be slow)")

            if plan.get("max_width") > 1000:
                result.warnings.append("Very wide result set")

        except Exception as e:
            result.warnings.append(f"Could not analyze: {str(e)}")

        result.is_valid = len(result.errors) == 0

        return result

    async def _analyze_query_plan(self, sql: str) -> dict:
        """Get EXPLAIN ANALYZE output"""

        explain_sql = f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS) {sql}"

        result = await db.fetch(explain_sql)
        plan = result[0]["Plan"]

        return {
            "estimated_cost": plan.get("Total Cost"),
            "actual_time_ms": plan.get("Actual Total Time"),
            "rows": plan.get("Actual Rows"),
            "node_type": plan.get("Node Type")
        }
```

#### 6.2.3 API Manager Service

```python
# app/modules/api_manager/services/api_service.py

class ApiManagerService:

    async def create_api(
        self,
        api_def: CreateApiRequest,
        current_user: TbUser
    ) -> ApiDefinitionResponse:
        """Create new API with validation"""

        # Validate input
        if api_def.mode == "sql":
            validation = await self.sql_validator.validate(api_def.logic)
            if not validation.is_safe:
                raise HTTPException(400, f"SQL validation failed: {validation.errors}")

        # Create API definition
        new_api = ApiDefinition(
            scope=api_def.scope,
            name=api_def.name,
            method=api_def.method,
            path=api_def.path,
            logic=api_def.logic,
            mode=api_def.mode,
            input_schema=api_def.input_schema,
            output_schema=api_def.output_schema,
            owner_id=current_user.id,
            created_by=current_user.id,
            updated_by=current_user.id,
            version=1,
            validation_status=validation.is_valid if api_def.mode == "sql" else "pending",
            sql_analysis=validation.metadata if api_def.mode == "sql" else None
        )

        await db.insert(new_api)

        # Create version record
        version = ApiDefinitionVersion(
            api_id=new_api.id,
            version_number=1,
            snapshot=new_api.dict(),
            change_type="create",
            change_description="Initial creation",
            created_by=current_user.id
        )

        await db.insert(version)

        # Audit log
        await audit_log.log(
            resource_type="api",
            resource_id=str(new_api.id),
            action="create",
            actor=current_user.id,
            changes={"created": True}
        )

        return ApiDefinitionResponse.from_orm(new_api)

    async def update_api(
        self,
        api_id: str,
        update_req: UpdateApiRequest,
        current_user: TbUser
    ) -> ApiDefinitionResponse:
        """Update API with version history"""

        api = await db.get(ApiDefinition, api_id)

        # Check permission
        if api.owner_id != current_user.id and not current_user.is_admin:
            raise HTTPException(403, "Permission denied")

        # Validate changes
        if update_req.logic and api.mode == "sql":
            validation = await self.sql_validator.validate(update_req.logic)
            if not validation.is_safe:
                raise HTTPException(400, "SQL validation failed")

        # Track changes
        old_data = api.dict()

        # Update fields
        if update_req.name:
            api.name = update_req.name
        if update_req.logic:
            api.logic = update_req.logic
        if update_req.input_schema:
            api.input_schema = update_req.input_schema

        api.version += 1
        api.updated_by = current_user.id
        api.updated_at = datetime.utcnow()

        await db.update(api)

        # Create version record
        new_data = api.dict()
        changed_fields = [k for k, v in old_data.items() if old_data[k] != new_data[k]]

        version = ApiDefinitionVersion(
            api_id=api.id,
            version_number=api.version,
            snapshot=new_data,
            change_type="update",
            changed_fields=changed_fields,
            created_by=current_user.id
        )

        await db.insert(version)

        # Audit log
        await audit_log.log(
            resource_type="api",
            resource_id=api_id,
            action="update",
            actor=current_user.id,
            old_values={k: old_data[k] for k in changed_fields},
            new_values={k: new_data[k] for k in changed_fields}
        )

        return ApiDefinitionResponse.from_orm(api)

    async def rollback_api(
        self,
        api_id: str,
        target_version: int,
        current_user: TbUser
    ) -> ApiDefinitionResponse:
        """Rollback to previous version"""

        api = await db.get(ApiDefinition, api_id)

        # Check permission
        if api.owner_id != current_user.id and not current_user.is_admin:
            raise HTTPException(403, "Permission denied")

        # Get target version
        target = await db.fetch(
            "SELECT snapshot FROM tb_api_definition_version WHERE api_id = $1 AND version_number = $2",
            api_id,
            target_version
        )

        if not target:
            raise HTTPException(404, "Version not found")

        snapshot = target[0]["snapshot"]

        # Restore
        api.logic = snapshot["logic"]
        api.input_schema = snapshot["input_schema"]
        api.output_schema = snapshot["output_schema"]
        api.version += 1
        api.updated_by = current_user.id
        api.updated_at = datetime.utcnow()

        await db.update(api)

        # Create rollback version record
        version = ApiDefinitionVersion(
            api_id=api.id,
            version_number=api.version,
            snapshot=api.dict(),
            change_type="rollback",
            change_description=f"Rolled back to version {target_version}",
            created_by=current_user.id
        )

        await db.insert(version)

        return ApiDefinitionResponse.from_orm(api)

    async def execute_api(
        self,
        api_id: str,
        params: dict,
        current_user: TbUser
    ) -> dict:
        """Execute API with logging and performance tracking"""

        api = await db.get(ApiDefinition, api_id)

        # Check permission
        if not await check_resource_permission(api.id, "execute", current_user):
            raise HTTPException(403, "Permission denied")

        start_time = time.time()
        trace_id = str(uuid4())

        try:
            # Validate input
            jsonschema.validate(params, api.input_schema)
        except jsonschema.ValidationError as e:
            raise HTTPException(400, f"Invalid input: {str(e)}")

        try:
            # Execute
            if api.mode == "sql":
                result = await self._execute_sql(api.logic, params)
            elif api.mode == "python":
                result = await self._execute_python(api.logic, params)
            elif api.mode == "workflow":
                result = await self._execute_workflow(api.logic, params)

            # Validate output
            jsonschema.validate(result, api.output_schema)

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Log execution
            log = ApiExecutionLog(
                api_id=api.id,
                version=api.version,
                request_params=params,
                request_trace_id=trace_id,
                status_code=200,
                response_data=result,
                execution_time_ms=execution_time_ms,
                called_by=current_user.id
            )

            await db.insert(log)

            return result

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Log error
            log = ApiExecutionLog(
                api_id=api.id,
                version=api.version,
                request_params=params,
                request_trace_id=trace_id,
                status_code=500,
                response_data={"error": str(e)},
                execution_time_ms=execution_time_ms,
                called_by=current_user.id
            )

            await db.insert(log)

            raise HTTPException(500, f"Execution failed: {str(e)}")
```

#### 6.2.4 API Test Runner

```python
# app/modules/api_manager/services/test_runner.py

class ApiTestRunner:

    async def run_tests(self, api_id: str) -> TestRunResult:
        """Run all tests for an API"""

        tests = await db.fetch(
            "SELECT * FROM tb_api_test WHERE api_id = $1 AND is_enabled = true",
            api_id
        )

        results = []

        for test in tests:
            try:
                # Execute API with test input
                result = await self.api_service.execute_api(
                    api_id,
                    test.input_data,
                    # Use admin user for testing
                )

                # Compare with expected output
                if result == test.expected_output:
                    status = "pass"
                    error = None
                else:
                    status = "fail"
                    error = f"Expected {test.expected_output}, got {result}"

            except Exception as e:
                status = "error"
                error = str(e)

            results.append(TestResult(
                test_id=test.test_id,
                status=status,
                error=error,
                run_at=datetime.utcnow()
            ))

        return TestRunResult(
            api_id=api_id,
            total=len(tests),
            passed=len([r for r in results if r.status == "pass"]),
            failed=len([r for r in results if r.status == "fail"]),
            errors=len([r for r in results if r.status == "error"]),
            results=results
        )
```

### 6.3 API Endpoints

```python
# API Manager endpoints

@router.post("/api-manager/{api_id}/versions")
async def get_api_versions(api_id: str, current_user: TbUser = Depends(get_current_user)):
    """Get version history"""
    versions = await db.fetch(
        "SELECT * FROM tb_api_definition_version WHERE api_id = $1 ORDER BY version_number DESC",
        api_id
    )
    return ResponseEnvelope(data={"versions": versions})

@router.post("/api-manager/{api_id}/rollback")
async def rollback_api(
    api_id: str,
    request: RollbackRequest,
    current_user: TbUser = Depends(get_current_user)
):
    """Rollback to previous version"""
    result = await api_service.rollback_api(api_id, request.target_version, current_user)
    return ResponseEnvelope(data=result)

@router.post("/api-manager/{api_id}/validate-sql")
async def validate_sql(
    api_id: str,
    request: ValidateSqlRequest,
    current_user: TbUser = Depends(get_current_user)
):
    """Validate SQL query"""
    validation = await sql_validator.validate(request.sql)
    return ResponseEnvelope(data=validation.dict())

@router.post("/api-manager/{api_id}/test")
async def run_tests(
    api_id: str,
    current_user: TbUser = Depends(get_current_user)
):
    """Run all tests for API"""
    result = await test_runner.run_tests(api_id)
    return ResponseEnvelope(data=result.dict())

@router.get("/api-manager/{api_id}/execution-logs")
async def get_execution_logs(
    api_id: str,
    limit: int = 50,
    current_user: TbUser = Depends(get_current_user)
):
    """Get API execution history"""
    logs = await db.fetch(
        "SELECT * FROM tb_api_execution_log WHERE api_id = $1 ORDER BY created_at DESC LIMIT $2",
        api_id,
        limit
    )
    return ResponseEnvelope(data={"logs": logs})
```

---

## Part 3: Task 7 - Chat History Enhancement

### 7.1 Overview

**Current State**:
- Basic ChatThread and ChatMessage models
- Message storage in database

**Target State**:
- Auto-generate conversation titles using LLM
- Token usage tracking (input/output per message)
- Result export (PNG, CSV, JSON)
- History search with full-text and vector search
- Soft delete support

### 7.2 Technical Architecture

#### 7.2.1 Extended Chat Models

```python
# app/models/chat.py (extend existing)

class ChatThread(SQLModel, table=True):
    __tablename__ = "tb_chat_thread"

    # Existing fields...
    id: UUID = Field(primary_key=True)
    tenant_id: UUID = Field(foreign_key="tb_tenant.id")
    user_id: UUID = Field(foreign_key="tb_user.id")

    # New fields
    title: Optional[str] = None
    title_generated_by: str = "user"  # "user" | "llm"
    title_generated_at: Optional[datetime]

    summary: Optional[str] = None  # Short summary of conversation
    summary_generated_at: Optional[datetime]

    tags: List[str] = Field(default_factory=list)  # User-defined tags
    is_starred: bool = False  # Pin favorite conversations

    # Token tracking
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    estimated_cost: Optional[float] = None

    # Soft delete
    deleted_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    # Relationships
    messages: List["ChatMessage"] = Field(default=None, foreign_key="tb_chat_message.thread_id")

class ChatMessage(SQLModel, table=True):
    __tablename__ = "tb_chat_message"

    # Existing fields...
    id: UUID = Field(primary_key=True)
    thread_id: UUID = Field(foreign_key="tb_chat_thread.id")

    # New fields
    tokens_in: Optional[int] = None  # Input tokens for this message
    tokens_out: Optional[int] = None  # Output tokens for response

    # Content metadata
    content_type: str = "text"  # "text" | "image" | "code" | "mixed"

    # Search optimization
    search_vector: Optional[Vector] = None  # For semantic search
    search_text: Optional[str] = None  # For full-text search (tsvector)

    # Message metadata
    model: Optional[str] = None  # "gpt-4", "gpt-3.5", etc.
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    # References
    references: List[dict] = Field(default_factory=list)  # {kind, title, payload}

    created_at: datetime
    updated_at: datetime

class ChatExport(SQLModel, table=True):
    __tablename__ = "tb_chat_export"

    export_id: UUID = Field(primary_key=True)
    thread_id: UUID = Field(foreign_key="tb_chat_thread.id")

    # Export info
    format: str  # "json" | "csv" | "png" | "pdf"
    filename: str
    file_path: str  # S3 or local path
    file_size_bytes: int

    # Metadata
    messages_count: int
    exported_by: UUID = Field(foreign_key="tb_user.id")
    created_at: datetime
```

#### 7.2.2 Chat Service with Auto-Title Generation

```python
# app/modules/chat/services/chat_service.py

class ChatService:

    async def create_thread(
        self,
        user_id: UUID,
        tenant_id: UUID,
        initial_title: Optional[str] = None
    ) -> ChatThread:
        """Create new chat thread"""

        thread = ChatThread(
            tenant_id=tenant_id,
            user_id=user_id,
            title=initial_title,
            title_generated_by="user" if initial_title else None
        )

        await db.insert(thread)
        return thread

    async def add_message(
        self,
        thread_id: UUID,
        role: str,
        content: str,
        model: Optional[str] = None,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None
    ) -> ChatMessage:
        """Add message and auto-generate title on first response"""

        message = ChatMessage(
            thread_id=thread_id,
            role=role,
            content=content,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            created_at=datetime.utcnow()
        )

        await db.insert(message)

        # Get thread
        thread = await db.get(ChatThread, thread_id)

        # Update token counts
        if tokens_in:
            thread.total_tokens_in += tokens_in
        if tokens_out:
            thread.total_tokens_out += tokens_out

        # Calculate estimated cost (rough: GPT-4: $0.03/$0.06 per 1K tokens)
        thread.estimated_cost = (
            (thread.total_tokens_in * 0.00003) +
            (thread.total_tokens_out * 0.00006)
        )

        # Auto-generate title if not set and this is first assistant response
        if not thread.title and role == "assistant":
            title = await self._generate_title(thread_id)
            thread.title = title
            thread.title_generated_by = "llm"
            thread.title_generated_at = datetime.utcnow()

        await db.update(thread)

        return message

    async def _generate_title(self, thread_id: UUID) -> str:
        """Generate conversation title using LLM"""

        # Get first user message and assistant response
        messages = await db.fetch(
            """
            SELECT role, content FROM tb_chat_message
            WHERE thread_id = $1
            ORDER BY created_at ASC
            LIMIT 4
            """,
            thread_id
        )

        if len(messages) < 2:
            return "New Conversation"

        # Create prompt for title generation
        prompt = f"""
        Based on this conversation excerpt, generate a short, concise title (max 50 chars):

        User: {messages[0]['content'][:200]}...
        Assistant: {messages[1]['content'][:200]}...

        Title:
        """

        # Call LLM
        title = await self.llm_service.generate(prompt, max_tokens=20)

        return title.strip()

    async def search_history(
        self,
        user_id: UUID,
        query: str,
        search_type: str = "hybrid"  # "text" | "semantic" | "hybrid"
    ) -> List[ChatThread]:
        """Search chat history across threads"""

        if search_type == "text":
            # Full-text search on messages
            threads = await db.fetch(
                """
                SELECT DISTINCT thread_id FROM tb_chat_message
                WHERE thread_id IN (
                    SELECT id FROM tb_chat_thread WHERE user_id = $1 AND deleted_at IS NULL
                )
                AND to_tsvector(content) @@ plainto_tsquery($2)
                """,
                user_id,
                query
            )

        elif search_type == "semantic":
            # Vector similarity search
            query_embedding = await self.embedding_service.embed(query)

            threads = await db.fetch(
                """
                SELECT DISTINCT thread_id FROM tb_chat_message
                WHERE thread_id IN (
                    SELECT id FROM tb_chat_thread WHERE user_id = $1 AND deleted_at IS NULL
                )
                AND 1 - (search_vector <=> $2) > 0.5
                ORDER BY 1 - (search_vector <=> $2) DESC
                """,
                user_id,
                query_embedding
            )

        else:  # hybrid
            # Combine both approaches
            text_results = await self.search_history(user_id, query, "text")
            semantic_results = await self.search_history(user_id, query, "semantic")

            # Merge and deduplicate
            thread_ids = set()
            for r in text_results + semantic_results:
                thread_ids.add(r[0])

            threads = await db.fetch(
                "SELECT * FROM tb_chat_thread WHERE id = ANY($1) AND deleted_at IS NULL",
                list(thread_ids)
            )

        return threads

    async def soft_delete_thread(self, thread_id: UUID, user_id: UUID):
        """Soft delete (mark as deleted, don't remove)"""

        thread = await db.get(ChatThread, thread_id)

        if thread.user_id != user_id:
            raise HTTPException(403, "Permission denied")

        thread.deleted_at = datetime.utcnow()
        await db.update(thread)
```

#### 7.2.3 Export Service

```python
# app/modules/chat/services/export_service.py

class ChatExportService:

    async def export_thread(
        self,
        thread_id: UUID,
        format: str,  # "json" | "csv" | "png" | "pdf"
        user_id: UUID
    ) -> ChatExport:
        """Export conversation in specified format"""

        thread = await db.get(ChatThread, thread_id)

        if thread.user_id != user_id:
            raise HTTPException(403, "Permission denied")

        # Get messages
        messages = await db.fetch(
            "SELECT * FROM tb_chat_message WHERE thread_id = $1 ORDER BY created_at",
            thread_id
        )

        if format == "json":
            content = self._export_json(thread, messages)
            filename = f"{thread.title or 'chat'}.json"

        elif format == "csv":
            content = self._export_csv(thread, messages)
            filename = f"{thread.title or 'chat'}.csv"

        elif format == "png":
            # Generate image of conversation
            content = await self._export_png(thread, messages)
            filename = f"{thread.title or 'chat'}.png"

        elif format == "pdf":
            # Generate PDF
            content = await self._export_pdf(thread, messages)
            filename = f"{thread.title or 'chat'}.pdf"

        else:
            raise HTTPException(400, f"Unsupported format: {format}")

        # Save to storage
        file_path = await self._save_to_storage(filename, content)

        # Create export record
        export = ChatExport(
            thread_id=thread_id,
            format=format,
            filename=filename,
            file_path=file_path,
            file_size_bytes=len(content),
            messages_count=len(messages),
            exported_by=user_id
        )

        await db.insert(export)

        return export

    def _export_json(self, thread: ChatThread, messages: List[ChatMessage]) -> str:
        """Export as JSON"""

        data = {
            "thread": {
                "id": str(thread.id),
                "title": thread.title,
                "created_at": thread.created_at.isoformat(),
                "total_tokens": thread.total_tokens_in + thread.total_tokens_out,
                "estimated_cost": thread.estimated_cost
            },
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "tokens_in": m.tokens_in,
                    "tokens_out": m.tokens_out,
                    "created_at": m.created_at.isoformat()
                }
                for m in messages
            ]
        }

        return json.dumps(data, indent=2)

    def _export_csv(self, thread: ChatThread, messages: List[ChatMessage]) -> str:
        """Export as CSV"""

        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Timestamp", "Role", "Content", "Tokens In", "Tokens Out"])

        # Rows
        for m in messages:
            writer.writerow([
                m.created_at.isoformat(),
                m.role,
                m.content,
                m.tokens_in or "",
                m.tokens_out or ""
            ])

        return output.getvalue()

    async def _export_png(self, thread: ChatThread, messages: List[ChatMessage]) -> bytes:
        """Generate PNG image of conversation"""

        from PIL import Image, ImageDraw, ImageFont

        # Create image
        img_width = 1200
        line_height = 30
        padding = 20

        img_height = (len(messages) + 2) * line_height + padding * 2
        img = Image.new("RGB", (img_width, img_height), color=(255, 255, 255))

        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()

        y = padding

        # Title
        draw.text((padding, y), thread.title, fill=(0, 0, 0), font=font)
        y += line_height * 2

        # Messages
        for msg in messages:
            prefix = "You: " if msg.role == "user" else "Assistant: "
            text = prefix + msg.content[:80] + ("..." if len(msg.content) > 80 else "")

            color = (100, 100, 200) if msg.role == "user" else (100, 200, 100)
            draw.text((padding, y), text, fill=color, font=font)

            y += line_height

        # Save to bytes
        output = BytesIO()
        img.save(output, format="PNG")

        return output.getvalue()

    async def _export_pdf(self, thread: ChatThread, messages: List[ChatMessage]) -> bytes:
        """Generate PDF of conversation"""

        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO

        output = BytesIO()
        c = canvas.Canvas(output, pagesize=letter)

        y = 750

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, thread.title or "Conversation")
        y -= 30

        # Metadata
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Total tokens: {thread.total_tokens_in + thread.total_tokens_out}")
        y -= 15

        # Messages
        c.setFont("Helvetica", 12)

        for msg in messages:
            if y < 50:
                c.showPage()
                y = 750

            # Role label
            c.setFont("Helvetica-Bold", 11)
            role_text = "User" if msg.role == "user" else "Assistant"
            c.drawString(50, y, f"{role_text}:")
            y -= 20

            # Content (wrapped)
            c.setFont("Helvetica", 11)
            content_lines = self._wrap_text(msg.content, 80)

            for line in content_lines:
                if y < 50:
                    c.showPage()
                    y = 750

                c.drawString(70, y, line)
                y -= 15

            y -= 10

        c.save()

        return output.getvalue()

    @staticmethod
    def _wrap_text(text: str, width: int) -> List[str]:
        """Wrap text to specified width"""

        import textwrap
        return textwrap.wrap(text, width=width)
```

### 7.3 API Endpoints

```python
# Chat endpoints

@router.post("/chat/threads")
async def create_thread(
    request: CreateThreadRequest,
    current_user: TbUser = Depends(get_current_user)
):
    """Create new chat thread"""
    thread = await chat_service.create_thread(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        initial_title=request.title
    )
    return ResponseEnvelope(data={"thread": thread})

@router.post("/chat/{thread_id}/messages")
async def add_message(
    thread_id: str,
    request: AddMessageRequest,
    current_user: TbUser = Depends(get_current_user)
):
    """Add message to thread"""
    message = await chat_service.add_message(
        thread_id=UUID(thread_id),
        role=request.role,
        content=request.content,
        tokens_in=request.tokens_in,
        tokens_out=request.tokens_out
    )
    return ResponseEnvelope(data={"message": message})

@router.get("/chat/search")
async def search_history(
    q: str,
    type: str = "hybrid",
    current_user: TbUser = Depends(get_current_user)
):
    """Search chat history"""
    threads = await chat_service.search_history(
        user_id=current_user.id,
        query=q,
        search_type=type
    )
    return ResponseEnvelope(data={"threads": threads})

@router.post("/chat/{thread_id}/export")
async def export_thread(
    thread_id: str,
    request: ExportRequest,
    current_user: TbUser = Depends(get_current_user)
):
    """Export conversation"""
    export = await export_service.export_thread(
        thread_id=UUID(thread_id),
        format=request.format,
        user_id=current_user.id
    )

    # Return download link or file
    return FileResponse(
        path=export.file_path,
        filename=export.filename,
        media_type=f"application/{request.format}"
    )

@router.delete("/chat/{thread_id}")
async def delete_thread(
    thread_id: str,
    current_user: TbUser = Depends(get_current_user)
):
    """Soft delete thread"""
    await chat_service.soft_delete_thread(UUID(thread_id), current_user.id)
    return ResponseEnvelope(data={"deleted": True})
```

---

## Part 4: Task 8 - CEP Engine Integration

### 8.1 Overview

**Current State**:
- Basic CEP rule management
- Webhook notifications
- Apscheduler-based scheduling

**Target State**:
- Bytewax CEP engine integration
- Multi-channel notifications (Slack, Email, SMS)
- Rule performance monitoring
- Cron expression support
- Rule composition and complex event patterns

### 8.2 CEP Architecture with Bytewax

#### 8.2.1 Bytewax Integration

```python
# app/modules/cep_builder/bytewax_engine.py

from bytewax.dataflow import Dataflow
from bytewax.testing import TestingSource, TestingSink
from bytewax.connectors.kafka import KafkaSource, KafkaSink

class BytewaxCEPEngine:
    """Bytewax-based Complex Event Processing"""

    def __init__(self):
        self.dataflows: Dict[str, Dataflow] = {}
        self.state_store = {}

    def create_dataflow(self, rule_id: str, rule_def: CEPRuleDefinition) -> Dataflow:
        """
        Create Bytewax dataflow from CEP rule

        Rule types:
        1. Pattern matching: sequence of events
        2. Aggregation: group by and aggregate metrics
        3. Windowing: time-based windows
        4. Enrichment: join with external data
        """

        flow = Dataflow("cep_" + rule_id)

        # Source: Kafka, Redis, or REST API
        if rule_def.source_type == "kafka":
            source = KafkaSource(
                brokers=rule_def.source_config["brokers"],
                topics=[rule_def.source_config["topic"]]
            )
        elif rule_def.source_type == "api":
            source = ApiEventSource(rule_def.source_config["url"])
        else:
            source = TestingSource()

        flow.input("source", source)

        # Parse and validate events
        def parse_event(data):
            event = json.loads(data) if isinstance(data, str) else data
            return (event.get("id"), event)

        flow.map(parse_event, name="parse")

        # Apply filters
        def apply_filters(event_tuple):
            key, event = event_tuple
            if rule_def.filters:
                for filter_expr in rule_def.filters:
                    if not self._evaluate_filter(event, filter_expr):
                        return None
            return event_tuple

        flow.filter(lambda x: x is not None, name="filter")
        flow.map(apply_filters)

        # Apply transformations (enrichment)
        async def enrich(event):
            if rule_def.enrichment:
                for enrichment_rule in rule_def.enrichment:
                    enriched_data = await self._enrich_event(event, enrichment_rule)
                    event.update(enriched_data)
            return event

        # Aggregate (if needed)
        if rule_def.aggregation:
            flow.stateful_map(
                lambda state, event: self._aggregate(state, event, rule_def.aggregation),
                name="aggregate"
            )

        # Windowing
        if rule_def.window_type:
            if rule_def.window_type == "tumbling":
                flow.map(lambda e: (e, datetime.utcnow()), name="add_timestamp")
                # Group by window
                flow.stateful_map(
                    lambda state, event_tuple: self._tumbling_window(
                        state, event_tuple, rule_def.window_size_seconds
                    ),
                    name="window"
                )

            elif rule_def.window_type == "sliding":
                flow.stateful_map(
                    lambda state, event: self._sliding_window(
                        state, event, rule_def.window_size_seconds, rule_def.slide_seconds
                    ),
                    name="window"
                )

        # Sink: notify or store results
        def create_sink(event):
            if rule_def.action_type == "notify":
                self._queue_notification(rule_id, event, rule_def.actions)
            elif rule_def.action_type == "store":
                self._store_event(rule_id, event)

            return event

        flow.map(create_sink, name="sink")

        return flow

    def _evaluate_filter(self, event: dict, filter_expr: str) -> bool:
        """
        Evaluate filter expression

        Examples:
        - "event.metric > 100"
        - "event.status == 'error'"
        - "event.timestamp > now() - 5m"
        """

        # Simple eval (in production, use safe expression evaluator)
        context = {
            "event": event,
            "now": datetime.utcnow
        }

        try:
            return eval(filter_expr, {"__builtins__": {}}, context)
        except Exception:
            return False

    async def _enrich_event(self, event: dict, enrichment_rule: dict) -> dict:
        """Enrich event with additional data"""

        enrichment_type = enrichment_rule.get("type")

        if enrichment_type == "lookup":
            # Look up in database or cache
            key = enrichment_rule.get("key")
            lookup_table = enrichment_rule.get("table")

            value = await self._lookup_table(lookup_table, event.get(key))
            return {key: value}

        elif enrichment_type == "http":
            # Call external API
            url = enrichment_rule.get("url")
            response = await self._call_external_api(url, event)
            return response

        return {}

    def _aggregate(
        self,
        state: dict,
        event: dict,
        aggregation_spec: dict
    ) -> dict:
        """
        Aggregate events

        Examples:
        - count: number of events
        - sum: sum of metric values
        - avg: average of metric values
        - min/max: minimum/maximum
        """

        if state is None:
            state = {}

        agg_type = aggregation_spec.get("type")
        metric_field = aggregation_spec.get("field")

        if agg_type == "count":
            state["count"] = state.get("count", 0) + 1

        elif agg_type == "sum":
            value = event.get(metric_field, 0)
            state["sum"] = state.get("sum", 0) + value

        elif agg_type == "avg":
            value = event.get(metric_field, 0)
            state["sum"] = state.get("sum", 0) + value
            state["count"] = state.get("count", 0) + 1
            state["avg"] = state["sum"] / state["count"]

        return state

    def _tumbling_window(
        self,
        state: dict,
        event_tuple: tuple,
        window_size_seconds: int
    ) -> dict:
        """
        Tumbling window: non-overlapping windows

        Window boundaries: [0-60s), [60-120s), etc.
        """

        event, timestamp = event_tuple

        window_id = int(timestamp.timestamp() // window_size_seconds)

        if state is None:
            state = {}

        if window_id not in state:
            state[window_id] = []

        state[window_id].append(event)

        return state
```

#### 8.2.2 Multi-Channel Notification Service

```python
# app/modules/cep_builder/notification_channels.py

class NotificationChannel(ABC):
    """Base class for notification channels"""

    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        pass

class SlackNotificationChannel(NotificationChannel):
    """Send notifications to Slack"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, message: NotificationMessage) -> bool:
        """Send message to Slack"""

        payload = {
            "text": message.title,
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": message.title}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": message.body}
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Rule: {message.metadata.get('rule_id', 'N/A')}"
                        }
                    ]
                }
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Slack notification failed: {str(e)}")
            return False

class EmailNotificationChannel(NotificationChannel):
    """Send notifications via email (SMTP)"""

    def __init__(self, smtp_host: str, smtp_port: int, from_email: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_email = from_email
        self.password = password

    async def send(self, message: NotificationMessage) -> bool:
        """Send email"""

        try:
            # Create MIME message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.title
            msg["From"] = self.from_email
            msg["To"] = ", ".join(message.recipients)

            # HTML content
            html = f"""
            <html>
                <body>
                    <h2>{message.title}</h2>
                    <p>{message.body}</p>
                    <hr>
                    <small>Rule: {message.metadata.get('rule_id')}</small>
                </body>
            </html>
            """

            msg.attach(MIMEText(html, "html"))

            # Send
            async with aiosmtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
                await smtp.login(self.from_email, self.password)
                await smtp.send_message(msg)

            return True

        except Exception as e:
            logger.error(f"Email notification failed: {str(e)}")
            return False

class SmsNotificationChannel(NotificationChannel):
    """Send notifications via SMS (Twilio)"""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number

    async def send(self, message: NotificationMessage) -> bool:
        """Send SMS"""

        try:
            for recipient in message.recipients:
                await self.client.messages.create(
                    body=message.body[:160],  # SMS length limit
                    from_=self.from_number,
                    to=recipient
                )

            return True

        except Exception as e:
            logger.error(f"SMS notification failed: {str(e)}")
            return False

class NotificationChannelFactory:
    """Factory for creating notification channels"""

    @staticmethod
    def create(
        channel_type: str,
        config: dict
    ) -> NotificationChannel:
        """Create notification channel based on type"""

        if channel_type == "slack":
            return SlackNotificationChannel(config["webhook_url"])

        elif channel_type == "email":
            return EmailNotificationChannel(
                config["smtp_host"],
                config["smtp_port"],
                config["from_email"],
                config["password"]
            )

        elif channel_type == "sms":
            return SmsNotificationChannel(
                config["account_sid"],
                config["auth_token"],
                config["from_number"]
            )

        elif channel_type == "webhook":
            return WebhookNotificationChannel(config["url"])

        else:
            raise ValueError(f"Unknown channel type: {channel_type}")
```

#### 8.2.3 Rule Performance Monitoring

```python
# app/modules/cep_builder/rule_monitor.py

class RulePerformanceMonitor:
    """Monitor CEP rule execution performance"""

    async def record_execution(
        self,
        rule_id: str,
        execution_time_ms: int,
        events_processed: int,
        events_matched: int,
        errors: Optional[List[str]] = None
    ):
        """Record rule execution metrics"""

        metric = RuleExecutionMetric(
            rule_id=rule_id,
            execution_time_ms=execution_time_ms,
            events_processed=events_processed,
            events_matched=events_matched,
            error_count=len(errors or []),
            created_at=datetime.utcnow()
        )

        await db.insert(metric)

        # Update rule statistics
        await self._update_rule_stats(rule_id)

    async def get_rule_performance(
        self,
        rule_id: str,
        time_range_minutes: int = 60
    ) -> RulePerformanceStats:
        """Get aggregated performance statistics"""

        metrics = await db.fetch(
            """
            SELECT * FROM tb_rule_execution_metric
            WHERE rule_id = $1
            AND created_at > now() - interval '1 minute' * $2
            """,
            rule_id,
            time_range_minutes
        )

        if not metrics:
            return RulePerformanceStats(rule_id=rule_id)

        execution_times = [m["execution_time_ms"] for m in metrics]

        return RulePerformanceStats(
            rule_id=rule_id,
            total_executions=len(metrics),
            avg_execution_time_ms=statistics.mean(execution_times),
            min_execution_time_ms=min(execution_times),
            max_execution_time_ms=max(execution_times),
            p95_execution_time_ms=statistics.quantiles(execution_times, n=20)[18],
            total_events_processed=sum(m["events_processed"] for m in metrics),
            total_events_matched=sum(m["events_matched"] for m in metrics),
            total_errors=sum(m["error_count"] for m in metrics)
        )
```

### 8.3 Database Models for Task 8

```python
# New models for CEP enhancements

class CEPRuleDefinition(SQLModel, table=True):
    __tablename__ = "tb_cep_rule"

    # Existing fields...
    rule_id: UUID = Field(primary_key=True)
    name: str
    description: Optional[str]

    # Engine & patterns
    engine: str = "bytewax"  # "apscheduler" | "bytewax"

    # Trigger types
    trigger_type: str  # "metric", "event", "schedule", "webhook"
    trigger_spec: dict  # Trigger configuration

    # Multi-channel notifications
    notification_channels: List[dict] = Field(default_factory=list)
    # [
    #   {"type": "slack", "webhook_url": "..."},
    #   {"type": "email", "recipients": ["..."]},
    #   {"type": "sms", "recipients": ["+1234567890"]}
    # ]

    # Rule composition
    depends_on: List[UUID] = Field(default_factory=list)  # Other rule IDs
    rule_condition: Optional[str]  # Complex condition

    # Cron scheduling
    cron_expression: Optional[str]  # For schedule-based triggers
    schedule_timezone: str = "UTC"

    # Performance config
    max_execution_time_ms: int = 5000
    max_events_batch: int = 1000

    # Status
    is_enabled: bool = True
    status: str  # "active", "paused", "error"
    error_message: Optional[str]

    created_at: datetime
    updated_at: datetime

class RuleExecutionMetric(SQLModel, table=True):
    __tablename__ = "tb_rule_execution_metric"

    metric_id: UUID = Field(primary_key=True)
    rule_id: UUID = Field(foreign_key="tb_cep_rule.rule_id")

    execution_time_ms: int
    events_processed: int
    events_matched: int
    error_count: int

    created_at: datetime

class NotificationLog(SQLModel, table=True):
    __tablename__ = "tb_notification_log"

    notification_id: UUID = Field(primary_key=True)
    rule_id: UUID = Field(foreign_key="tb_cep_rule.rule_id")

    channel: str  # "slack", "email", "sms", "webhook"
    recipient: str
    message_title: str
    message_body: str

    status: str  # "sent", "failed", "pending"
    error_message: Optional[str]

    created_at: datetime
```

---

## Part 5: Task 9 - Admin Dashboard

### 9.1 Overview

**Target State**:
- User/tenant monitoring and analytics
- System resource monitoring
- Asset registry management UI
- Log viewing and download
- Settings/configuration interface

### 9.2 Admin Dashboard Components

#### 9.2.1 User Management Panel

```typescript
// apps/web/src/components/admin/UserManagementPanel.tsx

export function UserManagementPanel() {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [filters, setFilters] = useState({ role: "", status: "" });

  const usersQuery = useQuery({
    queryKey: ["users", filters],
    queryFn: () => authenticatedFetch("/admin/users", { params: filters })
  });

  const updateUserMutation = useMutation({
    mutationFn: (data) => authenticatedFetch(`/admin/users/${selectedUser.id}`, {
      method: "PUT",
      body: JSON.stringify(data)
    })
  });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* User List */}
      <div className="lg:col-span-2">
        <Card>
          <CardHeader>
            <CardTitle>Users</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Filters */}
              <div className="flex gap-4">
                <Select
                  value={filters.role}
                  onChange={(role) => setFilters({...filters, role})}
                >
                  <option value="">All Roles</option>
                  <option value="admin">Admin</option>
                  <option value="manager">Manager</option>
                  <option value="developer">Developer</option>
                  <option value="viewer">Viewer</option>
                </Select>
              </div>

              {/* User Table */}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Login</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {usersQuery.data?.users?.map((user) => (
                    <TableRow key={user.id} className="cursor-pointer" onClick={() => setSelectedUser(user)}>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>{user.role}</TableCell>
                      <TableCell>
                        <Badge variant={user.is_active ? "success" : "destructive"}>
                          {user.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatDate(user.last_login_at)}</TableCell>
                      <TableCell>
                        <Button size="sm" variant="outline">Edit</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* User Details */}
      {selectedUser && (
        <Card>
          <CardHeader>
            <CardTitle>User Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium">Email</label>
              <Input value={selectedUser.email} disabled />
            </div>

            <div>
              <label className="block text-sm font-medium">Role</label>
              <Select defaultValue={selectedUser.role}>
                <option value="viewer">Viewer</option>
                <option value="developer">Developer</option>
                <option value="manager">Manager</option>
                <option value="admin">Admin</option>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium">Status</label>
              <Checkbox defaultChecked={selectedUser.is_active} label="Active" />
            </div>

            <div className="text-sm text-gray-600">
              <p>Created: {formatDate(selectedUser.created_at)}</p>
              <p>Last Login: {formatDate(selectedUser.last_login_at)}</p>
            </div>

            <Button
              className="w-full"
              onClick={() => updateUserMutation.mutate({
                role: selectedUser.role,
                is_active: selectedUser.is_active
              })}
            >
              Save Changes
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

#### 9.2.2 System Monitoring Dashboard

```typescript
// apps/web/src/components/admin/SystemMonitoringDashboard.tsx

export function SystemMonitoringDashboard() {
  const systemStatsQuery = useQuery({
    queryKey: ["system-stats"],
    queryFn: () => authenticatedFetch("/admin/system-stats"),
    refetchInterval: 5000  // Refresh every 5 seconds
  });

  const stats = systemStatsQuery.data?.stats;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Database Size */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Database Size</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatBytes(stats?.db_size_bytes)}</div>
          <p className="text-xs text-gray-500">PostgreSQL + extensions</p>
          <Progress value={stats?.db_usage_percent || 0} className="mt-2" />
        </CardContent>
      </Card>

      {/* Redis Memory */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Redis Memory</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatBytes(stats?.redis_memory_bytes)}</div>
          <p className="text-xs text-gray-500">Cache + Queue</p>
          <Progress value={stats?.redis_usage_percent || 0} className="mt-2" />
        </CardContent>
      </Card>

      {/* Active Sessions */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Active Sessions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats?.active_sessions || 0}</div>
          <p className="text-xs text-gray-500">Connected users</p>
        </CardContent>
      </Card>

      {/* API Health */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">API Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${stats?.api_healthy ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm font-medium">{stats?.api_healthy ? 'Healthy' : 'Down'}</span>
          </div>
          <p className="text-xs text-gray-500">{stats?.api_response_time_ms}ms avg</p>
        </CardContent>
      </Card>
    </div>
  );
}
```

#### 9.2.3 Audit Log Viewer

```typescript
// apps/web/src/components/admin/AuditLogViewer.tsx

export function AuditLogViewer() {
  const [filters, setFilters] = useState({
    action: "",
    resourceType: "",
    dateFrom: null,
    dateTo: null
  });

  const logsQuery = useQuery({
    queryKey: ["audit-logs", filters],
    queryFn: () => authenticatedFetch("/admin/audit-logs", { params: filters })
  });

  const exportMutation = useMutation({
    mutationFn: () => authenticatedFetch("/admin/audit-logs/export", {
      method: "POST",
      body: JSON.stringify(filters)
    })
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>Audit Log</CardTitle>
          <Button
            size="sm"
            variant="outline"
            onClick={() => exportMutation.mutate()}
          >
            Export
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Select
              placeholder="Action"
              value={filters.action}
              onChange={(action) => setFilters({...filters, action})}
            >
              <option value="">All Actions</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="delete">Delete</option>
            </Select>

            <Select
              placeholder="Resource Type"
              value={filters.resourceType}
              onChange={(resourceType) => setFilters({...filters, resourceType})}
            >
              <option value="">All Resources</option>
              <option value="api">API</option>
              <option value="asset">Asset</option>
              <option value="api_key">API Key</option>
            </Select>

            <DatePicker
              label="From"
              value={filters.dateFrom}
              onChange={(date) => setFilters({...filters, dateFrom: date})}
            />

            <DatePicker
              label="To"
              value={filters.dateTo}
              onChange={(date) => setFilters({...filters, dateTo: date})}
            />
          </div>

          {/* Audit Log Table */}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>Changes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logsQuery.data?.logs?.map((log) => (
                <TableRow key={log.audit_id}>
                  <TableCell>{formatDateTime(log.created_at)}</TableCell>
                  <TableCell>{log.actor_email}</TableCell>
                  <TableCell>
                    <Badge variant={
                      log.action === "delete" ? "destructive" :
                      log.action === "create" ? "success" : "default"
                    }>
                      {log.action}
                    </Badge>
                  </TableCell>
                  <TableCell>{log.resource_type}</TableCell>
                  <TableCell className="max-w-sm truncate">
                    <code className="text-xs">{JSON.stringify(log.changes)}</code>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## Part 6: Task 10 - Testing Infrastructure

### 10.1 Overview

**Target State**:
- Unit test suite (80%+ coverage)
- Integration tests for APIs
- E2E tests with Playwright
- CI/CD pipeline configuration (GitHub Actions, GitLab CI, etc.)

### 10.2 Backend Testing Architecture

#### 10.2.1 Unit Tests

```python
# tests/unit/test_api_manager.py

import pytest
from app.modules.api_manager.services.sql_validator import SQLValidator
from app.modules.api_manager.models import ApiDefinition

class TestSQLValidator:
    """Test SQL validation"""

    @pytest.fixture
    def validator(self):
        return SQLValidator()

    @pytest.mark.asyncio
    async def test_validate_safe_query(self, validator):
        """Test that safe SELECT query passes"""
        sql = "SELECT * FROM tb_user WHERE id = $1"

        result = await validator.validate(sql)

        assert result.is_safe is True
        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_reject_dangerous_keywords(self, validator):
        """Test that DROP queries are rejected"""
        sql = "DROP TABLE tb_user"

        result = await validator.validate(sql)

        assert result.is_safe is False
        assert "DROP" in result.errors[0]

    @pytest.mark.asyncio
    async def test_extract_tables(self, validator):
        """Test table extraction from query"""
        sql = """
        SELECT u.*, a.* FROM tb_user u
        JOIN tb_api_definition a ON u.id = a.owner_id
        """

        result = await validator.validate(sql)

        assert result.is_valid is True
        assert "tb_user" in result.metadata["tables"]
        assert "tb_api_definition" in result.metadata["tables"]

@pytest.mark.asyncio
async def test_api_creation():
    """Test creating new API"""

    api_data = {
        "name": "Get Users",
        "method": "GET",
        "path": "/users",
        "mode": "sql",
        "logic": "SELECT * FROM tb_user",
        "input_schema": {},
        "output_schema": {"type": "array"}
    }

    api = await api_service.create_api(api_data, current_user)

    assert api.id is not None
    assert api.version == 1
    assert api.status == "draft"

@pytest.mark.asyncio
async def test_api_versioning():
    """Test API version management"""

    # Create API
    api = await api_service.create_api(api_data, current_user)
    original_version = api.version

    # Update API
    api = await api_service.update_api(
        api.id,
        {"logic": "SELECT * FROM tb_user WHERE is_active = true"},
        current_user
    )

    # Check version incremented
    assert api.version == original_version + 1

    # Get version history
    versions = await db.fetch(
        "SELECT * FROM tb_api_definition_version WHERE api_id = $1",
        api.id
    )

    assert len(versions) == 2

@pytest.mark.asyncio
async def test_api_rollback():
    """Test rolling back to previous version"""

    api = await api_service.create_api(api_data, current_user)
    v1_logic = api.logic

    # Update
    await api_service.update_api(api.id, {"logic": "UPDATED LOGIC"}, current_user)

    # Rollback
    api = await api_service.rollback_api(api.id, 1, current_user)

    assert api.logic == v1_logic
```

#### 10.2.2 Integration Tests

```python
# tests/integration/test_chat_api.py

@pytest.mark.asyncio
class TestChatAPI:
    """Integration tests for Chat API"""

    @pytest.fixture
    async def client(self):
        """Test client with authentication"""
        return AsyncClient(app=app, base_url="http://test")

    @pytest.fixture
    async def auth_headers(self, client):
        """Authenticated headers"""
        response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password"}
        )
        token = response.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    async def test_create_thread(self, client, auth_headers):
        """Test creating chat thread"""
        response = await client.post(
            "/chat/threads",
            json={"title": "Test Chat"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "thread" in data
        assert data["thread"]["title"] == "Test Chat"

    async def test_add_message_and_auto_title(self, client, auth_headers):
        """Test message addition triggers auto-title generation"""

        # Create thread
        thread_response = await client.post(
            "/chat/threads",
            json={},
            headers=auth_headers
        )
        thread_id = thread_response.json()["data"]["thread"]["id"]

        # Add user message
        await client.post(
            f"/chat/{thread_id}/messages",
            json={"role": "user", "content": "What is Python?"},
            headers=auth_headers
        )

        # Add assistant response (should trigger title generation)
        await client.post(
            f"/chat/{thread_id}/messages",
            json={
                "role": "assistant",
                "content": "Python is a programming language",
                "tokens_out": 10
            },
            headers=auth_headers
        )

        # Get thread to verify title
        thread_response = await client.get(
            f"/chat/{thread_id}",
            headers=auth_headers
        )

        thread = thread_response.json()["data"]
        assert thread["title"] is not None
        assert thread["title_generated_by"] == "llm"

    async def test_search_chat_history(self, client, auth_headers):
        """Test searching chat history"""

        # Create thread with messages
        # ... (setup code)

        response = await client.get(
            "/chat/search?q=Python&type=hybrid",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "threads" in data
```

### 10.3 Frontend E2E Tests

#### 10.3.1 Authentication & Dashboard Flow

```typescript
// apps/web/e2e/auth.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should login successfully', async ({ page }) => {
    // Navigate to login
    await page.goto('/login');

    // Fill credentials
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');

    // Submit
    await page.click('button[type="submit"]');

    // Should redirect to home
    await expect(page).toHaveURL('/');

    // Check user menu shows email
    const userMenu = page.locator('[data-testid="user-menu"]');
    await expect(userMenu).toContainText('test@example.com');
  });

  test('should handle login errors', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[name="email"]', 'wrong@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Should show error message
    const error = page.locator('[data-testid="error-message"]');
    await expect(error).toBeVisible();
    await expect(error).toContainText('Invalid credentials');
  });

  test('should refresh token on 401', async ({ page }) => {
    // Login
    await page.goto('/');
    // ... login process ...

    // Make request that returns 401
    // (Token should auto-refresh)

    // Should still be logged in
    const userMenu = page.locator('[data-testid="user-menu"]');
    await expect(userMenu).toBeVisible();
  });
});
```

#### 10.3.2 Admin Dashboard Tests

```typescript
// apps/web/e2e/admin-dashboard.spec.ts

test.describe('Admin Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await loginAsAdmin(page);
    // Navigate to admin
    await page.goto('/admin');
  });

  test('should display user management panel', async ({ page }) => {
    // Wait for users table to load
    const usersTable = page.locator('[data-testid="users-table"]');
    await expect(usersTable).toBeVisible();

    // Should have at least one row
    const rows = page.locator('tbody tr');
    expect(await rows.count()).toBeGreaterThan(0);
  });

  test('should update user role', async ({ page }) => {
    // Find user row and click
    const firstUserRow = page.locator('tbody tr').first();
    await firstUserRow.click();

    // Update role dropdown
    const roleSelect = page.locator('[data-testid="role-select"]');
    await roleSelect.selectOption('manager');

    // Save
    await page.click('button:has-text("Save Changes")');

    // Should show success toast
    const toast = page.locator('[data-testid="success-toast"]');
    await expect(toast).toBeVisible();
  });

  test('should filter audit logs', async ({ page }) => {
    // Navigate to audit logs
    await page.click('a:has-text("Audit Logs")');

    // Apply filter
    const actionSelect = page.locator('[name="action"]');
    await actionSelect.selectOption('update');

    // Results should be filtered
    const rows = page.locator('tbody tr');
    for (let i = 0; i < await rows.count(); i++) {
      const actionCell = rows.nth(i).locator('td:nth-child(3)');
      await expect(actionCell).toContainText('Update');
    }
  });

  test('should export audit logs', async ({ page }) => {
    // Navigate to audit logs
    await page.click('a:has-text("Audit Logs")');

    // Click export button
    const downloadPromise = page.waitForEvent('download');
    await page.click('button:has-text("Export")');

    const download = await downloadPromise;

    // Verify file
    expect(download.suggestedFilename()).toContain('audit-log');
  });
});
```

### 10.4 CI/CD Pipeline Configuration

#### 10.4.1 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          cd apps/api
          pip install -r requirements.txt

      - name: Run linting
        run: |
          cd apps/api
          ruff check .
          mypy . --ignore-missing-imports

      - name: Run tests
        run: |
          cd apps/api
          pytest tests/ --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./apps/api/coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: "18"

      - name: Install dependencies
        run: |
          cd apps/web
          npm install

      - name: Run linting
        run: |
          cd apps/web
          npm run lint

      - name: Run E2E tests
        run: |
          cd apps/web
          npm run test:e2e

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: apps/web/playwright-report/
```

---

## Summary

### Implementation Timeline
- **Week 1-2**: Task 5 (Document Search) + Task 6 (API Manager) in parallel
- **Week 3**: Task 7 (Chat History)
- **Week 4**: Task 8 (CEP Engine)
- **Week 5-6**: Task 9 (Admin Dashboard)
- **Week 6-7**: Task 10 (Testing Infrastructure)
- **Week 8**: Integration, bug fixes, documentation

### Key Technical Decisions

1. **Document Processing**: Async RQ jobs for background processing
2. **Search**: Hybrid vector + BM25 with RRF ranking
3. **API Versioning**: Full snapshot-based versioning with rollback
4. **Chat Enhancement**: LLM-based auto-titling + token tracking
5. **CEP Engine**: Bytewax for complex event patterns
6. **Notifications**: Factory pattern for multi-channel support
7. **Testing**: Pytest + Playwright for comprehensive coverage

### Risk Mitigation

- **OCR Performance**: Use lazy loading for large PDFs
- **Bytewax Complexity**: Start with simple patterns, build incrementally
- **Multi-channel Notifications**: Graceful degradation if channel fails
- **Admin Dashboard**: Rate limit sensitive operations
- **Test Flakiness**: Use proper wait conditions, avoid sleep()

---

**Status**: ✅ Design complete - Ready for implementation
**Date**: January 18, 2026
**Quality**: Production-ready architecture
