"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CalendarClock, ExternalLink, Globe2, Loader2, Plus, RefreshCw, Search } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch, apiJson, dossierApi } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { ProductContext, RegIntelDashboard } from "@/lib/types";

const inputClass = "h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100";

export default function RegulatoryIntelligencePage() {
  const { dossierId } = useParams<{ dossierId: string }>();
  const [data, setData] = useState<RegIntelDashboard | null>(null);
  const [context, setContext] = useState<ProductContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [deadline, setDeadline] = useState({ title: "", due_date: "", product: "", authority: "" });
  const { t } = useLanguage();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [dashboard, product] = await Promise.all([
        apiFetch<RegIntelDashboard>("/api/v1/regintelligence/dashboard"),
        apiFetch<ProductContext>(dossierApi(dossierId, "/context")).catch(() => null),
      ]);
      setData(dashboard);
      setContext(product);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load dashboard.");
    } finally {
      setLoading(false);
    }
  }, [dossierId]);

  useEffect(() => { void load(); }, [load]);

  const crawl = async (sourceKey?: string) => {
    setBusy(sourceKey ?? "__all__");
    try {
      const result = await apiFetch<{ new_alerts: number; new_documents: number }>(
        `/api/v1/regintelligence/crawl${sourceKey ? `?source_key=${encodeURIComponent(sourceKey)}` : ""}`,
        { method: "POST" }
      );
      toast.success(`Crawl complete: ${result.new_alerts} alerts.`);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Crawl failed.");
    } finally { setBusy(null); }
  };

  const toggleSource = async (key: string, enabled: boolean) => {
    try {
      await apiJson("/api/v1/regintelligence/sources", "POST", { source_key: key, enabled });
      setData(prev => prev ? { ...prev, sources: prev.sources.map(s => s.key === key ? { ...s, enabled } : s) } : prev);
    } catch (err) { toast.error(err instanceof Error ? err.message : "Failed to update source."); }
  };

  const impact = async (alertId: string) => {
    setBusy(alertId);
    try {
      const product = context ? [context.product_name, context.market].filter(Boolean).join(" — ") || "the product" : "the product";
      const result = (await apiJson(`/api/v1/regintelligence/alerts/${alertId}/impact`, "POST", product)) as { impact_summary: string };
      setData(prev => prev ? { ...prev, alerts: prev.alerts.map(a => a.alert_id === alertId ? { ...a, impact_summary: result.impact_summary } : a) } : prev);
    } catch (err) { toast.error(err instanceof Error ? err.message : "Impact analysis failed."); }
    finally { setBusy(null); }
  };

  const addDeadline = async () => {
    if (!deadline.title.trim() || !deadline.due_date) { toast.error("Title and due date are required."); return; }
    try {
      await apiJson("/api/v1/regintelligence/deadlines", "POST", { ...deadline, source: "manual", product: deadline.product || null, authority: deadline.authority || null });
      setDeadline({ title: "", due_date: "", product: "", authority: "" });
      await load();
      toast.success("Deadline added.");
    } catch (err) { toast.error(err instanceof Error ? err.message : "Failed to add deadline."); }
  };

  if (loading && !data) return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-500"><Loader2 className="mr-2 h-5 w-5 animate-spin" />Loading regulatory intelligence…</div>;

  return (
    <div className="min-h-screen bg-slate-50/60 px-6 py-8 text-slate-900">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-500 text-white"><Globe2 className="h-6 w-6" /></div>
            <div>
              <h1 className="font-serif text-3xl font-bold leading-none">{t.regintel.title}</h1>
              <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{t.regintel.subtitle}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={load} disabled={loading}>{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}Refresh</Button>
            <Button onClick={() => crawl()} disabled={busy !== null}>{busy === "__all__" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}Crawl all</Button>
          </div>
        </header>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            ["New this week", data?.stats.new_this_week ?? 0],
            ["Pending deadlines", data?.stats.pending_deadlines ?? 0],
            ["Sources", data?.sources.length ?? 0],
            ["Changes", data?.changes.length ?? 0],
          ].map(([label, value]) => (
            <Card key={String(label)}><CardContent className="space-y-1 pt-0">
              <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
              <p className="font-serif text-3xl font-bold">{value}</p>
            </CardContent></Card>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
          <Card className="xl:col-span-2">
            <CardHeader className="border-b border-slate-100 pb-4"><CardTitle className="font-serif text-lg">{t.regintel.alerts}</CardTitle><CardDescription>Detected regulatory documents and announcements</CardDescription></CardHeader>
            <CardContent className="space-y-3 pt-4">
              {data?.alerts.length ? data.alerts.map(alert => (
                <div key={alert.alert_id} className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <a href={alert.url} target="_blank" rel="noreferrer" className="font-semibold hover:text-indigo-700">{alert.title}</a>
                      <p className="text-xs text-slate-500">{alert.authority} · {alert.country} · {new Date(alert.detected_at).toLocaleDateString()}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="capitalize">{alert.doc_type.replaceAll("_", " ")}</Badge>
                      <Button size="sm" variant="outline" onClick={() => impact(alert.alert_id)} disabled={busy === alert.alert_id}>{busy === alert.alert_id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}Impact</Button>
                      <a href={alert.url} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-indigo-600"><ExternalLink className="h-4 w-4" /></a>
                    </div>
                  </div>
                  {alert.impact_summary && <p className="mt-3 rounded-xl bg-indigo-50 p-3 text-sm text-indigo-900">{alert.impact_summary}</p>}
                </div>
              )) : <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">No alerts yet.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-slate-100 pb-4"><CardTitle className="font-serif text-lg">{t.regintel.sources}</CardTitle><CardDescription>Toggle and crawl authorities</CardDescription></CardHeader>
            <CardContent className="space-y-3 pt-4">
              {data?.sources.map(source => (
                <div key={source.key} className="space-y-2 rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0"><p className="truncate font-semibold">{source.authority}</p><p className="text-xs text-slate-500">{source.country}</p></div>
                    <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={source.enabled} onChange={e => toggleSource(source.key, e.target.checked)} className="h-4 w-4 accent-indigo-600" />Enabled</label>
                  </div>
                  <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
                    <span>Last crawl: {source.last_crawled ? new Date(source.last_crawled).toLocaleString() : "Never"}</span>
                    <Button size="xs" variant="outline" onClick={() => crawl(source.key)} disabled={busy !== null}>{busy === source.key ? <Loader2 className="h-3 w-3 animate-spin" /> : <Search className="h-3 w-3" />}Crawl</Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-slate-100 pb-4"><CardTitle className="font-serif text-lg">{t.regintel.changes}</CardTitle><CardDescription>Document similarity between crawls</CardDescription></CardHeader>
            <CardContent className="space-y-3 pt-4">
              {data?.changes.length ? data.changes.map(change => (
                <div key={`${change.url}-${change.detected_at}`} className="rounded-2xl border border-slate-200 bg-white p-4">
                  <a href={change.url} target="_blank" rel="noreferrer" className="line-clamp-2 text-sm font-semibold hover:text-indigo-700">{change.url}</a>
                  <div className="mt-2 flex items-center gap-2"><Badge variant="outline">{Math.round(change.similarity * 100)}% similar</Badge><span className="text-xs text-slate-500">{new Date(change.detected_at).toLocaleString()}</span></div>
                </div>
              )) : <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">No changes detected.</p>}
            </CardContent>
          </Card>

          <Card className="xl:col-span-2">
            <CardHeader className="border-b border-slate-100 pb-4"><CardTitle className="font-serif text-lg">{t.regintel.deadlines}</CardTitle><CardDescription>Manual and crawled deadlines</CardDescription></CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5 lg:items-end">
                <label className="space-y-1.5"><span className="text-xs font-semibold text-slate-600">Title</span><input className={inputClass} value={deadline.title} onChange={e => setDeadline({ ...deadline, title: e.target.value })} /></label>
                <label className="space-y-1.5"><span className="text-xs font-semibold text-slate-600">Due date</span><input type="date" className={inputClass} value={deadline.due_date} onChange={e => setDeadline({ ...deadline, due_date: e.target.value })} /></label>
                <label className="space-y-1.5"><span className="text-xs font-semibold text-slate-600">Product</span><input className={inputClass} value={deadline.product} onChange={e => setDeadline({ ...deadline, product: e.target.value })} /></label>
                <label className="space-y-1.5"><span className="text-xs font-semibold text-slate-600">Authority</span><input className={inputClass} value={deadline.authority} onChange={e => setDeadline({ ...deadline, authority: e.target.value })} /></label>
                <Button onClick={addDeadline}><Plus className="h-4 w-4" />{t.regintel.add}</Button>
              </div>
              <div className="space-y-2">
                {data?.deadlines.length ? data.deadlines.map(item => (
                  <div key={item.deadline_id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 text-sm">
                    <div className="min-w-0"><p className="truncate font-semibold">{item.title}</p><p className="text-xs text-slate-500">{item.authority || "Manual"} · {item.product || "All products"}</p></div>
                    <Badge variant="outline" className="shrink-0"><CalendarClock className="h-3 w-3" />{new Date(item.due_date).toLocaleDateString()}</Badge>
                  </div>
                )) : <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">No deadlines configured.</p>}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
