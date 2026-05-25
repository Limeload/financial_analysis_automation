"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { wsUrl } from "@/lib/api";
import { fmtRelative, eventLabel, sentimentColor } from "@/lib/utils";
import { EVENT_TYPES, type EventType } from "@/lib/types";
import Card from "@/components/shared/Card";
import Badge, { sentimentVariant } from "@/components/shared/Badge";
import { Radio, CircleDot, XCircle } from "lucide-react";

interface StreamEntry {
  id: string;
  article_id?: number;
  ticker?: string;
  company_name?: string;
  sentiment?: string;
  sentiment_score?: number;
  event_type?: string;
  event_confidence?: number;
  title?: string;
  reason?: string;
  ts: string;
}

type ConnStatus = "disconnected" | "connecting" | "connected" | "error";

export default function StreamPage() {
  const [entries, setEntries] = useState<StreamEntry[]>([]);
  const [status, setStatus] = useState<ConnStatus>("disconnected");
  const [filterTicker, setFilterTicker] = useState("");
  const [filterEvent, setFilterEvent] = useState<EventType | "">("");
  const [paused, setPaused] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pausedRef = useRef(false);

  pausedRef.current = paused;

  const connect = useCallback(() => {
    const params = new URLSearchParams();
    if (filterTicker) params.set("ticker", filterTicker.toUpperCase());
    if (filterEvent) params.set("event_type", filterEvent);

    const url = wsUrl(`/analysis/stream?${params.toString()}`);
    if (!url) return;

    setStatus("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setStatus("connected");
    ws.onclose = () => setStatus("disconnected");
    ws.onerror = () => setStatus("error");
    ws.onmessage = (e) => {
      if (pausedRef.current) return;
      try {
        const data = JSON.parse(e.data);
        const entry: StreamEntry = {
          id: `${Date.now()}-${Math.random()}`,
          ts: new Date().toISOString(),
          ...data,
        };
        setEntries((prev) => [entry, ...prev].slice(0, 200));
      } catch {}
    };
  }, [filterTicker, filterEvent]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setStatus("disconnected");
  }, []);

  useEffect(() => () => { wsRef.current?.close(); }, []);

  const statusColor: Record<ConnStatus, string> = {
    disconnected: "text-muted",
    connecting:   "text-warn animate-pulse2",
    connected:    "text-pos",
    error:        "text-neg",
  };

  return (
    <div className="flex h-full flex-col p-6 gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-primary">Live Feed</h1>
          <p className="mt-0.5 text-sm text-muted">Real-time analysis stream via WebSocket</p>
        </div>
        <div className="flex items-center gap-2">
          <CircleDot className={`h-3.5 w-3.5 ${statusColor[status]}`} />
          <span className={`text-xs font-medium ${statusColor[status]}`}>{status}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          placeholder="Ticker filter (e.g. AAPL)"
          value={filterTicker}
          onChange={(e) => setFilterTicker(e.target.value)}
          disabled={status === "connected"}
          className="h-8 w-40 rounded-lg border border-line bg-raised px-3 text-xs text-primary placeholder:text-muted uppercase focus:border-accent focus:outline-none disabled:opacity-50"
        />
        <select
          value={filterEvent}
          onChange={(e) => setFilterEvent(e.target.value as EventType | "")}
          disabled={status === "connected"}
          className="h-8 rounded-lg border border-line bg-raised px-2 text-xs text-primary focus:border-accent focus:outline-none disabled:opacity-50"
        >
          <option value="">All event types</option>
          {EVENT_TYPES.map((t) => <option key={t} value={t}>{eventLabel(t)}</option>)}
        </select>

        {status === "disconnected" || status === "error" ? (
          <button onClick={connect} className="h-8 rounded-lg bg-accent px-3 text-xs font-medium text-white hover:bg-accent-hover transition-colors">
            Connect
          </button>
        ) : (
          <button onClick={disconnect} className="h-8 rounded-lg border border-neg/30 bg-neg/10 px-3 text-xs font-medium text-neg hover:bg-neg/20 transition-colors">
            Disconnect
          </button>
        )}

        {status === "connected" && (
          <button
            onClick={() => setPaused((p) => !p)}
            className="h-8 rounded-lg border border-line px-3 text-xs font-medium text-secondary hover:text-primary transition-colors"
          >
            {paused ? "Resume" : "Pause"}
          </button>
        )}

        {entries.length > 0 && (
          <button onClick={() => setEntries([])} className="h-8 rounded-lg border border-line px-3 text-xs font-medium text-muted hover:text-secondary transition-colors">
            Clear
          </button>
        )}
      </div>

      {/* Stream */}
      <div className="flex-1 overflow-y-auto space-y-2 min-h-0">
        {entries.length === 0 && (
          <div className="flex flex-col items-center justify-center h-48 gap-2">
            <Radio className="h-8 w-8 text-muted" />
            <p className="text-sm text-secondary">
              {status === "connected" ? "Waiting for events…" : "Connect to start streaming"}
            </p>
          </div>
        )}

        {entries.map((e) => (
          <Card key={e.id} className="animate-fade-in hover:border-subtle transition-colors">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                {e.title && <p className="text-xs font-medium text-primary leading-snug">{e.title}</p>}
                {e.reason && <p className="mt-1 text-xs text-secondary">{e.reason}</p>}
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  {e.ticker && <Badge variant="accent">{e.ticker}</Badge>}
                  {e.company_name && !e.ticker && <Badge variant="muted">{e.company_name}</Badge>}
                  {e.sentiment && <Badge variant={sentimentVariant(e.sentiment)}>{e.sentiment}</Badge>}
                  {e.event_type && <Badge variant="info">{eventLabel(e.event_type)}</Badge>}
                  <span className="text-2xs text-muted">{fmtRelative(e.ts)}</span>
                </div>
              </div>
              {e.sentiment_score != null && (
                <span className={`text-sm font-bold ${sentimentColor(e.sentiment ?? "")}`}>
                  {e.sentiment_score > 0 ? "+" : ""}{e.sentiment_score.toFixed(2)}
                </span>
              )}
              {e.event_confidence != null && (
                <span className="text-xs text-muted">{(e.event_confidence * 100).toFixed(0)}%</span>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
