#!/usr/bin/env python3
"""
Simple HTTP Server for Speaker Verification Integration

This script starts just the HTTP API service on port 8767.
Your speaker verification app can connect to:
- http://localhost:8767/presence/simple (for guard clauses)
- http://localhost:8767/presence (for full status)
- http://localhost:8767/health (for health checks)
"""
import asyncio
import signal
import sys
from src.service.http_service import HTTPDetectionService, HTTPServiceConfig

async def run_server():
    """Run the HTTP service."""
    print("🌐 Starting HTTP API Server for Speaker Verification...")
    print("=" * 50)
    
    # Configure HTTP service
    config = HTTPServiceConfig(
        host="localhost",
        port=8767,
        enable_history=True,
        history_limit=100
    )
    
    # Create service
    service = HTTPDetectionService(config)
    
    print(f"🚀 HTTP API available at: http://localhost:8767")
    print("📋 Key endpoints for your app:")
    print("   • http://localhost:8767/presence/simple  ← Guard clause (boolean)")
    print("   • http://localhost:8767/presence         ← Full status")
    print("   • http://localhost:8767/health           ← Health check")
    print("   • http://localhost:8767/statistics       ← Performance stats")
    print("")
    print("🔌 Your speaker verification app can now connect!")
    print("Press Ctrl+C to stop the server")
    print("")
    
    # Start server
    try:
        import uvicorn
        config = uvicorn.Config(
            service.app,
            host="localhost",
            port=8767,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")
        return 1
    
    return 0

def main():
    """Main entry point."""
    try:
        return asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
 
 