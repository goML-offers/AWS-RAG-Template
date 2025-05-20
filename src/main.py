# THE MAIN UVICORN BASED APPLICATION DRIVING FILE.
# CAN BE CHANGED AS PER THE APPLICATION NEEDS.

import logging

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.generate import router as generate_router

# Import application modules
from src.services.schema import ServiceException

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Initialize FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific allowed origins in production
    allow_methods=["*"],  # Replace with specific HTTP methods
    allow_headers=["*"],  # Replace with specific headers
)

# Include router
app.include_router(generate_router, prefix="", tags=["generate"])


# Global exception handler
@app.exception_handler(ServiceException)
async def service_exception_handler(request, exc: ServiceException):
    return {"status": "error", "message": exc.message}, exc.status_code


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
