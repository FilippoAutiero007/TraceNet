import { Helmet } from 'react-helmet-async';
import { useLanguage } from '@/context/LanguageContext';

interface SEOHeadProps {
  title?: string;
  description?: string;
  keywords?: string;
  ogImage?: string;
  ogUrl?: string;
  canonicalUrl?: string;
  type?: 'website' | 'article';
  noIndex?: boolean;
}

export function SEOHead({
  title,
  description,
  keywords,
  ogImage,
  ogUrl,
  canonicalUrl,
  type = 'website',
  noIndex = false,
}: SEOHeadProps) {
  const { lang } = useLanguage();
  
  const siteTitle = lang === 'it' ? 'NetTrace - Generatore di Reti Cisco con AI' : 'NetTrace - AI-Powered Cisco Network Generator';
  const siteDescription = lang === 'it' 
    ? 'Genera reti Cisco complesse in secondi. Descrivi la tua rete e ottieni file .pkt compatibili con Cisco Packet Tracer. Simulatore di rete con intelligenza artificiale.'
    : 'Generate complex Cisco networks in seconds. Describe your network and get .pkt files compatible with Cisco Packet Tracer. AI-powered network simulator.';
  const siteKeywords = lang === 'it'
    ? 'generatore reti cisco, network simulator, cisco packet tracer, simulazione rete, AI network generator, topologie di rete, configurazione automatica'
    : 'cisco network generator, network simulator, cisco packet tracer, network simulation, AI network generator, network topologies, automatic configuration';

  const finalTitle = title ? `${title} | ${siteTitle}` : siteTitle;
  const finalDescription = description || siteDescription;
  const finalKeywords = keywords || siteKeywords;
  const finalOgImage = ogImage || 'https://nettrace.app/og-image.jpg';
  const finalOgUrl = ogUrl || 'https://nettrace.app';
  const finalCanonicalUrl = canonicalUrl || 'https://nettrace.app';

  const structuredData = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": finalTitle,
    "description": finalDescription,
    "url": finalCanonicalUrl,
    "applicationCategory": "NetworkApplication",
    "operatingSystem": "Web",
    "offers": {
      "@type": "Offer",
      "price": "0",
      "priceCurrency": "EUR"
    },
    "creator": {
      "@type": "Organization",
      "name": "NetTrace",
      "url": finalCanonicalUrl
    },
    "featureList": [
      "AI-powered network generation",
      "Cisco Packet Tracer compatibility",
      "Automatic IP configuration",
      "Multiple topology support",
      "Real-time simulation"
    ]
  };

  const organizationData = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "NetTrace",
    "url": finalCanonicalUrl,
    "logo": "https://nettrace.app/logo.png",
    "contactPoint": {
      "@type": "ContactPoint",
      "contactType": "customer service",
      "url": "https://nettrace.app#contact"
    }
  };

  return (
    <Helmet>
      {/* Basic Meta Tags */}
      <title>{finalTitle}</title>
      <meta name="description" content={finalDescription} />
      <meta name="keywords" content={finalKeywords} />
      <meta name="author" content="Filippo Autiero" />
      <meta name="robots" content={noIndex ? "noindex,nofollow" : "index,follow"} />
      <meta name="language" content={lang === 'it' ? 'it-IT' : 'en-US'} />
      <meta name="geo.country" content="IT" />
      
      {/* Canonical URL */}
      <link rel="canonical" href={finalCanonicalUrl} />
      
      {/* Open Graph Meta Tags */}
      <meta property="og:type" content={type} />
      <meta property="og:title" content={finalTitle} />
      <meta property="og:description" content={finalDescription} />
      <meta property="og:image" content={finalOgImage} />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />
      <meta property="og:url" content={finalOgUrl} />
      <meta property="og:site_name" content="NetTrace" />
      <meta property="og:locale" content={lang === 'it' ? 'it_IT' : 'en_US'} />
      
      {/* Twitter Card Meta Tags */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={finalTitle} />
      <meta name="twitter:description" content={finalDescription} />
      <meta name="twitter:image" content={finalOgImage} />
      <meta name="twitter:creator" content="@nettraceapp" />
      
      {/* Technical Meta Tags */}
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <meta name="theme-color" content="#0891b2" />
      <meta name="msapplication-TileColor" content="#0891b2" />
      
      {/* Preconnect to external domains */}
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      
      {/* Structured Data */}
      <script type="application/ld+json">
        {JSON.stringify(structuredData)}
      </script>
      <script type="application/ld+json">
        {JSON.stringify(organizationData)}
      </script>
      
      {/* Favicon */}
      <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
      <link rel="icon" type="image/png" href="/favicon.png" />
      <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
      
      {/* Sitemap */}
      <link rel="sitemap" type="application/xml" href="/sitemap.xml" />
    </Helmet>
  );
}
