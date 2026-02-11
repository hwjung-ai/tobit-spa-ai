"""add_llm_call_log

Revision ID: 0052
Revises: 0051
Create Date: 2026-02-10 16:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0052'
down_revision: Union[str, None] = '0051'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tb_llm_call_log table for tracking LLM API calls"""

    # Create the LLM call log table
    op.create_table(
        'tb_llm_call_log',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('trace_id', sa.Text(), nullable=True),
        sa.Column('call_type', sa.Text(), nullable=False, index=True),  # 'planner', 'output_parser', 'tool', etc
        sa.Column('call_index', sa.Integer(), nullable=False, default=1),  # For ordering multiple calls

        # Input (what we sent to LLM)
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('user_prompt', sa.Text(), nullable=True),
        sa.Column('context', sa.JSON(), nullable=True),  # Asset versions, tools, etc

        # Output (what we received from LLM)
        sa.Column('raw_response', sa.Text(), nullable=True),  # Full LLM response
        sa.Column('parsed_response', sa.JSON(), nullable=True),  # Parsed result (Plan, tool_calls, etc)

        # Metadata
        sa.Column('model_name', sa.Text(), nullable=False, index=True),  # 'gpt-4o', 'claude-3-5-sonnet-20241022', etc
        sa.Column('provider', sa.Text(), nullable=True),  # 'openai', 'anthropic', 'google', etc
        sa.Column('input_tokens', sa.Integer(), nullable=False, default=0),
        sa.Column('output_tokens', sa.Integer(), nullable=False, default=0),
        sa.Column('total_tokens', sa.Integer(), nullable=False, default=0),
        sa.Column('latency_ms', sa.Integer(), nullable=False, default=0),  # Request to response time

        # Timing
        sa.Column('request_time', sa.TIMESTAMP(timezone=True), nullable=False),  # When request was sent
        sa.Column('response_time', sa.TIMESTAMP(timezone=True), nullable=True),  # When response was received
        sa.Column('duration_ms', sa.Integer(), nullable=False, default=0),  # Calculated duration

        # Status
        sa.Column('status', sa.Text(), nullable=False, default='success'),  # 'success', 'error', 'timeout'
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),

        # Feature/UI context
        sa.Column('feature', sa.Text(), nullable=True, index=True),  # 'ops', 'docs', 'cep', etc
        sa.Column('ui_endpoint', sa.Text(), nullable=True),  # '/ops/ask', '/ops/query', etc
        sa.Column('user_id', sa.UUID(), nullable=True),

        # Analytics fields
        sa.Column('tags', sa.JSON(), nullable=True),  # Custom tags for filtering/grouping

        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),

        # NOTE:
        # tb_execution_trace.trace_id is TEXT, so we keep this as TEXT without FK
        # to avoid UUID/TEXT type mismatch across environments.
    )

    # Create indexes for common queries
    op.create_index('ix_llm_call_created_at', 'tb_llm_call_log', ['created_at'], unique=False)
    op.create_index('ix_llm_call_trace_id', 'tb_llm_call_log', ['trace_id'], unique=False)
    op.create_index('ix_llm_call_model_name', 'tb_llm_call_log', ['model_name'], unique=False)
    op.create_index('ix_llm_call_status', 'tb_llm_call_log', ['status'], unique=False)
    op.create_index('ix_llm_call_feature', 'tb_llm_call_log', ['feature'], unique=False)

    # Create composite index for time-series queries
    op.create_index('ix_llm_call_created_model', 'tb_llm_call_log', ['created_at', 'model_name'], unique=False)


def downgrade() -> None:
    """Drop tb_llm_call_log table"""
    op.drop_index('ix_llm_call_created_model', table_name='tb_llm_call_log')
    op.drop_index('ix_llm_call_trace_id', table_name='tb_llm_call_log')
    op.drop_index('ix_llm_call_feature', table_name='tb_llm_call_log')
    op.drop_index('ix_llm_call_status', table_name='tb_llm_call_log')
    op.drop_index('ix_llm_call_model_name', table_name='tb_llm_call_log')
    op.drop_index('ix_llm_call_created_at', table_name='tb_llm_call_log')
    op.drop_table('tb_llm_call_log')
