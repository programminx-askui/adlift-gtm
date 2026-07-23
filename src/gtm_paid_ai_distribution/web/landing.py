"""Renders a real, standalone, responsive landing page for an experiment (FR4).

Each experiment (A/B arm) renders with a **distinct visual theme** — palette,
typography, and layout differ per variant — so comparing variants is a real
design A/B test, not just a copy swap. The AI-generated `LandingPage` +
`MarketingMessage` supply the content; the theme supplies the look.
Self-contained (inline CSS), no external assets.
"""

from __future__ import annotations

from html import escape

from ..campaigns.models import Experiment


class Theme:
    def __init__(
        self,
        key: str,
        accent: str,
        accent_2: str,
        ink: str,
        bg: str,
        bg_2: str,
        line: str,
        font: str,
        display_font: str,
        radius: str,
        hero_align: str,
        display_weight: str = "700",
        uppercase_hero: bool = False,
    ) -> None:
        self.key = key
        self.accent = accent
        self.accent_2 = accent_2
        self.ink = ink
        self.bg = bg
        self.bg_2 = bg_2
        self.line = line
        self.font = font
        self.display_font = display_font
        self.radius = radius
        self.hero_align = hero_align
        self.display_weight = display_weight
        self.uppercase_hero = uppercase_hero


# Deliberately different design directions — one per variant.
THEMES: list[Theme] = [
    Theme(  # A — "Aurora": modern SaaS, indigo/violet, centered, pill buttons
        key="aurora", accent="#4f46e5", accent_2="#7c3aed", ink="#14151a",
        bg="#ffffff", bg_2="#f5f5fb", line="#e6e7ee",
        font='-apple-system, "SF Pro Text", system-ui, sans-serif',
        display_font='-apple-system, "SF Pro Display", system-ui, sans-serif',
        radius="980px", hero_align="center",
    ),
    Theme(  # B — "Editorial": warm cream, serif display, left-aligned, squared
        key="editorial", accent="#c2410c", accent_2="#b45309", ink="#1c1917",
        bg="#faf6ef", bg_2="#f2ebdd", line="#e6ddcb",
        font='Georgia, "Times New Roman", serif',
        display_font='"Playfair Display", Georgia, serif',
        radius="6px", hero_align="left", display_weight="800",
    ),
    Theme(  # C — "Signal": high-contrast dark, bold, uppercase hero
        key="signal", accent="#10b981", accent_2="#059669", ink="#0b0f0d",
        bg="#0b0f0d", bg_2="#121815", line="#1f2a24",
        font='"Segoe UI", system-ui, sans-serif',
        display_font='"Arial Black", "Segoe UI", system-ui, sans-serif',
        radius="4px", hero_align="center", display_weight="900", uppercase_hero=True,
    ),
    Theme(  # D — "Slate": calm blue, geometric, left-aligned, soft
        key="slate", accent="#0ea5e9", accent_2="#2563eb", ink="#0f172a",
        bg="#f8fafc", bg_2="#eef2f7", line="#e2e8f0",
        font='system-ui, "Segoe UI", sans-serif',
        display_font='system-ui, "Segoe UI", sans-serif',
        radius="14px", hero_align="left",
    ),
]


def _theme_for(exp: Experiment) -> Theme:
    name = exp.name.strip()
    if name.lower().startswith("variant ") and name[-1:].isalpha():
        return THEMES[(ord(name[-1].upper()) - ord("A")) % len(THEMES)]
    return THEMES[sum(ord(c) for c in exp.id) % len(THEMES)]


def _benefits(items: list[str]) -> str:
    icons = ["⚡", "📈", "🎯", "✨", "🔒", "🚀"]
    return "".join(
        f'<div class="benefit"><div class="benefit-ico">{icons[i % len(icons)]}</div>'
        f"<p>{escape(b)}</p></div>"
        for i, b in enumerate(items)
    )


def _faq(items: list[dict[str, str]]) -> str:
    return "".join(
        "<details class='faq'>"
        f"<summary>{escape(qa.get('question', ''))}</summary>"
        f"<p>{escape(qa.get('answer', ''))}</p></details>"
        for qa in items
    )


def render_landing_page(exp: Experiment) -> str:
    t = _theme_for(exp)
    lp = exp.landing_page
    msg = exp.message
    headline = escape(msg.headline or lp.hero or "Your Product")
    subhead = escape(msg.description or "")
    cta = escape(msg.cta or lp.cta or "Get started")
    testimonials = lp.testimonials or []
    center = t.hero_align == "center"

    testimonial_html = ""
    if testimonials:
        testimonial_html = (
            '<section class="section quotes"><div class="wrap">'
            + "".join(f"<blockquote>{escape(x)}</blockquote>" for x in testimonials)
            + "</div></section>"
        )

    return f"""<!doctype html>
<html lang="en" data-theme="{t.key}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{headline}</title>
<style>
  :root {{
    --accent: {t.accent}; --accent-2: {t.accent_2};
    --ink: {t.ink}; --bg: {t.bg}; --bg-2: {t.bg_2}; --line: {t.line};
    --sub: color-mix(in srgb, {t.ink} 58%, {t.bg});
    --radius: {t.radius};
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: {t.font}; color: var(--ink); background: var(--bg);
    line-height: 1.5; -webkit-font-smoothing: antialiased; }}
  a {{ color: var(--accent); text-decoration: none; }}
  .wrap {{ max-width: 1000px; margin: 0 auto; padding: 0 22px; }}
  nav {{ position: sticky; top: 0; z-index: 10; border-bottom: 1px solid var(--line);
    background: color-mix(in srgb, var(--bg) 85%, transparent);
    backdrop-filter: saturate(180%) blur(18px); }}
  nav .wrap {{ display: flex; align-items: center; height: 56px; }}
  nav b {{ font-family: {t.display_font}; font-weight: {t.display_weight}; font-size: 17px; }}
  nav .cta {{ margin-left: auto; }}
  .btn {{ display: inline-block; background: linear-gradient(135deg, var(--accent), var(--accent-2));
    color: #fff; padding: 13px 26px; border-radius: var(--radius); font-weight: 600; font-size: 16px;
    transition: transform .12s ease, filter .12s ease; }}
  .btn:hover {{ filter: brightness(1.06); transform: translateY(-1px); }}
  .btn.ghost {{ background: transparent; color: var(--accent); box-shadow: inset 0 0 0 1.5px var(--accent); }}
  nav .cta.btn {{ padding: 8px 16px; font-size: 14px; }}
  .hero {{ text-align: {t.hero_align}; padding: 96px 0 82px; }}
  .hero h1 {{ font-family: {t.display_font}; font-weight: {t.display_weight};
    font-size: clamp(40px, 7vw, 74px); line-height: 1.05; letter-spacing: -.02em;
    margin: 0 0 20px; {"text-transform: uppercase;" if t.uppercase_hero else ""} }}
  .hero p {{ font-size: clamp(18px, 2.3vw, 24px); color: var(--sub);
    max-width: 640px; margin: {"0 auto 32px" if center else "0 0 32px"}; }}
  .hero .row {{ display: flex; gap: 14px; {"justify-content: center;" if center else ""} flex-wrap: wrap; }}
  .logos {{ background: var(--bg-2); padding: 30px 0; text-align: center; }}
  .logos p {{ color: var(--sub); font-size: 12px; text-transform: uppercase; letter-spacing: .1em; margin: 0 0 14px; }}
  .logos .strip {{ display: flex; gap: 38px; justify-content: center; flex-wrap: wrap;
    font-weight: 700; font-size: 19px; color: var(--sub); opacity: .75; }}
  .section {{ padding: 80px 0; }}
  .section h2 {{ font-family: {t.display_font}; font-weight: {t.display_weight};
    font-size: clamp(28px, 4vw, 44px); letter-spacing: -.02em;
    text-align: {t.hero_align}; margin: 0 0 46px; }}
  .benefits {{ display: grid; gap: 22px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
  .benefit {{ background: var(--bg-2); border: 1px solid var(--line); border-radius: calc(var(--radius) / 1.5 + 8px);
    padding: 32px 26px; }}
  .benefit-ico {{ font-size: 32px; margin-bottom: 12px; }}
  .benefit p {{ font-size: 18px; margin: 0; font-weight: 600; }}
  .quotes {{ background: var(--bg-2); text-align: center; }}
  blockquote {{ font-family: {t.display_font}; font-size: clamp(23px, 3.3vw, 33px);
    max-width: 760px; margin: 0 auto; font-weight: {t.display_weight}; letter-spacing: -.01em; }}
  .faq {{ border-top: 1px solid var(--line); padding: 20px 0; }}
  .faq:last-child {{ border-bottom: 1px solid var(--line); }}
  .faq summary {{ font-size: 19px; font-weight: 600; cursor: pointer; list-style: none; }}
  .faq summary::-webkit-details-marker {{ display: none; }}
  .faq summary::after {{ content: "+"; float: right; color: var(--sub); }}
  .faq[open] summary::after {{ content: "\\2013"; }}
  .faq p {{ color: var(--sub); font-size: 17px; margin: 12px 0 0; }}
  .final {{ text-align: center; padding: 92px 0;
    background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 10%, var(--bg)), var(--bg)); }}
  .final h2 {{ text-align: center; margin-bottom: 26px; }}
  footer {{ border-top: 1px solid var(--line); padding: 26px 0; color: var(--sub); font-size: 13px; text-align: center; }}
</style>
</head>
<body>
  <nav><div class="wrap"><b>{headline}</b><a class="cta btn" href="#cta">{cta}</a></div></nav>

  <header class="hero"><div class="wrap">
    <h1>{headline}</h1>
    {f"<p>{subhead}</p>" if subhead else ""}
    <div class="row">
      <a class="btn" href="#cta">{cta}</a>
      <a class="btn ghost" href="#learn">Learn more</a>
    </div>
  </div></header>

  <div class="logos"><div class="wrap">
    <p>Trusted by high-growth B2B SaaS teams</p>
    <div class="strip"><span>Northwind</span><span>Acme</span><span>Globex</span>
      <span>Initech</span><span>Umbrella</span></div>
  </div></div>

  <section class="section" id="learn"><div class="wrap">
    <h2>Why teams choose us</h2>
    <div class="benefits">{_benefits(lp.benefits)}</div>
  </div></section>
  {testimonial_html}
  <section class="section"><div class="wrap">
    <h2>Questions, answered</h2>
    {_faq(lp.faq)}
  </div></section>

  <section class="final" id="cta"><div class="wrap">
    <h2>{headline}</h2>
    <a class="btn" href="#cta">{cta}</a>
  </div></section>

  <footer><div class="wrap">“{escape(exp.name)}” · {t.key} theme · channel {escape(exp.channel.value)}
    · landing page by AdLift</div></footer>
</body>
</html>"""
