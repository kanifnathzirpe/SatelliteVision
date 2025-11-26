// src/components/MapAOISelector.tsx
import React, { useEffect, useRef, useState } from 'react';
import * as L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MapPin, Square, X, RefreshCw } from 'lucide-react';

interface MapAOISelectorProps {
  onAOISelected?: (bounds: {
    west: number;
    south: number;
    east: number;
    north: number;
  } | null) => void;
}

// *** FIX: Define the exact center and bounds of our real satellite data ***
const DATA_BOUNDS: L.LatLngBoundsExpression = [[18.4, 73.7], [18.65, 74.0]]; // South-West, North-East
const DATA_CENTER: L.LatLngTuple = [18.525, 73.85]; // Center of Pune data
const DEFAULT_ZOOM = 11; // Zoom level to show the data area

const MapAOISelector: React.FC<MapAOISelectorProps> = ({
  onAOISelected
}) => {
  const [areaKm2, setAreaKm2] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const rectLayerRef = useRef<L.Rectangle | null>(null);
  const startPointRef = useRef<L.LatLng | null>(null);
  const isDrawingRef = useRef(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: DATA_CENTER, // <-- Use the correct center
      zoom: DEFAULT_ZOOM,  // <-- Use the correct zoom
      zoomControl: true,
      scrollWheelZoom: true
    });
    mapRef.current = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // *** NEW: Add a visual guide showing the data boundary ***
    L.rectangle(DATA_BOUNDS, {
      color: "#ff7800",
      weight: 2,
      dashArray: '5, 5',
      fill: false
    }).addTo(map).bindTooltip("Available Data Area", {permanent: true, direction: 'center'});


    const startDrawing = (latlng: L.LatLng) => {
      isDrawingRef.current = true;
      startPointRef.current = latlng;
      map.dragging.disable();
      map.getContainer().style.cursor = 'crosshair';
      if (rectLayerRef.current) {
        map.removeLayer(rectLayerRef.current);
        rectLayerRef.current = null;
      }
      setAreaKm2(null);
      onAOISelected?.(null);
    };

    const onMouseDown = (e: L.LeafletMouseEvent) => {
      startDrawing(e.latlng);
    };
    
    const updateDrawing = (latlng: L.LatLng) => {
      if (!isDrawingRef.current || !startPointRef.current) return;
      const bounds = L.latLngBounds(startPointRef.current, latlng);
      if (rectLayerRef.current) {
        rectLayerRef.current.setBounds(bounds);
      } else {
        rectLayerRef.current = L.rectangle(bounds, {
          color: '#3b82f6', weight: 2, fillColor: '#3b82f6', fillOpacity: 0.15
        }).addTo(map);
      }
    };

    const onMouseMove = (e: L.LeafletMouseEvent) => {
      updateDrawing(e.latlng);
    };

    const finishDrawing = (latlng: L.LatLng) => {
      if (!isDrawingRef.current || !startPointRef.current) return;
      
      isDrawingRef.current = false;
      map.dragging.enable();
      map.getContainer().style.cursor = '';
      
      const start = startPointRef.current;
      const bounds = L.latLngBounds(start, latlng);
      
      if (bounds.getWest() === bounds.getEast() || bounds.getSouth() === bounds.getNorth()) {
        if (rectLayerRef.current) map.removeLayer(rectLayerRef.current);
        rectLayerRef.current = null;
        return;
      }
      
      const dLatKm = Math.abs(bounds.getNorth() - bounds.getSouth()) * 111;
      const dLngKm = Math.abs(bounds.getEast() - bounds.getWest()) * 111 * Math.cos(bounds.getCenter().lat * Math.PI / 180);
      setAreaKm2(Number((dLatKm * dLngKm).toFixed(2)));
      
      onAOISelected?.({
        west: bounds.getWest(),
        south: bounds.getSouth(),
        east: bounds.getEast(),
        north: bounds.getNorth()
      });
    };

    const onMouseUp = (e: L.LeafletMouseEvent) => finishDrawing(e.latlng);

    map.on('mousedown', onMouseDown);
    map.on('mousemove', onMouseMove);
    map.on('mouseup', onMouseUp);
    
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [onAOISelected]);

  const handleClearAOI = () => {
    if (rectLayerRef.current && mapRef.current) {
      mapRef.current.removeLayer(rectLayerRef.current);
      rectLayerRef.current = null;
    }
    setAreaKm2(null);
    onAOISelected?.(null);
  };
  
  const resetView = () => {
    mapRef.current?.setView(DATA_CENTER, DEFAULT_ZOOM);
  }

  return (
    <div className="relative w-full h-full">
      <div className="absolute top-4 left-4 z-[1001] space-y-2">
        <Badge className="glass-card font-montserrat text-xs border-primary/30 bg-primary/10">
          <MapPin className="w-3 h-3 mr-1" />
          Drag on map to select area
        </Badge>
        {areaKm2 !== null && (
          <div className="space-y-2">
            <Badge className="glass-card font-montserrat text-xs bg-primary/20 border-primary/50">
              <Square className="w-3 h-3 mr-1" />
              Area: {areaKm2} km²
            </Badge>
            <Button size="sm" variant="outline" onClick={handleClearAOI} className="w-full text-xs h-7 glass-card">
              <X className="w-3 h-3 mr-1" />
              Clear AOI
            </Button>
          </div>
        )}
      </div>
      
      {/* NEW: Button to reset map view */}
      <div className="absolute top-4 right-4 z-[1001]">
         <Button size="sm" variant="outline" onClick={resetView} className="glass-card">
            <RefreshCw className="w-3 h-3 mr-2"/>
            Reset View
         </Button>
      </div>

      <div ref={containerRef} className="absolute inset-0 rounded-lg shadow-lg z-0" />
      <div className="absolute inset-0 pointer-events-none bg-gradient-to-b from-transparent to-background/10 rounded-lg z-[1000]" />
    </div>
  );
};
export default MapAOISelector;