import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

type Lang = 'en' | 'it';

const translations = {
  en: {
    'nav.features': 'Features',
    'nav.pricing': 'Pricing',
    'nav.generator': 'Generator',
    'nav.signin': 'Sign In',
    'nav.signup': 'Sign Up',
    'nav.contacts': 'Contacts',
    'hero.badge': 'AI-Powered Cisco Network Generator',
    'hero.tagline': 'Cisco networks from plain-language descriptions',
    'hero.subtitle': 'Describe the network you need — NetTrace generates a',
    'hero.subtitle2': 'file ready to open in Cisco Packet Tracer. No commands. No manual configuration.',
    'hero.cta': 'Try the Generator',
    'hero.card1.title': 'Instant Generation',
    'hero.card1.desc': 'Write "3 routers with OSPF and 2 switches" — your .pkt file is ready in seconds.',
    'hero.card2.title': 'Auto-Configured',
    'hero.card2.desc': 'IPs, routing, VLANs and interfaces are all set up correctly, automatically.',
    'hero.card3.title': 'Cisco PT Ready',
    'hero.card3.desc': 'Compatible .pkt file — open it directly in Cisco Packet Tracer.',
    'features.title': 'Powerful Features for Professionals',
    'features.subtitle': 'Everything you need to simulate, trace and analyze complex networks — in one intuitive tool.',
    'pricing.title': 'Simple, Transparent Pricing',
    'pricing.subtitle': 'Choose the plan that fits your needs.',
    'pricing.free': 'Free',
    'pricing.free.desc': 'Perfect for students and hobbyists',
    'pricing.pro': 'Pro',
    'pricing.pro.desc': 'For professionals and teams',
    'pricing.mostPopular': 'Most Popular',
    'pricing.yearly': 'or €149.99 / year — save 17%',
    'pricing.cta.free': 'Get Started Free',
    'pricing.cta.pro': 'Get Started with Pro',
    'pricing.unlimitedNodes': 'Unlimited nodes',
    'pricing.unlimitedProjects': 'Unlimited projects',
    'pricing.basicTopologies': 'Basic topologies (Star, Bus)',
    'pricing.pktExport': 'PKT export only',
    'pricing.communitySupport': 'Community support',
    'pricing.fullApiAccess': 'Full API access',
    'pricing.advancedTopologies': 'Advanced topologies (Mesh, Ring)',
    'pricing.multipleExports': 'PKT, XML, JSON, CSV export',
    'pricing.prioritySupport': 'Priority support',
    'pricing.chatgptApi': 'ChatGPT 4.5 API integration',
    'pricing.questions': 'Questions?',
    'pricing.contact': 'Contact us',
    'generator.back': 'Back to Home',
    'generator.title': 'Cisco Network Generator',
    'generator.subtitle': 'Describe your network — get a',
    'generator.subtitle2': 'file ready for Cisco Packet Tracer.',
    'generator.authRequired': 'Authentication Required',
    'generator.loginPrompt': 'Please sign in or create an account to access the network generator.',
    'generator.signIn': 'Sign In',
    'generator.signUp': 'Sign Up',
    'lang.toggle': 'IT',
    'lang.label': 'Switch to Italian',
    'tour.btn': 'Guided Tour',
    'tour.step1.title': 'Quick Templates',
    'tour.step1.content': 'Pick a preset template to populate the description instantly — or write your own below.',
    'tour.step2.title': 'Network Description',
    'tour.step2.content': 'Describe your network in plain English or Italian. Mention the number of routers, subnets, hosts, and the routing protocol (RIP, OSPF, EIGRP…).',
    'tour.step3.title': 'Generate',
    'tour.step3.content': 'Click here to generate your Cisco Packet Tracer file. The AI will parse your description and produce a ready-to-open .pkt file.',
    'tour.step4.title': 'Results',
    'tour.step4.content': 'Your topology preview and download links will appear here once generation is complete.',
    'tour.back': 'Back', 'tour.close': 'Close', 'tour.last': 'Done', 'tour.next': 'Next', 'tour.skip': 'Skip tour',
  },
  it: {
    'nav.features': 'Funzionalità',
    'nav.pricing': 'Prezzi',
    'nav.generator': 'Generatore',
    'nav.signin': 'Accedi',
    'nav.signup': 'Registrati',
    'nav.contacts': 'Contatti',
    'hero.badge': 'Generatore di Reti Cisco con AI',
    'hero.tagline': 'Reti Cisco da descrizioni in linguaggio naturale',
    'hero.subtitle': 'Descrivi la rete che vuoi — NetTrace genera un file',
    'hero.subtitle2': 'pronto da aprire in Cisco Packet Tracer. Niente comandi. Niente configurazione manuale.',
    'hero.cta': 'Prova il Generatore',
    'hero.card1.title': 'Generazione Istantanea',
    'hero.card1.desc': 'Scrivi "3 router con OSPF e 2 switch" — il tuo file .pkt è pronto in secondi.',
    'hero.card2.title': 'Configurazione Automatica',
    'hero.card2.desc': 'IP, routing, VLAN e interfacce configurati correttamente in automatico.',
    'hero.card3.title': 'Pronto per Cisco PT',
    'hero.card3.desc': 'File .pkt compatibile — aprilo direttamente in Cisco Packet Tracer.',
    'features.title': 'Funzionalità Potenti per Professionisti',
    'features.subtitle': 'Tutto ciò di cui hai bisogno per simulare, tracciare e analizzare reti complesse.',
    'pricing.title': 'Prezzi Semplici e Trasparenti',
    'pricing.subtitle': 'Scegli il piano che fa per te.',
    'pricing.free': 'Gratuito',
    'pricing.free.desc': 'Perfetto per studenti e hobbisti',
    'pricing.pro': 'Pro',
    'pricing.pro.desc': 'Per professionisti e team',
    'pricing.mostPopular': 'Più Popolare',
    'pricing.yearly': 'oppure €149,99 / anno — risparmia il 17%',
    'pricing.cta.free': 'Inizia Gratis',
    'pricing.cta.pro': 'Inizia con Pro',
    'pricing.unlimitedNodes': 'Nodi illimitati',
    'pricing.unlimitedProjects': 'Progetti illimitati',
    'pricing.basicTopologies': 'Topologie base (Star, Bus)',
    'pricing.pktExport': 'Solo export PKT',
    'pricing.communitySupport': 'Supporto community',
    'pricing.fullApiAccess': 'Accesso API completo',
    'pricing.advancedTopologies': 'Topologie avanzate (Mesh, Ring)',
    'pricing.multipleExports': 'Export PKT, XML, JSON, CSV',
    'pricing.prioritySupport': 'Supporto prioritario',
    'pricing.chatgptApi': 'Integrazione API ChatGPT 4.5',
    'pricing.questions': 'Domande?',
    'pricing.contact': 'Contattaci',
    'generator.back': '← Home',
    'generator.title': 'Generatore di Reti Cisco',
    'generator.subtitle': 'Descrivi la tua rete — ricevi un file',
    'generator.subtitle2': 'pronto per Cisco Packet Tracer.',
    'generator.authRequired': 'Autenticazione Richiesta',
    'generator.loginPrompt': 'Accedi o crea un account per utilizzare il generatore di reti.',
    'generator.signIn': 'Accedi',
    'generator.signUp': 'Registrati',
    'lang.toggle': 'EN',
    'lang.label': 'Passa all\'inglese',
    'tour.btn': 'Tour Guidato',
    'tour.step1.title': 'Template Rapidi',
    'tour.step1.content': 'Scegli un template predefinito per compilare subito la descrizione — oppure scrivi la tua rete da zero.',
    'tour.step2.title': 'Descrizione della Rete',
    'tour.step2.content': 'Descrivi la rete in italiano o inglese. Indica numero di router, subnet, host e il protocollo di routing (RIP, OSPF, EIGRP…).',
    'tour.step3.title': 'Genera',
    'tour.step3.content': 'Clicca qui per generare il file Cisco Packet Tracer. L\'AI analizzerà la descrizione e produrrà un file .pkt pronto da aprire.',
    'tour.step4.title': 'Risultati',
    'tour.step4.content': 'La preview della topologia e i link di download appariranno qui al termine della generazione.',
    'tour.back': 'Indietro', 'tour.close': 'Chiudi', 'tour.last': 'Fine', 'tour.next': 'Avanti', 'tour.skip': 'Salta tour',
  },
} satisfies Record<Lang, Record<string, string>>;

type TranslationKey = keyof typeof translations.en;

interface LanguageContextType {
  lang: Lang;
  toggle: () => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextType | null>(null);

function detectLang(): Lang {
  const nav = navigator.language?.toLowerCase() ?? '';
  return nav.startsWith('it') ? 'it' : 'en';
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(detectLang);

  const toggle = useCallback(() => setLang((l) => (l === 'en' ? 'it' : 'en')), []);

  const t = useCallback(
    (key: TranslationKey): string => translations[lang][key] ?? translations.en[key] ?? key,
    [lang],
  );

  return <LanguageContext.Provider value={{ lang, toggle, t }}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextType {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used inside LanguageProvider');
  return ctx;
}
