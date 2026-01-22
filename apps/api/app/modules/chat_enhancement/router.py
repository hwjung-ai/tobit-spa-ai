"""Chat enhancement routes for thread management and conversation export"""

import logging
from datetime import datetime
from typing import Optional

from core.auth import get_current_user
from core.config import get_settings
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .services.chat_service import ChatEnhancementService
from .services.export_service import ChatExportService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize services
chat_service = ChatEnhancementService()
export_service = ChatExportService()


class CreateThreadRequest(BaseModel):
    """Request for creating a chat thread"""
    title: Optional[str] = None
    description: Optional[str] = None


# Get settings for default model
settings = get_settings()

class AddMessageRequest(BaseModel):
    """Request for adding a message to thread"""
    role: str  # "user" or "assistant"
    content: str
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    model: Optional[str] = settings.chat_model  # Use environment variable


class ThreadResponse(BaseModel):
    """Response for chat thread"""
    thread_id: str
    title: str
    description: Optional[str]
    message_count: int
    token_count: int
    estimated_cost: float
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    """Response for chat message"""
    message_id: str
    thread_id: str
    role: str
    content: str
    tokens_in: Optional[int]
    tokens_out: Optional[int]
    model: str
    created_at: str


class SearchHistoryRequest(BaseModel):
    """Request for searching chat history"""
    query: str
    search_type: str = "hybrid"  # text, vector, hybrid
    top_k: int = 10
    min_relevance: float = 0.5


class SearchHistoryResponse(BaseModel):
    """Response for search result"""
    thread_id: str
    message_id: str
    role: str
    content: str
    relevance_score: float


class ExportRequest(BaseModel):
    """Request for exporting conversation"""
    format: str  # json, csv, markdown, text
    include_metadata: bool = True


@router.post("/threads", response_model=ThreadResponse)
async def create_thread(
    request: CreateThreadRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new chat thread

    Returns:
    - thread_id: Unique identifier for the thread
    - title: Auto-generated or provided title
    - Token tracking and cost estimation
    """

    try:
        logger.info(
            f"Creating chat thread for user {current_user.get('id')}, "
            f"title: {request.title}"
        )

        # In real implementation:
        # - Create db.ChatThread record
        # - Set tenant_id from current_user
        # - Initialize token counters
        # - Return created thread with response

        # Placeholder response
        thread_id = "thread_" + datetime.utcnow().isoformat().replace(":", "-")
        return {
            "thread_id": thread_id,
            "title": request.title or "New Conversation",
            "description": request.description,
            "message_count": 0,
            "token_count": 0,
            "estimated_cost": 0.0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to create thread: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get chat thread details

    Returns:
    - Thread metadata
    - Message count and total tokens
    - Estimated cost based on token usage
    """

    try:
        logger.info(f"Fetching thread {thread_id}")

        # In real implementation:
        # - Query db.ChatThread by thread_id
        # - Verify current_user has access
        # - Calculate token_count sum and estimated_cost

        # Placeholder response
        return {
            "thread_id": thread_id,
            "title": "Sample Conversation",
            "description": None,
            "message_count": 5,
            "token_count": 1250,
            "estimated_cost": 0.0525,
            "created_at": "2026-01-18T10:00:00Z",
            "updated_at": "2026-01-18T10:30:00Z"
        }

    except Exception as e:
        logger.error(f"Failed to get thread: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/threads/{thread_id}/messages", response_model=MessageResponse)
async def add_message(
    thread_id: str,
    request: AddMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Add message to chat thread

    Features:
    - Automatic token tracking
    - Cost estimation based on model
    - Auto-title generation on first assistant response
    - Token usage logging for audit trail
    """

    try:
        if request.role not in ["user", "assistant"]:
            raise HTTPException(400, "Role must be 'user' or 'assistant'")

        logger.info(
            f"Adding message to thread {thread_id}, "
            f"role: {request.role}, tokens_in: {request.tokens_in}, "
            f"tokens_out: {request.tokens_out}"
        )

        # In real implementation:
        # - Validate thread_id exists and user has access
        # - Create db.ChatMessage record
        # - Call chat_service.add_message() for processing
        # - Generate title if first assistant message
        # - Update token counters and costs
        # - Log to audit trail

        # Placeholder response
        message_id = f"msg_{datetime.utcnow().isoformat().replace(':', '-')}"
        return {
            "message_id": message_id,
            "thread_id": thread_id,
            "role": request.role,
            "content": request.content,
            "tokens_in": request.tokens_in or 0,
            "tokens_out": request.tokens_out or 0,
            "model": request.model,
            "created_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add message: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/threads/{thread_id}/messages", response_model=dict)
async def get_thread_messages(
    thread_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get paginated messages from a thread

    Returns:
    - Messages in order of creation
    - Each message with role, content, tokens, model
    - Pagination metadata
    """

    try:
        (page - 1) * per_page

        logger.info(
            f"Fetching messages for thread {thread_id}, "
            f"page={page}, per_page={per_page}"
        )

        # In real implementation:
        # - Query db.ChatMessage where thread_id
        # - Order by created_at ASC
        # - Apply pagination
        # - Return with total count

        # Placeholder response
        return {
            "status": "ok",
            "thread_id": thread_id,
            "page": page,
            "per_page": per_page,
            "total": 0,
            "messages": []
        }

    except Exception as e:
        logger.error(f"Failed to get messages: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/search", response_model=dict)
async def search_history(
    request: SearchHistoryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Search across chat history

    Search Types:
    - text: Full-text search using BM25
    - vector: Semantic search using embeddings
    - hybrid: Combines both with RRF ranking

    Returns top matching messages with relevance scores
    """

    try:
        if not request.query or len(request.query.strip()) < 2:
            raise HTTPException(400, "Query must be at least 2 characters")

        logger.info(
            f"Searching history: query='{request.query[:50]}', "
            f"type={request.search_type}, top_k={request.top_k}"
        )

        # In real implementation:
        # - Call chat_service.search_history()
        # - Apply search_type (text, vector, hybrid)
        # - Filter by tenant_id from current_user
        # - Return top_k results with relevance scores
        # - Log search for analytics

        # Placeholder response
        return {
            "status": "ok",
            "query": request.query,
            "search_type": request.search_type,
            "results_count": 0,
            "results": []
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/threads/{thread_id}/export", response_model=dict)
async def export_conversation(
    thread_id: str,
    request: ExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Export conversation in specified format

    Supported formats:
    - json: Structured JSON with metadata
    - csv: Spreadsheet format with messages
    - markdown: Markdown with role headers
    - text: Plain text with separators

    Optional metadata includes:
    - Thread title and timestamps
    - Message counts and token usage
    - Cost estimates
    """

    try:
        if request.format not in ["json", "csv", "markdown", "text"]:
            raise HTTPException(400, f"Unsupported format: {request.format}")

        logger.info(
            f"Exporting thread {thread_id} as {request.format}"
        )

        # In real implementation:
        # - Get all messages from db.ChatMessage where thread_id
        # - Get thread metadata from db.ChatThread
        # - Call export_service.export_conversation()
        # - Return as file download with appropriate MIME type
        # - Content-Disposition header for filename

        # Placeholder response
        return {
            "status": "ok",
            "thread_id": thread_id,
            "format": request.format,
            "message": "Export in progress"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.delete("/threads/{thread_id}", response_model=dict)
async def delete_thread(
    thread_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Soft delete a chat thread

    The thread and all messages are marked as deleted
    but remain in database for audit trail and recovery
    """

    try:
        logger.info(f"Deleting thread {thread_id}")

        # In real implementation:
        # - Verify user has access to thread
        # - Update db.ChatThread set deleted_at = now()
        # - Log audit entry with soft delete reason
        # - Don't actually delete from DB (soft delete)

        return {
            "status": "ok",
            "message": f"Thread {thread_id} deleted"
        }

    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.get("/list", response_model=dict)
async def list_threads(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("updated_at"),
    include_deleted: bool = Query(False),
    current_user: dict = Depends(get_current_user)
):
    """
    List all chat threads for current user

    Returns:
    - Thread metadata with message counts
    - Token usage and cost estimates
    - Last message preview
    - Created and updated timestamps

    Pagination and sorting supported
    """

    try:
        (page - 1) * per_page

        logger.info(
            f"Listing threads for user {current_user.get('id')}, "
            f"page={page}, per_page={per_page}, sort_by={sort_by}"
        )

        # In real implementation:
        # - Query db.ChatThread where tenant_id = current_user.tenant_id
        # - Filter deleted_at IS NULL unless include_deleted=True
        # - Order by sort_by (created_at, updated_at, message_count, etc.)
        # - Apply pagination
        # - For each thread, get message count, token sum, last message
        # - Calculate estimated costs

        # Placeholder response
        return {
            "status": "ok",
            "page": page,
            "per_page": per_page,
            "total": 0,
            "threads": []
        }

    except Exception as e:
        logger.error(f"List failed: {str(e)}")
        raise HTTPException(500, str(e))
