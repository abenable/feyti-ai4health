"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

export type Language = "en" | "fr" | "pt" | "sw";

const en = {
  nav: {
    dashboard: "Dashboard",
    structure: "Structure",
    pv: "PV / ADR",
    regintel: "Reg Intel",
    literature: "Literature",
    chat: "Chat",
  },
  language: { label: "Language", switch: "Switch language" },
  pv: {
    title: "Pharmacovigilance",
    subtitle: "ADR / ICSR reporting",
    newReport: "New report",
    openReport: "Open report",
    save: "Save",
    create: "Create report",
    sourceDocument: "Source document",
    extract: "Extract",
    meddra: "MedDRA coding",
    followUps: "Follow-ups",
    expectedReactions: "Reference safety information",
    e2b: "E2B XML",
  },
  regintel: {
    title: "Regulatory Intelligence",
    subtitle: "African authority monitoring",
    refresh: "Refresh",
    crawlAll: "Crawl all",
    alerts: "Authority alerts",
    sources: "Authority sources",
    changes: "Changes",
    deadlines: "Compliance deadlines",
    impact: "Impact",
    add: "Add",
    crawl: "Crawl",
  },
  literature: {
    title: "Literature Search",
    subtitle: "Global and African sources",
    query: "Query",
    region: "Region",
    from: "From",
    to: "To",
    topics: "Topics",
    search: "Search",
    file: "File",
    pastSearches: "Past searches",
    replay: "Replay",
  },
} as const;

export type Dictionary = DeepWiden<typeof en>;

// Machine translations are intentionally conservative and pending domain review.
type Widen<T> = T extends string ? string : { [K in keyof T]: Widen<T[K]> };
type DeepWiden<T> = { [K in keyof T]: Widen<T[K]> };
const dictionaries: Record<Language, Dictionary> = {
  en,
  fr: {
    nav: {
      dashboard: "Tableau de bord",
      structure: "Structure",
      pv: "PV / RIM",
      regintel: "Veille réglementaire",
      literature: "Littérature",
      chat: "Discussion",
    },
    language: { label: "Langue", switch: "Changer de langue" },
    pv: {
      title: "Pharmacovigilance",
      subtitle: "Déclaration des EIM / RIM",
      newReport: "Nouvelle déclaration",
      openReport: "Ouvrir la déclaration",
      save: "Enregistrer",
      create: "Créer la déclaration",
      sourceDocument: "Document source",
      extract: "Extraire",
      meddra: "Codage MedDRA",
      followUps: "Suites",
      expectedReactions: "Informations de référence de sécurité",
      e2b: "XML E2B",
    },
    regintel: {
      title: "Veille réglementaire",
      subtitle: "Suivi des autorités africaines",
      refresh: "Actualiser",
      crawlAll: "Tout explorer",
      alerts: "Alertes des autorités",
      sources: "Sources des autorités",
      changes: "Modifications",
      deadlines: "Échéances de conformité",
      impact: "Impact",
      add: "Ajouter",
      crawl: "Explorer",
    },
    literature: {
      title: "Recherche documentaire",
      subtitle: "Sources mondiales et africaines",
      query: "Requête",
      region: "Région",
      from: "Du",
      to: "Au",
      topics: "Thèmes",
      search: "Rechercher",
      file: "Classer",
      pastSearches: "Recherches précédentes",
      replay: "Relancer",
    },
  },
  pt: {
    nav: {
      dashboard: "Painel",
      structure: "Estrutura",
      pv: "PV / RAM",
      regintel: "Inteligência regulatória",
      literature: "Literatura",
      chat: "Conversa",
    },
    language: { label: "Idioma", switch: "Mudar idioma" },
    pv: {
      title: "Farmacovigilância",
      subtitle: "Notificação de RAM / RIM",
      newReport: "Nova notificação",
      openReport: "Abrir notificação",
      save: "Guardar",
      create: "Criar notificação",
      sourceDocument: "Documento-fonte",
      extract: "Extrair",
      meddra: "Codificação MedDRA",
      followUps: "Acompanhamentos",
      expectedReactions: "Informações de referência de segurança",
      e2b: "XML E2B",
    },
    regintel: {
      title: "Inteligência regulatória",
      subtitle: "Monitorização de autoridades africanas",
      refresh: "Atualizar",
      crawlAll: "Pesquisar tudo",
      alerts: "Alertas de autoridades",
      sources: "Fontes de autoridades",
      changes: "Alterações",
      deadlines: "Prazos de conformidade",
      impact: "Impacto",
      add: "Adicionar",
      crawl: "Pesquisar",
    },
    literature: {
      title: "Pesquisa bibliográfica",
      subtitle: "Fontes globais e africanas",
      query: "Consulta",
      region: "Região",
      from: "De",
      to: "Até",
      topics: "Temas",
      search: "Pesquisar",
      file: "Arquivar",
      pastSearches: "Pesquisas anteriores",
      replay: "Repetir",
    },
  },
  sw: {
    nav: {
      dashboard: "Dashibodi",
      structure: "Muundo",
      pv: "PV / Tathmini ya Dawa",
      regintel: "Ufuatiliaji wa Kanuni",
      literature: "Fasihi",
      chat: "Mazungumzo",
    },
    language: { label: "Lugha", switch: "Badilisha lugha" },
    pv: {
      title: "Ufuatiliaji wa Madhara ya Dawa",
      subtitle: "Ripoti za matukio mabaya ya dawa",
      newReport: "Ripoti mpya",
      openReport: "Fungua ripoti",
      save: "Hifadhi",
      create: "Unda ripoti",
      sourceDocument: "Nyaraka ya asili",
      extract: "Toa taarifa",
      meddra: "Usimbaji wa MedDRA",
      followUps: "Ufuatiliaji",
      expectedReactions: "Taarifa za usalama za kurejelea",
      e2b: "XML ya E2B",
    },
    regintel: {
      title: "Ufuatiliaji wa Kanuni",
      subtitle: "Kufuatilia mamlaka za Afrika",
      refresh: "Onyesha upya",
      crawlAll: "Tafuta zote",
      alerts: "Tahadhari za mamlaka",
      sources: "Vyanzo vya mamlaka",
      changes: "Mabadiliko",
      deadlines: "Muda wa utiifu",
      impact: "Athari",
      add: "Ongeza",
      crawl: "Tafuta",
    },
    literature: {
      title: "Utafutaji wa Fasihi",
      subtitle: "Vyanzo vya kimataifa na Afrika",
      query: "Swali",
      region: "Eneo",
      from: "Kuanzia",
      to: "Hadi",
      topics: "Mada",
      search: "Tafuta",
      file: "Weka kwenye dosari",
      pastSearches: "Utafutaji uliopita",
      replay: "Rudia",
    },
  },
};

const LanguageContext = createContext<{
  language: Language;
  setLanguage: (language: Language) => void;
  t: Dictionary;
} | null>(null);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    if (typeof window === "undefined") return "en";
    const saved = window.localStorage.getItem("feyti-language") as Language | null;
    return saved && saved in dictionaries ? saved : "en";
  });

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
    window.localStorage.setItem("feyti-language", next);
    document.documentElement.lang = next;
  }, []);

  const value = useMemo(
    () => ({ language, setLanguage, t: dictionaries[language] }),
    [language, setLanguage]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("useLanguage must be used inside LanguageProvider");
  return context;
}
