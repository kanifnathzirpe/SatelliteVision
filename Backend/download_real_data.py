# backend/download_real_data.py
import pystac_client
import planetary_computer
import odc.stac
import rasterio
import numpy as np
import os
import rasterio.transform

# Define Area of Interest (AOI) around Pune, India and date ranges
BBOX = [73.7, 18.4, 74.0, 18.65] # Lon/Lat
DATES_BEFORE = "2018-01-01/2018-03-30"
DATES_AFTER = "2023-01-01/2023-03-30"
BANDS = ["B04", "B03", "B02", "B08"] # Red, Green, Blue, NIR (for Sentinel-2)

def download_and_merge_assets(items, bands, output_path):
    """Downloads assets for given bands and merges them into a single GeoTIFF."""
    print(f"Downloading assets for {output_path}...")
    
    # Use odc-stac to load data directly into an xarray.Dataset
    data = odc.stac.stac_load(
        items,
        bands=bands,
        bbox=BBOX,
        resolution=10, # 10m resolution for Sentinel-2 RGB/NIR
    )
    
    # Extract the data for each band into a NumPy array
    np_data = np.array([data[band].squeeze().values for band in bands]).astype(np.uint16)
    
    # *** DEFINITIVE FIX: Get transform and CRS from xarray attributes ***
    # The CRS information is stored in the 'spatial_ref' coordinate's attributes
    try:
        crs_wkt = data.spatial_ref.attrs.get('crs_wkt')
        if crs_wkt is None:
            raise AttributeError("CRS WKT not found in spatial_ref attrs")
    except AttributeError:
        # Fallback for different library versions
        crs_wkt = data.attrs.get('crs', 'EPSG:4326')
        logger.warning("Could not find 'spatial_ref' attribute, falling back to dataset CRS attribute.")


    # The transform is derived from the coordinates
    coords = data.coords
    transform = rasterio.transform.from_origin(
        coords['x'][0].item(), # west
        coords['y'][0].item(), # north
        abs(coords['x'][1].item() - coords['x'][0].item()),  # pixel width
        abs(coords['y'][1].item() - coords['y'][0].item())   # pixel height
    )


    # Get metadata for saving
    profile = {
        'driver': 'GTiff',
        'height': np_data.shape[1],
        'width': np_data.shape[2],
        'count': len(bands),
        'dtype': np_data.dtype,
        'crs': crs_wkt, # Use the extracted CRS
        'transform': transform,
    }

    print(f"Writing merged file to {output_path}...")
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(np_data)

if __name__ == "__main__":
    output_dir = "test_data"
    os.makedirs(output_dir, exist_ok=True)

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    # --- Process BEFORE images ---
    search_before = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=BBOX,
        datetime=DATES_BEFORE,
        query={"eo:cloud_cover": {"lt": 10}},
    )
    items_before = search_before.item_collection()
    if not items_before:
        raise Exception(f"No clear images found for the 'before' date range: {DATES_BEFORE}")
    print(f"Found {len(items_before)} items for 'before' period. Using the first clear image.")
    download_and_merge_assets([items_before[0]], BANDS, os.path.join(output_dir, "real_before.tif"))
    
    # --- Process AFTER images ---
    search_after = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=BBOX,
        datetime=DATES_AFTER,
        query={"eo:cloud_cover": {"lt": 10}},
    )
    items_after = search_after.item_collection()
    if not items_after:
        raise Exception(f"No clear images found for the 'after' date range: {DATES_AFTER}")
    print(f"Found {len(items_after)} items for 'after' period. Using the first clear image.")
    download_and_merge_assets([items_after[0]], BANDS, os.path.join(output_dir, "real_after.tif"))

    print("\n✅ Real data download and preparation complete.")
    print("You can now run the backend server.")