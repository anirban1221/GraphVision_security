import React, { useState, useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';

export default function App() {
  const [wsConnected, setWsConnected] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(5.0);
  const [windowSpan, setWindowSpan] = useState(300);

  const [stats, setStats] = useState({
    total_processed: 0,
    fraud_blocked_count: 0,
    dollars_saved: 0.0,
    active_rings_count: 0,
  });

  const [transactions, setTransactions] = useState([]);
  const [activeRings, setActiveRings] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);

  const wsRef = useRef(null);
  const cyRef = useRef(null);

  useEffect(() => {
    if (!cyRef.current) {
      const cy = cytoscape({
        container: document.getElementById('cy-canvas'),
        style: [
          {
            selector: 'node[type = "card"]',
            style: {
              'background-color': '#3B82F6',
              'label': 'data(label)',
              'color': '#93C5FD',
              'font-size': '9px',
              'text-valign': 'bottom',
              'text-margin-y': 4,
              'width': 18,
              'height': 18,
              'border-width': 2,
              'border-color': '#1D4ED8'
            }
          },
          {
            selector: 'node[type = "device"]',
            style: {
              'shape': 'round-rectangle',
              'background-color': '#8B5CF6',
              'label': 'data(label)',
              'color': '#C4B5FD',
              'font-size': '8px',
              'text-valign': 'bottom',
              'text-margin-y': 4,
              'width': 22,
              'height': 22,
              'border-width': 2,
              'border-color': '#6D28D9'
            }
          },
          {
            selector: 'node[is_alert = true]',
            style: {
              'background-color': '#EF4444',
              'border-color': '#FCA5A5',
              'border-width': 3,
              'color': '#F87171',
              'width': 26,
              'height': 26,
              'shadow-blur': 12,
              'shadow-color': '#EF4444'
            }
          },
          {
            selector: 'edge',
            style: {
              'width': 1.5,
              'line-color': '#374151',
              'curve-style': 'bezier',
              'opacity': 0.6
            }
          },
          {
            selector: 'edge[is_alert = true]',
            style: {
              'width': 2.5,
              'line-color': '#EF4444',
              'opacity': 0.9
            }
          }
        ],
        layout: { name: 'cose', animate: false }
      });

      cy.on('tap', 'node', (evt) => {
        setSelectedNode(evt.target.data());
      });

      cyRef.current = cy;
    }
  }, []);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/stream');
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'TRANSACTION_EVENT') {
        const tx = msg.transaction;
        const delta = msg.graph_delta;
        if (msg.stats) setStats(prev => ({ ...prev, ...msg.stats }));
        setTransactions(prev => [tx, ...prev.slice(0, 49)]);

        if (cyRef.current && delta) {
          if (delta.new_nodes) delta.new_nodes.forEach(n => {
            if (!cyRef.current.getElementById(n.id).length) cyRef.current.add({ group: 'nodes', data: n });
          });
          if (delta.new_edges) delta.new_edges.forEach(e => {
            if (!cyRef.current.getElementById(e.id).length) cyRef.current.add({ group: 'edges', data: e });
          });
          if (delta.rings) setActiveRings(delta.rings);
        }
      }
    };

    return () => ws.close();
  }, []);

  const togglePlay = () => {
    const next = !isPlaying;
    setIsPlaying(next);
    wsRef.current?.send(JSON.stringify({ command: next ? 'play' : 'pause' }));
  };

  return (
    <div className="flex flex-col h-screen bg-[#0B0F19] text-gray-100">
      <header className="h-14 bg-[#111827] border-b border-gray-800 px-4 flex items-center justify-between">
        <h1 className="text-sm font-bold text-white flex items-center gap-2">
          ⚡ RAZORPAY SENTINEL AI <span className="text-xs bg-indigo-900/50 text-indigo-300 px-2 py-0.5 rounded border border-indigo-700">VITE REACT</span>
        </h1>
        <div className="flex items-center gap-2">
          <button onClick={togglePlay} className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 rounded text-xs font-semibold text-white">
            {isPlaying ? '⏸ Pause' : '▶ Play'}
          </button>
          <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'}`} />
        </div>
      </header>
      <div className="flex-1 flex">
        <div id="cy-canvas" className="flex-1 w-full h-full bg-[#0B0F19]" />
      </div>
    </div>
  );
}

