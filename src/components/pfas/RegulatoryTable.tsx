import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

interface Product {
  name: string;
  regulatory_status?: {
    california?: string;
    eu?: string;
    epa?: string;
  };
}

interface RegulatoryTableProps {
  products: Product[];
}

const RegulatoryTable = ({ products }: RegulatoryTableProps) => {
  if (!products || products.length === 0) {
    return <p className="text-muted-foreground">No regulatory data available.</p>;
  }

  const getStatusBadge = (status: string | undefined) => {
    if (!status) return <Badge variant="outline">Not Listed</Badge>;
    
    if (status.toLowerCase().includes("drinking water")) {
      return <Badge variant="destructive">Regulated</Badge>;
    }
    if (status.toLowerCase().includes("concern")) {
      return <Badge className="bg-yellow-500">Concern</Badge>;
    }
    return <Badge variant="outline">{status}</Badge>;
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="font-semibold">PFAS Compound</TableHead>
          <TableHead className="font-semibold">California</TableHead>
          <TableHead className="font-semibold">EU</TableHead>
          <TableHead className="font-semibold">EPA</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {products.map((product, idx) => (
          <TableRow key={idx}>
            <TableCell className="font-medium">{product.name}</TableCell>
            <TableCell>{getStatusBadge(product.regulatory_status?.california)}</TableCell>
            <TableCell>{getStatusBadge(product.regulatory_status?.eu)}</TableCell>
            <TableCell>{getStatusBadge(product.regulatory_status?.epa)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

export default RegulatoryTable;