import { useState, useCallback } from 'react';

export interface Node {
  id: string;
  label: string;
  type: 'host' | 'router' | 'switch';
}

export interface Link {
  source: string;
  target: string;
  bandwidth: number;
  delay: number;
}

export const useNetworkSimulation = () => {
  const [nodes, setNodes] = useState<Node[]>([
    { id: '1', label: 'Host A', type: 'host' },
    { id: '2', label: 'Router 1', type: 'router' },
    { id: '3', label: 'Host B', type: 'host' },
  ]);

  const [links, setLinks] = useState<Link[]>([
    { source: '1', target: '2', bandwidth: 100, delay: 10 },
    { source: '2', target: '3', bandwidth: 100, delay: 10 },
  ]);

  const [isSimulating, setIsSimulating] = useState(false);

  const startSimulation = useCallback(() => setIsSimulating(true), []);
  const stopSimulation = useCallback(() => setIsSimulating(false), []);

  const addNode = useCallback((node: Node) => {
    setNodes((prev) => [...prev, node]);
  }, []);

  const addLink = useCallback((link: Link) => {
    setLinks((prev) => [...prev, link]);
  }, []);

  return {
    nodes,
    links,
    isSimulating,
    startSimulation,
    stopSimulation,
    addNode,
    addLink,
  };
};
