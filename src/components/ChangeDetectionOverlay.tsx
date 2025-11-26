import { Badge } from '@/components/ui/badge';
import { AnalysisResult } from './VisualizationSection';

interface ChangeDetectionOverlayProps {
  result: AnalysisResult | null;
}

const ChangeDetectionOverlay = ({ result }: ChangeDetectionOverlayProps) => {
  if (!result) {
    return <div className="flex items-center justify-center h-full text-muted-foreground">No analysis result to display.</div>;
  }

  return (
    <div className="relative w-full h-full">
      <img src={result.overlays.class_png} alt="Change Detection Overlay" className="w-full h-full object-contain" />
      <div className="absolute bottom-4 right-4 glass-card p-2 space-y-1">
        <p className="font-montserrat text-xs font-semibold text-foreground">Change Legend</p>
        <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-orange-500 rounded-sm"></div><span className="text-xs">Deforestation</span>
        </div>
        <div className="flex items-center space-x-2">
        </div>
      </div>
    </div>
  );
};

export default ChangeDetectionOverlay;