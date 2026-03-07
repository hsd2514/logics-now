"""Embedding service for document semantic similarity using Gemini API"""

from typing import Dict, List, Optional
from google import genai
from app.config import get_settings
import numpy as np
from app.pipeline.embedding_service import EmbeddingService as LocalEmbeddingService


class EmbeddingService:
    """Generate and compare document embeddings using Gemini's embedding API"""

    EMBEDDING_MODEL = get_settings().gemini_embedding_model or "models/text-embedding-004"
    
    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.google_api_key) if settings.google_api_key else None
        self._local = LocalEmbeddingService()
    
    def generate_document_embedding(self, entities: Dict) -> Optional[List[float]]:
        """
        Generate embedding from document entities.
        Combines key fields into a semantic representation.
        
        Args:
            entities: Dictionary of extracted entities (shipment_id, amount, party_name, etc.)
        
        Returns:
            List of floats (768-dimensional vector) or None if API unavailable
        """
        if not self.client:
            return None
        
        # Construct semantic text from entities
        text_parts = []
        
        # Prioritize key matching fields
        if entities.get('shipment_id'):
            text_parts.append(f"Shipment ID: {entities['shipment_id']}")
        if entities.get('party_name'):
            text_parts.append(f"Party: {entities['party_name']}")
        if entities.get('amount'):
            text_parts.append(f"Amount: {entities['amount']}")
        if entities.get('origin'):
            text_parts.append(f"From: {entities['origin']}")
        if entities.get('destination'):
            text_parts.append(f"To: {entities['destination']}")
        if entities.get('date'):
            text_parts.append(f"Date: {entities['date']}")
        if entities.get('vehicle_number'):
            text_parts.append(f"Vehicle: {entities['vehicle_number']}")
        
        if not text_parts:
            return None
        
        document_text = " | ".join(text_parts)
        
        try:
            response = self.client.models.embed_content(
                model=self.EMBEDDING_MODEL,
                contents=document_text
            )
            
            # Extract embedding from response
            if response and hasattr(response, 'embeddings') and response.embeddings:
                embedding = response.embeddings[0].values
                return list(embedding)
            
            return None
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    @staticmethod
    def cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
        
        Returns:
            Similarity score between 0 and 1
        """
        if not embedding1 or not embedding2:
            return 0.0
        
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Cosine similarity formula
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Clamp to [0, 1] range
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            print(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def compare_document_embeddings(
        self,
        lr_embedding: Optional[List[float]],
        pod_embedding: Optional[List[float]],
        invoice_embedding: Optional[List[float]]
    ) -> float:
        """
        Compare embeddings across three documents in a triplet.
        
        Args:
            lr_embedding: LR document embedding
            pod_embedding: POD document embedding
            invoice_embedding: Invoice document embedding
        
        Returns:
            Average similarity score between all valid pairs
        """
        embeddings = {
            'lr': lr_embedding,
            'pod': pod_embedding,
            'invoice': invoice_embedding
        }
        
        # Filter out None embeddings
        valid_embeddings = [emb for emb in embeddings.values() if emb is not None]
        
        if len(valid_embeddings) < 2:
            return 0.5  # Neutral score if insufficient embeddings
        
        # Calculate pairwise similarities
        similarities = []
        
        if lr_embedding and pod_embedding:
            similarities.append(self.cosine_similarity(lr_embedding, pod_embedding))
        
        if lr_embedding and invoice_embedding:
            similarities.append(self.cosine_similarity(lr_embedding, invoice_embedding))
        
        if pod_embedding and invoice_embedding:
            similarities.append(self.cosine_similarity(pod_embedding, invoice_embedding))
        
        if not similarities:
            return 0.5
        
        # Return average similarity
        return sum(similarities) / len(similarities)

    def embed_document(self, text: str, entities: Dict) -> List[float]:
        """
        Backward/forward-compatible embedding API used by newer pipeline code.
        Falls back to deterministic local embedding when remote API is unavailable.
        """
        remote = self.generate_document_embedding(entities or {})
        if remote:
            return remote
        return self._local.embed_document(text or "", entities or {})
