import CytoscapeComponent from 'react-cytoscapejs';

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

interface TopologyPreviewProps {
  configSummary: ConfigSummary;
  subnets: SubnetInfo[];
}

function buildElements(configSummary: ConfigSummary, subnets: SubnetInfo[]) {
  const elements: cytoscape.ElementDefinition[] = [];
  const routerCount = Math.max(1, configSummary.routers);

  for (let i = 0; i < routerCount; i++) {
    elements.push({ data: { id: `r${i}`, label: `Router ${i + 1}`, type: 'router' } });
  }
  for (let i = 0; i < routerCount - 1; i++) {
    elements.push({ data: { id: `re${i}`, source: `r${i}`, target: `r${i + 1}` } });
  }
  subnets.forEach((subnet, i) => {
    const routerIdx = i % routerCount;
    elements.push({ data: { id: `sn${i}`, label: subnet.name, type: 'subnet', network: subnet.network } });
    elements.push({ data: { id: `sne${i}`, source: `r${routerIdx}`, target: `sn${i}` } });
  });

  return elements;
}

const stylesheet: cytoscape.Stylesheet[] = [
  {
    selector: 'node',
    style: {
      'background-color': '#1e293b',
      label: 'data(label)',
      color: '#94a3b8',
      'text-valign': 'bottom',
      'text-margin-y': 8,
      width: 36,
      height: 36,
      'border-width': 2,
      'border-color': '#334155',
      'font-size': '11px',
      'text-wrap': 'wrap',
      'text-max-width': '80px',
    },
  },
  {
    selector: 'node[type="router"]',
    style: { 'background-color': '#0e7490', 'border-color': '#22d3ee', shape: 'rectangle' },
  },
  {
    selector: 'node[type="subnet"]',
    style: { 'background-color': '#1e3a5f', 'border-color': '#3b82f6', shape: 'ellipse' },
  },
  {
    selector: 'edge',
    style: { width: 2, 'line-color': '#334155', 'curve-style': 'bezier' },
  },
];

export function TopologyPreview({ configSummary, subnets }: TopologyPreviewProps) {
  const elements = buildElements(configSummary, subnets);

  return (
    <div className="rounded-xl border border-slate-700 overflow-hidden bg-slate-950">
      <div className="px-4 py-2 bg-slate-900 border-b border-slate-700 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-cyan-400" />
        <span className="text-xs font-medium text-slate-300">Network Topology Preview</span>
        <span className="ml-auto text-xs text-slate-500 uppercase tracking-wider">
          {configSummary.routing_protocol}
        </span>
      </div>
      <CytoscapeComponent
        elements={elements}
        stylesheet={stylesheet}
        layout={{ name: 'cose', animate: false } as cytoscape.LayoutOptions}
        style={{ width: '100%', height: '260px' }}
        cy={(cy) => {
          cy.on('add', () => cy.fit(undefined, 24));
        }}
      />
      <div className="px-4 py-2 bg-slate-900 border-t border-slate-700 flex items-center gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 bg-cyan-800 border border-cyan-400 rounded-sm" />
          Routers ({configSummary.routers})
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 bg-blue-900 border border-blue-400 rounded-full" />
          Subnets ({configSummary.subnets_count})
        </span>
      </div>
    </div>
  );
}
