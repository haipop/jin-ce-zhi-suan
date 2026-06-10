from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "dashboard.html"


def _dashboard_html() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_dashboard_enables_fresh_theme_by_default():
    html = _dashboard_html()

    assert '<body class="theme-fresh ' in html
    assert "Fresh professional theme" in html
    assert "--jz-bg: #f5f9ff;" in html
    assert "--jz-primary: #2563eb;" in html
    assert "--jz-ink: #132033;" in html


def test_dashboard_fresh_theme_overrides_legacy_dark_surfaces():
    html = _dashboard_html()

    assert "body.theme-fresh [class*=\"bg-slate-950\"]" in html
    assert "body.theme-fresh [class*=\"bg-slate-900\"]" in html
    assert "body.theme-fresh [class*=\"bg-slate-800\"]" in html
    assert "background: rgba(255, 255, 255, 0.92) !important;" in html
    assert "body.theme-fresh input," in html
    assert "body.theme-fresh table thead" in html


def test_dashboard_fresh_theme_preserves_semantic_market_colors():
    html = _dashboard_html()

    assert "body.theme-fresh .text-trading-green" in html
    assert "body.theme-fresh .text-trading-red" in html
    assert "body.theme-fresh .text-trading-yellow" in html
    assert "body.theme-fresh .bg-trading-green" in html
    assert "body.theme-fresh .bg-trading-red" in html


def test_dashboard_main_layout_scrolls_instead_of_compressing_cards():
    html = _dashboard_html()

    assert '<body class="theme-fresh min-h-screen ' in html
    assert '<main class="dashboard-shell flex-1 p-4">' in html
    assert '<main class="flex-1 flex overflow-hidden' not in html
    assert "html:has(body.theme-fresh)" in html
    assert "body.theme-fresh main.dashboard-shell" in html
    assert "overflow: visible;" in html
    assert "overflow-x: hidden;" in html
    assert "overflow-y: auto;" in html


def test_dashboard_core_cards_use_responsive_readable_grid():
    html = _dashboard_html()

    assert '<div class="dashboard-card-grid">' in html
    assert "grid-rows-3" not in html
    assert "grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));" in html
    assert "grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));" in html
    assert "min-height: 230px;" in html
    assert "body.theme-fresh .decision-stack > .glass-panel" in html


def test_dashboard_three_provinces_six_ministries_are_grouped_by_workflow():
    html = _dashboard_html()

    assert "grid-template-areas:" in html
    assert '"decision logs"' in html
    assert '"execution logs"' in html
    assert "body.theme-fresh .decision-section" in html
    assert "body.theme-fresh .execution-section" in html
    assert "body.theme-fresh .logs-section" in html
    assert '<section class="dashboard-column decision-section decision-stack' in html
    assert '<section class="dashboard-column execution-section' in html
    assert '<section class="dashboard-column logs-section' in html
    assert "body.theme-fresh .decision-stack {\n            display: grid;" in html
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in html
