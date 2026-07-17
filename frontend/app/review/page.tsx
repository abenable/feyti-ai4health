"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
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
  FolderOpen,
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

interface DocumentDetail {
  markdown: string;
  status: "draft" | "edited" | "approved";
  meta: Record<string, unknown>;
}

// /generate and /feedback return only markdown + status (no meta).
type GenerateResult = Pick<DocumentDetail, "markdown" | "status">;

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
  const [docs, setDocs] = useState<ReviewDoc[]>([]);
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

  // Group the flat document list into a Module → Section → documents tree.
  const moduleTree = useMemo(() => {
    const mods = new Map<string, Map<string, ReviewDoc[]>>();
    for (const doc of docs) {
      // section_path is "<module>/<section> <title>"; take the section part.
      const section =
        doc.section_path.split("/").slice(1).join("/") || doc.section_path;
      if (!mods.has(doc.module)) mods.set(doc.module, new Map());
      const secs = mods.get(doc.module)!;
      if (!secs.has(section)) secs.set(section, []);
      secs.get(section)!.push(doc);
    }
    // Numeric-aware sort so "2.6.6.10" follows "2.6.6.2", not precedes it.
    const byNumber = (a: string, b: string) =>
      a.localeCompare(b, undefined, { numeric: true });
    return [...mods.entries()]
      .sort(([a], [b]) => byNumber(a, b))
      .map(([module, secs]) => ({
        module,
        sections: [...secs.entries()]
          .sort(([a], [b]) => byNumber(a, b))
          .map(([section, items]) => ({ section, items })),
      }));
  }, [docs]);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(getApiUrl("/api/v1/dossier/documents"));
      if (!res.ok) throw new Error(await readErrorMessage(res));
      const data: ReviewDoc[] = await res.json();
      setDocs(data);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to load documents.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const loadDocument = useCallback(async (doc: ReviewDoc) => {
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
      setDocs((prev) =>
        prev.map((d) =>
          d.section_path === selected.section_path && d.stem === selected.stem
            ? { ...d, status: "edited", updated_at: new Date().toISOString() }
            : d,
        ),
      );
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
  // carries only markdown + status), update the viewer and the list row.
  const applyRegenerated = (doc: ReviewDoc, data: GenerateResult) => {
    setDetail((prev) =>
      prev
        ? { ...prev, markdown: data.markdown, status: data.status }
        : { markdown: data.markdown, status: data.status, meta: {} },
    );
    setEditMarkdown(data.markdown);
    setDocs((prev) =>
      prev.map((d) =>
        d.section_path === doc.section_path && d.stem === doc.stem
          ? { ...d, status: data.status, updated_at: new Date().toISOString() }
          : d,
      ),
    );
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
      setDocs((prev) =>
        prev.map((d) =>
          d.section_path === selected.section_path && d.stem === selected.stem
            ? { ...d, status: "approved", updated_at: new Date().toISOString() }
            : d,
        ),
      );
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
            disabled={isExporting || docs.every((d) => d.status !== "approved")}
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
                Generated Documents
              </CardTitle>
              <CardDescription className="text-sm">
                {docs.length} {docs.length === 1 ? "document" : "documents"} in
                queue
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-3 scrollbar-thin">
              {loading ? (
                <div className="flex items-center justify-center h-40 text-slate-500">
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  Loading documents...
                </div>
              ) : docs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center px-4 py-12">
                  <div className="w-14 h-14 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400 mb-4">
                    <FolderOpen className="w-7 h-7" />
                  </div>
                  <p className="text-slate-600 font-medium mb-1">
                    No generated documents yet.
                  </p>
                  <p className="text-sm text-slate-500">
                    Upload a document on the home page to get started.
                  </p>
                  <Link
                    href="/"
                    className="mt-4 inline-flex items-center gap-1.5 h-7 px-2.5 rounded-[min(var(--radius-md),12px)] text-[0.8rem] font-medium border border-border bg-background hover:bg-muted hover:text-foreground transition-colors"
                  >
                    Go to Upload
                  </Link>
                </div>
              ) : (
                <div className="space-y-1">
                  {moduleTree.map((mod) => (
                    <details key={mod.module} open className="group/mod">
                      <summary className="flex items-center gap-1.5 cursor-pointer list-none select-none rounded-lg px-2 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">
                        <ChevronRight className="w-3.5 h-3.5 shrink-0 text-slate-400 transition-transform group-open/mod:rotate-90" />
                        <span className="line-clamp-1">{mod.module}</span>
                      </summary>

                      <div className="pl-3 mt-0.5 space-y-0.5 border-l border-slate-100 ml-3">
                        {mod.sections.map((sec) => (
                          <details
                            key={sec.section}
                            open
                            className="group/sec"
                          >
                            <summary className="flex items-center gap-1.5 cursor-pointer list-none select-none rounded-lg px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-50">
                              <ChevronRight className="w-3 h-3 shrink-0 text-slate-300 transition-transform group-open/sec:rotate-90" />
                              <span className="line-clamp-1">{sec.section}</span>
                            </summary>

                            <div className="pl-3 ml-2.5 border-l border-slate-100 space-y-0.5 mt-0.5">
                              {sec.items.map((doc) => {
                                const isSelected =
                                  selected?.section_path ===
                                    doc.section_path &&
                                  selected?.stem === doc.stem;
                                return (
                                  <button
                                    key={`${doc.section_path}/${doc.stem}`}
                                    onClick={() => loadDocument(doc)}
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
                                        {doc.filename || doc.title || doc.stem}
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
                        ))}
                      </div>
                    </details>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Right: Document viewer/editor */}
          <Card className="lg:col-span-8 flex flex-col border-slate-200/60 shadow-xl shadow-indigo-100/20 bg-white/80 backdrop-blur-xl rounded-3xl overflow-hidden">
            {!selected ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-12">
                <div className="w-16 h-16 rounded-3xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400 mb-4">
                  <FileText className="w-8 h-8" />
                </div>
                <h3 className="font-serif text-xl text-slate-700 mb-1">
                  Select a document
                </h3>
                <p className="text-slate-500 text-sm max-w-sm">
                  Choose a generated draft from the list to review, edit,
                  approve, or download.
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
