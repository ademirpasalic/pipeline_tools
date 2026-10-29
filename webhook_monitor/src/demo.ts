/**
 * Demo script — sends realistic pipeline events to the webhook monitor.
 * Run after starting the server: npm run demo
 */

const BASE = process.env.URL || "http://localhost:3000";

interface DemoEvent {
  source: string;
  event: string;
  severity?: string;
  data: Record<string, unknown>;
}

const sampleEvents: DemoEvent[] = [
  { source: "shotgrid", event: "shot.status_changed", data: { shot: "SH0120", from: "ip", to: "review", artist: "alex" } },
  { source: "shotgrid", event: "publish.complete", severity: "success", data: { asset: "hero_rig_v012.ma", artist: "kim", project: "forest_tales" } },
  { source: "render_farm", event: "job.complete", severity: "success", data: { job_id: "RF-8821", frames: "1001-1048", duration: "2h14m" } },
  { source: "render_farm", event: "job.warning", severity: "warning", data: { job_id: "RF-8834", message: "3 frames exceeded memory limit, retrying" } },
  { source: "file_delivery", event: "package.sent", severity: "success", data: { client: "Client A", package: "ep12_final_v003", files: 47 } },
  { source: "validator", event: "asset.validation_failed", severity: "error", data: { asset: "bg_forest_v008.psd", errors: ["naming convention", "missing metadata"] } },
  { source: "validator", event: "asset.validation_passed", severity: "success", data: { asset: "hero_rig_v012.ma", checks: 14 } },
  { source: "git", event: "push", data: { repo: "studio-pipeline", branch: "main", commits: 3, author: "ademir" } },
  { source: "docker", event: "build.complete", severity: "success", data: { image: "pipeline-tools:2.1.4", size: "342MB" } },
  { source: "docker", event: "build.failed", severity: "error", data: { image: "maya-env:2024.1", error: "pip install timeout" } },
  { source: "shotgrid", event: "task.assigned", data: { task: "anim", shot: "SH0145", artist: "sam", due: "2025-03-20" } },
  { source: "render_farm", event: "job.started", data: { job_id: "RF-8842", scene: "SH0120_comp_v004.nk", priority: "high" } },
  { source: "file_delivery", event: "ingest.complete", severity: "success", data: { source: "Client B", files: 23, destination: "/projects/demo_show/incoming/" } },
  { source: "shotgrid", event: "version.new", data: { entity: "SH0120", version: "v008", type: "comp", artist: "alex" } },
  { source: "ci_cd", event: "pipeline.deploy", severity: "success", data: { tool: "asset_validator", version: "1.3.0", env: "production" } },
  { source: "validator", event: "scene.error", severity: "error", data: { scene: "SH0145_layout.ma", errors: ["unknown nodes", "missing references"] } },
  { source: "render_farm", event: "job.complete", severity: "success", data: { job_id: "RF-8842", frames: "1001-1120", duration: "4h02m" } },
  { source: "file_delivery", event: "package.ready", data: { client: "Client C", package: "trailer_v001", size: "12.4GB" } },
];

async function sendEvent(event: DemoEvent): Promise<void> {
  try {
    const res = await fetch(`${BASE}/api/webhook`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(event),
    });
    const data = await res.json();
    console.log(`  ✓ [${event.source}] ${event.event} → ${(data as { id: string }).id}`);
  } catch {
    console.error(`  ✗ Failed to send event — is the server running?`);
    process.exit(1);
  }
}

async function main(): Promise<void> {
  console.log(`\n  ▶ Sending ${sampleEvents.length} demo events to ${BASE}\n`);

  for (const event of sampleEvents) {
    await sendEvent(event);
    await new Promise((r) => setTimeout(r, 400 + Math.random() * 600));
  }

  console.log(`\n  Done! Open ${BASE} to see the dashboard.\n`);
}

main();
