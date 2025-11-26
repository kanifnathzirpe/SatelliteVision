# backend/liss_change_detector.py
import os, json, datetime, uuid, logging
from typing import Optional, Tuple, Dict, Any
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.transform import xy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import joblib
import random
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor, MultiOutputClassifier
import cv2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LISSChangeDetector")
RND = 42
np.random.seed(RND)
random.seed(RND)

class LISSChangeDetector:
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self.reg_pipeline = None
        self.cls_pipeline = None
        self.feature_names = ["dR", "dG", "dB", "dNDVI", "dNDWI", "dNBR"]
        self._load_or_train_models()

    def _load_or_train_models(self):
        reg_path = os.path.join(self.model_dir, "reg_pipeline.joblib")
        cls_path = os.path.join(self.model_dir, "cls_pipeline.joblib")
        try:
            self.reg_pipeline, self.cls_pipeline = joblib.load(reg_path), joblib.load(cls_path)
            logger.info("Loaded pipelines from disk.")
        except Exception:
            logger.info("Pipelines not found — training new synthetic models.")
            self.reg_pipeline, self.cls_pipeline = self._train_synthetic_models()
            joblib.dump(self.reg_pipeline, reg_path)
            joblib.dump(self.cls_pipeline, cls_path)
            logger.info(f"Saved synthetic models to {self.model_dir}")

    def _train_synthetic_models(self):
        N = 2000
        X = np.random.randn(N, len(self.feature_names)) * 0.05
        # Add no-change samples
        X_no_change = np.random.randn(N, len(self.feature_names)) * 0.01
        X = np.vstack([X, X_no_change])
        
        y_cls = np.zeros((X.shape[0], 4), dtype=int)
        y_cls[:N, 0] = (X[:N, 3] < -0.15).astype(int)  # Deforestation
        y_cls[:N, 1] = (X[:N, 4] > 0.2).astype(int)   # Water
        y_cls[:N, 2] = (np.abs(X[:N, 0:3]).mean(axis=1) > 0.08).astype(int)  # Urban
        y_cls[:N, 3] = (X[:N, 3] > 0.15).astype(int)   # Agriculture
        
        y_reg = np.zeros((X.shape[0], 2))
        changed_mask = np.any(y_cls == 1, axis=1)
        y_reg[changed_mask, 0] = np.random.uniform(500, 2000, np.sum(changed_mask))
        y_reg[changed_mask, 1] = np.random.uniform(70, 95, np.sum(changed_mask))
        
        reg_pipeline = Pipeline([("scaler", StandardScaler()), ("reg", MultiOutputRegressor(RandomForestRegressor(n_estimators=100, random_state=RND)))])
        cls_pipeline = Pipeline([("scaler", StandardScaler()), ("clf", MultiOutputClassifier(RandomForestClassifier(n_estimators=100, random_state=RND)))])
        
        reg_pipeline.fit(X, y_reg)
        cls_pipeline.fit(X, y_cls)
        
        return reg_pipeline, cls_pipeline

    def _read_and_clip(self, path, aoi_geom=None):
        with rasterio.open(path) as src:
            if aoi_geom:
                try:
                    out_image, out_transform = mask(src, [aoi_geom], crop=True)
                    return out_image.astype(np.float32), out_transform, src.crs
                except ValueError:
                    return np.array([]), None, None
            return src.read().astype(np.float32), src.transform, src.crs

    def _normalize_band(self, band):
        min_val, max_val = np.nanmin(band), np.nanmax(band)
        if max_val - min_val > 1e-8:
            return (band - min_val) / (max_val - min_val)
        return np.zeros_like(band)

    def _calc_index(self, band1, band2):
        return np.clip((band1 - band2) / (band1 + band2 + 1e-8), -1, 1)

    def _build_pixel_features(self, arr_b, arr_a):
        B, H, W = arr_b.shape
        feats = np.zeros((H * W, len(self.feature_names)), dtype=np.float32)
        
        bands_b = [self._normalize_band(arr_b[i]) for i in range(B)]
        bands_a = [self._normalize_band(arr_a[i]) for i in range(B)]
        
        feats[:, 0] = (bands_a[0] - bands_b[0]).flatten() # dR
        feats[:, 1] = (bands_a[1] - bands_b[1]).flatten() # dG
        feats[:, 2] = (bands_a[2] - bands_b[2]).flatten() # dB
        
        ndvi_b = self._calc_index(bands_b[3], bands_b[0])
        ndvi_a = self._calc_index(bands_a[3], bands_a[0])
        feats[:, 3] = (ndvi_a - ndvi_b).flatten() # dNDVI
        
        ndwi_b = self._calc_index(bands_b[1], bands_b[3])
        ndwi_a = self._calc_index(bands_a[1], bands_a[3])
        feats[:, 4] = (ndwi_a - ndwi_b).flatten() # dNDWI
        
        feats[:, 5] = (self._calc_index(bands_b[3], bands_b[2]) - self._calc_index(bands_a[3], bands_a[2])).flatten() # dNBR
        
        return np.nan_to_num(feats), H, W

    def _save_png(self, arr, out_path, cmap, vmin=None, vmax=None):
        plt.figure(figsize=(arr.shape[1]/100, arr.shape[0]/100), dpi=100)
        plt.axis('off')
        plt.imshow(arr, cmap=cmap, vmin=vmin, vmax=vmax)
        plt.tight_layout(pad=0)
        plt.savefig(out_path, bbox_inches='tight', pad_inches=0, transparent=True)
        plt.close()

    def run_on_pair(self, before_tif, after_tif, aoi_geom=None, job_id=None, out_dir="outputs"):
        if not job_id: job_id = str(uuid.uuid4())[:8]
        job_out = os.path.join(out_dir, job_id)
        os.makedirs(job_out, exist_ok=True)

        arr_b, transform, crs = self._read_and_clip(before_tif, aoi_geom)
        arr_a, _, _ = self._read_and_clip(after_tif, aoi_geom)

        if arr_b.size == 0:
            raise RuntimeError("Selected AOI is empty or outside data bounds.")

        feats, H, W = self._build_pixel_features(arr_b, arr_a)
        
        # *** DEFINITIVE FIX for IndexError ***
        pred_cls_proba = self.cls_pipeline.predict_proba(feats)
        # Handle the two possible shapes returned by predict_proba
        prob_list = []
        for p in pred_cls_proba:
            if p.shape[1] == 2:
                prob_list.append(p[:, 1]) # Probability of class '1' (change)
            else:
                # If only one class is ever predicted, it returns shape (n, 1)
                # We assume this is prob of class '0', so prob of '1' is zero
                prob_list.append(np.zeros(p.shape[0]))
        
        pred_cls_stacked = np.stack(prob_list, axis=1)
        
        change_mask = np.any(pred_cls_stacked > 0.5, axis=1).reshape(H, W)
        cls_map = np.zeros((H, W), dtype=np.int32)
        if np.any(change_mask):
            changed_indices = np.where(change_mask.flatten())[0]
            highest_class = np.argmax(pred_cls_stacked[changed_indices], axis=1)
            cls_map.flat[changed_indices] = highest_class + 1

        cls_png = os.path.join(job_out, "class_map.png")
        self._save_png(cls_map, cls_png, 'tab10', vmin=0, vmax=9)

        total_pixels = H * W
        changed_pixels = int(np.sum(change_mask))
        percent_change = round(100.0 * changed_pixels / total_pixels, 3)
        
        categories = {
            "Deforestation": int(np.sum(cls_map == 1)),
            "Water": int(np.sum(cls_map == 2)),
            "Urban": int(np.sum(cls_map == 3)),
            "Agriculture": int(np.sum(cls_map == 4))
        }
        
        summary = {
            "job_id": job_id, "percent_change": percent_change, 
            "confidence_pct": 85.50, # Using a fixed confidence for this prototype
            "categories": categories,
        }
        
        return {"summary": summary, "overlays": {"class_png": cls_png}}