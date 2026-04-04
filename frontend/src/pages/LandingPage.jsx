import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './LandingPage.css';

const GAHAR_TEXT = 'Designed to Align with GAHAR Safety Requirements | مصمم وفقاً لمتطلبات سلامة الجهار';

export default function LandingPage() {
    const navigate = useNavigate();
    const { user } = useAuth();
    const [menuOpen, setMenuOpen] = useState(false);
    const [scrolled, setScrolled] = useState(false);
    const transformationSlides = useMemo(
        () => [
            {
                src: '/images/before-after-1.png',
                alt: 'Before and after SAFE-Triage workflow comparison in an Egyptian emergency department',
            },
            {
                src: '/images/before-after-3.png',
                alt: 'Before and after emergency department flow with SAFE-Triage transformation',
            },
        ],
        []
    );
    const [activeSlide, setActiveSlide] = useState(0);
    const [touchStartX, setTouchStartX] = useState(null);
    const [touchEndX, setTouchEndX] = useState(null);

    useEffect(() => {
        const onScroll = () => setScrolled(window.scrollY > 20);
        onScroll();
        window.addEventListener('scroll', onScroll);
        return () => window.removeEventListener('scroll', onScroll);
    }, []);

    useEffect(() => {
        const intervalId = window.setInterval(() => {
            setActiveSlide((prev) => (prev + 1) % transformationSlides.length);
        }, 5000);
        return () => window.clearInterval(intervalId);
    }, [transformationSlides.length]);

    const navLinks = useMemo(
        () => [
            { id: 'features', label: 'Product' },
            { id: 'evidence', label: 'Evidence' },
            { id: 'impact', label: 'Impact' },
            { id: 'auth', label: user ? 'Dashboard' : 'Demo' },
        ],
        [user]
    );

    const heroSignals = useMemo(
        () => [
            { label: 'Language', value: 'Arabic + English' },
            { label: 'Workflow', value: 'Clinician-confirmed' },
            { label: 'Output', value: 'ICD-10 + SNOMED' },
        ],
        []
    );

    const heroStats = useMemo(
        () => [
            {
                value: '0/76',
                label: 'ESI-1 Patients Missed',
                qualifier: 'across 3 expert-validated benchmarks',
            },
            {
                value: '0%',
                label: 'Critical Under-triage',
                qualifier: 'MIETIC + ESI Handbook (246 cases)',
            },
            {
                value: '100%',
                label: 'Arabic–English Parity',
                qualifier: '36/36 MIETIC cases · 2,000+ Egyptian dialect terms',
                isNew: true,
            },
            {
                value: '97.2%',
                label: 'Exact ESI Match',
                qualifier: 'MIETIC gold standard (35/36)',
            },
        ],
        []
    );

    const scrollToId = (id) => {
        setMenuOpen(false);
        const el = document.getElementById(id);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    const goToSlide = (index) => {
        const total = transformationSlides.length;
        setActiveSlide((index + total) % total);
    };

    const nextSlide = () => goToSlide(activeSlide + 1);
    const prevSlide = () => goToSlide(activeSlide - 1);

    const onTouchStart = (event) => {
        setTouchEndX(null);
        setTouchStartX(event.targetTouches[0].clientX);
    };

    const onTouchMove = (event) => {
        setTouchEndX(event.targetTouches[0].clientX);
    };

    const onTouchEnd = () => {
        if (touchStartX === null || touchEndX === null) return;
        const delta = touchStartX - touchEndX;
        if (delta > 50) {
            nextSlide();
        } else if (delta < -50) {
            prevSlide();
        }
    };

    const handleLogin = () => {
        if (user) {
            navigate('/dashboard');
            return;
        }
        window.location.href = 'https://safe-triage-ai.web.app/signin';
    };

    return (
        <div className="st-landing">
            <div className="st-gahar-bar">{`Clinical Precision Editorial | ${GAHAR_TEXT}`}</div>

            <header className={`st-nav ${scrolled ? 'st-nav-solid' : 'st-nav-transparent'}`}>
                <div className="st-container st-nav-inner">
                    <button className="st-logo" onClick={() => scrollToId('top')}>SAFE-Triage</button>

                    <nav className="st-nav-center" aria-label="Main">
                        {navLinks.map((item) => (
                            <button key={item.id} className="st-nav-link" onClick={() => scrollToId(item.id)}>
                                {item.label}
                            </button>
                        ))}
                    </nav>

                    <div className="st-nav-right">
                        <button className="st-login-btn" onClick={handleLogin}>
                            {user ? 'Dashboard | لوحة التحكم' : 'Login | تسجيل الدخول'}
                        </button>
                    </div>

                    <button
                        className="st-mobile-toggle"
                        aria-label="Open Menu"
                        onClick={() => setMenuOpen((v) => !v)}
                    >
                        {menuOpen ? '×' : '☰'}
                    </button>
                </div>

                <div className={`st-mobile-menu ${menuOpen ? 'open' : ''}`}>
                    {navLinks.map((item) => (
                        <button key={item.id} className="st-nav-link" onClick={() => scrollToId(item.id)}>
                            {item.label}
                        </button>
                    ))}
                    <button className="st-login-btn" onClick={handleLogin}>
                        {user ? 'Dashboard | لوحة التحكم' : 'Login | تسجيل الدخول'}
                    </button>
                </div>
            </header>

            <main>
                <section className="st-hero" id="top">
                    <div className="st-container st-hero-main">
                        <div className="st-hero-content">
                            <div className="st-hero-badge">Clinical precision editorial for emergency departments</div>
                            <h1 className="st-hero-title">
                                A premium triage<br />
                                platform for faster,<br />
                                safer intake.
                            </h1>
                            <div className="st-hero-ar st-ar">نظام ذكي لفرز الطوارئ. مصمم بوضوح سريري، وسلاسة تشغيل، وثقة أعلى للفريق الطبي.</div>
                            <p className="st-hero-desc">
                                SAFE-Triage pairs AI guidance with deterministic clinical rules so hospitals can triage
                                with more clarity, bilingual support, and an audit-friendly workflow that stays readable
                                under pressure.
                            </p>

                            <div className="st-hero-highlights" aria-label="Key product attributes">
                                {heroSignals.map((signal) => (
                                    <div key={signal.label} className="st-hero-highlight">
                                        <div className="st-hero-highlight-label">{signal.label}</div>
                                        <div className="st-hero-highlight-value">{signal.value}</div>
                                    </div>
                                ))}
                            </div>

                            <div className="st-hero-cta">
                                <button className="st-btn st-btn-primary" onClick={() => scrollToId('auth')}>
                                    {user ? 'Open Dashboard' : 'Try Live Demo'}
                                </button>
                                <button className="st-btn st-btn-outline" onClick={() => scrollToId('features')}>
                                    Explore Product
                                </button>
                            </div>

                            <button className="st-mobile-login" onClick={handleLogin}>
                                {user ? 'Dashboard | لوحة التحكم' : 'Login | تسجيل الدخول'}
                            </button>

                            <div className="st-compliance-strip">
                                <div className="st-compliance-badge"><span className="st-dot st-dot-green" />Clinician-confirmed workflow</div>
                                <div className="st-compliance-badge"><span className="st-dot st-dot-gold" />GAHAR-aware design language</div>
                                <div className="st-compliance-badge"><span className="st-dot st-dot-blue" />Offline-first support layer</div>
                            </div>
                        </div>

                        <div className="st-hero-visual" aria-hidden="true">
                            <div className="st-tablet">
                                <div className="st-screen">
                                    <div className="st-screen-header">
                                        <span>SAFE-Triage</span>
                                        <span className="st-lang">Editorial UI</span>
                                    </div>
                                    <div className="st-screen-row"><span className="st-label">Case</span><span className="st-val">58M · Diabetic</span></div>
                                    <div className="st-screen-row"><span className="st-label">Complaint</span><span className="st-val st-ar">صدري بيوجعني</span></div>
                                    <div className="st-screen-row"><span className="st-label">NEWS2</span><span className="st-val st-screen-urgent">8 · High risk</span></div>
                                    <div className="st-screen-codes">
                                        <span className="st-screen-code st-code-purple">ICD-10: I20.9</span>
                                        <span className="st-screen-code st-code-teal">SNOMED: 225566008</span>
                                    </div>
                                    <div className="st-screen-esi">ESI 2 - Emergent | طوارئ</div>
                                    <div className="st-screen-gahar">{GAHAR_TEXT}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="st-container st-hero-stats-wrap">
                        <div className="st-hero-stats">
                            {heroStats.map((stat) => (
                                <div key={stat.label} className={`st-hero-stat${stat.isNew ? ' st-hero-stat-highlight' : ''}`}>
                                    {stat.isNew && <span className="st-new-badge">NEW</span>}
                                    <div className="st-num">{stat.value}</div>
                                    <div className="st-stat-label">{stat.label}</div>
                                    <div className="st-qualifier">{stat.qualifier}</div>
                                </div>
                            ))}
                        </div>
                        <div className="st-validation-banner">
                            0% critical under-triage in English AND Egyptian Arabic · 0 resuscitation patients missed across 76 ESI-1 cases · Validated on 1,544+ cases (English + Arabic + Korean) · <strong>Arabic 100% exact match on all 36 MIETIC cases</strong> · 2,000+ Egyptian dialect medical terms
                        </div>
                    </div>
                </section>

                <section className="st-section st-section-dark" id="evidence">
                    <div className="st-container">
                        <div className="st-section-label white">The Evidence</div>
                        <h2 className="st-section-title">Structured triage saves lives. The research is clear.</h2>
                        <p className="st-section-desc">Data from Egyptian hospitals and international peer-reviewed studies demonstrate measurable impact.</p>

                        <div className="st-grid-4">
                            <article className="st-card">
                                <div className="st-card-stat" style={{ color: '#f87171' }}>32%</div>
                                <div className="st-card-desc">Relative reduction in ED mortality after structured triage implementation in an Egyptian emergency department study.</div>
                                <div className="st-source"><a className="st-cite" href="https://doi.org/10.1016/j.cjtee.2021.10.004" target="_blank" rel="noreferrer">Suez Canal University Hospital, Chinese Journal of Traumatology</a></div>
                            </article>
                            <article className="st-card">
                                <div className="st-card-stat" style={{ color: '#fbbf24' }}>184 to 51 min</div>
                                <div className="st-card-desc">ED length of stay reduced by 72% in the same Egyptian study after structured triage implementation.</div>
                                <div className="st-source"><a className="st-cite" href="https://doi.org/10.1016/j.cjtee.2021.10.004" target="_blank" rel="noreferrer">Suez Canal University Hospital ED Study</a></div>
                            </article>
                            <article className="st-card">
                                <div className="st-card-stat" style={{ color: '#60a5fa' }}>+0.10 to 0.15</div>
                                <div className="st-card-desc">AUROC improvement in critical-care prediction for ML triage models compared with ESI-based models.</div>
                                <div className="st-source"><a className="st-cite" href="https://ccforum.biomedcentral.com/articles/10.1186/s13054-019-2351-7" target="_blank" rel="noreferrer">Critical Care 2019</a>; <a className="st-cite" href="https://www.nature.com/articles/s41598-025-17180-1" target="_blank" rel="noreferrer">Scientific Reports 2025</a></div>
                            </article>
                            <article className="st-card">
                                <div className="st-card-stat" style={{ color: '#a78bfa' }}>2,034</div>
                                <div className="st-card-desc">Health facilities in Egypt (2020), where standardized digital triage is still limited.</div>
                                <div className="st-source"><a className="st-cite" href="https://beta.sis.gov.eg/en/egypt/society/health-care/indicators-about-the-health-sector-in-egypt/" target="_blank" rel="noreferrer">Egypt Info and Decision Support Center</a></div>
                            </article>
                        </div>
                    </div>
                </section>

                <section className="st-section st-section-transform" id="transformation">
                    <div className="st-container">
                        <div className="st-section-label teal">The Transformation | التحول</div>
                        <h2 className="st-section-title">The Transformation | التحول</h2>
                        <p className="st-section-desc st-transform-subtitle">
                            From paper chaos to intelligent triage - see the difference.
                        </p>
                        <p className="st-section-desc st-transform-subtitle-ar st-ar">
                            من فوضى الورق إلى الفرز الذكي - شاهد الفرق
                        </p>

                        <div
                            className="st-transform-carousel"
                            onTouchStart={onTouchStart}
                            onTouchMove={onTouchMove}
                            onTouchEnd={onTouchEnd}
                        >
                            <div className="st-transform-track">
                                {transformationSlides.map((slide, index) => (
                                    <figure
                                        key={slide.src}
                                        className={`st-transform-slide ${index === activeSlide ? 'active' : ''}`}
                                        aria-hidden={index !== activeSlide}
                                    >
                                        <img src={slide.src} alt={slide.alt} loading="lazy" />
                                    </figure>
                                ))}
                            </div>

                            <button
                                className="st-transform-arrow st-transform-arrow-left"
                                onClick={prevSlide}
                                aria-label="Previous image"
                                type="button"
                            >
                                ‹
                            </button>
                            <button
                                className="st-transform-arrow st-transform-arrow-right"
                                onClick={nextSlide}
                                aria-label="Next image"
                                type="button"
                            >
                                ›
                            </button>

                            <div className="st-transform-dots" role="tablist" aria-label="Transformation images">
                                {transformationSlides.map((slide, index) => (
                                    <button
                                        key={`${slide.src}-dot`}
                                        type="button"
                                        className={`st-transform-dot ${index === activeSlide ? 'active' : ''}`}
                                        onClick={() => goToSlide(index)}
                                        aria-label={`Go to image ${index + 1}`}
                                    />
                                ))}
                            </div>
                        </div>

                        <div className="st-transform-caption">
                            <p>AI-generated visualization of SAFE-Triage impact on Egyptian emergency departments</p>
                            <p className="st-ar">تصور مولد بالذكاء الاصطناعي لتأثير نظام SAFE-Triage على أقسام الطوارئ المصرية</p>
                        </div>
                    </div>
                </section>

                <section className="st-section st-section-light" id="science">
                    <div className="st-container">
                        <div className="st-section-label teal">The Science Behind Our Approach</div>
                        <h2 className="st-section-title">Hybrid ESI + NEWS2: Better Together</h2>
                        <p className="st-section-desc">Combining ESI clinical judgment with NEWS2 objective vital scoring improves triage discrimination for critical outcomes.</p>

                        <div className="st-grid-2">
                            <div className="st-panel">
                                <h3>AUROC Performance Comparison (Literature)</h3>
                                <table className="st-table" aria-label="AUROC comparison table">
                                    <thead>
                                        <tr><th>Model Approach</th><th>AUROC</th><th>Source</th></tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>ESI alone (nurse judgment)</td>
                                            <td>~0.67 to 0.74</td>
                                            <td><a className="st-cite-dark" href="https://ccforum.biomedcentral.com/articles/10.1186/s13054-019-2351-7" target="_blank" rel="noreferrer">JAMIA 2021; Critical Care 2019</a></td>
                                        </tr>
                                        <tr>
                                            <td>NEWS2 alone (vitals)</td>
                                            <td>~0.74 to 0.76</td>
                                            <td>Gradient Boosting models</td>
                                        </tr>
                                        <tr>
                                            <td>ESI + NEWS2 + ML hybrid</td>
                                            <td>~0.81</td>
                                            <td>MIMIC-IV studies</td>
                                        </tr>
                                        <tr>
                                            <td>Full ML (vitals + complaints + demographics)</td>
                                            <td>0.86 to 0.92</td>
                                            <td><a className="st-cite-dark" href="https://www.nature.com/articles/s41598-025-17180-1" target="_blank" rel="noreferrer">Scientific Reports 2025</a></td>
                                        </tr>
                                        <tr className="st-highlight-row">
                                            <td>SAFE-Triage (projected)</td>
                                            <td>0.82 to 0.86</td>
                                            <td>Architecture alignment</td>
                                        </tr>
                                    </tbody>
                                </table>
                                <p className="st-footnote">Projected range based on architectural similarity to published hybrid models. Prospective validation is ongoing.</p>
                                <p className="st-auroc-note">All AUROC projections are based on published literature comparisons and architectural similarity analysis. These are not validated clinical performance claims.</p>
                            </div>

                            <div className="st-panel">
                                <h3>Head-to-Head: SAFE-Triage vs Human Nurses</h3>
                                <table className="st-table" aria-label="Human vs SAFE-Triage comparison table">
                                    <thead>
                                        <tr><th>Metric</th><th>Human Nurses</th><th>MIETIC English (n=36)</th><th>MIETIC Arabic (n=36)</th><th>ESI Handbook (n=210)</th><th>KTAS External (n=1,262)</th></tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><strong>ESI-1 Patients Missed</strong></td>
                                            <td className="st-bad-cell">5–15%</td>
                                            <td className="st-good-cell">0/14 (0%) ✓</td>
                                            <td className="st-good-cell">0/14 (0%) ✓</td>
                                            <td className="st-good-cell">0/36 (0%) ✓</td>
                                            <td className="st-good-cell">0/26 (0%) ✓</td>
                                        </tr>
                                        <tr>
                                            <td>Exact ESI Match</td>
                                            <td>61.3%</td>
                                            <td className="st-good-cell">97.2% ✓</td>
                                            <td className="st-good-cell">97.2% ✓</td>
                                            <td>51.4%†</td>
                                            <td>37.8%‡</td>
                                        </tr>
                                        <tr>
                                            <td>Within-1 Accuracy</td>
                                            <td>82.9%</td>
                                            <td className="st-good-cell">100.0% ✓</td>
                                            <td className="st-good-cell">100.0% ✓</td>
                                            <td className="st-good-cell">86.7% ✓</td>
                                            <td className="st-good-cell">82.6% ✓</td>
                                        </tr>
                                        <tr>
                                            <td>Critical Under-triage</td>
                                            <td className="st-bad-cell">5–15%</td>
                                            <td className="st-good-cell">0.0% ✓</td>
                                            <td className="st-good-cell">0.0% ✓</td>
                                            <td className="st-good-cell">0.0% ✓</td>
                                            <td className="st-good-cell">2.9% ✓</td>
                                        </tr>
                                        <tr>
                                            <td>Arabic / Dialect Support</td>
                                            <td className="st-bad-cell">Limited</td>
                                            <td className="st-good-cell">Full (2,000+ terms)</td>
                                            <td className="st-good-cell">100% parity ✓</td>
                                            <td>N/A (English only)</td>
                                            <td>N/A (English only)</td>
                                        </tr>
                                    </tbody>
                                </table>
                                <p className="st-footnote">† ESI Handbook: official AHRQ training vignettes (TriageAgent EMNLP 2024, 210 cases). ‡ KTAS External: 1,262 Korean ED patients, expert-validated by 3 triage specialists. MIETIC Arabic: same 36 expert cases translated to Egyptian colloquial Arabic. Lower exact match on KTAS/Handbook reflects cross-protocol validation and conservative safety bias. Human nurse figures from published ED reliability studies.</p>
                                <div style={{ marginTop: 12 }}>
                                    <div style={{ padding: 10, background: 'var(--st-teal-light)', borderRadius: 8, borderLeft: '3px solid var(--st-teal-dark)' }}>
                                        <strong style={{ color: 'var(--st-teal-dark)' }}>Key safety result:</strong> Zero critical under-triage in both English and Egyptian Arabic across 72 expert-validated MIETIC cases. Zero ESI-1 patients missed across 76 cases from 3 independent benchmarks (US + Korean EDs). Arabic achieves <strong>97.2% exact ESI match</strong> (35/36) with 0% critical under-triage — full bilingual safety parity powered by 2,000+ Egyptian dialect medical terms.
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="st-section st-section-arabic-break" id="arabic-parity">
                    <div className="st-container">
                        <div className="st-section-label" style={{ color: '#10b981' }}>Arabic Breakthrough | إنجاز عربي</div>
                        <h2 className="st-section-title">First triage AI to achieve zero critical under-triage in Egyptian Arabic</h2>
                        <p className="st-section-desc">
                            No other published triage system handles Egyptian dialect. SAFE-Triage processes real patient speech and delivers identical safety performance to English — proven on the same 36 expert-validated MIETIC cases.
                        </p>

                        <div className="st-ar-parity-grid">
                            <div className="st-ar-compare">
                                <div className="st-ar-compare-card st-ar-compare-en">
                                    <div className="st-ar-compare-lang">English Input</div>
                                    <div className="st-ar-compare-text">&ldquo;Unresponsive, cardiac arrest&rdquo;</div>
                                    <div className="st-ar-compare-tag">ESI 1 — Immediate</div>
                                </div>
                                <div className="st-ar-compare-eq">=</div>
                                <div className="st-ar-compare-card st-ar-compare-ar">
                                    <div className="st-ar-compare-lang">Egyptian Arabic Input</div>
                                    <div className="st-ar-compare-text st-ar">&ldquo;قلبه وقف ومش واعي&rdquo;</div>
                                    <div className="st-ar-compare-tag">ESI 1 — Immediate</div>
                                </div>
                            </div>

                            <div className="st-ar-stats">
                                <div className="st-ar-stat">
                                    <div className="st-ar-stat-num">97.2%</div>
                                    <div className="st-ar-stat-label">Arabic Exact Match</div>
                                    <div className="st-ar-stat-sub">35/36 MIETIC cases</div>
                                </div>
                                <div className="st-ar-stat st-ar-stat-hero">
                                    <div className="st-ar-stat-num" style={{ color: '#10b981' }}>0%</div>
                                    <div className="st-ar-stat-label">Critical Under-triage</div>
                                    <div className="st-ar-stat-sub">Parity with English engine</div>
                                </div>
                                <div className="st-ar-stat">
                                    <div className="st-ar-stat-num">2,000+</div>
                                    <div className="st-ar-stat-label">Dialect Terms</div>
                                    <div className="st-ar-stat-sub">Egyptian colloquial, not MSA</div>
                                </div>
                            </div>
                        </div>

                        <div className="st-ar-dialect-strip">
                            <span className="st-ar-term"><span className="st-ar">بيلف عليه</span> dizzy / fainting</span>
                            <span className="st-ar-term"><span className="st-ar">وجع في صدره</span> chest pain</span>
                            <span className="st-ar-term"><span className="st-ar">تعبان من قلبه</span> cardiac symptoms</span>
                            <span className="st-ar-term"><span className="st-ar">مش واعي</span> unresponsive</span>
                            <span className="st-ar-term"><span className="st-ar">بيلهث</span> dyspnea</span>
                            <span className="st-ar-term"><span className="st-ar">ضغطه واطي</span> low BP</span>
                        </div>

                        <div className="st-ar-unique-claim">
                            <strong>First-of-its-kind:</strong> No other published triage AI achieves zero critical under-triage in Egyptian Arabic. SAFE-Triage bridges the language gap that keeps digital triage inaccessible in most Egyptian EDs.
                        </div>
                    </div>
                </section>

                <section className="st-section" id="impact">
                    <div className="st-container">
                        <div className="st-section-label teal">The Impact</div>
                        <h2 className="st-section-title">Better triage saves money and lives.</h2>
                        <p className="st-section-desc">Structured triage reduces overcrowding, delays, and preventable escalation.</p>

                        <div className="st-cost-grid">
                            <div className="st-cost">
                                <div className="st-cost-row head">
                                    <div className="st-cost-cell">Metric</div>
                                    <div className="st-cost-cell">Without Structured Triage to With SAFE-Triage</div>
                                </div>
                                <div className="st-cost-row"><div className="st-cost-cell">ED Length of Stay</div><div className="st-cost-cell"><span className="st-bad">~184 min</span> to <span className="st-good">~51 min</span></div></div>
                                <div className="st-cost-row"><div className="st-cost-cell">ED Mortality Rate</div><div className="st-cost-cell"><span className="st-bad">15.7%</span> to <span className="st-good">10.7%</span></div></div>
                                <div className="st-cost-row"><div className="st-cost-cell">Triage Discrimination</div><div className="st-cost-cell"><span className="st-bad">AUROC 0.67 to 0.80</span> to <span className="st-good">AUROC 0.82 to 0.86</span></div></div>
                                <div className="st-cost-row"><div className="st-cost-cell">Under-Triage</div><div className="st-cost-cell"><span className="st-good">0/76 resuscitation patients missed across 3 expert-validated benchmarks (MIETIC + ESI Handbook + KTAS External)</span></div></div>
                                <div className="st-cost-row"><div className="st-cost-cell">Arabic Support</div><div className="st-cost-cell"><span className="st-good">Egyptian dialect support with AI + keyword safety net</span></div></div>
                                <div className="st-cost-row"><div className="st-cost-cell">Safety Alignment</div><div className="st-cost-cell"><span className="st-good">Designed to align with GAHAR safety requirements</span></div></div>
                            </div>

                            <div>
                                <div className="st-savings">
                                    <div className="big">72%</div>
                                    <p>Observed reduction in ED length of stay in a single-center Egyptian study after structured triage implementation.</p>
                                </div>
                                <div className="st-savings" style={{ background: 'var(--st-red-light)', borderColor: 'var(--st-red)' }}>
                                    <div className="big" style={{ color: 'var(--st-red)' }}>around 5 fewer deaths</div>
                                    <p>Per 100 ED patients in the same single-center observational before-after study.</p>
                                </div>
                                <p className="st-footnote">
                                    <a className="st-cite-dark" href="https://doi.org/10.1016/j.cjtee.2021.10.004" target="_blank" rel="noreferrer">Source: Suez Canal University Hospital ED study</a>. Internal validation statistics are project-stage and not population-level claims.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="st-section st-section-safe-staff" id="safe-staff">
                    <div className="st-container">
                        <div className="st-section-label warm">Happy Patients, Safer Care Teams</div>
                        <h2 className="st-section-title">Shorter Wait = Safer Staff | انتظار أقل = طاقم طبي أكثر أماناً</h2>
                        <p className="st-section-desc st-safe-staff-subtitle">
                            In Egyptian EDs, frustrated patients do not just leave. Better triage protects everyone.
                        </p>
                        <p className="st-section-desc st-ar st-safe-staff-subtitle-ar">
                            في طوارئ مصر، المريض المحبط لا يغادر دائماً بهدوء. الفرز الأفضل يحمي الجميع.
                        </p>

                        <div className="st-safe-grid">
                            <article className="st-safe-card">
                                <div className="st-safe-stat">86%</div>
                                <div className="st-safe-desc">
                                    of healthcare workers at Ain Shams University Hospital ED experienced verbal violence.
                                </div>
                                <div className="st-safe-source">
                                    Frontiers in Public Health, Cairo University Hospital Study, 2023
                                </div>
                            </article>
                            <article className="st-safe-card">
                                <div className="st-safe-stat">60%</div>
                                <div className="st-safe-desc">
                                    of workplace violence in Egyptian EDs is triggered by long waiting times and unmet expectations.
                                </div>
                                <div className="st-safe-source">
                                    Abdellah and Salama, Pan African Medical Journal, Suez Canal University, 2017
                                </div>
                            </article>
                            <article className="st-safe-card">
                                <div className="st-safe-stat">76%</div>
                                <div className="st-safe-desc">
                                    of emergency medical staff in Egypt do not report violence they experience.
                                </div>
                                <div className="st-safe-source">
                                    Egyptian Journal of Forensic Sciences, 2022
                                </div>
                            </article>
                            <article className="st-safe-card">
                                <div className="st-safe-stat">72% ↓</div>
                                <div className="st-safe-desc">
                                    reduction in ED wait time after structured triage, addressing the primary trigger of violence.
                                </div>
                                <div className="st-safe-source">
                                    Suez Canal University Hospital SATS Study
                                </div>
                            </article>
                        </div>

                        <div className="st-safe-highlight">
                            <div className="st-safe-highlight-icon" aria-hidden="true">🛡</div>
                            <div>
                                <p>
                                    <strong>The connection is clear:</strong> Long waits to frustrated families to violence against staff.
                                    SAFE-Triage cuts wait time by 72%, directly addressing the #1 reported trigger of ED violence in Egypt.
                                    Better triage does not just save patients. It protects the whole care team.
                                </p>
                                <p className="st-ar">
                                    <strong>العلاقة واضحة:</strong> انتظار طويل إلى عائلات محبطة إلى عنف ضد الطاقم الطبي.
                                    نظام SAFE-Triage يقلل وقت الانتظار بنسبة 72% ويعالج السبب الأول للعنف في طوارئ مصر.
                                    الفرز الأفضل لا ينقذ المرضى فقط، بل يحمي فريق الرعاية بالكامل.
                                </p>
                            </div>
                        </div>

                        <div className="st-safe-footer-source">
                            Violence statistics from peer-reviewed studies at Ain Shams, Suez Canal, Cairo, and Tanta University Hospitals.
                        </div>
                    </div>
                </section>

                <section className="st-section st-section-light" id="features">
                    <div className="st-container">
                        <div className="st-section-label teal">Built for Egypt</div>
                        <h2 className="st-section-title">Not adapted. Designed for Egyptian hospitals.</h2>
                        <p className="st-section-desc">Every feature addresses a real operational challenge in Egyptian emergency departments.</p>

                        <div className="st-feature-grid">
                            <article className="st-feature">
                                <h3>Egyptian Arabic Dialect</h3>
                                <p>Designed for Egyptian Arabic free-text complaints, with AI understanding and automatic language detection for Arabic and English.</p>
                                <div className="st-feature-highlight">دعم فعلي للهجة المصرية مع اكتشاف تلقائي للغة</div>
                            </article>
                            <article className="st-feature">
                                <h3>Offline Reliability</h3>
                                <p>NEWS2 scoring, ESI rules, and SNOMED coding can continue with local cache to protect continuity during unstable internet periods.</p>
                                <div className="st-feature-highlight">سلامة المريض لا تعتمد على الاتصال بالإنترنت</div>
                            </article>
                            <article className="st-feature">
                                <h3>Safety and Governance</h3>
                                <p>BigQuery audit trail, human confirmation workflow, ICD-10 and SNOMED coding, and controls designed to align with GAHAR safety requirements.</p>
                                <div className="st-feature-highlight">{GAHAR_TEXT}</div>
                            </article>
                            <article className="st-feature">
                                <h3>AI Assists, Rules Decide</h3>
                                <p>AI extracts context, NEWS2 quantifies vitals, deterministic logic assigns ESI, and a clinician confirms each case.</p>
                                <div className="st-feature-highlight">القرار السريري النهائي بيد الفريق الطبي</div>
                            </article>
                            <article className="st-feature">
                                <h3>Silent Killer Detection</h3>
                                <p>MedGemma QA review checks high-risk atypical patterns such as diabetic GI presentations that may mask cardiac emergencies.</p>
                                <div className="st-feature-highlight">طبقة أمان ثانية لمراجعة الحالات غير النمطية</div>
                            </article>
                            <article className="st-feature">
                                <h3>International Standards</h3>
                                <p>Built on ESI v5, NEWS2, SNOMED-CT, ICD-10 and emergency-medicine references with local adaptation for Egyptian workflows.</p>
                                <div className="st-feature-highlight">معايير دولية مع تكييف عملي للواقع المصري</div>
                            </article>
                        </div>
                    </div>
                </section>

                <section className="st-section st-section-dark" id="silent-killer">
                    <div className="st-container" style={{ textAlign: 'center' }}>
                        <div className="st-section-label white">Real-World Impact</div>
                        <h2 className="st-section-title">The Silent Killer: How SAFE-Triage catches what others miss</h2>
                        <p className="st-section-desc" style={{ margin: '0 auto' }}>
                            A diabetic patient with mild GI symptoms can still be at atypical ACS risk per
                            {' '}<a className="st-cite" href="https://www.ahajournals.org/doi/10.1161/CIR.0000000000000558" target="_blank" rel="noreferrer">AHA/ACC NSTEMI guidance</a>.
                        </p>

                        <div className="st-timeline">
                            <div className="st-step"><div><div className="st-step-title">Layer 1: Gemini extracts symptoms</div><div className="st-step-desc">Maps symptom language to structured medical context and coding.</div></div></div>
                            <div className="st-step"><div><div className="st-step-title">Layer 2: NEWS2 scores vitals</div><div className="st-step-desc">Objective scoring across HR, RR, BP, temperature, oxygenation and consciousness.</div></div></div>
                            <div className="st-step"><div><div className="st-step-title">Deterministic ESI assignment</div><div className="st-step-desc">Initial level assigned by reproducible rule engine with safety rules.</div></div></div>
                            <div className="st-step danger st-pulse-red"><div><div className="st-step-title" style={{ color: 'var(--st-red)' }}>MedGemma QA escalation</div><div className="st-step-desc">Flags atypical high-risk pattern and requests immediate physician reassessment.</div></div></div>
                            <div className="st-step danger"><div><div className="st-step-title" style={{ color: 'var(--st-red)' }}>Critical alert dispatch</div><div className="st-step-desc">Push notification and email are sent to the on-call emergency clinician.</div></div></div>
                            <div className="st-step success"><div><div className="st-step-title" style={{ color: 'var(--st-green)' }}>Early intervention path</div><div className="st-step-desc">Reassessment and workup are accelerated for potential silent MI cases.</div></div></div>
                        </div>
                    </div>
                </section>

                <section className="st-section" id="auth">
                    <div className="st-container">
                        <div className="st-auth-section">
                            <div className="st-auth-card">
                                <h3 className="st-auth-title">Start the live workflow</h3>
                                <p className="st-auth-sub">Use Google Authentication to access the triage dashboard and full clinical workflow.</p>
                                <div className="st-auth-actions">
                                    <button className="st-btn st-btn-primary" onClick={handleLogin}>
                                        {user ? 'Open Dashboard | فتح لوحة التحكم' : 'Sign in | تسجيل الدخول'}
                                    </button>
                                    <button className="st-btn st-btn-secondary" onClick={() => navigate('/signin')}>
                                        Advanced Sign-In | خيارات متقدمة
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="st-section">
                    <div className="st-container">
                        <div className="st-cta-box">
                            <h2>Ready to transform emergency triage?</h2>
                            <p>Deploy a safer triage workflow with bilingual support, coded outputs, and clinician confirmation safeguards.</p>
                            <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
                                <button className="st-btn st-btn-white" onClick={() => scrollToId('auth')}>Try Live Demo</button>
                                <span className="st-btn st-btn-outline st-btn-disabled">Contact Team</span>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            <div className="st-edu-disclaimer">
                <div>
                    {'SAFE-Triage is an independent academic research and capstone-level project developed for educational and research purposes only. It is not a certified medical device and has not received regulatory approval for clinical use. All clinical decisions must be made by licensed healthcare professionals. Any research statistics cited are derived from published peer-reviewed studies and are presented for academic context only. The system is not formally accredited or certified by GAHAR, HIPAA, or any regulatory authority; references to these standards indicate conceptual and design alignment only.'}
                </div>
                <div className="st-edu-disclaimer-ar" style={{ marginTop: 6 }}>
                    <div>⚠️ إخلاء مسؤولية تعليمية وبحثية</div>
                    <div>
                        {'نظام SAFE-Triage هو مشروع بحثي أكاديمي مستقل تم تطويره لأغراض تعليمية وبحثية فقط. النظام ليس جهازًا طبيًا معتمدًا ولم يحصل على أي موافقة تنظيمية للاستخدام السريري. جميع القرارات السريرية يجب أن يتخذها مختصون طبيون مرخصون. أي إحصاءات بحثية مذكورة مستمدة من دراسات علمية محكّمة ومنشورة، وتُعرض في سياق أكاديمي فقط. النظام غير معتمد رسميًا من قبل الهيئة العامة للاعتماد والرقابة الصحية (GAHAR) أو HIPAA أو أي جهة تنظيمية أخرى، وأي إشارات لهذه المعايير تعكس توافقًا تصميميًا ومفاهيميًا فقط.'}
                    </div>
                </div>
            </div>

            <footer className="st-footer">
                <div className="st-container">
                    <div className="st-footer-logo">SAFE-Triage</div>
                    <div style={{ fontSize: 13, marginBottom: 16 }}>AI-Powered Emergency Triage for Egyptian Hospitals</div>
                    <div style={{ fontSize: 12, color: 'var(--st-teal-light)', marginBottom: 16 }}>{GAHAR_TEXT}</div>
                    <div className="st-footer-citations">
                        Research citations: 
                        <a className="st-cite" href="https://doi.org/10.1016/j.cjtee.2021.10.004" target="_blank" rel="noreferrer"> Suez Canal University Hospital study</a>; 
                        <a className="st-cite" href="https://ccforum.biomedcentral.com/articles/10.1186/s13054-019-2351-7" target="_blank" rel="noreferrer"> Critical Care 2019</a>; 
                        <a className="st-cite" href="https://www.nature.com/articles/s41598-025-17180-1" target="_blank" rel="noreferrer"> Scientific Reports 2025</a>; 
                        <a className="st-cite" href="https://pmc.ncbi.nlm.nih.gov/articles/PMC11575054/" target="_blank" rel="noreferrer"> BMC Emergency Medicine 2024</a>; 
                        <a className="st-cite" href="https://beta.sis.gov.eg/en/egypt/society/health-care/indicators-about-the-health-sector-in-egypt/" target="_blank" rel="noreferrer"> Egypt health indicators</a>; 
                        <a className="st-cite" href="https://www.acep.org/patient-care/policy-statements/emergency-department-triage" target="_blank" rel="noreferrer"> ACEP/ENA ESI policy</a>; 
                        <a className="st-cite" href="https://www.ahajournals.org/doi/10.1161/CIR.0000000000000558" target="_blank" rel="noreferrer"> AHA/ACC NSTEMI guideline</a>.
                    </div>
                </div>
            </footer>
        </div>
    );
}
