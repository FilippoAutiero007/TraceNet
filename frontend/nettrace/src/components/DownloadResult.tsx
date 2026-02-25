import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { CheckCircle, Download, FileText, Network, RefreshCw, Clock } from 'lucide-react';
import { API_BASE_URL } from '@/config';
import { TopologyPreview } from '@/components/TopologyPreview';
import { formatDistanceToNow } from 'date-fns';

interface SubnetInfo {
  name: string;
  network: string;
  gateway: string;
  usable_hosts: number;
}

interface ConfigSummary {
  base_network: string;
  subnets_count: number;
  routers: number;
  switches: number;
  pcs: number;
  routing_protocol: string;
}

interface DownloadResultProps {
  data: {
    success: boolean;
    message: string;
    pkt_download_url: string;
    xml_download_url?: string;
    config_summary: ConfigSummary;
    subnets: SubnetInfo[];
  };
  generatedAt?: number;
  onRegenerate?: () => void;
}

export function DownloadResult({ data, generatedAt, onRegenerate }: DownloadResultProps) {
  const pktUrl = `${API_BASE_URL}${data.pkt_download_url}`;
  const xmlUrl = data.xml_download_url ? `${API_BASE_URL}${data.xml_download_url}` : null;

  return (
    <Card className="w-full bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-green-400">
            <CheckCircle className="w-5 h-5" aria-hidden="true" />
            Network Generated
          </CardTitle>
          {generatedAt && (
            <span className="flex items-center gap-1 text-xs text-slate-500 mt-0.5">
              <Clock className="w-3 h-3" />
              {formatDistanceToNow(generatedAt, { addSuffix: true })}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Topology Preview */}
        <TopologyPreview configSummary={data.config_summary} subnets={data.subnets} />

        {/* Configuration Summary */}
        <div className="bg-slate-800 rounded-lg p-4 space-y-3">
          <h3 className="font-semibold text-cyan-400 flex items-center gap-2 text-sm">
            <Network className="w-4 h-4" aria-hidden="true" />
            Configuration Summary
          </h3>
          <div className="grid grid-cols-2 gap-y-2.5 gap-x-4 text-sm">
            {[
              { label: 'Base Network', value: data.config_summary.base_network, mono: true },
              { label: 'Subnets', value: data.config_summary.subnets_count },
              { label: 'Routers', value: data.config_summary.routers },
              { label: 'Switches', value: data.config_summary.switches },
              { label: 'PCs', value: data.config_summary.pcs },
              { label: 'Routing Protocol', value: data.config_summary.routing_protocol.toUpperCase() },
            ].map(({ label, value, mono }) => (
              <div key={label}>
                <p className="text-slate-500 text-xs">{label}</p>
                <p className={`text-slate-100 font-semibold ${mono ? 'font-mono text-xs' : ''}`}>{value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Subnets Table — horizontally scrollable */}
        <div className="space-y-2">
          <h3 className="font-semibold text-cyan-400 text-sm">Subnet Details</h3>
          <div className="rounded-lg border border-slate-700 overflow-x-auto">
            <Table className="min-w-[480px]">
              <TableHeader className="bg-slate-800">
                <TableRow className="border-slate-700 hover:bg-slate-800">
                  <TableHead className="text-slate-300 font-semibold text-xs">Name</TableHead>
                  <TableHead className="text-slate-300 font-semibold text-xs">Network</TableHead>
                  <TableHead className="text-slate-300 font-semibold text-xs">Gateway</TableHead>
                  <TableHead className="text-slate-300 font-semibold text-xs text-right">Hosts</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.subnets.map((subnet, idx) => (
                  <TableRow key={idx} className="border-slate-700 hover:bg-slate-800/50">
                    <TableCell className="font-medium text-slate-100 text-sm py-2">{subnet.name}</TableCell>
                    <TableCell className="font-mono text-slate-300 text-xs py-2">{subnet.network}</TableCell>
                    <TableCell className="font-mono text-slate-300 text-xs py-2">{subnet.gateway}</TableCell>
                    <TableCell className="text-right text-slate-300 text-sm py-2">{subnet.usable_hosts}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>

        {/* Download Buttons */}
        <div className="space-y-2">
          <Button
            className="w-full bg-cyan-500 hover:bg-cyan-400 text-white font-semibold py-5 focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 shadow-md shadow-cyan-500/20"
            onClick={() => window.open(pktUrl, '_blank')}
            aria-label="Download .pkt file"
          >
            <Download className="mr-2 h-4 w-4" aria-hidden="true" />
            Download .pkt File
          </Button>
          {xmlUrl && (
            <Button
              variant="outline"
              className="w-full border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 focus-visible:ring-2 focus-visible:ring-slate-400"
              onClick={() => window.open(xmlUrl, '_blank')}
              aria-label="Download XML debug file"
            >
              <FileText className="mr-2 h-4 w-4" aria-hidden="true" />
              Download XML Debug
            </Button>
          )}
          {onRegenerate && (
            <Button
              variant="ghost"
              className="w-full text-slate-400 hover:text-cyan-400 text-sm gap-1.5 focus-visible:ring-2 focus-visible:ring-cyan-500"
              onClick={onRegenerate}
              aria-label="Regenerate with same parameters"
            >
              <RefreshCw className="w-4 h-4" aria-hidden="true" />
              Regenerate
            </Button>
          )}
        </div>

        {/* How to use */}
        <div className="bg-slate-800/60 rounded-lg p-4 space-y-1.5">
          <h4 className="font-semibold text-cyan-400 text-xs uppercase tracking-wider">How to open the file</h4>
          <ol className="list-decimal list-inside space-y-1 text-xs text-slate-400 leading-relaxed">
            <li>Download the <code className="text-slate-300">.pkt</code> file above</li>
            <li>Open <strong className="text-slate-300">Cisco Packet Tracer</strong> (v8.x or higher)</li>
            <li>Go to <strong className="text-slate-300">File → Open</strong> and select the file</li>
            <li>Use Simulation mode to test connectivity</li>
          </ol>
        </div>
      </CardContent>
    </Card>
  );
}
