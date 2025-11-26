import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { AnalysisResult } from './VisualizationSection';

interface ImageComparisonProps {
  result: AnalysisResult | null;
}

const ImageComparison = ({ result }: ImageComparisonProps) => {
  const [sliderPosition, setSliderPosition] = useState(50);

  if (!result) {
    return <div className="flex items-center justify-center h-full text-muted-foreground">Please select an AOI to begin analysis.</div>;
  }

  return (
    <div className="relative w-full h-full select-none">
      <div className="absolute inset-0">
        <img src={result.beforeImage} alt="Before" className="w-full h-full object-contain" />
        <Badge className="absolute top-2 left-2 glass-card">Before: 2018</Badge>
      </div>
      <div className="absolute inset-0" style={{ clipPath: `inset(0 ${100 - sliderPosition}% 0 0)` }}>
        <img src={result.afterImage} alt="After" className="w-full h-full object-contain" />
        <Badge className="absolute top-2 right-2 glass-card">After: 2023</Badge>
      </div>
      <div className="absolute top-0 bottom-0 w-1 bg-white/80 cursor-ew-resize" style={{ left: `calc(${sliderPosition}% - 2px)` }}>
        <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center">
          <div className="w-1 h-4 bg-gray-500 rounded-full" />
        </div>
      </div>
      <input
        type="range" min="0" max="100" value={sliderPosition}
        onChange={(e) => setSliderPosition(Number(e.target.value))}
        className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize"
      />
    </div>
  );
};

export default ImageComparison;