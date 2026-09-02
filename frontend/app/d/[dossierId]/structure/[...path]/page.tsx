"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Download,
  Edit3,
  FileText,
  Loader2,
  MessageSquare,
  RefreshCw,
  Save,
  ScanText,
  Sparkles,
  Tags,
  X,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { apiFetch, apiJson, dossierApi, downloadFromApi, sectionPathFromSegments, workspaceHref } from "@/lib/api";
import { useLanguage, type Dictionary } from "@/lib/i18n";
import type {
  DocumentDetail,
  ExtractedField,
  GenerateResult,
  PlanModule,
  ReclassifyResponse,
  SourceDoc,
  ValidationReport,
} from "@/lib/types";

const TABS = ["source", "analysis", "draft", "validation"] as const;
type Tab = (typeof TABS)[number];

function tabMeta(t: Dictionary): Record<Tab, { label: string; icon: typeof ScanText }> {
  return {
    source: { label: t.sectionDetail.tabSource, icon: ScanText },
    analysis: { label: t.sectionDetail.tabAnalysis, icon: Tags },
    draft: { label: t.sectionDetail.tabDraft, icon: FileText },
    validation: { label: t.sectionDetail.tabValidation, icon: CheckCircle2 },
  };
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
function docStatusLabel(t: Dictionary, status: string): string {
  return { approved: t.structurePage.statusApproved, edited: t.structurePage.statusEdited, draft: t.structurePage.statusDraft }[status] ?? status;
}

function DocumentWorkspacePageInner() {
  const params = useParams<{ dossierId: string; path: string[] }>();
  const searchParams = useSearchParams();
  const router = useRouter();

  const { t } = useLanguage();
  const TAB_META = tabMeta(t);

  const dossierId = params.dossierId;
  const sectionPath = useMemo(() => sectionPathFromSegments(params.path ?? []), [params.path]);
  const stem = searchParams.get("stem") ?? "";

  const [tab, setTab] = useState<Tab>("draft");
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const [isEditing, setIsEditing] = useState(!!searchParams.get("edit"));
  const [editMarkdown, setEditMarkdown] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isAugmenting, setIsAugmenting] = useState(false);
  const [isApproving, setIsApproving] = useState(false);

  const [source, setSource] = useState<SourceDoc | null>(null);
  const [sourceLoading, setSourceLoading] = useState(false);

  const [fields, setFields] = useState<ExtractedField[]>([]);
  const [reExtracting, setReExtracting] = useState(false);
  const [reclassifyPath, setReclassifyPath] = useState("");
  const [reclassifying, setReclassifying] = useState(false);
  const [catalogue, setCatalogue] = useState<{ path: string; title: string }[]>([]);

  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);

  const loadDocument = useCallback(async () => {
    if (!sectionPath || !stem) return;
    setLoading(true);
    try {
      const data = await apiFetch<DocumentDetail>(
        dossierApi(dossierId, `/document?section_path=${encodeURIComponent(sectionPath)}&stem=${encodeURIComponent(stem)}`),
      );
      setDetail(data);
      setEditMarkdown(data.markdown);
      setFields(data.meta.fields ?? []);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.sectionDetail.loadDocumentFailedToast);
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [dossierId, sectionPath, stem, t]);

  useEffect(() => {
    loadDocument();
  }, [loadDocument]);

  const loadSource = useCallback(async () => {
    if (source || sourceLoading) return;
    setSourceLoading(true);
    try {
      setSource(
        await apiFetch<SourceDoc>(
          dossierApi(dossierId, `/source?section_path=${encodeURIComponent(sectionPath)}&stem=${encodeURIComponent(stem)}`),
        ),
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.sectionDetail.loadSourceFailedToast);
    } finally {
      setSourceLoading(false);
    }
  }, [dossierId, sectionPath, stem, source, sourceLoading, t]);

  const loadCatalogue = useCallback(async () => {
    if (catalogue.length) return;
    try {
      const plan = await apiFetch<PlanModule[]>(dossierApi(dossierId, "/plan"));
      setCatalogue(plan.flatMap((m) => m.sections.map((s) => ({ path: s.path, title: s.title }))));
    } catch {
      /* autocomplete is a nicety; failing silently is fine */
    }
  }, [dossierId, catalogue.length]);

  const loadValidation = useCallback(async () => {
    setValidationLoading(true);
    try {
      setValidation(
        await apiFetch<ValidationReport>(
          dossierApi(dossierId, `/validate?section_path=${encodeURIComponent(sectionPath)}&stem=${encodeURIComponent(stem)}`),
        ),
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.sectionDetail.validateFailedToast);
    } finally {
      setValidationLoading(false);
    }
  }, [dossierId, sectionPath, stem, t]);

  useEffect(() => {
    if (tab === "source") loadSource();
    if (tab === "analysis") loadCatalogue();
    if (tab === "validation" && !validation) loadValidation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const confirmRevertIfApproved = () =>
    detail?.status !== "approved" || window.confirm(t.sectionDetail.revertConfirm);

  const applyRegenerated = (data: GenerateResult) => {
    setDetail((prev) => (prev ? { ...prev, markdown: data.markdown, status: data.status } : prev));
    setEditMarkdown(data.markdown);
    setValidation(null);
  };

  const saveEdit = async () => {
    setIsSaving(true);
    try {
      await apiJson(dossierApi(dossierId, "/document"), "PUT", { section_path: sectionPath, stem, markdown: editMarkdown });
      setDetail((prev) => (prev ? { ...prev, markdown: editMarkdown, status: "edited" } : prev));
      setValidation(null);
      setIsEditing(false);
      toast.success(t.sectionDetail.changesSavedToast);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.sectionDetail.saveFailedToast);
    } finally {
      setIsSaving(false);
    }
  };

  const submitFeedback = async () => {
    if (!feedback.trim() || !confirmRevertIfApproved()) return;
    setIsRegenerating(true);
    try {
      const data = await apiJson(dossierApi(dossierId, "/feedback"), "POST", {
        section_path: sectionPath,
        stem,
        feedback: feedback.trim(),
      }) as GenerateResult;
      applyRegenerated(data);
      setFeedback("");
      toast.success(t.sectionDetail.regeneratedToast);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.sectionDetail.regenerateFailedToast);
    } finally {
      setIsRegenerating(false);
    }
  };

  const augmentDocument = async () => {
    if (!confirmRevertIfApproved()) return;
    setIsAugmenting(true);
    try {
      const data = await apiJson(dossierApi(dossierId, "/generate"), "POST", {
        section_path: sectionPath,
        stem,
        augment: true,
      }) as GenerateResult;
      applyRegenerated(data);
      toast.success(t.sectionDetail.augmentedToast);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.sectionDetail.augmentFailedToast);
    } finally {
      setIsAugmenting(false);
    }
  };

  const approve = async () => {
    setIsApproving(true);
    try {
      await apiJson(dossierApi(dossierId, "/approve"), "POST", { section_path: sectionPath, stem });
      setDetail((prev) => (prev ? { ...prev, status: "approved" } : prev));
      toast.success(t.sectionDetail.approvedToast);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.sectionDetail.approveFailedToast);
    } finally {
      setIsApproving(false);
    }
  };

  const downloadDocx = async () => {
    try {
      await downloadFromApi(
        dossierApi(dossierId, `/export?section_path=${encodeURIComponent(sectionPath)}&stem=${encodeURIComponent(stem)}&format=docx`),
        `${stem}.docx`,
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.sectionDetail.downloadFailedToast);
    }
  };

  const reExtractFields = async () => {
    setReExtracting(true);
    try {
      setFields(await apiJson(dossierApi(dossierId, "/extract"), "POST", { section_path: sectionPath, stem }) as ExtractedField[]);
      toast.success(t.sectionDetail.fieldsReExtractedToast);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.sectionDetail.extractFailedToast);
    } finally {
      setReExtracting(false);
    }
  };

  const reclassify = async () => {
    const ctdPath = reclassifyPath.trim().split(/\s/)[0]; // "3.2.P.8.3 Stability Data" → "3.2.P.8.3"
    if (!ctdPath) return;
    setReclassifying(true);
    try {
      const data = await apiJson(dossierApi(dossierId, "/reclassify"), "POST", {
        section_path: sectionPath,
        stem,
        ctd_path: ctdPath,
      }) as ReclassifyResponse;
      toast.success(t.sectionDetail.movedToToast.replace("{path}", ctdPath));
      router.replace(workspaceHref(dossierId, data.section_path, data.stem));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t.sectionDetail.reclassifyFailedToast);
    } finally {
      setReclassifying(false);
    }
  };

  const meta = detail?.meta ?? {};

  return (
    <div className="min-h-screen bg-slate-50/50 text-slate-900">
      <header className="w-full max-w-5xl mx-auto px-6 pt-6 pb-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href={`/d/${dossierId}/structure`}
            className="w-9 h-9 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-slate-500 hover:text-indigo-600 hover:border-indigo-200 transition-colors shrink-0"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="font-serif text-xl font-bold text-slate-900 truncate">
                {meta.title || stem}
              </h1>
              {detail && (
                <Badge variant="outline" className={`text-[10px] px-2 py-0.5 rounded-full capitalize shrink-0 ${statusClasses(detail.status)}`}>
                  {docStatusLabel(t, detail.status)}
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-500 truncate">{meta.section_path} · {meta.module}</p>
          </div>
        </div>
        <Link
          href={`/d/${dossierId}/chat?section_path=${encodeURIComponent(sectionPath)}&stem=${encodeURIComponent(stem)}`}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider border border-indigo-200 bg-indigo-50 text-indigo-700 shadow-sm hover:bg-indigo-100 transition-colors shrink-0"
        >
          <MessageSquare className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{t.sectionDetail.askAboutThis}</span>
        </Link>
      </header>

      <div className="w-full max-w-5xl mx-auto px-6">
        <div className="flex items-center gap-1 border-b border-slate-200/60 mb-6">
          {TABS.map((tabId) => {
            const { label, icon: Icon } = TAB_META[tabId];
            return (
              <button
                key={tabId}
                onClick={() => setTab(tabId)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  tab === tabId ? "border-indigo-600 text-indigo-700" : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            );
          })}
        </div>
      </div>

      <main className="w-full max-w-5xl mx-auto px-6 pb-16">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-slate-500">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            {t.sectionDetail.loadingDocument}
          </div>
        ) : !detail ? (
          <div className="flex items-center justify-center h-64 text-slate-500">{t.sectionDetail.documentNotFound}</div>
        ) : (
          <>
            {tab === "source" && (
              <Card className="border-slate-200/60 shadow-lg rounded-3xl overflow-hidden">
                <CardHeader className="bg-slate-50/50 border-b border-slate-100/60 flex flex-row items-center justify-between gap-3">
                  <div>
                    <h2 className="font-serif text-lg text-slate-800">{t.sectionDetail.tabSource}</h2>
                    <p className="text-xs text-slate-500">
                      {source
                        ? t.sectionDetail.sourceSubtitlePages
                            .replace("{pages}", String(source.pages.length))
                            .replace("{chars}", source.extracted_chars.toLocaleString())
                        : t.sectionDetail.sourceSubtitleEmpty}
                    </p>
                  </div>
                  {meta.filename && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        downloadFromApi(
                          dossierApi(dossierId, `/original?section_path=${encodeURIComponent(sectionPath)}&stem=${encodeURIComponent(stem)}`),
                          meta.filename!,
                        ).catch((err) => toast.error(err instanceof Error ? err.message : t.sectionDetail.downloadOriginalFailedToast))
                      }
                    >
                      <Download className="w-4 h-4" />
                      {t.sectionDetail.originalFile}
                    </Button>
                  )}
                </CardHeader>
                <CardContent className="p-0">
                  {sourceLoading ? (
                    <div className="flex items-center justify-center h-40 text-slate-500">
                      <Loader2 className="w-5 h-5 animate-spin mr-2" />
                      {t.sectionDetail.loadingSource}
                    </div>
                  ) : !source || source.pages.length === 0 ? (
                    <div className="text-center py-16 text-slate-500 text-sm">{t.sectionDetail.noSourceText}</div>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {source.pages.map((p) => (
                        <details key={p.page} open={source.pages.length <= 3} className="group">
                          <summary className="flex items-center gap-2 cursor-pointer list-none select-none px-6 py-3 hover:bg-slate-50">
                            <span className="text-sm font-semibold text-slate-700">{t.sectionDetail.page.replace("{n}", String(p.page))}</span>
                            {p.is_ocr && (
                              <Badge variant="outline" className="text-[9px] px-1.5 py-0 rounded-full bg-violet-50 border-violet-200 text-violet-700">
                                {t.dossier.ocr}
                              </Badge>
                            )}
                          </summary>
                          <div className="px-6 pb-4 text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                            {p.text || <span className="text-slate-400 italic">{t.sectionDetail.noTextOnPage}</span>}
                          </div>
                        </details>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {tab === "analysis" && (
              <div className="space-y-6">
                <Card className="border-slate-200/60 shadow-lg rounded-3xl overflow-hidden">
                  <CardHeader className="bg-slate-50/50 border-b border-slate-100/60">
                    <h2 className="font-serif text-lg text-slate-800">{t.sectionDetail.classification}</h2>
                  </CardHeader>
                  <CardContent className="p-6 space-y-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <Badge variant="outline" className="bg-slate-50 border-slate-200 text-slate-800 px-3 py-1 rounded-full font-medium">
                        {meta.section_path} {meta.title}
                      </Badge>
                      <span className="text-sm text-slate-500">
                        {t.sectionDetail.confidencePct.replace("{pct}", String(Math.round((meta.confidence ?? 0) * 100)))}
                      </span>
                    </div>
                    {meta.justification && <p className="text-sm text-slate-600 leading-relaxed">{meta.justification}</p>}
                    {meta.summary && (
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">{t.dossier.summary}</p>
                        <p className="text-sm text-slate-700 leading-relaxed">{meta.summary}</p>
                      </div>
                    )}
                    {meta.key_points && meta.key_points.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">{t.dossier.keyPoints}</p>
                        <ul className="space-y-1.5">
                          {meta.key_points.map((point, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                              <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0" />
                              <span className="leading-relaxed">{point}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="border-t border-slate-100 pt-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t.sectionDetail.reclassifyLabel}</p>
                      <div className="flex gap-2">
                        <input
                          list="ctd-catalogue"
                          value={reclassifyPath}
                          onChange={(e) => setReclassifyPath(e.target.value)}
                          onFocus={loadCatalogue}
                          placeholder={t.sectionDetail.reclassifyPlaceholder}
                          className="flex-1 h-9 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                        />
                        <datalist id="ctd-catalogue">
                          {catalogue.map((c) => (
                            <option key={c.path} value={`${c.path} ${c.title}`} />
                          ))}
                        </datalist>
                        <Button size="sm" variant="outline" onClick={reclassify} disabled={reclassifying || !reclassifyPath.trim()}>
                          {reclassifying ? <Loader2 className="w-4 h-4 animate-spin" /> : t.sectionDetail.move}
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-slate-200/60 shadow-lg rounded-3xl overflow-hidden">
                  <CardHeader className="bg-slate-50/50 border-b border-slate-100/60 flex flex-row items-center justify-between gap-3">
                    <h2 className="font-serif text-lg text-slate-800">{t.sectionDetail.extractedFields}</h2>
                    <Button size="sm" variant="outline" onClick={reExtractFields} disabled={reExtracting}>
                      {reExtracting ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                      {t.sectionDetail.reExtract}
                    </Button>
                  </CardHeader>
                  <CardContent className="p-0">
                    {fields.length === 0 ? (
                      <div className="text-center py-10 text-slate-500 text-sm">{t.sectionDetail.noFieldsExtracted}</div>
                    ) : (
                      <table className="w-full text-sm">
                        <tbody className="divide-y divide-slate-100">
                          {fields.map((f, i) => (
                            <tr key={i}>
                              <td className="px-6 py-2.5 font-medium text-slate-600 whitespace-nowrap">{f.label}</td>
                              <td className="px-3 py-2.5 text-slate-800">
                                {f.value ? (
                                  f.value
                                ) : (
                                  <span className="text-amber-600 italic flex items-center gap-1">
                                    <AlertTriangle className="w-3.5 h-3.5" /> {t.sectionDetail.notFoundInSource}
                                  </span>
                                )}
                              </td>
                              <td className="px-3 py-2.5 text-slate-400 text-xs whitespace-nowrap">
                                {f.page ? `p.${f.page}` : ""} {f.value ? `${Math.round(f.confidence * 100)}%` : ""}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}

            {tab === "draft" && (
              <Card className="border-slate-200/60 shadow-lg rounded-3xl overflow-hidden">
                <CardHeader className="bg-slate-50/50 border-b border-slate-100/60 flex flex-row items-center justify-between gap-4">
                  <AnimatePresence mode="wait">
                    {!isEditing ? (
                      <motion.div key="actions" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center gap-2 flex-wrap">
                        <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                          <Edit3 className="w-4 h-4" />
                          <span className="hidden sm:inline">{t.dossier.edit}</span>
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={augmentDocument}
                          disabled={isAugmenting}
                          title={t.sectionDetail.augmentTooltip}
                        >
                          {isAugmenting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                          <span className="hidden sm:inline">{t.sectionDetail.augment}</span>
                        </Button>
                        <Button
                          variant={detail.status === "approved" ? "secondary" : "default"}
                          size="sm"
                          onClick={approve}
                          disabled={isApproving || detail.status === "approved"}
                        >
                          {isApproving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                          <span className="hidden sm:inline">{detail.status === "approved" ? t.sectionDetail.approved : t.sectionDetail.approve}</span>
                        </Button>
                        <Button variant="outline" size="sm" onClick={downloadDocx}>
                          <Download className="w-4 h-4" />
                          <span className="hidden sm:inline">{t.sectionDetail.docx}</span>
                        </Button>
                      </motion.div>
                    ) : (
                      <motion.div key="edit-actions" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setIsEditing(false);
                            setEditMarkdown(detail.markdown);
                          }}
                        >
                          <X className="w-4 h-4" />
                          {t.dossier.cancel}
                        </Button>
                        <Button size="sm" onClick={saveEdit} disabled={isSaving}>
                          {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                          {t.pv.save}
                        </Button>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </CardHeader>

                <CardContent className="p-0">
                  <AnimatePresence mode="wait">
                    {isEditing ? (
                      <motion.div key="editor" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="p-6">
                        <textarea
                          value={editMarkdown}
                          onChange={(e) => setEditMarkdown(e.target.value)}
                          className="w-full h-[60vh] resize-none rounded-xl border border-slate-200 bg-white p-4 text-sm leading-relaxed text-slate-800 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 font-mono"
                          spellCheck={false}
                        />
                      </motion.div>
                    ) : (
                      <motion.div key="preview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="p-6 sm:p-8">
                        <div className="prose prose-sm prose-slate prose-headings:font-serif prose-p:leading-relaxed prose-pre:bg-slate-900 max-w-none">
                          <ReactMarkdown>{detail.markdown || t.sectionDetail.noContent}</ReactMarkdown>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </CardContent>

                {!isEditing && (
                  <div className="border-t border-slate-100 bg-slate-50/50 p-4">
                    <div className="flex items-end gap-3">
                      <div className="flex-1">
                        <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">{t.sectionDetail.aiFeedback}</label>
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
                          placeholder={t.sectionDetail.feedbackPlaceholder}
                          className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                        />
                      </div>
                      <Button onClick={submitFeedback} disabled={isRegenerating || !feedback.trim()}>
                        {isRegenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                        {t.sectionDetail.regenerate}
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            )}

            {tab === "validation" && (
              <Card className="border-slate-200/60 shadow-lg rounded-3xl overflow-hidden">
                <CardHeader className="bg-slate-50/50 border-b border-slate-100/60 flex flex-row items-center justify-between gap-4">
                  <div>
                    <h2 className="font-serif text-lg text-slate-800">{t.sectionDetail.outputValidation}</h2>
                    <p className="text-xs text-slate-500">{t.sectionDetail.validationSubtitle}</p>
                  </div>
                  <Button size="sm" variant="outline" onClick={loadValidation} disabled={validationLoading}>
                    {validationLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    {t.sectionDetail.reRun}
                  </Button>
                </CardHeader>
                <CardContent className="p-6 space-y-6">
                  {validationLoading && !validation ? (
                    <div className="flex items-center justify-center h-32 text-slate-500">
                      <Loader2 className="w-5 h-5 animate-spin mr-2" />
                      {t.sectionDetail.validating}
                    </div>
                  ) : !validation ? (
                    <div className="text-center py-10 text-slate-500 text-sm">{t.sectionDetail.noValidationRun}</div>
                  ) : (
                    <>
                      <div className="flex items-center gap-4">
                        <div className="text-3xl font-bold font-serif text-slate-800">{validation.score}%</div>
                        <div className="text-sm text-slate-500">
                          {t.sectionDetail.errorsWarningsGaps
                            .replace("{errors}", String(validation.checks.filter((c) => c.level === "error").length))
                            .replace("{warnings}", String(validation.checks.filter((c) => c.level === "warn").length))
                            .replace("{gaps}", String(validation.open_gaps))}
                        </div>
                      </div>

                      {validation.checks.length === 0 ? (
                        <div className="flex items-center gap-2 text-emerald-700 text-sm font-medium">
                          <CheckCircle2 className="w-4 h-4" /> {t.sectionDetail.allChecksPassed}
                        </div>
                      ) : (
                        <ul className="space-y-2">
                          {validation.checks.map((c, i) => (
                            <li key={i} className="flex items-start gap-2.5 text-sm">
                              {c.level === "error" ? (
                                <XCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                              ) : (
                                <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                              )}
                              <span className="text-slate-700">
                                {c.message}
                                {c.line && <span className="text-slate-400"> {t.sectionDetail.lineN.replace("{n}", String(c.line))}</span>}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}

                      <div className="prose prose-sm prose-slate max-w-none prose-headings:font-serif border-t border-slate-100 pt-4">
                        <ReactMarkdown>{validation.narrative}</ReactMarkdown>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default function DocumentWorkspacePage() {
  return (
    <Suspense>
      <DocumentWorkspacePageInner />
    </Suspense>
  );
}
