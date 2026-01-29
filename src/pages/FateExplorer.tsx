import { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Search, AlertTriangle, FileText, ChevronsUpDown, Check } from "lucide-react";
import ChemoursHeader from "@/components/layout/ChemoursHeader";
import helpContent from "@/config/helpContent";
import { API_BASE } from "@/config/api";

interface Transformation {
  parent: string;
  child: string;
  observations: number;
  score: number;
  temp_range: string;
  atmosphere: string;
  degradation_types: string[];
  hazard_level: string | null;
  is_regulated: boolean;
  source_count: number;
}

interface FateQueryResponse {
  query: string;
  total_transformations: number;
  transformations: Transformation[];
  compounds_involved: string[];
}

interface GraphSummary {
  total_nodes: number;
  total_edges: number;
  parent_compounds: number;
  endpoint_compounds: number;
  haiku_records: number;
}

const PARENT_COMPOUNDS = [
  "PTFE", "PVDF", "FEP", "PFA", "ETFE", "PCTFE",
  "PFOS", "PFOA", "6:2 FTOH", "8:2 FTOH",
];

const FateExplorer = () => {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<FateQueryResponse | null>(null);
  const [summary, setSummary] = useState<GraphSummary | null>(null);
  const [parents, setParents] = useState<string[]>([]);

  const [parentOpen, setParentOpen] = useState(false);

  const [formData, setFormData] = useState({
    parent: "PTFE",
    tempMin: 400,
    tempMax: 600,
    atmosphere: "any",
    minObservations: 1,
  });

  // Load summary and parent list on mount
  useEffect(() => {
    loadSummary();
    loadParents();
  }, []);

  const loadSummary = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/pfas/summary`);
      if (res.ok) {
        setSummary(await res.json());
      }
    } catch (e) {
      console.error("Failed to load summary:", e);
    }
  };

  const loadParents = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/pfas/parents`);
      if (res.ok) {
        const data = await res.json();
        setParents(data.parents || []);
      }
    } catch (e) {
      console.error("Failed to load parents:", e);
    }
  };

  const handleSearch = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        parent: formData.parent,
        temp_min: formData.tempMin.toString(),
        temp_max: formData.tempMax.toString(),
        min_observations: formData.minObservations.toString(),
      });
      if (formData.atmosphere && formData.atmosphere !== "any") {
        params.append("atmosphere", formData.atmosphere);
      }

      const res = await fetch(`${API_BASE}/api/v1/pfas/fate?${params}`);
      if (!res.ok) throw new Error("Query failed");

      const data: FateQueryResponse = await res.json();
      setResults(data);

      toast({
        title: "Query Complete",
        description: `Found ${data.total_transformations} degradation pathways for ${formData.parent}`,
      });
    } catch (error) {
      toast({
        title: "Query Failed",
        description: "Could not connect to AEGIS API. Make sure the backend is running on port 8002.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getHazardColor = (level: string | null) => {
    switch (level?.toUpperCase()) {
      case "CRITICAL": return "bg-red-600";
      case "HIGH": return "bg-red-500";
      case "MEDIUM": return "bg-yellow-500";
      case "LOW": return "bg-green-500";
      default: return "bg-gray-400";
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <ChemoursHeader title="AEGIS Fate Explorer" subtitle="PFAS Degradation Intelligence" helpContent={helpContent.fateExplorer}>
        {summary && (
          <>
            <div className="text-gray-600">
              <span className="text-chemours-red font-bold">{summary.total_nodes}</span> compounds
            </div>
            <div className="text-gray-600">
              <span className="text-chemours-red font-bold">{summary.total_edges.toLocaleString()}</span> transformations
            </div>
            <div className="text-gray-600">
              <span className="text-chemours-red font-bold">{summary.haiku_records}</span> papers extracted
            </div>
          </>
        )}
      </ChemoursHeader>

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Query Panel */}
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-chemours-dark">Query Parameters</CardTitle>
              <CardDescription>Search degradation pathways</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-gray-700">Parent Compound</Label>
                <Popover open={parentOpen} onOpenChange={setParentOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={parentOpen}
                      className="w-full justify-between bg-white border-gray-300 text-left font-normal"
                    >
                      {formData.parent || "Select compound..."}
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                    <Command>
                      <CommandInput placeholder="Search compounds..." />
                      <CommandList>
                        <CommandEmpty>No compound found.</CommandEmpty>
                        <CommandGroup>
                          {(parents.length > 0 ? parents : PARENT_COMPOUNDS).map((p) => (
                            <CommandItem
                              key={p}
                              value={p}
                              onSelect={(v) => {
                                setFormData({ ...formData, parent: v.toUpperCase() });
                                setParentOpen(false);
                              }}
                            >
                              <Check className={`mr-2 h-4 w-4 ${formData.parent === p ? "opacity-100" : "opacity-0"}`} />
                              {p}
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label className="text-gray-700">Min Temp (°C)</Label>
                  <Input
                    type="number"
                    value={formData.tempMin}
                    onChange={(e) => setFormData({ ...formData, tempMin: parseInt(e.target.value) || 0 })}
                    className="bg-white border-gray-300"
                  />
                </div>
                <div>
                  <Label className="text-gray-700">Max Temp (°C)</Label>
                  <Input
                    type="number"
                    value={formData.tempMax}
                    onChange={(e) => setFormData({ ...formData, tempMax: parseInt(e.target.value) || 0 })}
                    className="bg-white border-gray-300"
                  />
                </div>
              </div>

              <div>
                <Label className="text-gray-700">Atmosphere</Label>
                <Select
                  value={formData.atmosphere}
                  onValueChange={(v) => setFormData({ ...formData, atmosphere: v })}
                >
                  <SelectTrigger className="bg-white border-gray-300">
                    <SelectValue placeholder="Any atmosphere" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Any</SelectItem>
                    <SelectItem value="oxidative">Oxidative</SelectItem>
                    <SelectItem value="inert">Inert</SelectItem>
                    <SelectItem value="aqueous">Aqueous</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-gray-700">Min Observations</Label>
                <Input
                  type="number"
                  value={formData.minObservations}
                  onChange={(e) => setFormData({ ...formData, minObservations: parseInt(e.target.value) || 1 })}
                  className="bg-white border-gray-300"
                />
              </div>

              <Button
                onClick={handleSearch}
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-chemours-red to-chemours-orange hover:opacity-90 text-white"
              >
                {isLoading ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Searching...</>
                ) : (
                  <><Search className="mr-2 h-4 w-4" /> Search Pathways</>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Results Panel */}
          <div className="lg:col-span-3 space-y-6">
            {results && (
              <>
                {/* Summary Card */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <CardTitle className="text-chemours-dark flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-chemours-orange" />
                      {results.total_transformations} Degradation Pathways Found
                    </CardTitle>
                    <CardDescription>
                      Query: {formData.parent} at {formData.tempMin}-{formData.tempMax}°C
                    </CardDescription>
                  </CardHeader>
                </Card>

                {/* Results Table */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardContent className="p-0">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-gray-200 hover:bg-gray-50">
                          <TableHead className="text-gray-700">Product</TableHead>
                          <TableHead className="text-gray-700">Confidence</TableHead>
                          <TableHead className="text-gray-700">Temperature</TableHead>
                          <TableHead className="text-gray-700">Mechanism</TableHead>
                          <TableHead className="text-gray-700">Hazard</TableHead>
                          <TableHead className="text-gray-700">Regulated</TableHead>
                          <TableHead className="text-gray-700">Sources</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {results.transformations.map((t, i) => (
                          <TableRow key={i} className="border-gray-200 hover:bg-gray-50">
                            <TableCell className="font-medium text-chemours-dark">{t.child}</TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2 min-w-[100px]">
                                <Progress
                                  value={t.score * 100}
                                  className="h-2 w-16"
                                />
                                <span className="text-xs text-gray-500 tabular-nums">
                                  {(t.score * 100).toFixed(0)}%
                                </span>
                              </div>
                            </TableCell>
                            <TableCell className="text-gray-600">{t.temp_range || "N/A"}</TableCell>
                            <TableCell>
                              <span className="text-gray-600 text-xs capitalize">
                                {(t.degradation_types?.[0] || "unknown").replace(/_/g, " ")}
                              </span>
                            </TableCell>
                            <TableCell>
                              <Badge className={getHazardColor(t.hazard_level)}>
                                {t.hazard_level || "Unknown"}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {t.is_regulated ? (
                                <Badge className="bg-chemours-red">Regulated</Badge>
                              ) : (
                                <span className="text-gray-400">—</span>
                              )}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1 text-gray-500">
                                <FileText className="h-4 w-4" />
                                {t.source_count}
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                {/* Degradation Types Legend */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <CardTitle className="text-chemours-dark text-sm">Degradation Types in Results</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {Array.from(new Set(results.transformations.flatMap(t => t.degradation_types))).map((type) => (
                        <Badge key={type} variant="outline" className="border-gray-400 text-gray-600 capitalize">
                          {type.replace(/_/g, " ")}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </>
            )}

            {!results && (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardContent className="py-16 text-center">
                  <div className="h-16 w-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-chemours-red to-chemours-orange flex items-center justify-center">
                    <Search className="h-8 w-8 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold text-chemours-dark mb-2">PFAS Fate Knowledge Graph</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    {summary
                      ? `Query ${summary.total_edges.toLocaleString()} degradation transformations across ${summary.parent_compounds} compounds from ${summary.haiku_records} peer-reviewed papers.`
                      : "Loading knowledge graph..."
                    }
                    {" "}Select a parent compound and temperature range to explore degradation pathways.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default FateExplorer;
