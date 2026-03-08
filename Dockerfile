# =============================================
# HEAS — N8N Self-Annealing System
# Multi-stage Docker build: Next.js static + FastAPI
# =============================================

# --- Stage 1: Build Next.js static export ---
FROM node:20-alpine AS frontend-build

WORKDIR /app/dashboard_next

# Install dependencies
COPY dashboard_next/package.json dashboard_next/package-lock.json ./
RUN npm ci --ignore-scripts

# Copy source and build
COPY dashboard_next/ ./
RUN npm run build

# --- Stage 2: Python FastAPI server ---
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python source
COPY execution/ ./execution/

# Copy the Next.js static export from Stage 1
COPY --from=frontend-build /app/dashboard_next/out ./static_dashboard

# Expose port (Render assigns PORT env var)
EXPOSE 8000

# Start FastAPI with uvicorn
CMD python -m uvicorn execution.api:app --host 0.0.0.0 --port ${PORT:-8000}
