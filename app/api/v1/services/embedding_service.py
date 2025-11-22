"""
Embedding Service for generating and managing vector embeddings
Uses OpenAI's text-embedding-3-small model for cost-effective embeddings
"""
from typing import List, Optional
from openai import OpenAI
import json

from app.core.config import settings


class EmbeddingService:
    """Service for generating embeddings using OpenAI"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = "text-embedding-3-small"  # Cost-effective, 1536 dimensions
        self.embedding_dimensions = 1536
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text.strip(),
                dimensions=self.embedding_dimensions
            )
            return response.data[0].embedding
        except Exception as e:
            raise ValueError(f"Error generating embedding: {str(e)}")
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single API call (more efficient).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Filter out empty texts
        valid_texts = [t.strip() for t in texts if t and t.strip()]
        if not valid_texts:
            return []
        
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=valid_texts,
                dimensions=self.embedding_dimensions
            )
            # Return embeddings in the same order as input
            embeddings_dict = {item.index: item.embedding for item in response.data}
            return [embeddings_dict.get(i, [0.0] * self.embedding_dimensions) for i in range(len(valid_texts))]
        except Exception as e:
            raise ValueError(f"Error generating batch embeddings: {str(e)}")
    
    def create_content_text(
        self,
        content_type: str,
        content_data: dict,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Create a searchable text representation of content for embedding.
        This text will be used for semantic search.
        
        Args:
            content_type: Type of content ('employee', 'project', 'task', 'department', 'company')
            content_data: Dictionary containing the content data
            metadata: Optional additional metadata
            
        Returns:
            Formatted text string for embedding
        """
        if content_type == "employee":
            return self._format_employee_text(content_data)
        elif content_type == "project":
            return self._format_project_text(content_data)
        elif content_type == "task":
            return self._format_task_text(content_data)
        elif content_type == "department":
            return self._format_department_text(content_data)
        elif content_type == "company":
            return self._format_company_text(content_data)
        else:
            # Generic format
            return json.dumps(content_data, indent=2)
    
    def _format_employee_text(self, data: dict) -> str:
        """Format employee data as searchable text"""
        parts = [
            f"Employee: {data.get('name', 'Unknown')}",
            f"Employee Code: {data.get('code', 'N/A')}",
            f"Email: {data.get('email', 'N/A')}",
            f"Position: {data.get('position', 'N/A')}",
        ]
        if data.get('department'):
            parts.append(f"Department: {data['department']}")
        if data.get('phone'):
            parts.append(f"Phone: {data['phone']}")
        return " | ".join(parts)
    
    def _format_project_text(self, data: dict) -> str:
        """Format project data as searchable text"""
        parts = [
            f"Project: {data.get('name', 'Unknown')}",
            f"Client: {data.get('client', 'N/A')}",
        ]
        if data.get('target_date'):
            parts.append(f"Target Date: {data['target_date']}")
        if data.get('lead'):
            parts.append(f"Project Lead: {data['lead']}")
        return " | ".join(parts)
    
    def _format_task_text(self, data: dict) -> str:
        """Format task data as searchable text"""
        parts = [
            f"Task: {data.get('title', 'Unknown')}",
            f"Status: {data.get('status', 'N/A')}",
            f"Priority: {data.get('priority', 'N/A')}",
        ]
        if data.get('description'):
            parts.append(f"Description: {data['description']}")
        if data.get('assigned_to'):
            parts.append(f"Assigned To: {data['assigned_to']}")
        if data.get('project'):
            parts.append(f"Project: {data['project']}")
        if data.get('due_date'):
            parts.append(f"Due Date: {data['due_date']}")
        return " | ".join(parts)
    
    def _format_department_text(self, data: dict) -> str:
        """Format department data as searchable text"""
        parts = [f"Department: {data.get('name', 'Unknown')}"]
        if data.get('description'):
            parts.append(f"Description: {data['description']}")
        return " | ".join(parts)
    
    def _format_company_text(self, data: dict) -> str:
        """Format company data as searchable text"""
        parts = [
            f"Company: {data.get('name', 'Unknown')}",
            f"Company Code: {data.get('code', 'N/A')}",
            f"Type: {data.get('type', 'N/A')}",
        ]
        if data.get('email'):
            parts.append(f"Email: {data['email']}")
        if data.get('phone'):
            parts.append(f"Phone: {data['phone']}")
        return " | ".join(parts)

