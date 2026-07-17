"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import {
  ArrowLeft,
  Check,
  ChevronRight,
  Download,
  Edit3,
  FileDown,
  FileText,
  Loader2,
  RefreshCw,
  Save,
  Sparkles,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, "") ?? "";

function getApiUrl(path: string) {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

async function readErrorMessage(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) return payload.detail;
  } catch {
    /* non-JSON error */
  }
  return `Request failed with status ${response.status}.`;
}

interface ReviewDoc {
  module: string;
  section_path: string;
  title: string;
  stem: string;
  filename: string;
  status: "draft" | "edited" | "approved";
  updated_at: string;
}

// Full CTD plan: every section, filled or empty.
interface PlanDoc {
  section_path: string;
  stem: string;
  filename: string;
  title: string;
  status: "draft" | "edited" | "approved";
  updated_at: string;
}
interface PlanSection {
  path: string;
  title: string;
  status: "approved" | "in_review" | "empty";
  documents: PlanDoc[];
}
interface PlanModule {
  module: string;
  sections: PlanSection[];
}

interface DocumentDetail {
  markdown: string;
  status: "draft" | "edited" | "approved";
  meta: Record<string, unknown>;
}

// /generate and /feedback return only markdown + status (no meta).
type GenerateResult = Pick<DocumentDetail, "markdown" | "status">;

interface NewSectionResponse {
  section_path: string;
  stem: string;
  markdown: string;
  status: "draft" | "edited" | "approved";
}

function statusClasses(status: string) {
  switch (status) {
    case "approved":
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "edited":
      return "bg-amber-100 text-amber-800 border-amber-200";
    default:
      return "bg-slate-100 text-slate-700 border-slate-200";
  }
}

// Section-level rollup status → badge classes + label.
function planStatusClasses(status: string) {
  switch (status) {
    case "approved":
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "in_review":
      return "bg-amber-100 text-amber-800 border-amber-200";
    default: // empty
      return "bg-slate-50 text-slate-400 border-slate-200";
  }
}
const PLAN_STATUS_LABEL: Record<string, string> = {
  approved: "approved",
  in_review: "in review",
  empty: "empty",
};

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export default function ReviewPage() {
  const [plan, setPlan] = useState<PlanModule[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ReviewDoc | null>(null);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editMarkdown, setEditMarkdown] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isAugmenting, setIsAugmenting] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  // An empty CTD section the user opened to author from scratch.
  const [newSection, setNewSection] = useState<{
    path: string;
    title: string;
    module: string;
  } | null>(null);
  const [creating, setCreating] = useState<"blank" | "ai" | null>(null);

  // Flattened view of every filed document across the plan, for counts/checks.
  const allDocs = plan.flatMap((m) => m.sections.flatMap((s) => s.documents));
  const approvedCount = allDocs.filter((d) => d.status === "approved").length;

  const fetchPlan = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("/api/v1/dossier/plan"));
      if (!res.ok) throw new Error(await readErrorMessage(res));
      setPlan(await res.json());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load plan.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlan();
  }, [fetchPlan]);

  const loadDocument = useCallback(async (doc: ReviewDoc) => {
    setNewSection(null);
    setSelected(doc);
    setDetailLoading(true);
    setIsEditing(false);
    setFeedback("");
    try {
      const res = await fetch(
        getApiUrl(
          `/api/v1/dossier/document?section_path=${encodeURIComponent(doc.section_path)}&stem=${encodeURIComponent(doc.stem)}`,
        ),
      );
      if (!res.ok) throw new Error(await readErrorMessage(res));
      const data: DocumentDetail = await res.json();
      setDetail(data);
      setEditMarkdown(data.markdown);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to load document.",
      );
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  // Open an empty CTD section to author it (choose blank or AI in the panel).
  const openEmptySection = (path: string, title: string, module: string) => {
    setSelected(null);
    setDetail(null);
    setIsEditing(false);
    setNewSection({ path, title, module });
  };

  // Create the document for the opened empty section, then load it normally.
  const createSection = async (augment: boolean) => {
    if (!newSection) return;
    setCreating(augment ? "ai" : "blank");
    try {
      const res = await fetch(getApiUrl("/api/v1/dossier/section"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ctd_path: newSection.path, augment }),
      });
      if (!res.ok) throw new Error(await readErrorMessage(res));
      const data: NewSectionResponse = await res.json();
      const doc: ReviewDoc = {
        module: newSection.module,
        section_path: data.section_path,
        title: newSection.title,
        stem: data.stem,
        filename: "",
        status: data.status,
        updated_at: new Date().toISOString(),
      };
      setNewSection(null);
      setSelected(doc);
      setDetail({ markdown: data.markdown, status: data.status, meta: {} });
      setEditMarkdown(data.markdown);
      setIsEditing(!augment); // blank → drop straight into the editor
      fetchPlan();
      toast.success(augment ? "Section drafted — review the ⚠️ gaps." : "Blank section created.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create section.");
    } finally {
      setCreating(null);
    }
  };

  const saveEdit = async () => {
    if (!selected) return;
    setIsSaving(true);
    try {
      const res = await fetch(getApiUrl("/api/v1/dossier/document"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          section_path: selected.section_path,
          stem: selected.stem,
          markdown: editMarkdown,
        }),
      });
      if (!res.ok) throw new Error(await readErrorMessage(res));
      setDetail((prev) =>
        prev ? { ...prev, markdown: editMarkdown, status: "edited" } : null,
      );
      fetchPlan();
      setIsEditing(false);
      toast.success("Changes saved.");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to save changes.",
      );
    } finally {
      setIsSaving(false);
    }
  };

  const submitFeedback = async () => {
    if (!selected || !feedback.trim()) return;
    if (!confirmRevertIfApproved()) return;
    setIsRegenerating(true);
    try {
      const res = await fetch(getApiUrl("/api/v1/dossier/feedback"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          section_path: selected.section_path,
          stem: selected.stem,
          feedback: feedback.trim(),
        }),
      });
      if (!res.ok) throw new Error(await readErrorMessage(res));
      const data: GenerateResult = await res.json();
      applyRegenerated(selected, data);
      setFeedback("");
      toast.success("Document regenerated.");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to regenerate.",
      );
    } finally {
      setIsRegenerating(false);
    }
  };

  // Regenerating (augment/feedback) resets an approved doc to draft — confirm first.
  const confirmRevertIfApproved = () =>
    detail?.status !== "approved" ||
    window.confirm(
      "This document is approved. Regenerating it will revert it to draft. Continue?",
    );

  // Apply a /generate|/feedback result: keep the existing meta (the response
  // carries only markdown + status), update the viewer, and refresh the plan.
  const applyRegenerated = (_doc: ReviewDoc, data: GenerateResult) => {
    setDetail((prev) =>
      prev
        ? { ...prev, markdown: data.markdown, status: data.status }
        : { markdown: data.markdown, status: data.status, meta: {} },
    );
    setEditMarkdown(data.markdown);
    fetchPlan();
  };

  const augmentDocument = async () => {
    if (!selected) return;
    if (!confirmRevertIfApproved()) return;
    setIsAugmenting(true);
    try {
      const res = await fetch(getApiUrl("/api/v1/dossier/generate"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          section_path: selected.section_path,
          stem: selected.stem,
          augment: true,
        }),
      });
      if (!res.ok) throw new Error(await readErrorMessage(res));
      const data: GenerateResult = await res.json();
      applyRegenerated(selected, data);
      toast.success("Document augmented — review the ⚠️ gaps before approving.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to augment.");
    } finally {
      setIsAugmenting(false);
    }
  };

  const approve = async () => {
    if (!selected) return;
    setIsApproving(true);
    try {
      const res = await fetch(getApiUrl("/api/v1/dossier/approve"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          section_path: selected.section_path,
          stem: selected.stem,
        }),
      });
      if (!res.ok) throw new Error(await readErrorMessage(res));
      setDetail((prev) => (prev ? { ...prev, status: "approved" } : null));
      fetchPlan();
      toast.success("Document approved.");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to approve.",
      );
    } finally {
      setIsApproving(false);
    }
  };

  const downloadDocx = async () => {
    if (!selected) return;
    try {
      const res = await fetch(
        getApiUrl(
          `/api/v1/dossier/export?section_path=${encodeURIComponent(selected.section_path)}&stem=${encodeURIComponent(selected.stem)}&format=docx`,
        ),
      );
      if (!res.ok) throw new Error(await readErrorMessage(res));
      const blob = await res.blob();
      downloadBlob(blob, `${selected.stem}.docx`);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to download document.",
      );
    }
  };

  const exportAll = async () => {
    setIsExporting(true);
    try {
      const res = await fetch(
        getApiUrl("/api/v1/dossier/export/all?format=docx"),
      );
      if (!res.ok) throw new Error(await readErrorMessage(res));
      const blob = await res.blob();
      downloadBlob(blob, "approved-dossier.zip");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to export dossier.",
      );
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 text-slate-900 flex flex-col relative overflow-hidden">
      {/* Decorative background */}
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
            <h1 className="font-serif text-2xl font-bold text-slate-900 leading-none">
              Review Documents
            </h1>
            <p className="text-xs text-slate-500 font-medium tracking-wide uppercase mt-1">
              Generated CTD Drafts
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={exportAll}
            disabled={isExporting || approvedCount === 0}
          >
            {isExporting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FileDown className="w-4 h-4" />
            )}
            <span className="hidden sm:inline">Export all approved</span>
          </Button>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-[min(var(--radius-md),12px)] text-[0.8rem] font-medium border border-border bg-background hover:bg-muted hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Upload</span>
          </Link>
        </div>
      </header>

      <main className="flex-1 w-full max-w-7xl mx-auto px-6 pb-6 relative z-10 min-h-0">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-120px)]">
          {/* Left: Document list */}
          <Card className="lg:col-span-4 flex flex-col border-slate-200/60 shadow-xl shadow-indigo-100/20 bg-white/80 backdrop-blur-xl rounded-3xl overflow-hidden">
            <CardHeader className="bg-slate-50/50 border-b border-slate-100/60 pb-4 px-5 pt-5">
              <CardTitle className="text-lg font-serif text-slate-800">
                CTD Dossier Plan
              </CardTitle>
              <CardDescription className="text-sm">
                {allDocs.length} filed · {approvedCount} approved · full CTD tree
              </CardDescription>
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
                    const filled = mod.sections.filter(
                      (s) => s.status !== "empty",
                    ).length;
                    return (
                      <details
                        key={mod.module}
                        open={filled > 0}
                        className="group/mod"
                      >
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
                                <span className="text-[11px] font-medium text-slate-600">
                                  {sec.path}
                                </span>{" "}
                                <span className="text-[11px] text-slate-400 line-clamp-1">
                                  {sec.title}
                                </span>
                              </span>
                            );

                            // Empty section: clickable to author it from scratch.
                            if (sec.documents.length === 0) {
                              const isOpen = newSection?.path === sec.path;
                              return (
                                <button
                                  key={sec.path}
                                  type="button"
                                  onClick={() =>
                                    openEmptySection(
                                      sec.path,
                                      sec.title,
                                      mod.module,
                                    )
                                  }
                                  className={`w-full text-left flex items-center gap-1.5 px-2 py-1 rounded-lg transition-colors ${
                                    isOpen
                                      ? "bg-indigo-50 ring-1 ring-indigo-200"
                                      : "opacity-60 hover:opacity-100 hover:bg-slate-50"
                                  }`}
                                >
                                  <span className="w-3 shrink-0" />
                                  {label}
                                  {badge}
                                </button>
                              );
                            }

                            // Filled section: expand to its document(s).
                            return (
                              <details key={sec.path} open className="group/sec">
                                <summary className="flex items-center gap-1.5 cursor-pointer list-none select-none rounded-lg px-2 py-1 hover:bg-slate-50">
                                  <ChevronRight className="w-3 h-3 shrink-0 text-slate-300 transition-transform group-open/sec:rotate-90" />
                                  {label}
                                  {badge}
                                </summary>

                                <div className="pl-3 ml-2.5 border-l border-slate-100 space-y-0.5 mt-0.5">
                                  {sec.documents.map((doc) => {
                                    const isSelected =
                                      selected?.section_path ===
                                        doc.section_path &&
                                      selected?.stem === doc.stem;
                                    return (
                                      <button
                                        key={`${doc.section_path}/${doc.stem}`}
                                        onClick={() =>
                                          loadDocument({
                                            ...doc,
                                            module: mod.module,
                                          })
                                        }
                                        type="button"
                                        className={`w-full text-left rounded-lg px-2.5 py-1.5 flex items-center justify-between gap-2 transition-colors ${
                                          isSelected
                                            ? "bg-indigo-50 text-indigo-900 ring-1 ring-indigo-200"
                                            : "text-slate-700 hover:bg-indigo-50/40"
                                        }`}
                                      >
                                        <span className="flex items-center gap-1.5 min-w-0">
                                          <FileText className="w-3.5 h-3.5 shrink-0 text-slate-400" />
                                          <span className="text-xs line-clamp-1">
                                            {doc.filename ||
                                              doc.title ||
                                              doc.stem}
                                          </span>
                                        </span>
                                        <Badge
                                          variant="outline"
                                          className={`text-[9px] px-1.5 py-0 rounded-full capitalize shrink-0 ${statusClasses(doc.status)}`}
                                        >
                                          {doc.status}
                                        </Badge>
                                      </button>
                                    );
                                  })}
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

          {/* Right: Document viewer/editor */}
          <Card className="lg:col-span-8 flex flex-col border-slate-200/60 shadow-xl shadow-indigo-100/20 bg-white/80 backdrop-blur-xl rounded-3xl overflow-hidden">
            {newSection ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-12">
                <div className="w-16 h-16 rounded-3xl bg-indigo-100 flex items-center justify-center text-indigo-600 mb-4">
                  <Sparkles className="w-8 h-8" />
                </div>
                <h3 className="font-serif text-xl text-slate-800 mb-1">
                  {newSection.path} · {newSection.title}
                </h3>
                <p className="text-slate-500 text-sm max-w-md mb-6">
                  This section has no document yet. Draft it with AI (structure +
                  ⚠️ gaps for missing data) or start from a blank page.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-3">
                  <Button
                    onClick={() => createSection(true)}
                    disabled={creating !== null}
                  >
                    {creating === "ai" ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Sparkles className="w-4 h-4" />
                    )}
                    Generate with AI
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => createSection(false)}
                    disabled={creating !== null}
                  >
                    {creating === "blank" ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Edit3 className="w-4 h-4" />
                    )}
                    Start writing
                  </Button>
                </div>
              </div>
            ) : !selected ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-12">
                <div className="w-16 h-16 rounded-3xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400 mb-4">
                  <FileText className="w-8 h-8" />
                </div>
                <h3 className="font-serif text-xl text-slate-700 mb-1">
                  Select a document
                </h3>
                <p className="text-slate-500 text-sm max-w-sm">
                  Choose a section from the plan to review, edit, approve, or
                  author a new one.
                </p>
              </div>
            ) : detailLoading ? (
              <div className="flex-1 flex items-center justify-center text-slate-500">
                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                Loading document...
              </div>
            ) : !detail ? (
              <div className="flex-1 flex items-center justify-center text-slate-500">
                Failed to load document.
              </div>
            ) : (
              <>
                <CardHeader className="bg-slate-50/50 border-b border-slate-100/60 px-6 py-5 flex flex-row items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <CardTitle className="text-lg font-serif text-slate-800 truncate">
                        {selected.title}
                      </CardTitle>
                      <Badge
                        variant="outline"
                        className={`text-[10px] px-2 py-0.5 rounded-full capitalize ${statusClasses(detail.status)}`}
                      >
                        {detail.status}
                      </Badge>
                    </div>
                    <CardDescription className="text-xs truncate">
                      {selected.module} · {selected.section_path} ·{" "}
                      {selected.stem}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <AnimatePresence mode="wait">
                      {!isEditing ? (
                        <motion.div
                          key="actions"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          className="flex items-center gap-2"
                        >
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setIsEditing(true)}
                          >
                            <Edit3 className="w-4 h-4" />
                            <span className="hidden sm:inline">Edit</span>
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={augmentDocument}
                            disabled={isAugmenting}
                            title="Expand sparse content into a complete section; missing data is marked ⚠️ TO BE PROVIDED, never invented."
                          >
                            {isAugmenting ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Sparkles className="w-4 h-4" />
                            )}
                            <span className="hidden sm:inline">Augment</span>
                          </Button>
                          <Button
                            variant={
                              detail.status === "approved"
                                ? "secondary"
                                : "default"
                            }
                            size="sm"
                            onClick={approve}
                            disabled={
                              isApproving || detail.status === "approved"
                            }
                          >
                            {isApproving ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Check className="w-4 h-4" />
                            )}
                            <span className="hidden sm:inline">
                              {detail.status === "approved"
                                ? "Approved"
                                : "Approve"}
                            </span>
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={downloadDocx}
                          >
                            <Download className="w-4 h-4" />
                            <span className="hidden sm:inline">DOCX</span>
                          </Button>
                        </motion.div>
                      ) : (
                        <motion.div
                          key="edit-actions"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          className="flex items-center gap-2"
                        >
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setIsEditing(false);
                              setEditMarkdown(detail.markdown);
                            }}
                          >
                            <X className="w-4 h-4" />
                            Cancel
                          </Button>
                          <Button
                            size="sm"
                            onClick={saveEdit}
                            disabled={isSaving}
                          >
                            {isSaving ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Save className="w-4 h-4" />
                            )}
                            Save
                          </Button>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </CardHeader>

                <CardContent className="flex-1 overflow-y-auto p-0 scrollbar-thin">
                  <AnimatePresence mode="wait">
                    {isEditing ? (
                      <motion.div
                        key="editor"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="h-full p-6"
                      >
                        <textarea
                          value={editMarkdown}
                          onChange={(e) => setEditMarkdown(e.target.value)}
                          className="w-full h-full resize-none rounded-xl border border-slate-200 bg-white p-4 text-sm leading-relaxed text-slate-800 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 font-mono"
                          spellCheck={false}
                        />
                      </motion.div>
                    ) : (
                      <motion.div
                        key="preview"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="p-6 sm:p-8"
                      >
                        <div className="prose prose-sm prose-slate prose-headings:font-serif prose-p:leading-relaxed prose-pre:bg-slate-900 max-w-none">
                          <ReactMarkdown>
                            {detail.markdown || "*(No content)*"}
                          </ReactMarkdown>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </CardContent>

                {/* Feedback bar */}
                {!isEditing && (
                  <div className="border-t border-slate-100 bg-slate-50/50 p-4">
                    <div className="flex items-end gap-3">
                      <div className="flex-1">
                        <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                          AI Feedback
                        </label>
                        <input
                          type="text"
                          value={feedback}
                          onChange={(e) => setFeedback(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                              e.preventDefault();
                              submitFeedback();
                            }
                          }}
                          placeholder="Tell the AI what to change..."
                          className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                        />
                      </div>
                      <Button
                        onClick={submitFeedback}
                        disabled={isRegenerating || !feedback.trim()}
                      >
                        {isRegenerating ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <RefreshCw className="w-4 h-4" />
                        )}
                        Regenerate
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </Card>
        </div>
      </main>
    </div>
  );
}
