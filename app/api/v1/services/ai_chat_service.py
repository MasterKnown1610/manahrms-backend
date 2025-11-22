"""
AI Chat Service for HRMS
Uses OpenAI API with RAG (Retrieval-Augmented Generation) and pgvector
to answer questions about company data efficiently using minimal tokens.
Only retrieves relevant data chunks based on semantic similarity.
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam
from openai import OpenAI
import json

from app.core.config import settings
from app.api.v1.models.company_model import Company
from app.api.v1.services.embedding_service import EmbeddingService
from app.api.v1.utils.error_handler import raise_http_exception
from fastapi import status


class AIChatService:
    """Service for AI-powered chat using semantic search with pgvector"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured. Please set OPENAI_API_KEY in environment variables or .env file.")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.embedding_service = EmbeddingService()
        self.top_k = 10  # Number of relevant chunks to retrieve
    
    def _get_company_info(self, db: Session, company_id: int) -> Dict:
        """Get basic company information"""
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return {}
        
        return {
            "name": company.company_name,
            "code": company.company_code,
            "type": company.company_type,
        }
    
    def _search_relevant_chunks(
        self,
        db: Session,
        company_id: int,
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[Dict]:
        """
        Search for relevant chunks using pgvector similarity search.
        Uses cosine distance to find most similar content.
        
        Args:
            db: Database session
            company_id: Company ID to filter results
            query_embedding: Embedding vector of the user's question
            top_k: Number of top results to return
            
        Returns:
            List of relevant chunks with metadata
        """
        # Convert embedding list to PostgreSQL array format for vector type
        # pgvector expects a string representation: '[0.1,0.2,0.3,...]'
        # This is safe because query_embedding comes from OpenAI API, not user input
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        # Use pgvector's cosine distance operator (<->) for similarity search
        # Lower distance = higher similarity
        # We need to embed the vector string directly in SQL since CAST with parameters
        # doesn't work well with psycopg2 parameter binding
        # The embedding_str is safe - it's generated from OpenAI API response (list of floats)
        query = text(f"""
            SELECT 
                content_type,
                content_id,
                content_text,
                content_metadata,
                1 - (embedding <=> '{embedding_str}'::vector) AS similarity
            FROM vector_store
            WHERE company_id = :company_id
            ORDER BY embedding <=> '{embedding_str}'::vector
            LIMIT :top_k
        """)
        
        result = db.execute(
            query,
            {
                "company_id": company_id,
                "top_k": top_k
            }
        )
        
        chunks = []
        for row in result:
            chunks.append({
                "content_type": row.content_type,
                "content_id": row.content_id,
                "content_text": row.content_text,
                "metadata": json.loads(row.content_metadata) if row.content_metadata else {},
                "similarity": float(row.similarity)
            })
        
        return chunks
    
    def _build_context_from_chunks(self, chunks: List[Dict], company_info: Dict) -> Dict:
        """
        Build a concise context dictionary from retrieved chunks.
        Groups chunks by content type for better organization.
        """
        context = {
            "company": company_info,
            "relevant_data": {}
        }
        
        # Group chunks by content type
        for chunk in chunks:
            content_type = chunk["content_type"]
            if content_type not in context["relevant_data"]:
                context["relevant_data"][content_type] = []
            
            # Include metadata for richer context
            item = {
                "content": chunk["content_text"],
                "metadata": chunk["metadata"],
                "similarity": round(chunk["similarity"], 3)
            }
            context["relevant_data"][content_type].append(item)
        
        return context
    
    def _create_system_prompt(self, context: Dict) -> str:
        """Create a system prompt with only relevant context"""
        # Format context more efficiently
        context_parts = []
        
        if context.get("company"):
            context_parts.append(f"Company: {context['company'].get('name', 'N/A')} ({context['company'].get('code', 'N/A')})")
        
        relevant_data = context.get("relevant_data", {})
        
        if relevant_data.get("employee"):
            context_parts.append(f"\nRelevant Employees ({len(relevant_data['employee'])}):")
            for emp in relevant_data["employee"][:5]:  # Limit to top 5
                context_parts.append(f"  - {emp['content']}")
        
        if relevant_data.get("project"):
            context_parts.append(f"\nRelevant Projects ({len(relevant_data['project'])}):")
            for proj in relevant_data["project"][:5]:
                context_parts.append(f"  - {proj['content']}")
        
        if relevant_data.get("task"):
            context_parts.append(f"\nRelevant Tasks ({len(relevant_data['task'])}):")
            for task in relevant_data["task"][:5]:
                context_parts.append(f"  - {task['content']}")
        
        if relevant_data.get("department"):
            context_parts.append(f"\nRelevant Departments ({len(relevant_data['department'])}):")
            for dept in relevant_data["department"][:3]:
                context_parts.append(f"  - {dept['content']}")
        
        context_str = "\n".join(context_parts)
        
        return f"""You are an AI assistant for an HRMS (Human Resource Management System).

Relevant Company Context (retrieved via semantic search):
{context_str}

Instructions:
1. Answer questions based ONLY on the provided relevant context
2. Be concise and accurate - use minimal tokens
3. If information is not available in the context, say so clearly
4. Focus on the specific data provided rather than making assumptions
5. Always be helpful and professional
6. If asked about data not in context, suggest checking the HRMS system directly

Remember: Keep responses brief and token-efficient while being helpful."""
    
    def chat(
        self,
        db: Session,
        company_id: int,
        user_question: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Process a chat question and return AI response using semantic search.
        Only retrieves relevant data chunks, dramatically reducing token usage.
        
        Args:
            db: Database session
            company_id: Company ID to filter data
            user_question: User's question in natural language
            conversation_history: Optional list of previous messages [{"role": "user/assistant", "content": "..."}]
        
        Returns:
            AI response string
        """
        if not settings.OPENAI_API_KEY:
            raise_http_exception(
                message="OpenAI API key is not configured",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code="OPENAI_NOT_CONFIGURED"
            )
        
        try:
            # Get basic company info
            company_info = self._get_company_info(db, company_id)
            
            # Generate embedding for user's question
            query_embedding = self.embedding_service.generate_embedding(user_question)
            
            # Search for relevant chunks using semantic similarity
            relevant_chunks = self._search_relevant_chunks(
                db=db,
                company_id=company_id,
                query_embedding=query_embedding,
                top_k=self.top_k
            )
            
            # If no relevant chunks found, provide basic company info only
            if not relevant_chunks:
                context = {
                    "company": company_info,
                    "relevant_data": {}
                }
            else:
                # Build context from retrieved chunks
                context = self._build_context_from_chunks(relevant_chunks, company_info)
            
            # Create system prompt with only relevant context
            system_prompt = self._create_system_prompt(context)
            
            # Build messages
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation history if provided (limit to last 3 exchanges to save tokens)
            if conversation_history:
                # Keep only recent history to minimize tokens
                recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
                messages.extend(recent_history)
            
            # Add current question
            messages.append({"role": "user", "content": user_question})
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500,  # Limit response length for token efficiency
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            raise_http_exception(
                message=f"Error processing AI chat request: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="AI_CHAT_ERROR"
            )
