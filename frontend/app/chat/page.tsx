"use client";

import { useState, useRef, useEffect, useCallback, KeyboardEvent } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  ArrowLeft,
  Bot,
  Sparkles,
  Loader2,
  Wifi,
  WifiOff,
  FlaskConical,
} from "lucide-react";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, "");

const SYSTEM_PROMPT =
  "You are Aicyclinder, a precise pharmaceutical regulatory assistant.";

const SUGGESTIONS = [
  "Draft Module 3.2.S.1.1 Nomenclature for Lamivudine including INN, IUPAC name, and CAS.",
  "Summarize the stability data requirements for a Module 3.2.P.8 submission.",
  "What sections belong in CTD Module 1 for a generic drug application?",
  "Explain the difference between a Type IA and Type IB variation.",
];

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

function getApiUrl(path: string) {
  if (!API_BASE_URL) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not configured. Set it in frontend/.env or frontend/.env.local and rebuild the frontend.",
    );
  }
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

type Mode = "aicyclinder" | "cloud";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isModelOnline, setIsModelOnline] = useState<boolean | null>(null);
  const [mode, setMode] = useState<Mode>("aicyclinder");
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Poll the selected backend's health through the proxy. Re-runs on mode change.
  useEffect(() => {
    const checkHealth = async () => {
      if (!API_BASE_URL) {
        setIsModelOnline(false);
        return;
      }
      try {
        const res = await fetch(
          getApiUrl(`/api/v1/chat/health?provider=${mode}`),
          { cache: "no-store" },
        );
        setIsModelOnline(res.ok);
      } catch {
        setIsModelOnline(false);
      }
    };
    setIsModelOnline(null);
    checkHealth();
    const id = setInterval(checkHealth, 30000);
    return () => clearInterval(id);
  }, [mode]);

  // Auto-scroll to the newest message.
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isSending]);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isSending) return;

      const nextMessages: ChatMessage[] = [
        ...messages,
        { role: "user", content: trimmed },
      ];
      setMessages(nextMessages);
      setInput("");
      setIsSending(true);

      try {
        const res = await fetch(getApiUrl("/api/v1/chat"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: [
              { role: "system", content: SYSTEM_PROMPT },
              ...nextMessages,
            ],
            max_new_tokens: 512,
            temperature: 0.0,
            provider: mode,
          }),
        });

        if (!res.ok) {
          if (res.status === 503) setIsModelOnline(false);
          throw new Error(await readErrorMessage(res));
        }

        const data: { response: string } = await res.json();
        setIsModelOnline(true);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.response || "*(empty response)*" },
        ]);
      } catch (err: unknown) {
        setMessages((prev) => prev.slice(0, -1)); // drop the unanswered user turn
        setInput(trimmed); // restore their text so they can retry
        toast.error(
          err instanceof Error ? err.message : "Failed to reach the model.",
        );
      } finally {
        setIsSending(false);
        textareaRef.current?.focus();
      }
    },
    [messages, isSending, mode],
  );

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 text-slate-900 flex flex-col relative overflow-hidden">
      {/* Decorative background */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-full bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
        <div className="absolute -top-[300px] left-[50%] -translate-x-1/2 w-[800px] h-[600px] bg-indigo-500/10 rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <header className="w-full max-w-4xl mx-auto px-6 pt-6 pb-4 relative z-10 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-lg shadow-indigo-200/50">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-serif text-2xl font-bold text-slate-900 leading-none">
              Aicyclinder
            </h1>
            <p className="text-xs text-slate-500 font-medium tracking-wide uppercase mt-1">
              Regulatory AI · Feyti
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Backend toggle — both modes are branded Aicyclinder. "Cloud" runs
              on the fallback provider; never surfaced by name. */}
          <div className="flex items-center p-0.5 rounded-full bg-slate-100 border border-slate-200 shadow-inner">
            {(
              [
                ["aicyclinder", "Fine-tuned"],
                ["cloud", "Cloud"],
              ] as [Mode, string][]
            ).map(([value, label]) => (
              <button
                key={value}
                onClick={() => setMode(value)}
                className={
                  "px-3 py-1 rounded-full text-xs font-semibold transition-colors " +
                  (mode === value
                    ? "bg-white text-indigo-700 shadow-sm"
                    : "text-slate-500 hover:text-slate-700")
                }
              >
                {label}
              </button>
            ))}
          </div>
          {isModelOnline !== null && (
            <span
              className={
                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider border shadow-sm " +
                (isModelOnline
                  ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                  : "bg-red-50 border-red-200 text-red-700")
              }
            >
              {isModelOnline ? (
                <Wifi className="w-3.5 h-3.5" />
              ) : (
                <WifiOff className="w-3.5 h-3.5" />
              )}
              <span className="hidden sm:inline">
                {isModelOnline ? "Model Online" : "Model Offline"}
              </span>
            </span>
          )}
          <Link
            href="/"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold text-slate-600 border border-slate-200 bg-white shadow-sm hover:bg-slate-50 hover:text-indigo-600 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Dossier</span>
          </Link>
        </div>
      </header>

      {/* Message thread */}
      <main className="flex-1 w-full max-w-4xl mx-auto px-4 sm:px-6 relative z-10 flex flex-col min-h-0">
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto py-6 space-y-6 scroll-smooth"
        >
          {messages.length === 0 && !isSending ? (
            <div className="h-full flex flex-col items-center justify-center text-center py-16">
              <div className="w-16 h-16 rounded-3xl bg-white border border-slate-200 shadow-sm flex items-center justify-center text-indigo-500 mb-6">
                <FlaskConical className="w-8 h-8" strokeWidth={1.5} />
              </div>
              <h2 className="font-serif text-2xl text-slate-800 mb-2">
                Ask Aicyclinder anything
              </h2>
              <p className="text-slate-500 max-w-md mb-8">
                Our fine-tuned regulatory model, trained on CTD dossiers. Try one
                of these to start:
              </p>
              <div className="grid sm:grid-cols-2 gap-3 w-full max-w-2xl">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="text-left text-sm text-slate-700 bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm hover:border-indigo-300 hover:bg-indigo-50/40 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {messages.map((m, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                  className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {m.role === "assistant" && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-sm mt-1">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}
                  <div
                    className={
                      m.role === "user"
                        ? "max-w-[80%] rounded-2xl rounded-tr-sm bg-indigo-600 text-white px-4 py-3 shadow-sm whitespace-pre-wrap"
                        : "max-w-[80%] rounded-2xl rounded-tl-sm bg-white border border-slate-200 px-4 py-3 shadow-sm"
                    }
                  >
                    {m.role === "user" ? (
                      m.content
                    ) : (
                      <div className="prose prose-sm prose-slate prose-headings:font-serif prose-p:leading-relaxed prose-pre:bg-slate-900 max-w-none">
                        <ReactMarkdown>{m.content}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          )}

          {isSending && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-3 justify-start"
            >
              <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-sm mt-1">
                <Bot className="w-4 h-4" />
              </div>
              <div className="rounded-2xl rounded-tl-sm bg-white border border-slate-200 px-4 py-3 shadow-sm flex items-center gap-2 text-slate-500">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
                <span className="text-sm">Aicyclinder is thinking…</span>
              </div>
            </motion.div>
          )}
        </div>

        {/* Composer */}
        <div className="pb-6 pt-2">
          <div className="flex items-end gap-3 bg-white border border-slate-200 rounded-2xl p-2 shadow-lg shadow-indigo-100/30 focus-within:border-indigo-400 transition-colors">
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask about a CTD section, a variation, a submission…"
              className="flex-1 resize-none bg-transparent px-3 py-2.5 outline-none text-slate-800 placeholder:text-slate-400 max-h-40 text-base"
            />
            <button
              onClick={() => send(input)}
              disabled={isSending || !input.trim()}
              className="flex-shrink-0 w-11 h-11 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-sm hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label="Send message"
            >
              {isSending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          <p className="text-center text-xs text-slate-400 mt-3 flex items-center justify-center gap-1.5">
            <Sparkles className="w-3 h-3" />
            Powered by Feyti AIcyclinder · responses may be imperfect
          </p>
        </div>
      </main>
    </div>
  );
}
