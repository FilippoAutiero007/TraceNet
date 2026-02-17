import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { CheckCircle, Download, FileText, Network } from 'lucide-react';
import { API_BASE_URL } from '@/config';

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
}

export function DownloadResult({ data }: DownloadResultProps) {
  const API_URL = API_BASE_URL;
  const pktUrl = `${API_URL}${data.pkt_download_url}`;
  const xmlUrl = data.xml_download_url ? `${API_URL}${data.xml_download_url}` : null;

  return (
    <Card className="w-full bg-slate-900 border-slate-800">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-green-500">
          <CheckCircle className="w-5 h-5" />
          Network Generated Successfully!
        </CardTitle>
        <CardDescription className="text-slate-400">
          Your network configuration is ready to download
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Configuration Summary */}
        <div className="bg-slate-800 rounded-lg p-4 space-y-3">
          <h3 className="font-semibold text-cyan-500 flex items-center gap-2">
            <Network className="w-4 h-4" />
            Configuration Summary
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-slate-400">Base Network:</span>
              <p className="text-slate-100 font-mono">{data.config_summary.base_network}</p>
            </div>
            <div>
              <span className="text-slate-400">Subnets:</span>
              <p className="text-slate-100 font-semibold">{data.config_summary.subnets_count}</p>
            </div>
            <div>
              <span className="text-slate-400">Routers:</span>
              <p className="text-slate-100 font-semibold">{data.config_summary.routers}</p>
            </div>
            <div>
              <span className="text-slate-400">Switches:</span>
              <p className="text-slate-100 font-semibold">{data.config_summary.switches}</p>
            </div>
            <div>
              <span className="text-slate-400">PCs:</span>
              <p className="text-slate-100 font-semibold">{data.config_summary.pcs}</p>
            </div>
            <div>
              <span className="text-slate-400">Routing Protocol:</span>
              <p className="text-slate-100 font-semibold uppercase">{data.config_summary.routing_protocol}</p>
            </div>
          </div>
        </div>

        {/* Subnets Table */}
        <div className="space-y-3">
          <h3 className="font-semibold text-cyan-500">Subnet Details</h3>
          <div className="rounded-lg border border-slate-700 overflow-hidden">
            <Table>
              <TableHeader className="bg-slate-800">
                <TableRow className="border-slate-700 hover:bg-slate-800">
                  <TableHead className="text-slate-300 font-semibold">Subnet Name</TableHead>
                  <TableHead className="text-slate-300 font-semibold">Network Address</TableHead>
                  <TableHead className="text-slate-300 font-semibold">Gateway IP</TableHead>
                  <TableHead className="text-slate-300 font-semibold text-right">Usable Hosts</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.subnets.map((subnet, idx) => (
                  <TableRow key={idx} className="border-slate-700 hover:bg-slate-800/50">
                    <TableCell className="font-medium text-slate-100">{subnet.name}</TableCell>
                    <TableCell className="font-mono text-slate-300">{subnet.network}</TableCell>
                    <TableCell className="font-mono text-slate-300">{subnet.gateway}</TableCell>
                    <TableCell className="text-right text-slate-300">{subnet.usable_hosts}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>

        {/* Download Buttons */}
        <div className="space-y-3">
          <Button
            className="w-full bg-cyan-500 hover:bg-cyan-600 text-white font-semibold py-6 text-base"
            onClick={() => window.open(pktUrl, '_blank')}
          >
            <Download className="mr-2 h-5 w-5" />
            Download .pkt File
          </Button>
          {xmlUrl && (
            <Button
              variant="outline"
              className="w-full border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200"
              onClick={() => window.open(xmlUrl, '_blank')}
            >
              <FileText className="mr-2 h-4 w-4" />
              Download XML Debug File
            </Button>
          )}
        </div>

        {/* Instructions */}
        <div className="bg-slate-800 rounded-lg p-4 space-y-2">
          <h4 className="font-semibold text-cyan-500 text-sm">How to use the generated file:</h4>
          <ol className="list-decimal list-inside space-y-1 text-sm text-slate-300">
            <li>Download the .pkt file using the button above</li>
            <li>Open Cisco Packet Tracer (version 8.x or higher)</li>
            <li>Go to File → Open and select the downloaded .pkt file</li>
            <li>Your network will be loaded with all devices and configurations</li>
            <li>Use the simulation mode to test connectivity</li>
          </ol>
        </div>
      </CardContent>
    </Card>
  );
}
