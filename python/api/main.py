"""
FastAPI Main Application

Entry point for the accounting dashboard API.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import (
    dashboard_router,
    budget_router,
    transactions_router,
    approvals_router,
    fund_requests_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("Starting Accounting Dashboard API...")
    yield
    # Shutdown
    print("Shutting down Accounting Dashboard API...")


app = FastAPI(
    title="Accounting Dashboard API",
    description="API for BK Keyforce / BETRNK Group Accounting Automation System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dashboard_router, prefix="/api")
app.include_router(budget_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(approvals_router, prefix="/api")
app.include_router(fund_requests_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Accounting Dashboard API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "endpoints": {
            "dashboard": "/api/dashboard/summary",
            "budget": "/api/budget/{entity}/{period}",
            "transactions": "/api/transactions",
            "approvals": "/api/approvals/pending",
            "fund_requests": "/api/fund-requests",
        },
        "authentication": "X-Telegram-ID header required in production",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "python.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENVIRONMENT", "development") == "development",
    )
