"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import {
  ChevronRight,
  Edit3,
  FileDown,
  FileText,
  Gauge,
  Loader2,
  Sparkles,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch, apiJson, downloadFromApi, workspaceHref } from "@/lib/api";
import type { NewSectionResponse, PlanModule, ReadinessReport } from "@/lib/types";

function planStatusClasses(status: string) {
  switch (status) {
    case "approved":
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "in_review":
      return "bg-amber-100 text-amber-800 border-amber-200";
    default:
      return "bg-slate-50 text-slate-400 border-slate-200";
  }
}
const PLAN_STATUS_LABEL: Record<string, string> = {
  approved: "approved",
  in_review: "in review",
  empty: "empty",
};
function docStatusClasses(status: string) {
  switch (status) {
    case "approved":
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "edited":
      return "bg-amber-100 text-amber-800 border-amber-200";
    default:
      return "bg-slate-100 text-slate-700 border-slate-200";
  }
}

const VERDICT_META: Record<string, { label: string; text: string; ring: string }> = {
  ready: { label: "All drafts approved", text: "text-emerald-700", ring: "ring-emerald-200 bg-emerald-50" },
  nearly: { label: "Mostly approved", text: "text-amber-700", ring: "ring-amber-200 bg-amber-50" },
  not_ready: { label: "Drafting in progress", text: "text-rose-700", ring: "ring-rose-200 bg-rose-50" },
};

export default function DossierPage() {
  const router = useRouter();
  const [plan, setPlan] = useState<PlanModule[]>([]);
  const [loading, setLoading] = useState(true);
  const [newSection, setNewSection] = useState<{ path: string; title: string; module: string } | null>(null);
  const [creating, setCreating] = useState<"blank" | "ai" | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [readiness, setReadiness] = useState<ReadinessReport | null>(null);
  const [readinessOpen, setReadinessOpen] = useState(false);
  const [readinessLoading, setReadinessLoading] = useState(false);

  const allDocs = plan.flatMap((m) => m.sections.flatMap((s) => s.documents));
  const approvedCount = allDocs.filter((d) => d.status === "approved").length;

  const fetchPlan = useCallback(async () => {
    try {
      setPlan(await apiFetch<PlanModule[]>("/api/v1/dossier/plan"));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load plan.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlan();
  }, [fetchPlan]);

  useEffect(() => {
    if (!readinessOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setReadinessOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [readinessOpen]);

  const openEmptySection = (path: string, title: string, module: string) => {
    setNewSection({ path, title, module });
  };

  const createSection = async (augment: boolean) => {
    if (!newSection) return;
    setCreating(augment ? "ai" : "blank");
    try {
      const data = await apiJson("/api/v1/dossier/section", "POST", {
        ctd_path: newSection.path,
        augment,
      }) as NewSectionResponse;
      toast.success(augment ? "Section drafted — review the ⚠️ gaps." : "Blank section created.");
      router.push(`${workspaceHref(data.section_path, data.stem)}${augment ? "" : "&edit=1"}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create section.");
    } finally {
      setCreating(null);
      setNewSection(null);
    }
  };

  const openReadiness = async () => {
    setReadinessOpen(true);
    setReadinessLoading(true);
    try {
      setReadiness(await apiFetch<ReadinessReport>("/api/v1/dossier/readiness"));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to analyze readiness.");
      setReadinessOpen(false);
    } finally {
      setReadinessLoading(false);
    }
  };

  const exportAll = async () => {
    setIsExporting(true);
    try {
      await downloadFromApi("/api/v1/dossier/export/all?format=docx", "approved-dossier.zip");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to export dossier.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 text-slate-900 flex flex-col relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-full bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
        <div className="absolute -top-[300px] left-[50%] -translate-x-1/2 w-[800px] h-[600px] bg-indigo-500/10 rounded-full blur-[100px]" />
      </div>

      <header className="w-full max-w-7xl mx-auto px-6 pt-6 pb-4 relative z-10 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-lg shadow-indigo-200/50">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-serif text-2xl font-bold text-slate-900 leading-none">CTD Structure</h1>
            <p className="text-xs text-slate-500 font-medium tracking-wide uppercase mt-1">
              {allDocs.length} filed · {approvedCount} approved
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={openReadiness} disabled={readinessLoading}>
            {readinessLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Gauge className="w-4 h-4" />}
            <span className="hidden sm:inline">Readiness</span>
          </Button>
          <Button variant="outline" size="sm" onClick={exportAll} disabled={isExporting || approvedCount === 0}>
            {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />}
            <span className="hidden sm:inline">Export all approved</span>
          </Button>
        </div>
      </header>

      <main className="flex-1 w-full max-w-7xl mx-auto px-6 pb-6 relative z-10 min-h-0">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[calc(100vh-160px)]">
          {/* Left: full CTD tree */}
          <Card className="lg:col-span-7 flex flex-col border-slate-200/60 shadow-xl shadow-indigo-100/20 bg-white/80 backdrop-blur-xl rounded-3xl overflow-hidden">
            <CardHeader className="bg-slate-50/50 border-b border-slate-100/60 pb-4 px-5 pt-5">
              <CardTitle className="text-lg font-serif text-slate-800">CTD Dossier Plan</CardTitle>
              <CardDescription className="text-sm">Every section, filled or empty</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-3 scrollbar-thin">
              {loading ? (
                <div className="flex items-center justify-center h-40 text-slate-500">
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  Loading plan...
                </div>
              ) : (
                <div className="space-y-1">
                  {plan.map((mod) => {
                    const filled = mod.sections.filter((s) => s.status !== "empty").length;
                    return (
                      <details key={mod.module} open={filled > 0} className="group/mod">
                        <summary className="flex items-center gap-1.5 cursor-pointer list-none select-none rounded-lg px-2 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                          <ChevronRight className="w-3.5 h-3.5 shrink-0 text-slate-400 transition-transform group-open/mod:rotate-90" />
                          <span className="line-clamp-1 flex-1">{mod.module}</span>
                          <span className="text-[10px] font-medium text-slate-400 shrink-0">
                            {filled}/{mod.sections.length}
                          </span>
                        </summary>

                        <div className="pl-3 mt-0.5 space-y-0.5 border-l border-slate-100 ml-3">
                          {mod.sections.map((sec) => {
                            const badge = (
                              <Badge
                                variant="outline"
                                className={`text-[9px] px-1.5 py-0 rounded-full shrink-0 ${planStatusClasses(sec.status)}`}
                              >
                                {PLAN_STATUS_LABEL[sec.status]}
                              </Badge>
                            );
                            const label = (
                              <span className="min-w-0 flex-1">
                                <span className="text-[11px] font-medium text-slate-600">{sec.path}</span>{" "}
                                <span className="text-[11px] text-slate-400 line-clamp-1">{sec.title}</span>
                              </span>
                            );

                            if (sec.documents.length === 0) {
                              const isOpen = newSection?.path === sec.path;
                              return (
                                <button
                                  key={sec.path}
                                  type="button"
                                  onClick={() => openEmptySection(sec.path, sec.title, mod.module)}
                                  className={`w-full text-left flex items-center gap-1.5 px-2 py-1 rounded-lg transition-colors ${
                                    isOpen ? "bg-indigo-50 ring-1 ring-indigo-200" : "opacity-60 hover:opacity-100 hover:bg-slate-50"
                                  }`}
                                >
                                  <span className="w-3 shrink-0" />
                                  {label}
                                  {badge}
                                </button>
                              );
                            }

                            return (
                              <details key={sec.path} open className="group/sec">
                                <summary className="flex items-center gap-1.5 cursor-pointer list-none select-none rounded-lg px-2 py-1 hover:bg-slate-50">
                                  <ChevronRight className="w-3 h-3 shrink-0 text-slate-300 transition-transform group-open/sec:rotate-90" />
                                  {label}
                                  {badge}
                                </summary>

                                <div className="pl-3 ml-2.5 border-l border-slate-100 space-y-0.5 mt-0.5">
                                  {sec.documents.map((doc) => (
                                    <Link
                                      key={`${doc.section_path}/${doc.stem}`}
                                      href={workspaceHref(doc.section_path, doc.stem)}
                                      onClick={() => setNewSection(null)}
                                      className="w-full text-left rounded-lg px-2.5 py-1.5 flex items-center justify-between gap-2 transition-colors text-slate-700 hover:bg-indigo-50/40"
                                    >
                                      <span className="flex items-center gap-1.5 min-w-0">
                                        <FileText className="w-3.5 h-3.5 shrink-0 text-slate-400" />
                                        <span className="text-xs line-clamp-1">
                                          {doc.filename || doc.title || doc.stem}
                                        </span>
                                      </span>
                                      <Badge
                                        variant="outline"
                                        className={`text-[9px] px-1.5 py-0 rounded-full capitalize shrink-0 ${docStatusClasses(doc.status)}`}
                                      >
                                        {doc.status}
                                      </Badge>
                                    </Link>
                                  ))}
                                </div>
                              </details>
                            );
                          })}
                        </div>
                      </details>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Right: author an empty section, or a hint */}
          <Card className="lg:col-span-5 flex flex-col border-slate-200/60 shadow-xl shadow-indigo-100/20 bg-white/80 backdrop-blur-xl rounded-3xl overflow-hidden">
            {newSection ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-12">
                <div className="w-16 h-16 rounded-3xl bg-indigo-100 flex items-center justify-center text-indigo-600 mb-4">
                  <Sparkles className="w-8 h-8" />
                </div>
                <h3 className="font-serif text-xl text-slate-800 mb-1">
                  {newSection.path} · {newSection.title}
                </h3>
                <p className="text-slate-500 text-sm max-w-md mb-6">
                  This section has no document yet. Draft it with AI (structure + ⚠️ gaps for missing
                  data) or start from a blank page.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-3">
                  <Button onClick={() => createSection(true)} disabled={creating !== null}>
                    {creating === "ai" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    Generate with AI
                  </Button>
                  <Button variant="outline" onClick={() => createSection(false)} disabled={creating !== null}>
                    {creating === "blank" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Edit3 className="w-4 h-4" />}
                    Start writing
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-12">
                <div className="w-16 h-16 rounded-3xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400 mb-4">
                  <FileText className="w-8 h-8" />
                </div>
                <h3 className="font-serif text-xl text-slate-700 mb-1">Select a section</h3>
                <p className="text-slate-500 text-sm max-w-sm">
                  Open a filed document to review it, or click an empty section to author it from
                  scratch.
                </p>
              </div>
            )}
          </Card>
        </div>
      </main>

      {/* AI submission-readiness report */}
      <AnimatePresence>
        {readinessOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm"
            onClick={() => setReadinessOpen(false)}
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="Submission readiness report"
              initial={{ opacity: 0, scale: 0.96, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 8 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-2xl max-h-[85vh] flex flex-col bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden"
            >
              <div className="flex items-center justify-between gap-4 px-6 py-4 border-b border-slate-100 bg-slate-50/50">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-600">
                    <Gauge className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="font-serif text-lg text-slate-800 leading-none">Submission Readiness</h2>
                    <p className="text-[11px] text-slate-500 mt-1">AI analysis of your CTD dossier</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setReadinessOpen(false)}
                  className="text-slate-400 hover:text-slate-700 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto scrollbar-thin p-6">
                {readinessLoading || !readiness ? (
                  <div className="flex flex-col items-center justify-center h-48 text-slate-500 gap-2">
                    <Loader2 className="w-6 h-6 animate-spin" />
                    <span className="text-sm">Analyzing dossier…</span>
                  </div>
                ) : (
                  <div className="space-y-6">
                    <div className={`flex items-center gap-5 rounded-2xl ring-1 p-5 ${VERDICT_META[readiness.verdict_label].ring}`}>
                      <div className="text-center shrink-0">
                        <div className="text-4xl font-bold font-serif text-slate-800 leading-none">
                          {readiness.score}
                          <span className="text-lg text-slate-400">%</span>
                        </div>
                        <div className="text-[10px] uppercase tracking-wider text-slate-400 mt-1">approved / drafted</div>
                      </div>
                      <div className="min-w-0">
                        <div className={`font-semibold ${VERDICT_META[readiness.verdict_label].text}`}>
                          {VERDICT_META[readiness.verdict_label].label}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          {readiness.totals.approved} approved · {readiness.totals.in_review} in review ·{" "}
                          {readiness.totals.empty} empty · {readiness.open_gaps} open ⚠️ gap
                          {readiness.open_gaps === 1 ? "" : "s"}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2.5">
                      {readiness.modules.map((m) => {
                        const total = m.approved + m.in_review + m.empty || 1;
                        return (
                          <div key={m.module}>
                            <div className="flex items-center justify-between text-[11px] mb-1">
                              <span className="font-medium text-slate-600 line-clamp-1">{m.module}</span>
                              <span className="text-slate-400 shrink-0 ml-2">{m.drafted}/{total} drafted</span>
                            </div>
                            <div className="flex h-2 rounded-full overflow-hidden bg-slate-100">
                              <div className="bg-emerald-500" style={{ width: `${(m.approved / total) * 100}%` }} />
                              <div className="bg-amber-400" style={{ width: `${(m.in_review / total) * 100}%` }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <div className="prose prose-sm prose-slate max-w-none prose-headings:font-serif border-t border-slate-100 pt-4">
                      <ReactMarkdown>{readiness.narrative}</ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
