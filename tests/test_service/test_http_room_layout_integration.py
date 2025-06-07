"""
Tests for HTTP service room layout integration.

This module tests the room layout integration in the HTTP API service,
ensuring that room layout context is properly included in API responses
for conversational AI integration.
"""
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch

try:
    from src.service.http_service import HTTPDetectionService, HTTPServiceConfig
    from src.ollama.description_service import DescriptionService, DescriptionResult
    from fastapi.testclient import TestClient
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    HTTPDetectionService = None
    HTTPServiceConfig = None
    DescriptionService = None
    DescriptionResult = None
    TestClient = None
    DEPENDENCIES_AVAILABLE = False


class TestHTTPRoomLayoutIntegration:
    """Test HTTP API room layout integration."""
    
    def test_description_endpoint_includes_room_layout(self):
        """Should include room layout in description endpoint response."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Mock description service with room layout
        mock_description_service = Mock(spec=DescriptionService)
        room_layout = """Living Room Layout:
FURNITURE:
- Sofa: Large gray sectional against west wall
- Coffee Table: Glass rectangular table in center
- TV: 65" mounted on east wall"""
        
        mock_result = DescriptionResult(
            description="Person sitting on sofa reading book",
            confidence=0.88,
            timestamp=datetime.now(),
            processing_time_ms=250,
            cached=False,
            room_layout=room_layout
        )
        
        mock_description_service.get_latest_description.return_value = mock_result
        mock_description_service.ollama_client.is_available.return_value = True
        
        service.setup_description_integration(mock_description_service)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should include room layout
            assert 'room_layout' in data
            assert data['room_layout'] == room_layout
            assert "Living Room Layout:" in data['room_layout']
            assert "Sofa: Large gray sectional" in data['room_layout']
            
            # Should also include other expected fields
            assert data['description'] == "Person sitting on sofa reading book"
            assert data['confidence'] == 0.88
            assert data['success'] is True
    
    def test_description_endpoint_handles_missing_room_layout(self):
        """Should handle cases where room layout is None or empty."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Mock description service with no room layout
        mock_description_service = Mock(spec=DescriptionService)
        mock_result = DescriptionResult(
            description="Person at desk",
            confidence=0.75,
            timestamp=datetime.now(),
            processing_time_ms=150,
            cached=True,
            room_layout=None  # No room layout
        )
        
        mock_description_service.get_latest_description.return_value = mock_result
        mock_description_service.ollama_client.is_available.return_value = True
        
        service.setup_description_integration(mock_description_service)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should include room_layout field, even if None
            assert 'room_layout' in data
            assert data['room_layout'] is None
    
    def test_description_endpoint_handles_empty_room_layout(self):
        """Should handle cases where room layout is empty string."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Mock description service with empty room layout
        mock_description_service = Mock(spec=DescriptionService)
        mock_result = DescriptionResult(
            description="Person typing",
            confidence=0.82,
            timestamp=datetime.now(),
            processing_time_ms=180,
            cached=False,
            room_layout=""  # Empty room layout
        )
        
        mock_description_service.get_latest_description.return_value = mock_result
        mock_description_service.ollama_client.is_available.return_value = True
        
        service.setup_description_integration(mock_description_service)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should include room_layout field as empty string
            assert 'room_layout' in data
            assert data['room_layout'] == ""
    
    def test_description_endpoint_room_layout_in_error_cases(self):
        """Should include room layout even when description has errors."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Mock description service with error but room layout
        mock_description_service = Mock(spec=DescriptionService)
        room_layout = "Office with desk and chair"
        
        mock_result = DescriptionResult(
            description="Description temporarily unavailable",
            confidence=0.0,
            timestamp=datetime.now(),
            processing_time_ms=100,
            cached=False,
            error="timeout",
            room_layout=room_layout
        )
        
        mock_description_service.get_latest_description.return_value = mock_result
        mock_description_service.ollama_client.is_available.return_value = True
        
        service.setup_description_integration(mock_description_service)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should include room layout even with error
            assert 'room_layout' in data
            assert data['room_layout'] == room_layout
            assert data['success'] is False
            assert data['error'] == "timeout"
    
    def test_description_endpoint_uses_description_result_to_dict(self):
        """Should use DescriptionResult.to_dict() method for complete data."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Mock description service
        mock_description_service = Mock(spec=DescriptionService)
        room_layout = "Kitchen with island and appliances"
        
        mock_result = DescriptionResult(
            description="Person cooking pasta",
            confidence=0.91,
            timestamp=datetime.now(),
            processing_time_ms=320,
            cached=True,
            room_layout=room_layout
        )
        
        # Mock the to_dict method to ensure it's called
        expected_dict = mock_result.to_dict()
        mock_result.to_dict = Mock(return_value=expected_dict)
        
        mock_description_service.get_latest_description.return_value = mock_result
        mock_description_service.ollama_client.is_available.return_value = True
        
        service.setup_description_integration(mock_description_service)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            
            assert response.status_code == 200
            
            # Verify that to_dict() was called
            mock_result.to_dict.assert_called_once()
            
            # Verify response contains all fields from to_dict()
            data = response.json()
            assert 'room_layout' in data
            assert 'description' in data
            assert 'confidence' in data
            assert 'success' in data
            assert 'cached' in data
            assert 'processing_time_ms' in data


class TestHTTPRoomLayoutBackwardCompatibility:
    """Test backward compatibility of room layout integration."""
    
    def test_existing_clients_still_work(self):
        """Should not break existing clients that don't expect room_layout."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Mock description service without room layout (old behavior)
        mock_description_service = Mock(spec=DescriptionService)
        
        # Simulate old DescriptionResult without room_layout field
        mock_result = Mock()
        mock_result.description = "Person at computer"
        mock_result.confidence = 0.85
        mock_result.timestamp = datetime.now()
        mock_result.processing_time_ms = 200
        mock_result.cached = False
        mock_result.error = None
        mock_result.success = True
        
        # Old to_dict might not include room_layout
        mock_result.to_dict.return_value = {
            'description': "Person at computer",
            'confidence': 0.85,
            'timestamp': mock_result.timestamp.isoformat(),
            'processing_time_ms': 200,
            'cached': False,
            'error': None,
            'success': True
            # Note: no room_layout field
        }
        
        mock_description_service.get_latest_description.return_value = mock_result
        mock_description_service.ollama_client.is_available.return_value = True
        
        service.setup_description_integration(mock_description_service)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should work even without room_layout
            assert data['description'] == "Person at computer"
            assert data['confidence'] == 0.85
            assert data['success'] is True
            
            # room_layout might be absent or None, both should be acceptable
            room_layout = data.get('room_layout')
            assert room_layout is None or isinstance(room_layout, str)
    
    def test_service_without_description_integration_still_works(self):
        """Should work normally when description service is not integrated."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Don't integrate description service
        
        with TestClient(service.app) as client:
            # Other endpoints should still work
            response = client.get("/health")
            assert response.status_code == 200
            
            response = client.get("/presence")
            assert response.status_code == 200
            
            # Description endpoint should return appropriate error
            response = client.get("/description/latest")
            assert response.status_code == 503  # Service unavailable


class TestHTTPRoomLayoutSpecialCases:
    """Test special cases and edge conditions for room layout integration."""
    
    def test_large_room_layout_handled_properly(self):
        """Should handle large room layout descriptions without issues."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Create large room layout description
        large_room_layout = """Comprehensive Living Room Layout:
FURNITURE:
- Sectional Sofa: Large gray L-shaped sectional sofa against west and south walls, seats 6-7 people comfortably
- Coffee Table: Large glass rectangular coffee table (48" x 24") in center of seating area with chrome legs
- TV Stand: Black wooden entertainment center (72" wide) against east wall with multiple shelves
- Side Tables: Two matching wooden end tables beside sectional arms with lamps
- Bookshelf: Tall 6-shelf wooden bookcase against north wall filled with books and decorations
- Ottoman: Round fabric ottoman in brown/tan color for additional seating

ELECTRONICS:
- TV: 65" 4K Smart TV mounted on east wall at comfortable viewing height
- Sound System: Surround sound speakers positioned around room
- Gaming Console: PlayStation 5 on TV stand with wireless controllers
- Streaming Device: Apple TV connected to main television

LIGHTING:
- Ceiling Fan: White ceiling fan with LED lights in center of room
- Floor Lamps: Two tall floor lamps with fabric shades beside sectional
- Table Lamps: Matching table lamps on end tables with warm white bulbs
- String Lights: Decorative LED string lights around windows

COLOR REFERENCE FOR IDENTIFICATION:
- Sofa: Gray fabric upholstery with dark gray accent pillows
- Coffee table: Clear tempered glass surface with shiny chrome metal legs
- TV stand: Dark brown/black wood finish with visible wood grain
- End tables: Natural wood finish matching the bookshelf
- Walls: Light cream/beige paint color throughout
- Carpet: Medium brown area rug covering most of floor space
- Curtains: White semi-sheer curtains on windows allowing natural light"""
        
        mock_description_service = Mock(spec=DescriptionService)
        mock_result = DescriptionResult(
            description="Person relaxing on sectional watching TV",
            confidence=0.89,
            timestamp=datetime.now(),
            processing_time_ms=280,
            cached=False,
            room_layout=large_room_layout
        )
        
        mock_description_service.get_latest_description.return_value = mock_result
        mock_description_service.ollama_client.is_available.return_value = True
        
        service.setup_description_integration(mock_description_service)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should handle large room layout properly
            assert 'room_layout' in data
            assert data['room_layout'] == large_room_layout
            assert len(data['room_layout']) > 1000  # Verify it's actually large
            assert "Comprehensive Living Room Layout:" in data['room_layout']
    
    def test_room_layout_with_special_characters(self):
        """Should handle room layout with special characters and unicode."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Room layout with special characters and unicode
        special_room_layout = """Modern Café Layout:
FURNITURE:
- Tables: 5 small round tables (30" diameter) with café-style metal bases
- Chairs: Vintage wooden chairs with curved backs & cushioned seats
- Counter: Long marble-topped counter (8' × 2') for ordering & pickup
- Display Case: Glass display case with pastries, croissants & sandwiches

DÉCOR & AMBIANCE:
- Artwork: Framed prints of Parisian café scenes (très authentique!)
- Plants: Potted succulents & hanging ivy throughout space
- Lighting: Edison bulb fixtures & warm LED strips (≈2700K color temp)
- Mirrors: Antique mirrors on walls to create sense of larger space

COLOR PALETTE:
- Walls: Warm cream/café au lait color (#F5F5DC)
- Counter: White marble with gray veining
- Chairs: Dark walnut wood finish
- Accents: Copper & brass metallic elements"""
        
        mock_description_service = Mock(spec=DescriptionService)
        mock_result = DescriptionResult(
            description="Customer reading book at corner table",
            confidence=0.77,
            timestamp=datetime.now(),
            processing_time_ms=190,
            cached=True,
            room_layout=special_room_layout
        )
        
        mock_description_service.get_latest_description.return_value = mock_result
        mock_description_service.ollama_client.is_available.return_value = True
        
        service.setup_description_integration(mock_description_service)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should handle special characters properly
            assert 'room_layout' in data
            assert data['room_layout'] == special_room_layout
            assert "très authentique!" in data['room_layout']
            assert "≈2700K" in data['room_layout']
            assert "#F5F5DC" in data['room_layout']
    
    def test_json_serialization_of_room_layout(self):
        """Should properly serialize room layout in JSON responses."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        room_layout = """Test Room:
- Item with "quotes" and 'apostrophes'
- Line with \backslashes\ and /forward/slashes/
- Unicode: café, naïve, résumé"""
        
        mock_description_service = Mock(spec=DescriptionService)
        mock_result = DescriptionResult(
            description="Test description",
            confidence=0.8,
            timestamp=datetime.now(),
            processing_time_ms=150,
            cached=False,
            room_layout=room_layout
        )
        
        mock_description_service.get_latest_description.return_value = mock_result
        mock_description_service.ollama_client.is_available.return_value = True
        
        service.setup_description_integration(mock_description_service)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            
            assert response.status_code == 200
            
            # Verify JSON can be parsed properly
            data = response.json()
            assert 'room_layout' in data
            
            # Verify content is preserved correctly
            assert '"quotes"' in data['room_layout']
            assert "'apostrophes'" in data['room_layout']
            assert "café" in data['room_layout']
            assert "naïve" in data['room_layout']
            
            # Verify it's valid JSON by re-serializing
            json_str = json.dumps(data)
            reparsed = json.loads(json_str)
            assert reparsed['room_layout'] == room_layout 