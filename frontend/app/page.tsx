"use client";

import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  UploadCloud,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  Wifi,
  WifiOff,
  Folder,
  FolderOpen,
  MessageSquare,
  ClipboardCheck,
  Pill,
  Save,
  Loader2,
  ChevronDown,
} from "lucide-react";
import { toast } from "sonner";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { DossierTreePanel } from "@/components/dossier-tree";

interface ProductContext {
  product_name: string;
  active_ingredient: string;
  dosage_form: string;
  strength: string;
  applicant: string;
  market: string;
}

const EMPTY_CONTEXT: ProductContext = {
  product_name: "",
  active_ingredient: "",
  dosage_form: "",
  strength: "",
  applicant: "",
  market: "",
};

// Field metadata drives the form so we don't hand-write six near-identical inputs.
const CONTEXT_FIELDS: { key: keyof ProductContext; label: string; placeholder: string }[] = [
  { key: "product_name", label: "Product name", placeholder: "e.g. Povidone Oral Tablet" },
  { key: "active_ingredient", label: "Active ingredient(s)", placeholder: "e.g. Povidone" },
  { key: "dosage_form", label: "Dosage form", placeholder: "e.g. Tablet" },
  { key: "strength", label: "Strength", placeholder: "e.g. 500 mg" },
  { key: "applicant", label: "Applicant / manufacturer", placeholder: "e.g. Acme Pharma Ltd" },
  { key: "market", label: "Target market / authority", placeholder: "e.g. Uganda (NDA)" },
];

interface ProcessResponse {
  filename: string;
  extracted_chars: number;
  ocr_used: boolean;
  classification: {
    section_path: string;
    title: string;
    module: string;
    confidence: number;
    justification?: string;
  };
  summary?: string;
  key_points?: string[];
  dossier_folder: string;
}

interface DossierTreeSection {
  section_path: string;
  title: string;
  documents: { name: string; confidence: number; uploaded_at: string }[];
}

export interface DossierTree {
  module: string;
  sections: DossierTreeSection[];
}

const MAX_FILE_SIZE = 15 * 1024 * 1024;
// Empty by default: calls are same-origin relative paths, proxied server-side
// by Next.js rewrites to the internal backend (see next.config.ts). Set
// NEXT_PUBLIC_API_URL only to bypass the proxy and hit the backend directly.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, "") ?? "";

function getApiUrl(path: string) {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

async function readErrorMessage(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) {
      return payload.detail;
    }
  } catch {
    // Fall back to a generic error when the proxy returns a non-JSON response.
  }

  return `Request failed with status ${response.status}.`;
}

function confidenceProgressColor(confidence: number) {
  if (confidence >= 0.75) return "[&_[data-slot=progress-indicator]]:bg-emerald-500";
  if (confidence >= 0.4) return "[&_[data-slot=progress-indicator]]:bg-amber-500";
  return "[&_[data-slot=progress-indicator]]:bg-red-500";
}

function SectionBadge({ classification }: { classification: ProcessResponse["classification"] }) {
  return (
    <Badge
      variant="outline"
      className="bg-slate-50 border-slate-200 text-slate-800 px-3 py-1 rounded-full font-medium"
    >
      {classification.section_path} {classification.title}
    </Badge>
  );
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "analyzing" | "success" | "error">("idle");
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [dossierTree, setDossierTree] = useState<DossierTree[] | null>(null);
  const [context, setContext] = useState<ProductContext>(EMPTY_CONTEXT);
  const [savingContext, setSavingContext] = useState(false);
  const [flashName, setFlashName] = useState<string | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      try {
        const res = await fetch(getApiUrl("/health"), {
          cache: "no-store",
          signal: controller.signal,
        });
        setIsBackendOnline(res.ok);
      } catch {
        setIsBackendOnline(false);
      } finally {
        clearTimeout(timeoutId);
      }
    };

    checkHealth();

    const intervalId = setInterval(checkHealth, 60000);
    return () => clearInterval(intervalId);
  }, []);

  // Load the already-filed dossier + saved product context on mount so a
  // refresh doesn't start from zero — the backend filesystem is the source of truth.
  useEffect(() => {
    (async () => {
      try {
        const [treeRes, ctxRes] = await Promise.all([
          fetch(getApiUrl("/api/v1/dossier/tree")),
          fetch(getApiUrl("/api/v1/dossier/context")),
        ]);
        if (treeRes.ok) setDossierTree(await treeRes.json());
        if (ctxRes.ok) {
          const saved = await ctxRes.json();
          // Don't clobber anything the user already typed while this was loading.
          setContext((cur) =>
            Object.values(cur).some((v) => v)
              ? cur
              : { ...EMPTY_CONTEXT, ...saved },
          );
        }
      } catch {
        /* backend offline; the health check drives the offline messaging */
      }
    })();
  }, []);

  const saveContext = useCallback(async () => {
    setSavingContext(true);
    try {
      const res = await fetch(getApiUrl("/api/v1/dossier/context"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(context),
      });
      if (!res.ok) throw new Error("Failed to save product details.");
      toast.success("Product details saved.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save.");
    } finally {
      setSavingContext(false);
    }
  }, [context]);

  const handleUpload = useCallback(async (fileToUpload: File) => {
    setResult(null);
    setStatus("analyzing");

    const formData = new FormData();
    formData.append("file", fileToUpload);

    try {
      const res = await fetch(getApiUrl("/api/v1/documents/process"), {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        if (res.status === 503 || res.status === 504) {
          setIsBackendOnline(false);
        }

        throw new Error(await readErrorMessage(res));
      }

      const data: ProcessResponse = await res.json();
      setResult(data);
      setStatus("success");
      setIsBackendOnline(true);
      setFlashName(data.filename);
      setTimeout(() => setFlashName(null), 1500);
      toast.success("Document filed");

      try {
        const treeRes = await fetch(getApiUrl("/api/v1/dossier/tree"));
        if (treeRes.ok) {
          const tree: DossierTree[] = await treeRes.json();
          setDossierTree(tree);
        } else {
          console.error("Failed to refresh dossier tree", treeRes.status);
        }
      } catch (treeErr) {
        console.error(treeErr);
      }
    } catch (err: unknown) {
      console.error(err);
      setStatus("error");
      setIsBackendOnline(false);
      toast.error(
        err instanceof Error
          ? err.message
          : "An error occurred during processing.",
      );
    }
  }, []);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const selectedFile = acceptedFiles[0];
      if (!selectedFile) return;

      if (
        selectedFile.type !== "application/pdf" &&
        selectedFile.type !==
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document" &&
        !selectedFile.name.endsWith(".pdf") &&
        !selectedFile.name.endsWith(".docx")
      ) {
        toast.error("Unsupported file type. Please upload a PDF or DOCX.");
        return;
      }

      if (selectedFile.size > MAX_FILE_SIZE) {
        toast.error("File too large. Please upload a PDF or DOCX under 15MB.");
        return;
      }

      setFile(selectedFile);
      await handleUpload(selectedFile);
    },
    [handleUpload],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
    },
    maxFiles: 1,
  });

  const reset = () => {
    setFile(null);
    setResult(null);
    setStatus("idle");
  };

  return (
    <TooltipProvider delay={200}>
      <div className="min-h-screen bg-slate-50/50 text-slate-900 p-6 pb-0 md:p-12 md:pb-0 font-sans selection:bg-indigo-100 selection:text-indigo-900 flex flex-col relative overflow-hidden">
        {/* Decorative background grid and blurs */}
        <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-full bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>
          <div className="absolute -top-[300px] left-[50%] -translate-x-1/2 w-[800px] h-[600px] bg-indigo-500/10 rounded-full blur-[100px]"></div>
          <div className="absolute top-[20%] right-[-10%] w-[500px] h-[500px] bg-violet-500/10 rounded-full blur-[100px]"></div>
        </div>
        <header className="w-full mx-auto relative z-10 flex flex-col items-center justify-center pt-10 pb-16 md:pt-16 md:pb-24">
          {/* Top Right Badges (absolute on desktop, absolute on mobile top-right) */}
          <div className="absolute top-4 right-4 md:top-0 md:right-0 flex items-center gap-3 z-50">
            <Link
              href="/chat"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider border border-indigo-200 bg-indigo-50 text-indigo-700 shadow-sm hover:bg-indigo-100 transition-colors"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Chat with Aicyclinder</span>
              <span className="sm:hidden">Chat</span>
            </Link>
            <Link
              href="/review"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider border border-emerald-200 bg-emerald-50 text-emerald-700 shadow-sm hover:bg-emerald-100 transition-colors"
            >
              <ClipboardCheck className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Review Documents</span>
              <span className="sm:hidden">Review</span>
            </Link>
            {isBackendOnline !== null && (
              <Tooltip>
                <TooltipTrigger
                  className={
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider border shadow-sm transition-colors outline-none cursor-pointer " +
                    (isBackendOnline
                      ? "bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100"
                      : "bg-red-50 border-red-200 text-red-700 hover:bg-red-100")
                  }
                >
                  {isBackendOnline ? (
                    <Wifi className="w-3.5 h-3.5" />
                  ) : (
                    <WifiOff className="w-3.5 h-3.5" />
                  )}
                  <span className="hidden sm:inline">
                    {isBackendOnline ? "System Online" : "System Offline"}
                  </span>
                  <span className="sm:hidden">
                    {isBackendOnline ? "Online" : "Offline"}
                  </span>
                </TooltipTrigger>
                <TooltipContent
                  side="bottom"
                  className="bg-slate-800 text-white border-none shadow-xl max-w-xs text-center"
                >
                  {isBackendOnline
                    ? "Backend is connected and ready to process documents."
                    : "Cannot reach the analysis server. Please ensure the backend is running."}
                </TooltipContent>
              </Tooltip>
            )}
          </div>

          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            className="flex flex-col items-center justify-center gap-6"
          >
            <div className="text-center space-y-2">
              <h1 className="font-serif text-5xl sm:text-7xl md:text-[5.5rem] font-bold text-slate-900 tracking-tight leading-none">
                Feyti
              </h1>
              <p className="text-sm sm:text-base text-slate-500 font-medium tracking-[0.2em] uppercase mt-2">
                Regulatory Document Intelligence
              </p>
            </div>
          </motion.div>
        </header>

        {/* Product context — starting details that ground the whole dossier */}
        <section className="w-full max-w-6xl mx-auto pb-8 relative z-10">
          <details open className="group rounded-3xl border border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-xl shadow-indigo-100/20 overflow-hidden">
            <summary className="flex items-center justify-between gap-3 cursor-pointer list-none select-none px-6 sm:px-8 py-5 bg-slate-50/50 border-b border-slate-100/60">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-600">
                  <Pill className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-serif text-lg text-slate-800">Product details</h3>
                  <p className="text-sm text-slate-500">
                    Fill these in first — they ground classification and every generated document.
                  </p>
                </div>
              </div>
              <ChevronDown className="w-5 h-5 text-slate-400 transition-transform group-open:rotate-180" />
            </summary>

            <div className="p-6 sm:p-8">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {CONTEXT_FIELDS.map((f) => (
                  <label key={f.key} className="flex flex-col gap-1.5">
                    <span className="text-xs font-medium text-slate-600">{f.label}</span>
                    <input
                      type="text"
                      value={context[f.key]}
                      placeholder={f.placeholder}
                      onChange={(e) =>
                        setContext((prev) => ({ ...prev, [f.key]: e.target.value }))
                      }
                      className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                    />
                  </label>
                ))}
              </div>
              <div className="mt-5 flex justify-end">
                <Button onClick={saveContext} disabled={savingContext} size="sm">
                  {savingContext ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  Save details
                </Button>
              </div>
            </div>
          </details>
        </section>

        <main className="flex-1 w-full max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-20 pb-12">
          {/* Left Column: Info & How it works */}
          <div className="lg:col-span-5 flex flex-col justify-center">
            <Badge className="w-fit mb-6 bg-emerald-100 text-emerald-800 hover:bg-emerald-200 border-none px-5 py-2 shadow-sm rounded-full text-sm font-semibold tracking-wide">
              <span className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-7" /> Powered by Feyti AIcyclinder
              </span>
            </Badge>

            <h2 className="text-4xl sm:text-5xl font-serif font-bold tracking-tight text-slate-900 mb-6 leading-[1.15]">
              Transform documents into{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-violet-500">
                actionable insights.
              </span>
            </h2>

            <p className="text-lg text-slate-600 mb-10 leading-relaxed font-light">
              Feyti extracts, classifies, and files your regulatory documents
              into the right CTD section.
            </p>

            <div className="space-y-8 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
              <div className="relative flex items-start gap-5">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-white border border-blue-200 shadow-sm flex items-center justify-center text-blue-600 z-10">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <div className="pt-1.5">
                  <h4 className="font-semibold text-slate-900 text-lg">
                    1. Upload
                  </h4>
                  <p className="text-slate-600 mt-1.5 leading-relaxed text-sm">
                    Drag and drop your PDF or DOCX file into the portal. The
                    pipeline handles scanned pages with OCR when needed.
                  </p>
                </div>
              </div>

              <div className="relative flex items-start gap-5">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-white border border-amber-200 shadow-sm flex items-center justify-center text-amber-500 z-10">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="pt-1.5">
                  <h4 className="font-semibold text-slate-900 text-lg">
                    2. Extract &amp; classify
                  </h4>
                  <p className="text-slate-600 mt-1.5 leading-relaxed text-sm">
                    Feyti reads the document, identifies the CTD section, and
                    scores the match so you can trust the filing.
                  </p>
                </div>
              </div>

              <div className="relative flex items-start gap-5">
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-white border border-purple-200 shadow-sm flex items-center justify-center text-purple-600 z-10">
                  <FolderOpen className="w-5 h-5" />
                </div>
                <div className="pt-1.5">
                  <h4 className="font-semibold text-slate-900 text-lg">
                    3. Filed into your dossier
                  </h4>
                  <p className="text-slate-600 mt-1.5 leading-relaxed text-sm">
                    The document lands in the correct module and folder, ready
                    for your submission dossier.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Interactive Card */}
          <div className="lg:col-span-7 flex flex-col justify-center">
            <AnimatePresence mode="wait">
              {status === "idle" || status === "error" ? (
                <motion.div
                  key="upload"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                >
                  <Card className="border-slate-200/60 shadow-2xl shadow-indigo-100/30 bg-white/80 backdrop-blur-xl overflow-hidden rounded-3xl">
                    <CardHeader className="bg-slate-50/50 border-b border-slate-100/60 pb-6 px-6 sm:px-8 pt-8">
                      <CardTitle className="text-2xl font-serif text-slate-800">
                        Upload a regulatory document
                      </CardTitle>
                      <CardDescription className="text-base mt-2">
                        Drop a PDF or DOCX below and Feyti will file it into
                        your CTD dossier.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="p-6 sm:p-8">
                      <div
                        {...getRootProps()}
                        className={`group relative w-full rounded-2xl border-2 border-dashed transition-all duration-300 ease-out cursor-pointer overflow-hidden p-8 sm:p-12
                          ${isDragActive ? "border-indigo-500 bg-indigo-50/50" : "border-slate-200 hover:border-indigo-400 hover:bg-slate-50/80"}`}
                      >
                        <input {...getInputProps()} />

                        <motion.div
                          initial={false}
                          animate={{ scale: isDragActive ? 1.05 : 1 }}
                          className="z-10 flex flex-col items-center text-center space-y-4"
                        >
                          <div
                            className={`p-4 rounded-2xl shadow-sm border transition-all duration-300 ${isDragActive ? "bg-indigo-500 border-indigo-600 text-white" : "bg-white border-slate-200 text-indigo-500 group-hover:scale-110"}`}
                          >
                            <UploadCloud
                              className="w-8 h-8"
                              strokeWidth={1.5}
                            />
                          </div>
                          <div>
                            <p className="text-lg font-medium text-slate-800 mb-1">
                              {isDragActive
                                ? "Drop the file to upload"
                                : "Click or drag file to this area"}
                            </p>
                            <p className="text-sm text-slate-500">
                              Strictly PDF or DOCX files allowed.
                            </p>
                          </div>
                        </motion.div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ) : status === "analyzing" ? (
                <motion.div
                  key="analyzing"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.05 }}
                  transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
                  className="h-full min-h-[500px] flex flex-col items-center justify-center text-center py-20 bg-white/50 backdrop-blur-md rounded-3xl border border-slate-200 shadow-2xl shadow-indigo-100/30"
                >
                  <div className="relative w-28 h-28 mb-8">
                    <div className="absolute inset-0 rounded-full border-4 border-slate-100" />
                    <motion.div
                      className="absolute inset-0 rounded-full border-4 border-t-indigo-600 border-r-transparent border-b-transparent border-l-transparent"
                      animate={{ rotate: 360 }}
                      transition={{
                        duration: 1.5,
                        repeat: Infinity,
                        ease: "linear",
                      }}
                    />
                    <div className="absolute inset-0 flex items-center justify-center text-indigo-600">
                      <RefreshCw
                        className="w-8 h-8 animate-pulse"
                        strokeWidth={1.5}
                      />
                    </div>
                  </div>
                  <h3 className="font-serif text-3xl text-slate-800 mb-3">
                    Analyzing Document
                  </h3>
                  <p className="text-slate-500 font-light text-lg flex items-center justify-center gap-2 max-w-sm px-6 truncate">
                    <FileText className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">{file?.name}</span>
                  </p>
                </motion.div>
              ) : status === "success" && result ? (
                <motion.div
                  key="result"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                >
                  <Card className="border-emerald-200 shadow-2xl shadow-emerald-100/40 bg-white overflow-hidden rounded-3xl">
                    <CardHeader className="bg-emerald-50/50 border-b border-emerald-100 pb-5 px-6 sm:px-8 pt-8 flex flex-row items-center justify-between">
                      <div className="space-y-1 overflow-hidden pr-4">
                        <CardTitle className="text-xl font-serif text-emerald-900 flex items-center gap-2">
                          <Sparkles className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                          Filed Successfully
                        </CardTitle>
                        <CardDescription className="text-emerald-700 font-medium truncate">
                          {result.filename}
                        </CardDescription>
                      </div>
                      <Badge
                        variant="outline"
                        className="bg-white border-emerald-200 text-emerald-700 shadow-sm px-3 py-1 flex-shrink-0 rounded-full"
                      >
                        {result.extracted_chars.toLocaleString()} chars
                      </Badge>
                    </CardHeader>

                    <CardContent className="p-6 sm:p-8">
                      <div className="space-y-6">
                        <div className="flex flex-wrap items-center gap-3">
                          <SectionBadge classification={result.classification} />
                          {result.ocr_used && (
                            <Badge
                              variant="secondary"
                              className="text-[10px] px-2 py-0.5 rounded-md"
                            >
                              OCR
                            </Badge>
                          )}
                        </div>

                        <div>
                          <div className="flex justify-between text-sm font-medium text-slate-700 mb-2">
                            <span>Confidence</span>
                            <span>
                              {Math.round(result.classification.confidence * 100)}%
                            </span>
                          </div>
                          <div
                            className={confidenceProgressColor(
                              result.classification.confidence,
                            )}
                          >
                            <Progress
                              value={Math.round(
                                result.classification.confidence * 100,
                              )}
                            />
                          </div>
                        </div>

                        <div className="flex items-center gap-3 text-sm text-slate-700 bg-slate-50 p-3 rounded-xl border border-slate-100">
                          <Folder className="w-4 h-4 text-slate-400 flex-shrink-0" />
                          <span className="font-medium truncate">
                            {result.dossier_folder}
                          </span>
                        </div>

                        {result.classification.justification && (
                          <p className="text-sm text-slate-600 leading-relaxed">
                            {result.classification.justification}
                          </p>
                        )}

                        {result.summary && (
                          <div className="pt-1">
                            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                              Summary
                            </p>
                            <p className="text-sm text-slate-700 leading-relaxed">
                              {result.summary}
                            </p>
                          </div>
                        )}

                        {result.key_points && result.key_points.length > 0 && (
                          <div className="pt-1">
                            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                              Key Points
                            </p>
                            <ul className="space-y-1.5">
                              {result.key_points.map((point, i) => (
                                <li
                                  key={i}
                                  className="flex items-start gap-2 text-sm text-slate-700"
                                >
                                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0" />
                                  <span className="leading-relaxed">{point}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </CardContent>

                    <CardFooter className="bg-slate-50 border-t border-slate-100 p-6">
                      <button
                        onClick={reset}
                        className="w-full py-3.5 bg-white border border-slate-200 rounded-xl text-slate-700 font-semibold hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-200 transition-all shadow-sm flex items-center justify-center gap-2"
                      >
                        <RefreshCw className="w-4 h-4" />
                        Upload Another Document
                      </button>
                    </CardFooter>
                  </Card>
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>
        </main>

        {/* Dossier tree panel */}
        <section className="w-full max-w-6xl mx-auto pb-12 relative z-10">
          <DossierTreePanel tree={dossierTree} flashName={flashName} />
        </section>

        {/* Footer */}
        <footer className="w-full max-w-6xl mx-auto py-6 mt-auto flex justify-center items-center border-t border-slate-200/60 relative z-10">
          <p className="text-sm text-slate-500 font-medium tracking-wide">
            © {new Date().getFullYear()}{" "}
            <span className="text-slate-900 font-semibold font-serif italic">
              Feyti AIcyclinder
            </span>
          </p>
        </footer>
      </div>
    </TooltipProvider>
  );
}
