import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
import json

logger = logging.getLogger("app_observability")
logging.basicConfig(level=logging.INFO)

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Request Logging (simplified)
        method = request.method
        url = request.url.path
        
        response: Response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests or errors
        if process_time > 1.0 or response.status_code >= 400:
            logger.warning(
                f"Request {method} {url} completed in {process_time:.4f}s with status {response.status_code}"
            )
        else:
            logger.info(f"{method} {url} - {response.status_code}")
            
        return response

def setup_exception_handlers(app):
    from fastapi.responses import JSONResponse
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global Exception on {request.url.path}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Our team has been notified."},
        )
