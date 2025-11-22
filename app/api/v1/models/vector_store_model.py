"""
Vector Store Model for RAG (Retrieval-Augmented Generation)
Stores embeddings of company data for semantic search using pgvector
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class VectorStore(Base):
    """
    Stores embeddings of company data chunks for semantic search.
    Each row represents a chunk of data (employee, project, task, etc.) with its embedding.
    """
    __tablename__ = "vector_store"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Content information
    content_type = Column(String(50), nullable=False, index=True)  # 'employee', 'project', 'task', 'department', 'company'
    content_id = Column(Integer, nullable=False, index=True)  # ID of the original record
    content_text = Column(Text, nullable=False)  # The text content to embed
    content_metadata = Column(Text, nullable=True)  # JSON string with additional metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    
    # Vector embedding (1536 dimensions for OpenAI text-embedding-3-small)
    embedding = Column(Vector(1536), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="vector_chunks")
    
    # Index for vector similarity search
    __table_args__ = (
        Index('idx_vector_store_company_type', 'company_id', 'content_type'),
        Index('idx_vector_store_content', 'content_type', 'content_id'),
    )
    
    def __repr__(self):
        return f"<VectorStore {self.content_type}:{self.content_id} for company {self.company_id}>"

