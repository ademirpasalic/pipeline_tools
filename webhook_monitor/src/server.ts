/**
 * Pipeline Webhook Monitor
 * 
 * A real-time web dashboard for monitoring pipeline events —
 * publish notifications, render callbacks, delivery confirmations,
 * and status updates from production tracking systems.
 * 
 * Built with TypeScript, Express, and Server-Sent Events.
 * 
 * Usage:
 *   npm install
 *   npm run build
 *   npm start
 * 
 * Then open http://localhost:3000
 * 
 * Send test events:
 *   curl -X POST http://localhost:3000/api/webhook \
 *     -H "Content-Type: application/json" \
 *     -d '{"source": "shotgrid", "event": "publish.complete", "data": {"asset": "hero_rig_v012", "artist": "jane"}}'
 * 
 * Author: Ademir Pasalic
 * License: MIT
 */

import express, { Request, Response } from "express";
import path from "path";

// ── Types ──

interface PipelineEvent {
  id: string;
  timestamp: string;
  source: string;
  event: string;
  severity: Severity;
  data: Record<string, unknown>;
}

type Severity = "info" | "warning" | "error" | "success";

interface WebhookPayload {
  source: string;
  event: string;
  severity?: Severity;
  data?: Record<string, unknown>;
}

interface EventFilter {
  source?: string;
  severity?: Severity;
  search?: string;
}

interface EventStats {
  total: number;
  bySeverity: Record<Severity, number>;
  bySource: Record<string, number>;
  recentPerMinute: number;
}

// ── Event Store ──

class EventStore {
  private events: PipelineEvent[] = [];
  private readonly maxEvents: number = 1000;
  private listeners: Set<(event: PipelineEvent) => void> = new Set();

  add(payload: WebhookPayload): PipelineEvent {
    // Cap data payload to avoid memory bloat from oversized objects
    let data = payload.data || {};
    if (JSON.stringify(data).length > 10_000) {
      data = { _truncated: true, reason: "payload exceeded 10KB" };
    }

    const event: PipelineEvent = {
      id: this.generateId(),
      timestamp: new Date().toISOString(),
      source: payload.source || "unknown",
      event: payload.event || "unnamed",
      severity: this.classifySeverity(payload),
      data,
    };

    this.events.unshift(event);

    if (this.events.length > this.maxEvents) {
      this.events = this.events.slice(0, this.maxEvents);
    }

    this.listeners.forEach((listener) => listener(event));
    return event;
  }

  getFiltered(filter: EventFilter): PipelineEvent[] {
    return this.events.filter((e) => {
      if (filter.source && e.source !== filter.source) return false;
      if (filter.severity && e.severity !== filter.severity) return false;
      if (filter.search) {
        const term = filter.search.toLowerCase();
        const searchable = `${e.source} ${e.event} ${JSON.stringify(e.data)}`.toLowerCase();
        if (!searchable.includes(term)) return false;
      }
      return true;
    });
  }

  getStats(): EventStats {
    const now = Date.now();
    const oneMinuteAgo = now - 60_000;

    const stats: EventStats = {
      total: this.events.length,
      bySeverity: { info: 0, warning: 0, error: 0, success: 0 },
      bySource: {},
      recentPerMinute: 0,
    };

    for (const event of this.events) {
      stats.bySeverity[event.severity]++;
      stats.bySource[event.source] = (stats.bySource[event.source] || 0) + 1;

      if (new Date(event.timestamp).getTime() > oneMinuteAgo) {
        stats.recentPerMinute++;
      }
    }

    return stats;
  }

  subscribe(listener: (event: PipelineEvent) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private classifySeverity(payload: WebhookPayload): Severity {
    if (payload.severity) return payload.severity;

    const eventName = payload.event?.toLowerCase() || "";

    if (eventName.includes("error") || eventName.includes("fail")) return "error";
    if (eventName.includes("warning") || eventName.includes("timeout")) return "warning";
    if (eventName.includes("complete") || eventName.includes("success") || eventName.includes("publish")) return "success";
    return "info";
  }

  private generateId(): string {
    return `evt_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
  }
}

// ── Server ──

const app = express();
const store = new EventStore();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// Webhook endpoint — receives events from external systems
app.post("/api/webhook", (req: Request, res: Response) => {
  const payload = req.body as WebhookPayload;

  if (!payload.source?.trim() || !payload.event?.trim()) {
    res.status(400).json({ error: "Missing required fields: source, event" });
    return;
  }

  if (payload.source.length > 100 || payload.event.length > 200) {
    res.status(400).json({ error: "Field length exceeded (source: 100, event: 200)" });
    return;
  }

  const event = store.add(payload);
  res.status(201).json({ received: true, id: event.id });
});

// Get events with optional filtering
app.get("/api/events", (req: Request, res: Response) => {
  const filter: EventFilter = {
    source: req.query.source as string | undefined,
    severity: req.query.severity as Severity | undefined,
    search: req.query.search as string | undefined,
  };

  res.json(store.getFiltered(filter));
});

// Get aggregate stats
app.get("/api/stats", (_req: Request, res: Response) => {
  res.json(store.getStats());
});

// Server-Sent Events — real-time stream
app.get("/api/stream", (req: Request, res: Response) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  const unsubscribe = store.subscribe((event: PipelineEvent) => {
    // res.write() returns false on backpressure/closed connection
    if (!res.write(`data: ${JSON.stringify(event)}\n\n`)) {
      unsubscribe();
    }
  });

  req.on("close", unsubscribe);
  req.on("error", unsubscribe);
});

// ── Dashboard ──

app.use(express.static(path.join(__dirname, "..", "public")));

// ── Start ──

app.listen(PORT, () => {
  console.log(`\n  ▶ Pipeline Webhook Monitor\n  Listening on http://localhost:${PORT}\n`);
  console.log(`  Send test events:\n  curl -X POST http://localhost:${PORT}/api/webhook \\\n    -H "Content-Type: application/json" \\\n    -d '{"source": "shotgrid", "event": "publish.complete", "data": {"asset": "hero_rig_v012"}}'`);
  console.log();
});
