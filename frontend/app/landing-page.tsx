"use client";

import Link from "next/link";
import { useEffect, useRef, useState, useCallback } from "react";
import "./landing.css";

interface CardData {
  step: string;
  title: string;
  body: string;
  foot?: string;
}

const CARDS_DATA: CardData[] = [
  {
    step: "01 / 06",
    title: "Before the event",
    body: 'Three "independent" Tier-1 suppliers are flagged as likely sharing one Tier-3 source. Confidence 0.7 (illustrative).',
    foot: "Synthetic demo data",
  },
  {
    step: "02 / 06",
    title: "The event",
    body: "An export restriction lands on that source. The Sensor matches it to the right node in the graph.",
  },
  {
    step: "03 / 06",
    title: "The runway",
    body: "18 days of stock cover against 90 days to qualify a replacement. A 72-day gap. (Synthetic numbers.)",
    foot: "Synthetic demo data",
  },
  {
    step: "04 / 06",
    title: "The options",
    body: "The Action agent ranks a buffer buy, a plant reallocation, an expedite, or qualifying an alternate supplier.",
  },
  {
    step: "05 / 06",
    title: "The human",
    body: "A high-value step pauses. A person reviews the options and decides.",
  },
  {
    step: "06 / 06",
    title: "The record",
    body: "Every decision is logged with its reason, in a chain that shows if anyone tampers with it.",
  },
];

export default function LandingPage() {
  const heroRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const driftRef = useRef<HTMLDivElement>(null);
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [dragOffset, setDragOffset] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef(0);

  // Scroll animations for hero stage and drift artwork
  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    if (prefersReducedMotion) return;

    let ticking = false;

    const onScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          if (heroRef.current && stageRef.current) {
            const rect = heroRef.current.getBoundingClientRect();
            const scrollY = -rect.top;
            const maxScroll = rect.height - window.innerHeight;
            const p = Math.max(0, Math.min(1, maxScroll > 0 ? scrollY / maxScroll : 0));

            // Smooth easing
            const ease = (t: number) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t);
            const ep = ease(p);

            // Panel open: 0 to 52vw (clears the frame)
            stageRef.current.style.setProperty("--h-pan", String(ep * 52));
            // Scale down artwork: 1.2 to 1
            stageRef.current.style.setProperty("--h-scale", String(1.2 - ep * 0.2));
            // Wash opacity: 0 to 0.18
            stageRef.current.style.setProperty("--h-wash", String(ep * 0.18));
            // Wordmark scale: 1 to 1.35
            stageRef.current.style.setProperty("--h-wm-s", String(1 + ep * 0.35));
            // Wordmark letter-spacing: -0.02em to -0.06em
            stageRef.current.style.setProperty(
              "--h-wm-ls",
              `${-0.02 - ep * 0.04}em`
            );
            // Wordmark span translation: 0 to 150px
            stageRef.current.style.setProperty("--h-wm-x", String(ep * 150));
            // Dots translation: 0 to 40vw
            stageRef.current.style.setProperty("--h-dot", String(ep * 40));
          }

          if (driftRef.current) {
            const dr = driftRef.current.getBoundingClientRect();
            if (dr.top < window.innerHeight && dr.bottom > 0) {
              const scrollC = (window.innerHeight - dr.top) / 2;
              driftRef.current.style.setProperty("--s-drift", String(scrollC));
            }
          }
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const nextCard = useCallback(() => {
    setCurrentCardIndex((prev) => (prev + 1) % CARDS_DATA.length);
    setDragOffset(0);
  }, []);

  const prevCard = useCallback(() => {
    setCurrentCardIndex(
      (prev) => (prev - 1 + CARDS_DATA.length) % CARDS_DATA.length
    );
    setDragOffset(0);
  }, []);

  // Keyboard navigation for card deck
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowRight") {
      nextCard();
    } else if (e.key === "ArrowLeft") {
      prevCard();
    }
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    setIsDragging(true);
    dragStartRef.current = e.clientX;
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging) return;
    setDragOffset(e.clientX - dragStartRef.current);
  };

  const handlePointerUp = () => {
    if (!isDragging) return;
    setIsDragging(false);
    if (Math.abs(dragOffset) > 40) {
      nextCard();
    } else {
      setDragOffset(0);
    }
  };

  return (
    <div className="landing-root">
      {/* Navigation */}
      <nav aria-label="Main Navigation">
        <div className="wm-nav">
          Substrata<span className="amber">.</span>
        </div>
        <div className="nav-links label">
          <a href="#problem" className="label">Problem</a>
          <a href="#how" className="label">How it works</a>
          <a href="#agents" className="label">Agents</a>
          <a href="#timeline" className="label">Timeline</a>
        </div>
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <Link
            href="/dashboard/"
            className="nav-pill nav-pill-amber"
          >
            Open Workspace
          </Link>
          <a
            href="https://github.com/praju455/Substrata"
            target="_blank"
            rel="noopener noreferrer"
            className="nav-pill"
          >
            GitHub
          </a>
        </div>
      </nav>

      <main>
        {/* Portal Hero */}
        <section className="hero" id="hero" ref={heroRef}>
          <div className="hero-stage" id="hero-stage" ref={stageRef}>
            <svg
              className="hero-svg"
              id="hero-svg"
              preserveAspectRatio="xMidYMid slice"
              viewBox="0 0 1000 600"
              aria-label="Abstract strata cross-section showing shared tier-3 supplier"
            >
              <line
                x1="0"
                y1="200"
                x2="1000"
                y2="200"
                stroke="var(--c-ink)"
                strokeWidth="1"
                opacity="0.2"
              />
              <line
                x1="300"
                y1="200"
                x2="300"
                y2="400"
                stroke="var(--c-ink)"
                strokeWidth="1"
                opacity="0.3"
              />
              <line
                x1="500"
                y1="200"
                x2="500"
                y2="400"
                stroke="var(--c-ink)"
                strokeWidth="1"
                opacity="0.3"
              />
              <line
                x1="700"
                y1="200"
                x2="700"
                y2="400"
                stroke="var(--c-ink)"
                strokeWidth="1"
                opacity="0.3"
              />
              <path
                d="M0,250 Q250,260 500,240 T1000,250"
                fill="none"
                stroke="var(--c-ink)"
                strokeWidth="1"
                opacity="0.1"
              />
              <path
                d="M0,300 Q250,310 500,290 T1000,300"
                fill="none"
                stroke="var(--c-ink)"
                strokeWidth="1"
                opacity="0.05"
              />
              <path
                d="M0,350 Q250,340 500,360 T1000,350"
                fill="none"
                stroke="var(--c-ink)"
                strokeWidth="1"
                opacity="0.05"
              />

              <circle
                cx="500"
                cy="450"
                r="10"
                fill="var(--c-teal)"
                opacity="0.8"
              />
              <circle
                cx="500"
                cy="450"
                r="20"
                fill="none"
                stroke="var(--c-teal)"
                strokeWidth="1"
                opacity="0.5"
              />
              <line
                x1="300"
                y1="400"
                x2="490"
                y2="445"
                stroke="var(--c-ink)"
                strokeWidth="1"
                opacity="0.3"
              />
              <line
                x1="700"
                y1="400"
                x2="510"
                y2="445"
                stroke="var(--c-ink)"
                strokeWidth="1"
                opacity="0.3"
              />
              <line
                x1="500"
                y1="400"
                x2="500"
                y2="440"
                stroke="var(--c-amber)"
                strokeWidth="1"
                strokeDasharray="4,4"
              />
              <circle cx="500" cy="420" r="3" fill="var(--c-amber)" />
              <text
                x="510"
                y="423"
                fill="var(--c-amber)"
                fontSize="10"
                className="label"
                style={{ letterSpacing: "0.15em" }}
              >
                INFERRED
              </text>

              <text x="24" y="195" fill="var(--c-mute)" className="label">
                Tier 1
              </text>
              <text x="24" y="295" fill="var(--c-mute)" className="label">
                Tier 2
              </text>
              <text x="24" y="445" fill="var(--c-mute)" className="label">
                Tier 3 ... N
              </text>
            </svg>

            <div className="hero-wash" id="hero-wash" />
            <div className="hero-veil" />

            <div className="hero-panel left" id="panel-l">
              <span className="label">What the map shows</span>
            </div>
            <div className="hero-panel right" id="panel-r">
              <span className="label">What it doesn&apos;t</span>
            </div>

            <div className="hero-dots">
              <div className="dot amber" id="dot-l" />
              <div className="dot teal" id="dot-r" />
            </div>

            <h1 className="hero-wordmark" id="wordmark">
              <span className="wm-left" id="wm-l">SUB</span><span className="wm-right" id="wm-r">STRATA</span>
            </h1>

            <div className="meta tl label">Agentic early warning</div>
            <div className="meta tr label">
              SAP Hackfest &middot; Bengaluru 2026
            </div>
            <div className="meta bl label">Scroll to open</div>
            <div className="meta br label">Synthetic demo data</div>
          </div>
        </section>

        {/* Statement Fold */}
        <section className="statement" id="problem">
          <div className="statement-index">N</div>
          <div
            className="statement-drift"
            id="drift-art"
            ref={driftRef}
          >
            <svg viewBox="0 0 100 100" width="100%" height="100%">
              <circle
                cx="50"
                cy="50"
                r="48"
                fill="none"
                stroke="var(--c-ink)"
                opacity="0.2"
                strokeWidth="0.5"
              />
              <circle
                cx="30"
                cy="30"
                r="2"
                fill="var(--c-ink)"
                opacity="0.5"
              />
              <circle
                cx="70"
                cy="30"
                r="2"
                fill="var(--c-ink)"
                opacity="0.5"
              />
              <circle cx="50" cy="70" r="4" fill="var(--c-teal)" />
              <line
                x1="30"
                y1="30"
                x2="50"
                y2="70"
                stroke="var(--c-ink)"
                opacity="0.2"
              />
              <line
                x1="70"
                y1="30"
                x2="50"
                y2="70"
                stroke="var(--c-ink)"
                opacity="0.2"
              />
            </svg>
          </div>
          <div>
            <div
              className="label"
              style={{ color: "var(--c-mute)", marginBottom: "24px" }}
            >
              The problem
            </div>
            <p className="statement-text">
              Your suppliers look independent. Several of them quietly draw from{" "}
              <span className="amber">the same source</span>, two tiers down.
            </p>
          </div>
        </section>

        {/* How It Works (Deck Section) */}
        <section className="how" id="how">
          <div className="how-left">
            <h2>One event. Six steps. Weeks of warning.</h2>
            <p>
              Substrata infers which suppliers secretly share a source, measures
              how long before production is hit, and proposes governed fixes. A
              person approves anything high-stakes.
            </p>
            <div className="how-btns">
              <Link
                href="/dashboard/"
                className="btn label btn-amber"
              >
                Open Workspace
              </Link>
              <a
                href="https://github.com/praju455/Substrata"
                className="btn label"
                target="_blank"
                rel="noopener noreferrer"
              >
                Read the README
              </a>
              <a
                href="https://github.com/praju455/Substrata/tree/main/docs"
                className="btn label"
                target="_blank"
                rel="noopener noreferrer"
              >
                See the architecture
              </a>
            </div>
          </div>

          <div className="how-right">
            <div className="deck-hint label">
              Drag a card away, or use the arrow keys
            </div>
            <div id="deck-status" className="visually-hidden" aria-live="polite">
              Step {currentCardIndex + 1} of 6
            </div>
            <div
              tabIndex={0}
              onKeyDown={handleKeyDown}
              style={{
                position: "relative",
                width: "320px",
                height: "320px",
                outline: "none",
              }}
              role="region"
              aria-label="Walkthrough Step Cards"
            >
              {CARDS_DATA.map((card, i) => {
                const offset = i - currentCardIndex;
                if (offset < 0) return null;

                const translateX = offset * 12 + (offset === 0 ? dragOffset : 0);
                const translateY = offset * 12;
                const scale = 1 - offset * 0.05;
                const opacity = 1 - offset * 0.2;
                const zIndex = CARDS_DATA.length - offset;
                const rotate = offset === 0 ? dragOffset * 0.05 : 0;

                return (
                  <div
                    key={card.step}
                    className={`deck-card ${
                      offset === 0 && isDragging ? "dragging" : ""
                    }`}
                    style={{
                      transform: `translate(${translateX}px, ${translateY}px) scale(${scale}) rotate(${rotate}deg)`,
                      opacity,
                      zIndex,
                    }}
                    onPointerDown={offset === 0 ? handlePointerDown : undefined}
                    onPointerMove={offset === 0 ? handlePointerMove : undefined}
                    onPointerUp={offset === 0 ? handlePointerUp : undefined}
                    onClick={offset === 0 ? nextCard : undefined}
                    title="Drag away or click to advance"
                  >
                    <div className="card-num label">
                      Step {card.step}
                    </div>
                    <div className="card-title disp">{card.title}</div>
                    <div className="card-body">{card.body}</div>
                    {card.foot && (
                      <div className="card-foot label">{card.foot}</div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Agents Roster */}
        <section className="agents" id="agents">
          <div className="label agents-intro">
            Six roles. The math is plain code, never the model.
          </div>

          <div className="agent-row">
            <div className="ag-label label">Infers</div>
            <div className="ag-name disp">Mapper</div>
            <div className="ag-note label">LLM + rules</div>
          </div>
          <div className="agent-row">
            <div className="ag-label label">Listens</div>
            <div className="ag-name disp">Sensor</div>
            <div className="ag-note label">LLM + rules</div>
          </div>
          <div className="agent-row">
            <div className="ag-label label">Calculates</div>
            <div className="ag-name disp">Impact Engine</div>
            <div className="ag-note label">Plain code, no LLM</div>
          </div>
          <div className="agent-row">
            <div className="ag-label label">Proposes</div>
            <div className="ag-name disp">Action</div>
            <div className="ag-note label">Rules + LLM</div>
          </div>
          <div className="agent-row">
            <div className="ag-label label">Records</div>
            <div className="ag-name disp">Audit</div>
            <div className="ag-note label">Rules, append-only</div>
          </div>
          <div className="agent-row">
            <div className="ag-label label">Decides</div>
            <div className="ag-name disp">Human gate</div>
            <div className="ag-note label">A person</div>
          </div>
        </section>

        {/* Timeline Table */}
        <section className="timeline" id="timeline">
          <div className="tl-head label">
            <div>Date</div>
            <div>What happened or happens</div>
            <div style={{ textAlign: "right" }}>Kind</div>
          </div>

          <div className="tl-row">
            <div className="tl-date">30 Sep 2025</div>
            <div className="tl-desc">
              Dutch government takes control of Nexperia
            </div>
            <div className="tl-kind label">Real event</div>
          </div>
          <div className="tl-row">
            <div className="tl-date">04 Oct 2025</div>
            <div className="tl-desc">
              China restricts exports of Nexperia China output
            </div>
            <div className="tl-kind label">Real event</div>
          </div>
          <div className="tl-row">
            <div className="tl-date">29 Oct 2025</div>
            <div className="tl-desc">
              Honda suspends a Mexico plant, per press reports
            </div>
            <div className="tl-kind label">Real event</div>
          </div>
          <div className="tl-row">
            <div className="tl-date">21 Oct 2026</div>
            <div className="tl-desc">Hackfest registration closes</div>
            <div className="tl-kind label">Event rule</div>
          </div>
          <div className="tl-row">
            <div className="tl-date">TBD</div>
            <div className="tl-desc">
              Regional college round (ideas pitch)
            </div>
            <div className="tl-kind label">To be confirmed</div>
          </div>
          <div className="tl-row">
            <div className="tl-date">04 Nov 2026</div>
            <div className="tl-desc">
              Grand finale, New Horizon College of Engineering, Bengaluru
            </div>
            <div className="tl-kind label">Event rule</div>
          </div>
          <div className="tl-note">
            Real events are from public reporting. Everything Substrata shows on
            this page is a proposed design on synthetic data.
          </div>
        </section>
      </main>

      {/* Close (Footer) */}
      <footer className="close-sec">
        <h2 className="disp">See what your suppliers secretly share.</h2>
        <p>
          Proposal-stage project built for SAP Hackfest Bengaluru 2026. Demo data
          is synthetic. Not affiliated with or endorsed by SAP.
        </p>
        <div className="close-btns">
          <Link
            href="/dashboard/"
            className="btn label btn-amber"
          >
            Open Workspace
          </Link>
          <a
            href="https://github.com/praju455/Substrata"
            className="btn label"
            target="_blank"
            rel="noopener noreferrer"
          >
            View on GitHub
          </a>
          <a
            href="https://github.com/praju455/Substrata/tree/main/docs"
            className="btn label"
            target="_blank"
            rel="noopener noreferrer"
          >
            Read the research
          </a>
        </div>
        <div className="hairline" style={{ marginBottom: "24px" }} />
        <div className="close-wm">SUBSTRATA</div>
      </footer>
    </div>
  );
}
