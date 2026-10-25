"use client";

import { useCallback, useMemo, useState } from "react";
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, BriefcaseBusiness,
  Check, CheckCircle2, ChevronDown, CircleDot, ClipboardCheck, Clock3, Cloud,
  Database, FileCheck2, FileSearch, Fingerprint, GitBranch, LayoutDashboard,
  Menu, Play, Plus, RefreshCw, Search, ShieldAlert, ShieldCheck, Sparkles,
  TrendingUp, UserCheck, Workflow, X, AlertTriangle, ChevronRight,
} from "lucide-react";

type Event = { event_type: string; actor: string; details: Record<string, unknown>; created_at: string };
type WorkflowData = { workflow_id: string; customer_id: string; status: string; current_step: string; events: Event[] };
type ApiFailure = { detail?: string };
type Overview = { active_workflows: number; pending_reviews: number; discrepancy_findings: number; reviewed_handoffs: number; total_workflows: number };
type ReviewQueueItem = { handoff_id: string; workflow_id: string; customer_name: string; status: string; current_step: string; summary: string; created_at: string; findings: Array<Record<string, unknown>> };
type InsuranceFinding = { status?: string; coverage_type?: string; explanation?: string; policy_limit?: string; required_limit?: string; policy_evidence?: { document_id: string; page: number; excerpt: string } | null; requirement_evidence?: { document_id: string; page: number; excerpt: string } };

type ActivityItem = { title: string; subtitle: string; time: string; icon: "ok" | "review" | "activity" };

const sampleActivity: ActivityItem[] = [
  { title: "Policy evaluation flagged for review", subtitle: "Northstar Logistics · GL liability", time: "10:42 AM", icon: "review" },
  { title: "Coverage comparison completed", subtitle: "Limit discrepancy · $1M vs $2M", time: "10:41 AM", icon: "ok" },
  { title: "Policy data validated", subtitle: "Northstar Logistics · Policy Agent", time: "10:40 AM", icon: "ok" },
  { title: "Customer resubmission processed", subtitle: "Northstar Logistics · Intake", time: "Yesterday", icon: "activity" },
];

function pretty(value: string) { return value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()); }
function shortId(value?: string) { return value ? `${value.slice(0, 8)}…` : "—"; }
function fmtTime(value?: string) { if (!value) return "—"; const d = new Date(value); return Number.isNaN(d.getTime()) ? value : d.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); }
function eventText(event: Event) {
  const descriptions: Record<string, string> = {
    workflow_created: "Customer workflow created",
    onboarding_evaluated: "Onboarding agent evaluated intake",
    handoff_reviewed: "Human specialist submitted review",
    customer_intake_resubmitted: "Customer resubmitted intake",
    insurance_agent_completed: "Insurance agent produced analysis",
    insurance_review_requested: "Insurance specialist review requested",
  };
  return descriptions[event.event_type] || pretty(event.event_type);
}

export default function Dashboard() {
  const [view, setView] = useState<"overview" | "workflows" | "agents" | "reviews">("overview");
  const [mode, setMode] = useState<"demo" | "live">("demo");
  const [workflowIdInput, setWorkflowIdInput] = useState("");
  const [workflow, setWorkflow] = useState<WorkflowData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [companyName, setCompanyName] = useState("Northstar Logistics");
  const [industry, setIndustry] = useState("Logistics");
  const [reviewer, setReviewer] = useState("advisor-demo-001");
  const [reviewNotes, setReviewNotes] = useState("Reviewed the supplied evidence and requested corrections.");
  const [executionIndustry, setExecutionIndustry] = useState("");
  const [selectedDecision, setSelectedDecision] = useState<"approve" | "request_changes" | "reject">("request_changes");
  const [showSidebar, setShowSidebar] = useState(false);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [policyLimit, setPolicyLimit] = useState("1000000");
  const [requiredLimit, setRequiredLimit] = useState("2000000");
  const [selectedEvidence, setSelectedEvidence] = useState<InsuranceFinding | null>(null);

  async function api<T>(route: string, payload?: unknown): Promise<T> {
    const response = await fetch(`/api/coverage/${route}`, {
      method: payload === undefined ? "GET" : "POST",
      headers: payload === undefined ? undefined : { "Content-Type": "application/json" },
      body: payload === undefined ? undefined : JSON.stringify(payload),
      cache: "no-store",
    });
    const body: T | ApiFailure = await response.json().catch(() => ({ detail: "Invalid server response" }));
    if (!response.ok) throw new Error((body as ApiFailure).detail || `Request failed (${response.status})`);
    return body as T;
  }

  const loadOverview = useCallback(async () => {
    try {
      const [summary, reviews] = await Promise.all([
        api<Overview>("dashboard/overview"),
        api<ReviewQueueItem[]>("dashboard/reviews"),
      ]);
      setOverview(summary);
      setQueue(reviews);
    } catch (e) {
      setOverview(null);
      setQueue([]);
      setError(e instanceof Error ? e.message : "Overview API is unavailable. Install the backend extension.");
    }
  }, []);

  const loadWorkflow = useCallback(async (id: string, quietly = false) => {
    if (!id.trim()) { setError("Enter a workflow UUID to load live data."); return; }
    if (!quietly) setBusy(true);
    setError(""); setMessage("");
    try {
      const result = await api<WorkflowData>(`workflows/${encodeURIComponent(id.trim())}`);
      setWorkflow(result);
      setWorkflowIdInput(result.workflow_id);
      await loadOverview();
      setMode("live");
      if (!quietly) setMessage("Live workflow loaded successfully.");
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to load workflow."); }
    finally { setBusy(false); }
  }, [loadOverview]);

  async function createWorkflow() {
    setBusy(true); setError(""); setMessage("");
    try {
      const created = await api<{ workflow_id: string }>("onboarding", { company_name: companyName.trim(), industry: industry.trim() });
      setShowCreate(false); await loadWorkflow(created.workflow_id);
      setMessage("Customer onboarding created. You can now execute the onboarding agent.");
      setView("workflows");
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to create onboarding."); }
    finally { setBusy(false); }
  }

  async function executeOnboarding() {
    if (!workflow) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await api(`workflows/${workflow.workflow_id}/execute`, {
        company_name: companyName,
        ...(executionIndustry.trim() ? { industry: executionIndustry.trim() } : {}),
      });
      await loadWorkflow(workflow.workflow_id, true);
      setMessage("Onboarding executed; workflow refreshed.");
    } catch (e) { setError(e instanceof Error ? e.message : "Execution failed."); }
    finally { setBusy(false); }
  }

  async function executePolicyReview() {
    if (!workflow) return;
    if (!/^\d+(\.\d+)?$/.test(policyLimit) || !/^\d+(\.\d+)?$/.test(requiredLimit)) {
      setError("Enter valid nonnegative numeric insurance limits."); return;
    }
    if (!window.confirm("Run a SYNTHETIC policy comparison and record the findings against this workflow?")) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const payload = {
        policy: {
          policy_number: "SYNTHETIC-GL-001", insured_name: companyName || "Synthetic customer",
          carrier: "Fictional Insurance Co.", effective_date: "2026-10-01", expiration_date: "2027-10-01",
          limits: [{ coverage_type: "general_liability", limit_amount: policyLimit, currency: "USD",
            evidence: { document_id: "synthetic-policy-001", page: 1, excerpt: `Synthetic occurrence limit: $${policyLimit}` } }]
        },
        requirements: [{ coverage_type: "general_liability", minimum_limit: requiredLimit, currency: "USD",
          evidence: { document_id: "synthetic-requirements-001", page: 1, excerpt: `Synthetic minimum requirement: $${requiredLimit}` } }]
      };
      await api(`workflows/${workflow.workflow_id}/policy-review`, payload);
      await loadWorkflow(workflow.workflow_id, true);
      setMessage("Insurance agents executed and their findings were saved to PostgreSQL.");
    } catch (e) { setError(e instanceof Error ? e.message : "Policy review failed."); }
    finally { setBusy(false); }
  }

  const handoffId = useMemo(() => {
    if (!workflow) return "";
    for (const event of [...workflow.events].reverse()) {
      if (!(["insurance_review_requested", "onboarding_evaluated", "handoff_created"].includes(event.event_type))) continue;
      const id = event.details?.handoff_id;
      if (typeof id === "string") return id;
    }
    return "";
  }, [workflow]);

  async function submitReview() {
    if (!handoffId || !workflow || !awaitingSpecialist) { setError("This workflow is not awaiting a specialist decision."); return; }
    setBusy(true); setError(""); setMessage("");
    try {
      await api(`handoffs/${handoffId}/review`, {
        reviewer_id: reviewer.trim(), decision: selectedDecision, notes: reviewNotes.trim(),
      });
      await loadWorkflow(workflow.workflow_id, true);
      await loadOverview();
      setMessage("Human review saved with an audit event.");
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to submit review."); }
    finally { setBusy(false); }
  }

  const awaitingSpecialist = workflow?.status === "needs_review" &&
    ["insurance_review", "human_review", "onboarding_review", "intake_review"].includes(workflow.current_step);
  const awaitingCustomer = workflow?.current_step === "awaiting_customer";
  const reviewHistory = useMemo(() => (workflow?.events ?? []).filter(e => e.event_type === "handoff_reviewed")
    .map(e => ({ reviewer: e.actor, decision: String(e.details?.decision ?? ""), notes: String(e.details?.notes ?? ""), time: e.created_at, handoff: String(e.details?.handoff_id ?? "") })).reverse(), [workflow]);
  const events = useMemo(() => workflow ? [...workflow.events].reverse() : [], [workflow]);
  const insuranceEvents = events.filter(e => e.event_type === "insurance_agent_completed");
  const liveFindings: InsuranceFinding[] = insuranceEvents.flatMap((e) => {
    const output = (e.details as { output?: { findings?: InsuranceFinding[] } }).output;
    return output?.findings ?? [];
  });
  const liveReviewEvents = events.filter(e => e.event_type === "insurance_review_requested" || e.event_type === "handoff_reviewed");
  const showDemo = mode === "demo";
  const displayStatus = showDemo ? "Needs review" : workflow ? pretty(workflow.status) : "Not loaded";
  const nav = [
    { id: "overview" as const, label: "Overview", icon: LayoutDashboard },
    { id: "workflows" as const, label: "Workflows", icon: Workflow },
    { id: "agents" as const, label: "AI Agents", icon: Sparkles },
    { id: "reviews" as const, label: "Human Reviews", icon: ClipboardCheck },
  ];

  return <div className="shell">
    <aside className={`sidebar ${showSidebar ? "mobile-visible" : ""}`}>
      <div className="brand"><div className="brand-mark"><ShieldCheck size={22}/></div><div><div className="brand-title">coverage<span>ops</span><span className="ai">AI</span></div><div className="brand-sub">AGENT CONTROL CENTER</div></div></div>
      <div className="workspace-switch"><div className="workspace-avatar">C</div><div><strong>CoverageOps Workspace</strong><span>Insurance Operations</span></div><ChevronDown size={15}/></div>
      <div className="side-label">WORKSPACE</div>
      <nav>{nav.map(item => <button key={item.id} onClick={() => {setView(item.id); setShowSidebar(false);}} className={`nav-item ${view === item.id ? "active" : ""}`}><item.icon size={19}/>{item.label}{item.id === "reviews" && <span className="nav-count">{showDemo ? "3" : overview ? String(overview.pending_reviews) : "—"}</span>}</button>)}</nav>
      <div className="side-label secondary-label">PLATFORM</div>
      <div className="nav-item muted"><Database size={19}/>System Health <span className="health-unknown">Not verified</span></div>
      <div className="nav-item muted"><GitBranch size={19}/>Agent Orchestrator</div>
      <div className="sidebar-bottom"><div className="environment"><span className="pulse-dot"/>Local development <span className="env-tag">DEV</span></div><div className="sidebar-help"><Sparkles size={17}/><div><strong>Evidence-first AI</strong><p>Human oversight by design.</p></div></div></div>
    </aside>

    <main className="main-area">
      <div className="topbar"><button className="icon-only mobile-menu" aria-label="Open navigation" onClick={() => setShowSidebar(!showSidebar)}><Menu size={21}/></button><div className="crumb">Workspace <ChevronRight size={14}/> <strong>{nav.find(n => n.id === view)?.label}</strong></div><div className="top-actions"><div className="top-date">Synthetic insurance sandbox</div><div className="top-divider"/><div className="avatar">ZM</div></div></div>
      <div className="content">
        <div className="heading-row"><div><div className="eyebrow"><span className="eyebrow-line"/>INSURANCE INTELLIGENCE PLATFORM</div><h1>{view === "overview" ? "Operations Overview" : view === "workflows" ? "Workflow Explorer" : view === "agents" ? "AI Agent Performance" : "Human Review Center"}</h1><p className="subtitle">Monitor agents, investigate coverage findings, and keep humans in control.</p></div><div className="heading-buttons"><button className="button secondary" onClick={() => { if (workflow) loadWorkflow(workflow.workflow_id); else if (mode === "live") loadOverview(); }} disabled={busy}><RefreshCw size={16} className={busy ? "spin" : ""}/> Refresh</button><button className="button primary" onClick={() => {setMode("live"); setShowCreate(true);}}><Plus size={17}/> New workflow</button></div></div>

        <div className="connect-strip"><div className="strip-title"><span className={`indicator ${showDemo ? "amber" : "green"}`}/><span>{showDemo ? "DEMO PREVIEW" : "LIVE BACKEND"}</span></div><div className="strip-copy">{showDemo ? "Illustrative data — not sourced from PostgreSQL. Connect to your FastAPI workflow below." : `${workflow ? `Loaded workflow ${shortId(workflow.workflow_id)} · data from FastAPI` : "Live mode · load a workflow to see its agent events"}`}</div><div className="mode-switch"><button className={mode === "demo" ? "chosen" : ""} onClick={() => {setMode("demo");setError("");}}>Demo</button><button className={mode === "live" ? "chosen" : ""} onClick={() => {setMode("live");setError("");void loadOverview();}}>Live</button></div></div>
        {mode === "live" && <div className="live-connect"><div className="live-input-wrap"><Search size={17}/><input aria-label="Workflow UUID" placeholder="Paste your CoverageOps workflow UUID…" value={workflowIdInput} onChange={e => setWorkflowIdInput(e.target.value)} onKeyDown={e => {if (e.key === "Enter") loadWorkflow(workflowIdInput);}}/></div><button className="button secondary" onClick={() => loadWorkflow(workflowIdInput)} disabled={busy}>Load workflow <ArrowRight size={16}/></button></div>}
        {error && <div role="alert" className="flash error"><AlertTriangle size={17}/>{error}<button aria-label="Dismiss error" onClick={() => setError("")}><X size={16}/></button></div>}
        {message && <div className="flash success"><CheckCircle2 size={17}/>{message}<button aria-label="Dismiss message" onClick={() => setMessage("")}><X size={16}/></button></div>}

        <section className="metrics">
          <Metric icon={Workflow} label="Active workflows" value={showDemo ? "24" : overview ? String(overview.active_workflows) : "—"} trend={showDemo ? "Illustrative sample" : "Across PostgreSQL workflows"}/>
          <Metric icon={Sparkles} label="Recorded agent events" value={showDemo ? "1,284" : workflow ? String(insuranceEvents.length) : "—"} trend={showDemo ? "Illustrative sample" : "Selected workflow only"}/>
          <Metric icon={ShieldAlert} label="Pending human reviews" value={showDemo ? "03" : overview ? String(overview.pending_reviews) : "—"} trend={showDemo ? "Illustrative sample" : "Across PostgreSQL workflows"} attention/>
          <Metric icon={FileSearch} label="Awaiting customer" value={showDemo ? "—" : awaitingCustomer ? "1" : "0"} trend={showDemo ? "Illustrative sample" : "Saved insurance handoff findings"} attention/>
        </section>

        <div className="columns-main">
          <section className="panel pipeline-panel"><div className="panel-heading"><div><div className="small-eyebrow">WORKFLOW INTELLIGENCE</div><h2>{view === "agents" ? "Agent Execution Pipeline" : "Insurance Analysis Pipeline"}</h2><p>Traceable decisions at every stage of the policy review.</p></div><span className="chip"><CircleDot size={13}/> {showDemo ? "Demo run" : "Live workflow"}</span></div>
            <div className="pipeline">
              <PipelineStep number="01" icon={FileSearch} name="Policy Agent" detail="Validate terms & source evidence" status={showDemo ? "complete" : insuranceEvents.some(e => e.actor === "policy") ? "complete" : "idle"}/>
              <div className="pipeline-line"/>
              <PipelineStep number="02" icon={GitBranch} name="Coverage Comparison" detail="Evaluate requirements vs. policy" status={showDemo ? "complete" : insuranceEvents.some(e => e.actor === "coverage_comparison") ? "complete" : "idle"}/>
              <div className="pipeline-line"/>
              <PipelineStep number="03" icon={Fingerprint} name="Policy Evaluation" detail="Assess evidence & review flags" status={showDemo ? "review" : insuranceEvents.some(e => e.actor === "policy_evaluation") ? "complete" : "idle"}/>
              <div className="pipeline-line"/>
              <PipelineStep number="04" icon={UserCheck} name="Human Insurance Advisor" detail="Final specialist intervention" status={showDemo ? "review" : awaitingSpecialist ? "review" : reviewHistory.length ? "complete" : "idle"}/>
            </div>
            <div className="pipeline-note"><ShieldCheck size={17}/><div><strong>Safety by design</strong><span>A numeric limit comparison is not proof of coverage or insurance approval.</span></div></div>
          </section>

          <section className="panel findings-panel"><div className="panel-heading"><div><div className="small-eyebrow">EVIDENCE & RISK</div><h2>Coverage Findings</h2><p>{showDemo ? "Northstar Logistics · Sample GL policy" : `Workflow ${shortId(workflow?.workflow_id)}`}</p></div><span className="chip gold"><ShieldAlert size={13}/> {showDemo ? "1 flag" : `${liveFindings.length} findings`}</span></div>
            {showDemo ? <><div className="finding-flag"><div className="finding-label"><AlertTriangle size={16}/> LIMIT DISCREPANCY</div><h3>General Liability</h3><p>The reported policy limit is below the stated contractual minimum.</p><div className="comparison"><div><span>POLICY LIMIT</span><strong>$1,000,000</strong></div><div className="compare-arrow"><ArrowRight size={21}/></div><div><span>REQUIRED MINIMUM</span><strong>$2,000,000</strong></div></div><div className="gap-row"><span>Numeric shortfall</span><strong>$1,000,000</strong></div></div><div className="evidence"><FileCheck2 size={17}/><div><strong>2 source references</strong><span>Policy document · Contractual requirements</span></div><ChevronRight size={17}/></div></> : <div className="real-findings">{insuranceEvents.length ? insuranceEvents.map((event, i) => {const details = event.details as {output?: {findings?: Array<{status?:string; explanation?:string; policy_limit?:string; required_limit?:string}>}}; const findings = details.output?.findings || []; return <div className="real-event" key={i}><div className="real-event-title"><CheckCircle2 size={16}/>{pretty(event.actor)}</div>{findings.length ? findings.map((f, j) => <div key={j} className="real-finding"><strong>{pretty(f.status || "Finding")}</strong><p>{f.explanation}</p><small>Policy: {f.policy_limit ? Number(f.policy_limit).toLocaleString("en-US", {style:"currency",currency:"USD",maximumFractionDigits:0}) : "N/A"} · Required: {f.required_limit ? Number(f.required_limit).toLocaleString("en-US", {style:"currency",currency:"USD",maximumFractionDigits:0}) : "N/A"}</small><button type="button" className="evidence-link" onClick={() => setSelectedEvidence(f as InsuranceFinding)}>Inspect source evidence <ArrowRight size={13}/></button></div>) : <p>Agent result persisted · {fmtTime(event.created_at)}</p>}</div>;}) : <div className="empty-state"><FileSearch size={28}/><strong>No policy analysis events yet</strong><span>No insurance-agent events are recorded for this selected workflow.</span></div>}</div>}
          </section>
        </div>

        {mode === "live" && <section className="panel queue-panel"><div className="panel-heading"><div><div className="small-eyebrow">PRIORITIZED OPERATIONS</div><h2>Human review queue</h2><p>Unresolved handoffs from PostgreSQL. Select a workflow to investigate and act.</p></div><span className="chip subtle">{overview ? `${overview.pending_reviews} pending` : "Not loaded"}</span></div><div className="queue-list">{queue.length ? queue.map(item => <button type="button" key={item.handoff_id} className="queue-row" onClick={() => {setView("reviews");void loadWorkflow(item.workflow_id);}}><span className="queue-client"><strong>{item.customer_name}</strong><small>{shortId(item.workflow_id)} · {pretty(item.current_step)}</small></span><span className="queue-summary">{item.summary}</span><span className="queue-count">{item.findings.length} findings</span><ArrowRight size={16}/></button>) : <div className="empty-state narrow">{overview ? "No pending reviews." : "Connect the dashboard API to load the review queue."}</div>}</div></section>}
        {view === "reviews" && mode === "live" && workflow && (
          <section className="panel" style={{marginBottom: 24}}>
            <div className="panel-heading"><div><div className="small-eyebrow">CASE MANAGEMENT</div><h2>Specialist Decision History</h2><p>Evidence-backed review decisions for this selected workflow.</p></div><span className="chip subtle">{awaitingCustomer ? "Awaiting customer" : awaitingSpecialist ? "Awaiting specialist" : pretty(workflow.current_step)}</span></div>
            <div className="action-inner">
              <div className="status-line"><span>Workflow</span><strong>{shortId(workflow.workflow_id)}</strong></div>
              <div className="status-line"><span>Completed decisions</span><strong>{reviewHistory.length}</strong></div>
              {awaitingCustomer && <div className="info-note"><Clock3 size={17}/> Updated insurance documentation has been requested from the customer. Do not submit a second specialist decision for this completed handoff.</div>}
              {reviewHistory.length ? reviewHistory.map((review, i) => <div className="real-event" key={`${review.handoff}-${i}`} style={{marginTop: 14}}>
                <div className="real-event-title"><UserCheck size={17}/>{pretty(review.decision)}</div>
                <div className="status-line"><span>Reviewer</span><strong>{review.reviewer}</strong></div>
                <div className="status-line"><span>Recorded</span><strong>{fmtTime(review.time)}</strong></div>
                <p>{review.notes || "No notes recorded."}</p>
              </div>) : <div className="empty-state narrow">No completed specialist decisions yet.</div>}
            </div>
          </section>
        )}
        <div className="columns-bottom">
          <section className="panel activity-panel"><div className="panel-heading"><div><div className="small-eyebrow">AUDIT TRAIL</div><h2>Recent Activity</h2></div><span className="chip subtle"><Activity size={14}/> {showDemo ? "Illustrative" : "PostgreSQL events"}</span></div><div className="activity-list">{showDemo ? sampleActivity.map((item, i) => <ActivityRow key={i} {...item}/>) : events.length ? events.slice(0, 7).map((event, i) => <ActivityRow key={i} title={eventText(event)} subtitle={`${event.actor} · ${pretty(event.event_type)}`} time={fmtTime(event.created_at)} icon={event.event_type.includes("review") ? "review" : "ok"}/>) : <div className="empty-state narrow"><Clock3 size={24}/>No workflow events available.</div>}</div></section>
          <section className="panel action-panel"><div className="panel-heading"><div><div className="small-eyebrow">OPERATOR ACTIONS</div><h2>{view === "reviews" ? "Specialist Review" : "Quick Actions"}</h2></div><span className="chip subtle">{showDemo ? "Preview" : "Live"}</span></div>
            {showDemo ? <div className="action-inner"><div className="action-hero"><span className="action-hero-icon"><UserCheck size={22}/></span><strong>Review queue</strong><p>Human approval is required for flagged insurance discrepancies.</p></div><button className="button primary full" onClick={() => {setMode("live");setView("workflows");}}>Connect a real workflow <ArrowRight size={16}/></button><div className="info-note"><Database size={15}/> Actions become available after connecting to FastAPI.</div></div> : workflow ? <div className="action-inner"><div className="status-line"><span>Workflow state</span><strong>{pretty(workflow.status)}</strong></div><div className="status-line"><span>Current step</span><strong>{pretty(workflow.current_step)}</strong></div><div className="status-line"><span>Handoff</span><strong>{shortId(handoffId)}</strong></div>{workflow.status === "pending" && <><label className="form-label" htmlFor="intake-industry">Intake industry (optional: leave blank to test handoff)</label><input id="intake-industry" className="field" value={executionIndustry} onChange={e => setExecutionIndustry(e.target.value)} placeholder="e.g. Logistics"/><button className="button primary full" onClick={executeOnboarding} disabled={busy}><Play size={16}/> Execute onboarding</button></>}{awaitingSpecialist && handoffId && <><label className="form-label" htmlFor="decision">Specialist decision</label><select id="decision" className="field" value={selectedDecision} onChange={e => setSelectedDecision(e.target.value as typeof selectedDecision)}><option value="request_changes">Request changes</option><option value="approve">Approve review</option><option value="reject">Reject</option></select><label className="form-label" htmlFor="reviewer">Reviewer ID</label><input id="reviewer" className="field" value={reviewer} onChange={e => setReviewer(e.target.value)}/><label className="form-label" htmlFor="notes">Review notes</label><textarea id="notes" className="field" value={reviewNotes} onChange={e => setReviewNotes(e.target.value)} rows={3}/><button className="button primary full" onClick={submitReview} disabled={busy}><Check size={16}/> Submit review</button></>}{workflow.status === "running" && workflow.current_step === "policy_review" && <div className="synthetic-action"><strong>Run synthetic insurance analysis</strong><p>Uses validated structured example inputs. Does not extract or verify a PDF.</p><label className="form-label" htmlFor="policyLimit">Policy limit (USD)</label><input id="policyLimit" className="field" inputMode="decimal" value={policyLimit} onChange={e=>setPolicyLimit(e.target.value)}/><label className="form-label" htmlFor="requiredLimit">Contractual minimum (USD)</label><input id="requiredLimit" className="field" inputMode="decimal" value={requiredLimit} onChange={e=>setRequiredLimit(e.target.value)}/><button className="button primary full" onClick={executePolicyReview} disabled={busy}><Play size={16}/> Run policy agents</button></div>}{workflow.status !== "pending" && !awaitingSpecialist && !(workflow.status === "running" && workflow.current_step === "policy_review") && <div className="info-note"><CheckCircle2 size={16}/> No supported action is available for this workflow state.</div>}</div> : <div className="empty-state"><Cloud size={28}/><strong>Connect a workflow</strong><span>Enter a workflow UUID to load live data and actions.</span></div>}
          </section>
        </div>
        <footer className="footer"><span>CoverageOps AI · Independent synthetic demonstration</span><span>Designed for traceability · No real insurance decisions</span></footer>
      </div>
    </main>

    {selectedEvidence && <div className="overlay" onClick={() => setSelectedEvidence(null)}><div className="modal evidence-modal" onClick={e=>e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Insurance finding evidence"><div className="modal-head"><div><div className="small-eyebrow">TRACEABLE EVIDENCE</div><h2>{pretty(selectedEvidence.coverage_type ?? "Insurance finding")}</h2></div><button className="icon-only" onClick={()=>setSelectedEvidence(null)} aria-label="Close evidence"><X size={21}/></button></div><p>{selectedEvidence.explanation}</p><div className="evidence-columns"><div><h3>Policy source</h3>{selectedEvidence.policy_evidence ? <><small>{selectedEvidence.policy_evidence.document_id} · Page {selectedEvidence.policy_evidence.page}</small><blockquote>{selectedEvidence.policy_evidence.excerpt}</blockquote></> : <p>No policy source was provided.</p>}</div><div><h3>Requirement source</h3>{selectedEvidence.requirement_evidence ? <><small>{selectedEvidence.requirement_evidence.document_id} · Page {selectedEvidence.requirement_evidence.page}</small><blockquote>{selectedEvidence.requirement_evidence.excerpt}</blockquote></> : <p>No requirement evidence was provided.</p>}</div></div><div className="info-note"><ShieldAlert size={16}/> Structured source claims are not independently verified PDF citations.</div></div></div>}
    {showCreate && <div className="overlay" onClick={() => setShowCreate(false)}><div className="modal" onClick={e => e.stopPropagation()}><div className="modal-head"><div><div className="small-eyebrow">WORKFLOW SETUP</div><h2>New customer onboarding</h2></div><button className="icon-only" onClick={() => setShowCreate(false)} aria-label="Close"><X size={21}/></button></div><p>This calls your existing <code>POST /coverage/onboarding</code> FastAPI endpoint and creates a real PostgreSQL workflow.</p><label className="form-label" htmlFor="company">Company name</label><input id="company" className="field" value={companyName} onChange={e => setCompanyName(e.target.value)}/><label className="form-label" htmlFor="industry">Industry</label><input id="industry" className="field" value={industry} onChange={e => setIndustry(e.target.value)}/><div className="modal-actions"><button className="button secondary" onClick={() => setShowCreate(false)}>Cancel</button><button className="button primary" disabled={busy || !companyName.trim() || !industry.trim()} onClick={createWorkflow}><Plus size={16}/> Create workflow</button></div></div></div>}
  </div>;
}

function Metric({ icon: Icon, label, value, trend, trendUp, attention }: { icon: typeof Activity; label: string; value: string; trend: string; trendUp?: boolean; attention?: boolean }) {
  return <div className="metric-card"><div className="metric-top"><span>{label}</span><div className={`metric-icon ${attention ? "orange" : ""}`}><Icon size={19}/></div></div><div className="metric-value">{value}</div><div className="metric-trend">{trendUp && <ArrowUpRight size={14}/>} {attention && <ArrowDownRight size={14}/>} {trend}</div></div>;
}
function PipelineStep({ number, icon: Icon, name, detail, status }: { number: string; icon: typeof Activity; name: string; detail: string; status: "complete" | "review" | "idle" }) {
  return <div className="pipeline-step"><div className={`step-icon ${status}`}><Icon size={19}/></div><div className="step-content"><div className="step-title"><span className="step-number">{number}</span><strong>{name}</strong></div><div className="step-detail">{detail}</div></div><span className={`step-status ${status}`}>{status === "complete" ? <><CheckCircle2 size={14}/> Complete</> : status === "review" ? <><Clock3 size={14}/> Review</> : "Not run"}</span></div>;
}
function ActivityRow({ title, subtitle, time, icon }: ActivityItem) {
  return <div className="activity-row"><span className={`activity-icon ${icon}`}>{icon === "review" ? <ShieldAlert size={17}/> : icon === "ok" ? <Check size={17}/> : <Activity size={17}/>}</span><div className="activity-info"><strong>{title}</strong><span>{subtitle}</span></div><time>{time}</time></div>;
}
