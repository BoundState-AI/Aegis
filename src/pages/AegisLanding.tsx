import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { LanguageToggle } from "@/components/ui/language-toggle";

function Counter({ end, duration = 2000, delay = 0 }: { end: string; duration?: number; delay?: number }) {
  const [count, setCount] = useState(0);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setStarted(true), delay + 600);
    return () => clearTimeout(timer);
  }, [delay]);

  useEffect(() => {
    if (!started) return;
    const num = parseInt(end, 10);
    const step = Math.ceil(num / (duration / 16));
    let current = 0;
    const interval = setInterval(() => {
      current += step;
      if (current >= num) {
        setCount(num);
        clearInterval(interval);
      } else {
        setCount(current);
      }
    }, 16);
    return () => clearInterval(interval);
  }, [started, end, duration]);

  return <span>{count.toLocaleString()}</span>;
}

export default function AegisLanding() {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);
  const [hoveredPath, setHoveredPath] = useState<string | null>(null);

  const STATS = [
    { value: "260", label: t('landing.stats.compounds'), delay: 0 },
    { value: "732", label: t('landing.stats.pathways'), delay: 100 },
    { value: "328", label: t('landing.stats.papers'), delay: 200 },
  ];

  const PATHS = [
    {
      id: "regulatory",
      icon: "§",
      title: t('landing.regulatory.title'),
      subtitle: t('landing.regulatory.subtitle'),
      description: t('landing.regulatory.description'),
      features: t('landing.regulatory.features', { returnObjects: true }) as string[],
      cta: t('landing.regulatory.cta'),
      href: "/regulatory",
      accent: "#0097e0",
    },
    {
      id: "litigation",
      icon: "⚖",
      title: t('landing.litigation.title'),
      subtitle: t('landing.litigation.subtitle'),
      description: t('landing.litigation.description'),
      features: t('landing.litigation.features', { returnObjects: true }) as string[],
      cta: t('landing.litigation.cta'),
      href: "/litigation",
      accent: "#0099cc",
    },
  ];

  useEffect(() => {
    setTimeout(() => setVisible(true), 100);
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#FAFAF8",
        fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
        color: "#1a1a1a",
        overflow: "hidden",
      }}
    >
      <style>{`
        /* Daikin font stack: Helvetica/Arial/Meiryo — no external fonts needed */

        .aegis-landing * { margin: 0; padding: 0; box-sizing: border-box; }

        .fade-up {
          opacity: 0;
          transform: translateY(24px);
          transition: opacity 0.8s ease, transform 0.8s ease;
        }
        .fade-up.visible {
          opacity: 1;
          transform: translateY(0);
        }

        .path-card {
          background: white;
          border: 1px solid #e8e6e1;
          border-radius: 2px;
          padding: 3rem 2.5rem;
          cursor: pointer;
          transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
          position: relative;
          overflow: hidden;
        }
        .path-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 3px;
          transform: scaleX(0);
          transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
          transform-origin: left;
        }
        .path-card:hover {
          border-color: transparent;
          box-shadow: 0 8px 40px rgba(0,0,0,0.08), 0 1px 3px rgba(0,0,0,0.04);
          transform: translateY(-2px);
        }
        .path-card:hover::before {
          transform: scaleX(1);
        }
        .path-card.regulatory::before { background: #0097e0; }
        .path-card.litigation::before { background: #0099cc; }

        .stat-item {
          text-align: center;
          padding: 0 2rem;
        }
        .stat-item + .stat-item {
          border-left: 1px solid #d4d0c8;
        }

        .cta-button {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 2px;
          font-family: Helvetica, Arial, Meiryo, sans-serif;
          font-size: 0.85rem;
          font-weight: 500;
          letter-spacing: 0.03em;
          cursor: pointer;
          transition: all 0.3s ease;
          text-decoration: none;
          color: white;
        }
        .cta-button:hover {
          transform: translateX(4px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .explore-all {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 1rem 2.5rem;
          background: #0097e0;
          color: white;
          border: none;
          border-radius: 2px;
          font-family: Helvetica, Arial, Meiryo, sans-serif;
          font-size: 0.95rem;
          font-weight: 500;
          letter-spacing: 0.04em;
          cursor: pointer;
          transition: all 0.3s ease;
          text-decoration: none;
        }
        .explore-all:hover {
          background: #0099cc;
          box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }

        .feature-item {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          font-family: Helvetica, Arial, Meiryo, sans-serif;
          font-size: 0.85rem;
          color: #555;
          line-height: 1.5;
        }
        .feature-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          margin-top: 7px;
          flex-shrink: 0;
        }

        .trust-bar {
          font-family: Helvetica, Arial, Meiryo, sans-serif;
          font-size: 0.75rem;
          color: #999;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        @media (max-width: 768px) {
          .paths-grid { flex-direction: column !important; }
          .stats-row { flex-direction: column !important; gap: 1.5rem !important; }
          .stat-item { border-left: none !important; padding: 0 !important; }
          .stat-item + .stat-item { border-top: 1px solid #d4d0c8; padding-top: 1.5rem !important; }
          .path-card { padding: 2rem 1.5rem !important; }
          .hero-title { font-size: 2.4rem !important; }
        }
      `}</style>

      {/* Nav */}
      <nav
        className={`fade-up ${visible ? "visible" : ""}`}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "1.5rem 4rem",
          maxWidth: "1200px",
          margin: "0 auto",
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: "0.75rem" }}>
          <span
            style={{
              fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
              fontWeight: 600,
              fontSize: "1.1rem",
              letterSpacing: "0.12em",
              color: "#1a1a1a",
            }}
          >
            AEGIS
          </span>
          <span
            style={{
              fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
              fontSize: "0.7rem",
              color: "#999",
              letterSpacing: "0.06em",
            }}
          >
            by BoundState
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <LanguageToggle />
          <a
            href="/fate-explorer"
            style={{
              fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
              fontSize: "0.8rem",
              color: "#666",
              textDecoration: "none",
              letterSpacing: "0.04em",
              borderBottom: "1px solid transparent",
              paddingBottom: "2px",
              transition: "border-color 0.3s",
            }}
            onMouseEnter={(e) => ((e.target as HTMLElement).style.borderBottomColor = "#999")}
            onMouseLeave={(e) => ((e.target as HTMLElement).style.borderBottomColor = "transparent")}
          >
            {t('landing.goToPlatform')} →
          </a>
        </div>
      </nav>

      {/* Hero */}
      <section
        style={{
          maxWidth: "1200px",
          margin: "0 auto",
          padding: "5rem 4rem 3rem",
          textAlign: "center",
        }}
      >
        <div
          className={`fade-up ${visible ? "visible" : ""}`}
          style={{ transitionDelay: "0.15s" }}
        >
          <p
            style={{
              fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
              fontSize: "0.75rem",
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              color: "#0097e0",
              marginBottom: "1.5rem",
            }}
          >
            {t('landing.tagline')}
          </p>
        </div>

        <h1
          className={`fade-up hero-title ${visible ? "visible" : ""}`}
          style={{
            fontSize: "3.2rem",
            fontWeight: 400,
            lineHeight: 1.15,
            maxWidth: "800px",
            margin: "0 auto 1.5rem",
            transitionDelay: "0.25s",
            letterSpacing: "-0.01em",
          }}
        >
          {t('landing.heroLine1')}
          <br />
          <span style={{ fontStyle: "italic", fontWeight: 300 }}>
            {t('landing.heroLine2')}
          </span>
        </h1>

        <p
          className={`fade-up ${visible ? "visible" : ""}`}
          style={{
            fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
            fontSize: "1.05rem",
            lineHeight: 1.7,
            color: "#666",
            maxWidth: "620px",
            margin: "0 auto 3.5rem",
            transitionDelay: "0.35s",
          }}
        >
          {t('landing.heroDescription')}
        </p>

        {/* Stats */}
        <div
          className={`fade-up ${visible ? "visible" : ""}`}
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: "0",
            transitionDelay: "0.45s",
            marginBottom: "1rem",
          }}
        >
          <div className="stats-row" style={{ display: "flex", alignItems: "center" }}>
            {STATS.map((stat, i) => (
              <div key={i} className="stat-item">
                <div
                  style={{
                    fontSize: "2.4rem",
                    fontWeight: 500,
                    color: "#1a1a1a",
                    lineHeight: 1,
                    marginBottom: "0.35rem",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  <Counter end={stat.value} delay={stat.delay} />
                </div>
                <div
                  style={{
                    fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
                    fontSize: "0.75rem",
                    color: "#999",
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                  }}
                >
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Divider */}
      <div
        style={{
          maxWidth: "60px",
          height: "1px",
          background: "#d4d0c8",
          margin: "1rem auto 4rem",
        }}
      />

      {/* Two Paths */}
      <section
        style={{
          maxWidth: "1200px",
          margin: "0 auto",
          padding: "0 4rem 2rem",
        }}
      >
        <p
          className={`fade-up ${visible ? "visible" : ""}`}
          style={{
            fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
            fontSize: "0.75rem",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "#bbb",
            textAlign: "center",
            marginBottom: "2rem",
            transitionDelay: "0.55s",
          }}
        >
          {t('landing.twoPaths')}
        </p>

        <div
          className="paths-grid"
          style={{
            display: "flex",
            gap: "2rem",
          }}
        >
          {PATHS.map((path, i) => (
            <a
              key={path.id}
              href={path.href}
              className={`path-card fade-up ${path.id} ${visible ? "visible" : ""}`}
              style={{
                flex: 1,
                textDecoration: "none",
                color: "inherit",
                transitionDelay: `${0.6 + i * 0.1}s`,
              }}
              onMouseEnter={() => setHoveredPath(path.id)}
              onMouseLeave={() => setHoveredPath(null)}
            >
              <div
                style={{
                  fontSize: "1.8rem",
                  marginBottom: "1.25rem",
                  opacity: 0.8,
                }}
              >
                {path.icon}
              </div>

              <h3
                style={{
                  fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
                  fontSize: "1.5rem",
                  fontWeight: 400,
                  marginBottom: "0.35rem",
                }}
              >
                {path.title}
              </h3>

              <p
                style={{
                  fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
                  fontSize: "0.85rem",
                  color: path.accent,
                  marginBottom: "1.25rem",
                  fontWeight: 500,
                }}
              >
                {path.subtitle}
              </p>

              <p
                style={{
                  fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
                  fontSize: "0.9rem",
                  color: "#666",
                  lineHeight: 1.7,
                  marginBottom: "1.5rem",
                }}
              >
                {path.description}
              </p>

              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.6rem",
                  marginBottom: "2rem",
                }}
              >
                {path.features.map((f, j) => (
                  <div key={j} className="feature-item">
                    <div
                      className="feature-dot"
                      style={{ background: path.accent }}
                    />
                    <span>{f}</span>
                  </div>
                ))}
              </div>

              <div
                className="cta-button"
                style={{
                  background: path.accent,
                  display: "inline-flex",
                }}
              >
                {path.cta}
                <span style={{ transition: "transform 0.3s", transform: hoveredPath === path.id ? "translateX(4px)" : "none" }}>→</span>
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* Explore All */}
      <section
        style={{
          textAlign: "center",
          padding: "3.5rem 4rem 2rem",
        }}
      >
        <div
          className={`fade-up ${visible ? "visible" : ""}`}
          style={{ transitionDelay: "0.8s" }}
        >
          <p
            style={{
              fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
              fontSize: "1.15rem",
              fontStyle: "italic",
              color: "#888",
              marginBottom: "1.5rem",
              fontWeight: 300,
            }}
          >
            {t('landing.orGoStraight')}
          </p>
          <a href="/fate-explorer" className="explore-all">
            {t('landing.openFateExplorer')}
            <span>→</span>
          </a>
        </div>
      </section>

      {/* Trust / Bottom */}
      <section
        style={{
          maxWidth: "1200px",
          margin: "0 auto",
          padding: "4rem 4rem 2rem",
          textAlign: "center",
        }}
      >
        <div
          style={{
            height: "1px",
            background: "#e8e6e1",
            marginBottom: "2.5rem",
          }}
        />

        <div
          className="trust-bar"
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: "2.5rem",
            flexWrap: "wrap",
            marginBottom: "2rem",
          }}
        >
          <span>{t('landing.trust1')}</span>
          <span style={{ color: "#ddd" }}>·</span>
          <span>{t('landing.trust2')}</span>
          <span style={{ color: "#ddd" }}>·</span>
          <span>{t('landing.trust3')}</span>
        </div>

        <p
          style={{
            fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
            fontSize: "0.7rem",
            color: "#bbb",
            letterSpacing: "0.04em",
          }}
        >
          {t('landing.footer')}
        </p>
        <p
          style={{
            fontFamily: "Helvetica, Arial, Meiryo, sans-serif",
            fontSize: "0.75rem",
            color: "#ccc",
            fontStyle: "italic",
            marginTop: "0.35rem",
          }}
        >
          {t('landing.footerTagline')}
        </p>
      </section>
    </div>
  );
}
