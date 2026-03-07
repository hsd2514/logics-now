"""Test embedding generation and contrastive learning implementation"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from app.services.embedding_service import EmbeddingService
from app.services.document_service import DocumentService
from app.pipeline.triplet_matcher import TripletMatcher


class TestEmbeddingService:
    """Test the EmbeddingService class"""
    
    def test_cosine_similarity_identical_vectors(self):
        """Test cosine similarity with identical vectors returns 1.0"""
        service = EmbeddingService()
        vec1 = [1.0, 2.0, 3.0, 4.0]
        vec2 = [1.0, 2.0, 3.0, 4.0]
        
        similarity = service.cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0, abs=0.01)
    
    def test_cosine_similarity_orthogonal_vectors(self):
        """Test cosine similarity with orthogonal vectors returns 0.0"""
        service = EmbeddingService()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        
        similarity = service.cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0, abs=0.01)
    
    def test_cosine_similarity_opposite_vectors(self):
        """Test cosine similarity with opposite vectors returns close to 0.0 (clamped)"""
        service = EmbeddingService()
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [-1.0, -2.0, -3.0]
        
        similarity = service.cosine_similarity(vec1, vec2)
        # Cosine similarity of opposite vectors is -1, but we clamp to [0, 1]
        assert similarity == pytest.approx(0.0, abs=0.01)
    
    def test_cosine_similarity_none_vectors(self):
        """Test cosine similarity handles None gracefully"""
        service = EmbeddingService()
        
        assert service.cosine_similarity(None, [1.0, 2.0]) == 0.0
        assert service.cosine_similarity([1.0, 2.0], None) == 0.0
        assert service.cosine_similarity(None, None) == 0.0
    
    def test_cosine_similarity_empty_vectors(self):
        """Test cosine similarity handles empty vectors"""
        service = EmbeddingService()
        
        assert service.cosine_similarity([], [1.0, 2.0]) == 0.0
        assert service.cosine_similarity([1.0, 2.0], []) == 0.0
    
    def test_generate_document_embedding_no_client(self):
        """Test embedding generation without API key returns None"""
        with patch('app.services.embedding_service.get_settings') as mock_settings:
            mock_settings.return_value.google_api_key = ""
            service = EmbeddingService()
            
            entities = {
                'shipment_id': 'SHIP001',
                'party_name': 'ABC Logistics',
                'amount': '50000'
            }
            
            result = service.generate_document_embedding(entities)
            assert result is None
    
    def test_generate_document_embedding_with_entities(self):
        """Test embedding generation constructs proper text from entities"""
        mock_client = Mock()
        mock_response = Mock()
        mock_embedding = Mock()
        mock_embedding.values = [0.1] * 768  # Simulate 768-dim embedding
        mock_response.embeddings = [mock_embedding]
        mock_client.models.embed_content.return_value = mock_response
        
        with patch('app.services.embedding_service.genai.Client', return_value=mock_client):
            with patch('app.services.embedding_service.get_settings') as mock_settings:
                mock_settings.return_value.google_api_key = "test-key"
                service = EmbeddingService()
                
                entities = {
                    'shipment_id': 'SHIP001',
                    'party_name': 'ABC Logistics',
                    'amount': '50000',
                    'origin': 'Mumbai',
                    'destination': 'Delhi'
                }
                
                result = service.generate_document_embedding(entities)
                
                # Verify embedding was generated
                assert result is not None
                assert len(result) == 768
                assert all(isinstance(x, float) for x in result)
                
                # Verify API was called with properly formatted text
                mock_client.models.embed_content.assert_called_once()
                call_args = mock_client.models.embed_content.call_args
                assert 'SHIP001' in call_args.kwargs['contents']
                assert 'ABC Logistics' in call_args.kwargs['contents']
    
    def test_compare_document_embeddings_all_present(self):
        """Test comparing three valid embeddings"""
        service = EmbeddingService()
        
        # Create similar embeddings
        lr_emb = [1.0, 0.5, 0.2] * 256  # 768-dim
        pod_emb = [0.9, 0.5, 0.2] * 256
        inv_emb = [1.0, 0.4, 0.2] * 256
        
        similarity = service.compare_document_embeddings(lr_emb, pod_emb, inv_emb)
        
        # Should be high similarity
        assert similarity > 0.9
        assert similarity <= 1.0
    
    def test_compare_document_embeddings_with_none(self):
        """Test comparing embeddings when some are None"""
        service = EmbeddingService()
        
        lr_emb = [1.0, 0.5, 0.2] * 256
        pod_emb = [0.9, 0.5, 0.2] * 256
        
        # Should handle None gracefully
        similarity = service.compare_document_embeddings(lr_emb, pod_emb, None)
        assert 0.0 <= similarity <= 1.0
        
    def test_compare_document_embeddings_insufficient_data(self):
        """Test comparing with less than 2 embeddings returns neutral score"""
        service = EmbeddingService()
        
        similarity = service.compare_document_embeddings([1.0], None, None)
        assert similarity == 0.5  # Neutral score


class TestDocumentServiceEmbedding:
    """Test embedding generation in DocumentService"""
    
    def test_document_service_has_embedding_service(self):
        """Verify DocumentService initializes EmbeddingService"""
        service = DocumentService()
        assert hasattr(service, 'embedding_service')
        assert isinstance(service.embedding_service, EmbeddingService)


class TestTripletMatcherEmbedding:
    """Test embedding usage in TripletMatcher"""
    
    def test_triplet_matcher_has_embedding_service(self):
        """Verify TripletMatcher initializes EmbeddingService"""
        matcher = TripletMatcher()
        assert hasattr(matcher, 'embedding_service')
        assert isinstance(matcher.embedding_service, EmbeddingService)
    
    def test_triplet_matcher_has_embedding_weight(self):
        """Verify TripletMatcher defines embedding weight"""
        matcher = TripletMatcher()
        assert hasattr(matcher, 'embedding_weight')
        assert matcher.embedding_weight > 0
        assert matcher.embedding_weight <= 1.0
    
    def test_match_triplet_accepts_embeddings(self):
        """Test match_triplet accepts embedding parameters"""
        matcher = TripletMatcher()
        
        lr_entities = {'shipment_id': 'SHIP001', 'amount': '50000'}
        pod_entities = {'shipment_id': 'SHIP001', 'amount': '50000'}
        inv_entities = {'shipment_id': 'SHIP001', 'amount': '50000'}
        
        # Create dummy embeddings
        embedding = [0.5] * 768
        
        # Should not raise error with embeddings
        try:
            score, conf, fields, attention = matcher.match_triplet(
                lr_entities, pod_entities, inv_entities,
                lr_embedding=embedding,
                pod_embedding=embedding,
                invoice_embedding=embedding
            )
            assert True  # Successfully accepted embeddings
        except TypeError:
            pytest.fail("match_triplet should accept embedding parameters")
    
    def test_match_triplet_uses_embeddings_in_scoring(self):
        """Test that embeddings affect the match score"""
        matcher = TripletMatcher()
        
        lr_entities = {'shipment_id': 'SHIP001'}
        pod_entities = {'shipment_id': 'SHIP001'}
        inv_entities = {'shipment_id': 'SHIP001'}
        
        # Score without embeddings
        score1, conf1, _, _ = matcher.match_triplet(
            lr_entities, pod_entities, inv_entities
        )
        
        # Score with identical embeddings (should increase score)
        identical_embedding = [1.0] * 768
        score2, conf2, _, _ = matcher.match_triplet(
            lr_entities, pod_entities, inv_entities,
            lr_embedding=identical_embedding,
            pod_embedding=identical_embedding,
            invoice_embedding=identical_embedding
        )
        
        # With perfect embedding similarity, score should be higher or equal
        assert score2 >= score1
    
    def test_match_triplet_field_matches_includes_embedding_similarity(self):
        """Test that field_matches includes embedding similarity info"""
        matcher = TripletMatcher()
        
        lr_entities = {'shipment_id': 'SHIP001'}
        pod_entities = {'shipment_id': 'SHIP001'}
        inv_entities = {'shipment_id': 'SHIP001'}
        
        embedding = [0.5] * 768
        
        score, conf, field_matches, _ = matcher.match_triplet(
            lr_entities, pod_entities, inv_entities,
            lr_embedding=embedding,
            pod_embedding=embedding,
            invoice_embedding=embedding
        )
        
        # Should have embedding similarity in field_matches
        assert '_embedding_similarity' in field_matches
        assert 'score' in field_matches['_embedding_similarity']
        assert field_matches['_embedding_similarity']['score'] >= 0.0
        assert field_matches['_embedding_similarity']['score'] <= 1.0


class TestIntegration:
    """Integration tests for the full embedding pipeline"""
    
    def test_embedding_column_populated_check(self):
        """Verify the Document model still has the embedding column"""
        from app.models.document import Document
        
        # Check that the model has the embedding attribute
        assert hasattr(Document, 'embedding')
    
    def test_weights_sum_to_one(self):
        """Verify field weights + embedding weight = 1.0"""
        matcher = TripletMatcher()
        
        total_field_weight = sum(matcher.field_weights.values())
        total_weight = total_field_weight + matcher.embedding_weight
        
        # Should sum to approximately 1.0
        assert total_weight == pytest.approx(1.0, abs=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
