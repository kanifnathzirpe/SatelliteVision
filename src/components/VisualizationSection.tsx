// src/components/VisualizationSection.tsx
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MapPin, Layers, Activity, AlertTriangle } from 'lucide-react';
import MapAOISelector from './MapAOISelector';
import ImageComparison from './ImageComparison';
import ChangeDetectionOverlay from './ChangeDetectionOverlay';

interface AOIBounds { north: number; south: number; east: number; west: number; }
export interface AnalysisResult {
  summary: {
    percent_change: number;
    confidence_pct: number;
    categories: {
      Deforestation: number;
      Urban: number;
      Agriculture: number;
    };
  };
  overlays: { class_png?: string; };
  beforeImage?: string;
  afterImage?: string;
}

const LoadingState = ({ title, subtitle }: { title: string; subtitle: string }) => (
    <div className="flex flex-col items-center justify-center h-full text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
        <p className="font-semibold text-lg">{title}</p>
        <p className="text-muted-foreground">{subtitle}</p>
    </div>
);

const ErrorState = ({ message }: { message: string }) => (
    <div className="flex flex-col items-center justify-center h-full text-center text-destructive p-4">
        <AlertTriangle className="w-12 h-12 mb-4" />
        <p className="font-semibold text-lg">Analysis Failed</p>
        <p className="text-sm">{message}</p>
    </div>
);


const VisualizationSection = () => {
  const [activeTab, setActiveTab] = useState('aoi');
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAOISelected = async (bounds: AOIBounds | null) => {
    if (bounds) {
      setIsLoading(true);
      setAnalysisResult(null);
      setError(null);
      
      try {
        // Switch tabs immediately to show loading state
        setActiveTab('imagery'); 

        const response = await fetch('http://localhost:8000/api/analyze-aoi', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(bounds),
        });

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || "An unknown API error occurred.");
        }
        const data: AnalysisResult = await response.json();
        setAnalysisResult(data);
      } catch (err: any) {
        setError(err.message);
        console.error("Analysis failed:", err);
      } finally {
        setIsLoading(false);
      }
    } else {
      setAnalysisResult(null);
      setError(null);
    }
  };

  const renderContent = () => {
      // Prioritize error and loading states across all tabs except AOI
      if (activeTab !== 'aoi') {
        if (error) return <ErrorState message={error} />;
        if (isLoading) return <LoadingState title="Analyzing Satellite Imagery" subtitle="This may take a moment..." />;
      }
      
      switch(activeTab) {
          case 'aoi': return <MapAOISelector onAOISelected={handleAOISelected} />;
          case 'imagery': return <ImageComparison result={analysisResult} />;
          case 'detection': return <ChangeDetectionOverlay result={analysisResult} />;
          default: return null;
      }
  };

  return (
    <section id="visualization" className="py-24">
      <div className="container mx-auto px-4">
         {/* ... (Header and Tabs remain the same) ... */}
         <div className="flex flex-wrap justify-center gap-4 mb-12">
            {[{id: 'aoi', title: 'AOI Selection', icon: MapPin}, {id: 'imagery', title: 'LISS-IV Images', icon: Layers}, {id: 'detection', title: 'Change Detection', icon: Activity}].map((feature) => (
                <Button key={feature.id} variant={activeTab === feature.id ? "default" : "outline"} className={`glass-card ${activeTab === feature.id ? 'bg-gradient-cosmic' : ''}`} onClick={() => setActiveTab(feature.id)}>
                    <feature.icon className="w-4 h-4 mr-2" /> {feature.title}
                </Button>
            ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <Card className="glass-card border-border/50 h-[650px]">
              <CardContent className="p-2 h-full">{renderContent()}</CardContent>
            </Card>
          </div>
          <div className="space-y-6">
            <Card className="glass-card border-border/50">
                <CardHeader><CardTitle>Analysis Statistics</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                    {isLoading ? <p className="text-sm text-muted-foreground">Processing...</p> : analysisResult ? (
                        <>
                            <StatRow label="Change Detected" value={`${analysisResult.summary.percent_change.toFixed(2)}%`} color="text-warning" />
                            <StatRow label="Confidence Level" value={`${analysisResult.summary.confidence_pct.toFixed(2)}%`} color="text-success" />
                        </>
                    ) : <p className="text-sm text-muted-foreground">Select an AOI to see statistics.</p>}
                </CardContent>
            </Card>
            <Card className="glass-card border-border/50">
                <CardHeader><CardTitle>Change Categories</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                    {isLoading ? <p className="text-sm text-muted-foreground">Processing...</p> : analysisResult ? (
                        <>
                            <CategoryRow label="Deforestation" color="bg-red-500" value={analysisResult.summary.categories.Deforestation} />
                            <CategoryRow label="Urban Growth" color="bg-yellow-500" value={analysisResult.summary.categories.Urban} />
                            <CategoryRow label="Agriculture" color="bg-green-500" value={analysisResult.summary.categories.Agriculture} />
                        </>
                    ) : <p className="text-sm text-muted-foreground">No analysis data available.</p>}
                </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
};
const StatRow = ({ label, value, color }: any) => (<div className="flex justify-between"><span className="text-sm text-muted-foreground">{label}</span><span className={`font-semibold ${color}`}>{value}</span></div>);
const CategoryRow = ({ label, color, value }: any) => (<div className="flex items-center justify-between"><div className="flex items-center space-x-2"><div className={`w-3 h-3 ${color} rounded-full`}></div><span className="text-sm text-muted-foreground">{label}</span></div><span className="text-sm font-semibold">{value.toLocaleString()} px</span></div>);

export default VisualizationSection;
