interface Product {
  name: string;
  probability_mean: number;
  ci_lower: number;
  ci_upper: number;
}

interface ProbabilityChartProps {
  products: Product[];
}

const ProbabilityChart = ({ products }: ProbabilityChartProps) => {
  if (!products || products.length === 0) {
    return <p className="text-muted-foreground">No PFAS products detected under these conditions.</p>;
  }

  return (
    <div className="space-y-6">
      {products.map((product, idx) => (
        <div key={idx} className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-lg">{product.name}</span>
            <span className="text-sm font-medium">
              Mean: {(product.probability_mean * 100).toFixed(1)}%
            </span>
          </div>
          
          <div className="relative h-12 bg-muted rounded-lg overflow-hidden">
            <div 
              className="absolute h-full bg-primary/20"
              style={{ 
                left: `${product.ci_lower * 100}%`,
                width: `${(product.ci_upper - product.ci_lower) * 100}%`
              }}
            />
            
            <div 
              className="absolute h-full w-1 bg-primary"
              style={{ left: `${product.probability_mean * 100}%` }}
            />
          </div>
          
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>90% CI: [{(product.ci_lower * 100).toFixed(1)}% – {(product.ci_upper * 100).toFixed(1)}%]</span>
            <span>Probability Scale: 0% → 100%</span>
          </div>
        </div>
      ))}
    </div>
  );
};

export default ProbabilityChart;