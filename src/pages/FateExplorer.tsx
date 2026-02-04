import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
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
import { useHelpContent } from "@/config/helpContent";
import { API_BASE } from "@/config/api";
import { TermWithTooltip } from "@/components/ui/term-with-tooltip";
import { ProductLabel } from "@/components/pfas/ProductLabel";

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
  citations: string[];
}

interface FateQueryResponse {
  query: string;
  total_transformations: number;
  transformations: Transformation[];
  compounds_involved: string[];
  compound_found: boolean;
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
  const { t } = useTranslation();
  const { toast } = useToast();
  const helpContent = useHelpContent();
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<FateQueryResponse | null>(null);
  const [summary, setSummary] = useState<GraphSummary | null>(null);
  const [parents, setParents] = useState<string[]>([]);

  const [parentOpen, setParentOpen] = useState(false);

  const [formData, setFormData] = useState({
    parent: "PTFE",
    tempMin: 0,
    tempMax: 1400,
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
    } catch {
      // Silently handle - summary is optional enhancement
    }
  };

  const loadParents = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/pfas/parents`);
      if (res.ok) {
        const data = await res.json();
        setParents(data.parents || []);
      }
    } catch {
      // Silently handle - parents list is optional enhancement
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
        title: t('common.queryComplete'),
        description: t('fateExplorer.foundPathways', { count: data.total_transformations, compound: formData.parent }),
      });
    } catch (error) {
      toast({
        title: t('common.queryFailed'),
        description: t('common.couldNotConnect'),
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
      <ChemoursHeader title={t('fateExplorer.title')} subtitle={t('fateExplorer.subtitle')} helpContent={helpContent.fateExplorer}>
        {summary && (
          <>
            <div className="text-gray-600">
              <span className="text-chemours-red font-bold">{summary.total_nodes}</span> {t('common.compounds')}
            </div>
            <div className="text-gray-600">
              <span className="text-chemours-red font-bold">{summary.total_edges.toLocaleString()}</span> {t('common.transformations')}
            </div>
            <div className="text-gray-600">
              <span className="text-chemours-red font-bold">{summary.haiku_records}</span> {t('common.papersExtracted')}
            </div>
          </>
        )}
      </ChemoursHeader>

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Query Panel */}
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-chemours-dark">{t('fateExplorer.queryParameters')}</CardTitle>
              <CardDescription>{t('fateExplorer.searchDegradationPathways')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-gray-700">{t('fateExplorer.parentCompound')}</Label>
                <Popover open={parentOpen} onOpenChange={setParentOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={parentOpen}
                      className="w-full justify-between bg-white border-gray-300 text-left font-normal"
                    >
                      {formData.parent || t('fateExplorer.selectCompound')}
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                    <Command>
                      <CommandInput placeholder={t('fateExplorer.searchCompounds')} />
                      <CommandList>
                        <CommandEmpty>{t('fateExplorer.noCompoundFound')}</CommandEmpty>
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
                  <Label className="text-gray-700">{t('fateExplorer.minTemp')}</Label>
                  <Input
                    type="number"
                    value={formData.tempMin}
                    onChange={(e) => setFormData({ ...formData, tempMin: parseInt(e.target.value) || 0 })}
                    className="bg-white border-gray-300"
                  />
                </div>
                <div>
                  <Label className="text-gray-700">{t('fateExplorer.maxTemp')}</Label>
                  <Input
                    type="number"
                    value={formData.tempMax}
                    onChange={(e) => setFormData({ ...formData, tempMax: parseInt(e.target.value) || 0 })}
                    className="bg-white border-gray-300"
                  />
                </div>
              </div>

              <div>
                <Label className="text-gray-700">{t('common.atmosphere')}</Label>
                <Select
                  value={formData.atmosphere}
                  onValueChange={(v) => setFormData({ ...formData, atmosphere: v })}
                >
                  <SelectTrigger className="bg-white border-gray-300">
                    <SelectValue placeholder={t('common.any')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">{t('common.any')}</SelectItem>
                    <SelectItem value="oxidative">Oxidative</SelectItem>
                    <SelectItem value="inert">Inert</SelectItem>
                    <SelectItem value="aqueous">Aqueous</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-gray-700">{t('fateExplorer.minObservations')}</Label>
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
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('common.searching')}</>
                ) : (
                  <><Search className="mr-2 h-4 w-4" /> {t('fateExplorer.searchPathways')}</>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Results Panel */}
          <div className="lg:col-span-3 space-y-6">
            {results && (
              <>
                {/* Case 1: Compound not found in database */}
                {!results.compound_found && (
                  <Card className="bg-white border-gray-200 shadow-sm border-l-4 border-l-amber-500">
                    <CardContent className="py-12 text-center">
                      <div className="h-16 w-16 mx-auto mb-4 rounded-full bg-amber-100 flex items-center justify-center">
                        <AlertTriangle className="h-8 w-8 text-amber-600" />
                      </div>
                      <h3 className="text-xl font-semibold text-chemours-dark mb-2">
                        {t('fateExplorer.compoundNotInDatabase')}
                      </h3>
                      <p className="text-gray-500 max-w-md mx-auto mb-2">
                        {t('fateExplorer.fateExplorerScope')}
                      </p>
                      <p className="text-gray-600 font-medium">
                        {t('fateExplorer.trySuggestions')}
                      </p>
                    </CardContent>
                  </Card>
                )}

                {/* Case 2: Compound found but no pathways match filters */}
                {results.compound_found && results.total_transformations === 0 && (
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardHeader>
                      <CardTitle className="text-chemours-dark flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-chemours-orange" />
                        0 {t('fateExplorer.degradationPathwaysFound')}
                      </CardTitle>
                      <CardDescription>
                        {t('fateExplorer.query')}: {formData.parent} at {formData.tempMin}-{formData.tempMax}°C
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="text-center py-8">
                      <p className="text-gray-600 mb-2">
                        {t('fateExplorer.noPathwaysMatchFilters')}
                      </p>
                      <p className="text-gray-500 text-sm">
                        {t('fateExplorer.tryAdjustingFilters')}
                      </p>
                    </CardContent>
                  </Card>
                )}

                {/* Case 3: Compound found with pathways */}
                {results.compound_found && results.total_transformations > 0 && (
                  <>
                    {/* Summary Card */}
                    <Card className="bg-white border-gray-200 shadow-sm">
                      <CardHeader>
                        <CardTitle className="text-chemours-dark flex items-center gap-2">
                          <AlertTriangle className="h-5 w-5 text-chemours-orange" />
                          {results.total_transformations} {t('fateExplorer.degradationPathwaysFound')}
                        </CardTitle>
                        <CardDescription>
                          {t('fateExplorer.query')}: {formData.parent} at {formData.tempMin}-{formData.tempMax}°C
                        </CardDescription>
                      </CardHeader>
                    </Card>

                    {/* Results Table */}
                    <Card className="bg-white border-gray-200 shadow-sm">
                      <CardContent className="p-0">
                        <Table>
                          <TableHeader>
                            <TableRow className="border-gray-200 hover:bg-gray-50">
                              <TableHead className="text-gray-700">
                                <TermWithTooltip explanationKey="tooltips.product">
                                  {t('fateExplorer.tableHeaders.product')}
                                </TermWithTooltip>
                              </TableHead>
                              <TableHead className="text-gray-700">
                                <TermWithTooltip explanationKey="tooltips.confidence">
                                  {t('fateExplorer.tableHeaders.confidence')}
                                </TermWithTooltip>
                              </TableHead>
                              <TableHead className="text-gray-700">
                                <TermWithTooltip explanationKey="tooltips.temperature">
                                  {t('fateExplorer.tableHeaders.temperature')}
                                </TermWithTooltip>
                              </TableHead>
                              <TableHead className="text-gray-700">
                                <TermWithTooltip explanationKey="tooltips.mechanism">
                                  {t('fateExplorer.tableHeaders.mechanism')}
                                </TermWithTooltip>
                              </TableHead>
                              <TableHead className="text-gray-700">
                                <TermWithTooltip explanationKey="tooltips.hazard">
                                  {t('fateExplorer.tableHeaders.hazard')}
                                </TermWithTooltip>
                              </TableHead>
                              <TableHead className="text-gray-700">
                                <TermWithTooltip explanationKey="tooltips.regulated">
                                  {t('fateExplorer.tableHeaders.regulated')}
                                </TermWithTooltip>
                              </TableHead>
                              <TableHead className="text-gray-700">
                                <TermWithTooltip explanationKey="tooltips.sources">
                                  {t('fateExplorer.tableHeaders.sources')}
                                </TermWithTooltip>
                              </TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {results.transformations.map((tr, i) => (
                              <TableRow key={i} className="border-gray-200 hover:bg-gray-50">
                                <TableCell className="font-medium text-chemours-dark">
                                  <ProductLabel value={tr.child} />
                                </TableCell>
                                <TableCell>
                                  <div className="flex items-center gap-2 min-w-[100px]">
                                    <Progress
                                      value={tr.score * 100}
                                      className="h-2 w-16"
                                    />
                                    <span className="text-xs text-gray-500 tabular-nums">
                                      {(tr.score * 100).toFixed(0)}%
                                    </span>
                                  </div>
                                </TableCell>
                                <TableCell className="text-gray-600">{tr.temp_range || t('common.notAvailable')}</TableCell>
                                <TableCell>
                                  <span className="text-gray-600 text-xs capitalize">
                                    {(tr.degradation_types?.[0] || t('common.unknown')).replace(/_/g, " ")}
                                  </span>
                                </TableCell>
                                <TableCell>
                                  <Badge className={getHazardColor(tr.hazard_level)}>
                                    {tr.hazard_level || t('common.unknown')}
                                  </Badge>
                                </TableCell>
                                <TableCell>
                                  {tr.is_regulated ? (
                                    <Badge className="bg-chemours-red">{t('common.regulated')}</Badge>
                                  ) : (
                                    <span className="text-gray-400">—</span>
                                  )}
                                </TableCell>
                                <TableCell>
                                  {tr.citations && tr.citations.length > 0 ? (
                                    <Popover>
                                      <PopoverTrigger asChild>
                                        <Button variant="ghost" size="sm" className="h-auto p-1 text-gray-500 hover:text-chemours-red">
                                          <FileText className="h-4 w-4 mr-1" />
                                          {tr.source_count}
                                        </Button>
                                      </PopoverTrigger>
                                      <PopoverContent className="w-80" align="end">
                                        <div className="space-y-2">
                                          <h4 className="font-medium text-sm text-chemours-dark">{t('fateExplorer.sourceReferences')}</h4>
                                          <div className="space-y-1 max-h-48 overflow-y-auto">
                                            {tr.citations.map((doi, idx) => (
                                              <a
                                                key={idx}
                                                href={doi.startsWith('http') ? doi : `https://doi.org/${doi}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="block text-xs text-blue-600 hover:text-blue-800 hover:underline truncate"
                                              >
                                                {doi}
                                              </a>
                                            ))}
                                          </div>
                                        </div>
                                      </PopoverContent>
                                    </Popover>
                                  ) : (
                                    <div className="flex items-center gap-1 text-gray-400">
                                      <FileText className="h-4 w-4" />
                                      {tr.source_count}
                                    </div>
                                  )}
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
                        <CardTitle className="text-chemours-dark text-sm">{t('fateExplorer.degradationTypesInResults')}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2">
                          {Array.from(new Set(results.transformations.flatMap(tr => tr.degradation_types))).map((type) => (
                            <Badge key={type} variant="outline" className="border-gray-400 text-gray-600 capitalize">
                              {type.replace(/_/g, " ")}
                            </Badge>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  </>
                )}
              </>
            )}

            {!results && (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardContent className="py-16 text-center">
                  <div className="h-16 w-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-chemours-red to-chemours-orange flex items-center justify-center">
                    <Search className="h-8 w-8 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold text-chemours-dark mb-2">{t('fateExplorer.pfasFateKnowledgeGraph')}</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    {summary
                      ? t('fateExplorer.queryDescription', { edges: summary.total_edges.toLocaleString(), parents: summary.parent_compounds, papers: summary.haiku_records })
                      : t('fateExplorer.loadingKnowledgeGraph')
                    }
                    {" "}{t('fateExplorer.selectParentAndTemp')}
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
