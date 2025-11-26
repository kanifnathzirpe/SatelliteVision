# backend/main.py
import os, uuid, logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from liss_change_detector import LISSChangeDetector

# Configure and initialize app
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BackendAPI")
app = FastAPI(title="ISRO Change Detection API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Serve static files
os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Load ML model
try:
    detector = LISSChangeDetector(model_dir="./models")
except Exception as e:
    detector = None
    logger.error(f"FATAL: Could not initialize LISSChangeDetector: {e}")

# Pydantic model for request
class AOIBounds(BaseModel):
    west: float; south: float; east: float; north: float

# Helper to save image previews
def save_preview(arr: np.ndarray, job_id: str, suffix: str) -> str:
    path = os.path.join("outputs", job_id, f"{suffix}_preview.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Ensure we have at least 3 bands for RGB
    if arr.ndim < 3 or arr.shape[0] < 3:
        raise ValueError("Array for preview must have at least 3 bands.")
        
    rgb = np.dstack([arr[0], arr[1], arr[2]]).astype(np.float32)
    
    # Robust normalization
    p2, p98 = np.percentile(rgb[np.isfinite(rgb)], (2, 98))
    rgb = np.clip(rgb, p2, p98)
    if p98 > p2:
        rgb = (rgb - p2) / (p98 - p2)
    
    plt.imsave(path, rgb)
    logger.info(f"Saved preview image to {path}")
    return path

# API Endpoint
@app.post("/api/analyze-aoi")
async def analyze_aoi(aoi: AOIBounds, request: Request):
    if not detector:
        raise HTTPException(status_code=500, detail="Change detector model is not initialized.")

    before_tif = os.path.join("test_data", "real_before.tif")
    after_tif = os.path.join("test_data", "real_after.tif")
    
    if not os.path.exists(before_tif) or not os.path.exists(after_tif):
        raise HTTPException(status_code=500, detail="Real test data not found. Please run 'download_real_data.py'.")

    job_id = str(uuid.uuid4())[:8]
    logger.info(f"Starting analysis for job {job_id}. NOTE: Processing entire tile regardless of AOI.")

    try:
        # DEFINITIVE FIX: We will NOT use the user's AOI for clipping.
        # We read the ENTIRE file by passing `aoi_geom=None`. This avoids all clipping errors.
        arr_b, _, _ = detector._read_and_clip(before_tif, aoi_geom=None)
        arr_a, _, _ = detector._read_and_clip(after_tif, aoi_geom=None)

        # Create previews of the full images
        before_path = save_preview(arr_b, job_id, "before")
        after_path = save_preview(arr_a, job_id, "after")

        # Run analysis on the full images
        result = detector.run_on_pair(before_tif, after_tif, aoi_geom=None, job_id=job_id)
        
        # Format and return the successful response
        base_url = str(request.base_url).rstrip('/')
        def to_url(path):
            return f"{base_url}/{path.replace(os.sep, '/')}" if path else None

        response = {
            "summary": result["summary"],
            "overlays": {k: to_url(v) for k, v in result["overlays"].items()},
            "beforeImage": to_url(before_path),
            "afterImage": to_url(after_path),
        }
        logger.info(f"Analysis successful for job {job_id}.")
        return response
        
    except Exception as e:
        logger.error(f"Analysis for job {job_id} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during analysis: {e}")