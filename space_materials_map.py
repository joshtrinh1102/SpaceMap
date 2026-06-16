#!/usr/bin/env python3
"""
space_materials_map.py
======================

Generates an interactive, dark "command-center" style web map tracking the
critical raw materials behind space travel:

    * Rare-earth elements (neodymium / NdFeB magnets)
    * Titanium (airframes, propellant tanks, engine parts)
    * Platinum-group metals (thruster catalysts, fuel cells, contacts)

For each material it shows:
    * current price (with the benchmark spread)
    * dominant producers / manufacturers, plotted on a rotating 3D globe
    * a REUSE % bar  (how much of the material is recycled / re-used today)
    * related news & headlines

Run it:
    python3 space_materials_map.py            # uses the bundled snapshot data
    python3 space_materials_map.py --live      # also pulls fresh Google News headlines
    python3 space_materials_map.py --no-open    # don't auto-open the browser

Output:  space_materials_map.html  (self-contained, opens in any browser)

Dependencies: NONE beyond the Python standard library. The globe is rendered
client-side with globe.gl / three.js loaded from a CDN, so the machine that
*views* the HTML needs internet access; the machine that *builds* it does not
(unless you pass --live).

Prices/figures are a snapshot from ~15 Jun 2026 benchmarks (SMM, Kitco,
Strategic Metals Invest, IEA, UNEP). Edit the DATA dict below to update them,
or wire the PRICE_FEEDS / news fetcher to a live API.
"""

import argparse
import html
import json
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
#  DATA  — edit this block to update prices, producers, reuse %, headlines.    #
# --------------------------------------------------------------------------- #

DATA = {
    "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "as_of": "15 Jun 2026",
    "materials": [
        {
            "id": "ree",
            "price_per_kg": 140,      # used for per-spacecraft cost math
            "name": "Rare-Earth Elements",
            "symbol": "Nd",
            "subtitle": "Neodymium / NdFeB permanent magnets",
            "color": "#ff5a4d",          # red — high supply risk (echoes the alert markers)
            "accent": "#ff8a7a",
            "risk": "CRITICAL",
            "price_main": "≈ $140 / kg",
            "price_note": "Benchmark spread is wide: SMM China industrial ~$122/kg, "
                          "global benchmark ~$137–142/kg, Western private/retail up to ~$245/kg. "
                          "NdPr feedstock rallied ~160% YTD in early 2026.",
            "price_change": "+64% YTD",
            "price_dir": "up",
            "reuse_pct": 1,
            "reuse_note": "End-of-life recycling of rare earths is still ~1%. Most recycled "
                          "feedstock is manufacturing scrap; EOL magnet collection runs below "
                          "15%. Magnet-to-magnet recycling is rising but tiny.",
            "supply_conc": "China controls ~60% of mining and ~85–90% of separation/refining.",
            "space_use": "Neodymium-iron-boron (NdFeB) and samarium-cobalt magnets drive "
                         "reaction wheels, control-moment gyroscopes, the magnetic circuits of "
                         "Hall-effect and ion thrusters, actuators, magnetrons and traveling-wave "
                         "tubes. No high-performance permanent magnet, no fine spacecraft pointing.",
            "producers": [
                "China Northern Rare Earth Group (CN)",
                "China Rare Earth Group / Chinalco (CN)",
                "MP Materials – Mountain Pass (US)",
                "Lynas Rare Earths – Mt Weld (AU)",
                "Neo Performance Materials (CA / EE)",
            ],
            "sites": [
                {"label": "Baotou, Inner Mongolia (China Northern REG)", "lat": 40.66, "lng": 109.84, "share": 60, "primary": True},
                {"label": "Mountain Pass, California (MP Materials)",    "lat": 35.48, "lng": -115.53, "share": 12, "primary": False},
                {"label": "Mt Weld, W. Australia (Lynas)",               "lat": -28.86, "lng": 122.22, "share": 8,  "primary": False},
                {"label": "Narva, Estonia (Neo NdFeB plant)",            "lat": 59.38, "lng": 28.18,  "share": 3,  "primary": False},
            ],
        },
        {
            "id": "ti",
            "price_per_kg": 30,       # aerospace-alloy midpoint, used for cost math
            "name": "Titanium",
            "symbol": "Ti",
            "subtitle": "Airframes, propellant tanks, engine parts",
            "color": "#4db8ff",          # cyan — matches the blue tracks on the reference globe
            "accent": "#9bd6ff",
            "risk": "MODERATE",
            "price_main": "$20–43 / kg (aerospace alloy)",
            "price_note": "Titanium sponge feedstock ~$7/kg; processed bar/plate ~$8–16/kg; "
                          "certified aerospace Grade 5 (Ti-6Al-4V) plate ~$19–43/kg+. Energy-"
                          "intensive Kroll process keeps a hard price floor.",
            "price_change": "+4–9% market CAGR",
            "price_dir": "up",
            "reuse_pct": 52,
            "reuse_note": "Aerospace 'buy-to-fly' waste is high, so titanium revert/scrap is "
                          "heavily remelted — end-of-life recycling is estimated above ~50%, "
                          "among the better-recycled structural metals.",
            "supply_conc": "Sponge supply concentrated in Russia, China, Japan and the US; "
                           "classified as a critical mineral in the US.",
            "space_use": "Best strength-to-weight of common structural metals plus cryogenic "
                         "compatibility and corrosion resistance: airframe and interstage "
                         "structure, COPV / propellant-tank liners, rocket-engine components, "
                         "landing gear, fasteners and pressure vessels.",
            "producers": [
                "VSMPO-AVISMA (RU)",
                "TIMET / Precision Castparts (US)",
                "ATI – Allegheny Technologies (US)",
                "Toho Titanium (JP)",
                "Osaka Titanium / OTC (JP)",
                "Pangang / Baoji (CN)",
            ],
            "sites": [
                {"label": "Verkhnyaya Salda (VSMPO-AVISMA)", "lat": 58.05, "lng": 60.55,  "share": 25, "primary": True},
                {"label": "Pittsburgh, PA (ATI / TIMET, US)", "lat": 40.44, "lng": -79.99, "share": 12, "primary": False},
                {"label": "Chigasaki / Tokyo (Toho, Osaka Ti)", "lat": 35.33, "lng": 139.40, "share": 18, "primary": False},
                {"label": "Panzhihua, Sichuan (Pangang, CN)",  "lat": 26.58, "lng": 101.72, "share": 20, "primary": False},
            ],
        },
        {
            "id": "pgm",
            "price_per_kg": 55000,    # blended PGM ~$/kg (≈ platinum-weighted), for cost math
            "name": "Platinum-Group Metals",
            "symbol": "Pt·Pd·Rh",
            "subtitle": "Thruster catalysts, fuel cells, contacts",
            "color": "#c79bff",          # violet
            "accent": "#e0c8ff",
            "risk": "HIGH",
            "price_main": "Pt $1,750 · Pd $1,330 · Rh $8,000 /oz",
            "price_note": "Spot, ~15 Jun 2026 (Kitco): platinum at 12-year highs in a deficit "
                          "market; palladium soft amid surplus; rhodium volatile ($7.6k–8.6k). "
                          "Heraeus expects PGMs to reset lower through early 2026.",
            "price_change": "Pt at 12-yr high",
            "price_dir": "up",
            "reuse_pct": 55,
            "reuse_note": "Mature autocatalyst recovery makes platinum & palladium among the "
                          "best-recycled metals (~50–60% end-of-life). In electronics, though, "
                          "PGM recovery is only ~5–10%.",
            "supply_conc": "South Africa's Bushveld Complex dominates (~70%); Russia (Nornickel) "
                           "leads palladium; Zimbabwe's Great Dyke is the rising third source.",
            "space_use": "Platinum/rhodium catalyse hydrazine monopropellant thrusters "
                         "(Shell-405-type beds), iridium-coated rhenium chambers handle "
                         "high-temp bipropellant burns; PGMs also serve fuel cells, reliable "
                         "electrical contacts, thermocouples and crucibles.",
            "producers": [
                "Anglo American Platinum / Amplats (ZA)",
                "Impala Platinum / Implats (ZA)",
                "Sibanye-Stillwater (ZA / US)",
                "Norilsk Nickel / Nornickel (RU)",
                "Zimplats (ZW)",
            ],
            "sites": [
                {"label": "Rustenburg, Bushveld Complex (Amplats/Implats)", "lat": -25.67, "lng": 27.24, "share": 70, "primary": True},
                {"label": "Norilsk (Nornickel, Pd)",                        "lat": 69.35, "lng": 88.20,  "share": 12, "primary": False},
                {"label": "Great Dyke (Zimplats, ZW)",                      "lat": -18.0, "lng": 30.0,   "share": 8,  "primary": False},
                {"label": "Stillwater, Montana (Sibanye-Stillwater)",       "lat": 45.40, "lng": -109.9, "share": 4,  "primary": False},
            ],
        },
    ],
    # Bundled headline snapshot (drawn from public reporting, early–mid 2026).
    # --live appends fresh Google News results to these.
    "news": [
        {"material": "ree", "title": "Neodymium prices surge in 2026 on tightened Chinese export quotas and stricter quota enforcement",
         "source": "Critical Minerals News / IMARC", "date": "2026-05", "url": "https://critical-minerals-news.com/rare-earths-price/"},
        {"material": "ree", "title": "Neo Performance Materials opens Europe's first large-scale NdFeB magnet plant in Estonia",
         "source": "IMARC Group", "date": "2025-09", "url": "https://www.imarcgroup.com/neodymium-pricing-report"},
        {"material": "ree", "title": "Proterial develops heavy-rare-earth-free neodymium sintered magnets",
         "source": "IMARC Group", "date": "2025-07", "url": "https://www.imarcgroup.com/neodymium-pricing-report"},
        {"material": "ti", "title": "Aerospace titanium sponge market grows on aircraft backlogs and defense modernization",
         "source": "Research & Markets", "date": "2026-03", "url": "https://www.researchandmarkets.com/reports/5895360/titanium-sponge-aerospace-and-defense-market-report"},
        {"material": "ti", "title": "Titanium reaffirmed as a US critical mineral, shaping strategic reserves and sourcing",
         "source": "CarbonCredits.com", "date": "2026-06", "url": "https://carboncredits.com/titanium-prices-today/"},
        {"material": "pgm", "title": "Platinum hits 12-year highs as the market stays in deficit",
         "source": "Metals Focus / Nasdaq", "date": "2025-10", "url": "https://www.nasdaq.com/articles/metals-focus-bullish-platinum-bearish-palladium-2026"},
        {"material": "pgm", "title": "Heraeus 2026 forecast: PGM prices to reset; rhodium may swing to surplus on higher recycling",
         "source": "Heraeus Precious Metals", "date": "2026-01", "url": "https://www.heraeus-precious-metals.com/en/company/press-and-news/heraeus-precious-metals-forecast-2026/"},
        {"material": "pgm", "title": "Palladium near multi-month lows amid a widening surplus and falling ICE demand",
         "source": "Trading Economics", "date": "2026-06", "url": "https://tradingeconomics.com/commodity/palladium"},
    ],
    # Per-vehicle requirements of the THREE tracked materials.
    # IMPORTANT: these are engineering ESTIMATES from public dry-mass / material-mix
    # data, NOT manufacturer bills of materials (which are proprietary/unpublished).
    # "needs" is kg of each tracked material; cost is computed live from material prices.
    "spacecraft": [
        {
            "id": "starship",
            "name": "SpaceX Starship",
            "type": "Fully-reusable super-heavy launch + crew/cargo (full stack)",
            "dry_mass": "≈ 300 t (Starship ~120 t + Super Heavy ~180 t)",
            "primary_material": "304L / 30X stainless steel (~95%+ of dry mass, ~$3/kg)",
            "vehicle_cost": "≈ $100 M per vehicle (current est.)",
            "vehicle_cost_note": "Public figures put an expendable Starship near $100M; SpaceX's "
                                 "scaled production target is ~$5M/vehicle. Total program spend exceeds $15B.",
            "needs": {"ti": 1200, "ree": 40, "pgm": 6},
            "note": "Steel by design, so the tracked exotics are minor: titanium lives in the 39 Raptor "
                    "engines' turbomachinery, valves and plumbing; NdFeB magnets in flap actuators, "
                    "TVC and pumps; PGMs in electrical contacts and catalysts.",
        },
        {
            "id": "sls_orion",
            "name": "NASA SLS + Orion (Artemis)",
            "type": "Expendable super-heavy Moon rocket + crew capsule",
            "dry_mass": "SLS core ~98 t (Al-Li) + Orion CM/ESM ~15.5 t",
            "primary_material": "Aluminium-lithium (core tanks, capsule) + steel SRB cases",
            "vehicle_cost": "≈ $4.1 B per launch",
            "vehicle_cost_note": "NASA OIG breakdown per Artemis I–IV launch: ~$2.2B SLS + ~$1B Orion "
                                 "+ ~$0.3B European service module + ground systems.",
            "needs": {"ti": 2000, "ree": 50, "pgm": 10},
            "note": "Aluminium-lithium dominates the structure. Titanium sits in the four RS-25 engines, "
                    "struts and pressure vessels; PGMs in Orion's hydrazine thruster catalyst beds; "
                    "magnets across turbopumps, actuators and avionics.",
        },
        {
            "id": "shuttle",
            "name": "Space Shuttle Orbiter",
            "type": "Reusable crewed orbiter (retired 2011)",
            "dry_mass": "≈ 78 t empty",
            "primary_material": "Aluminium airframe; notable titanium thrust structure & wing spars",
            "vehicle_cost": "≈ $1.7 B to build (Endeavour, 1991); ~$1.5 B per flight averaged",
            "vehicle_cost_note": "Endeavour's replacement cost was about $1.7B in 1991; averaged across the "
                                 "program, each flight cost roughly $1.5B.",
            "needs": {"ti": 3000, "ree": 25, "pgm": 8},
            "note": "Used more titanium than later Al-Li designs (thrust structure, wing spars, landing-gear "
                    "forgings). Platinum sat in the alkaline fuel cells; NdFeB magnets were only emerging in "
                    "the 1980s, so magnet mass is modest.",
        },
    ],
    "sources": [
        "Prices: Shanghai Metals Market, Kitco, Strategic Metals Invest, Trading Economics (~15 Jun 2026)",
        "Reuse %: IEA Recycling of Critical Minerals; UNEP/IRP Recycling Rates of Metals; ScienceDirect REE review",
        "Producers: company filings & USGS Mineral Commodity Summaries",
    ],
}

# Live-news search queries per material (used only with --live)
NEWS_QUERIES = {
    "ree": "neodymium rare earth magnet supply",
    "ti": "aerospace titanium supply",
    "pgm": "platinum palladium rhodium catalyst supply",
}


# --------------------------------------------------------------------------- #
#  Optional live news fetch (Google News RSS, no API key needed)               #
# --------------------------------------------------------------------------- #

def fetch_live_news(max_per_material=4):
    """Pull recent headlines from Google News RSS. Best-effort; failures ignored."""
    import urllib.parse
    import urllib.request
    import xml.etree.ElementTree as ET

    out = []
    for mid, query in NEWS_QUERIES.items():
        url = ("https://news.google.com/rss/search?q="
               + urllib.parse.quote(query)
               + "&hl=en-US&gl=US&ceid=US:en")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                root = ET.fromstring(resp.read())
            items = root.findall(".//item")[:max_per_material]
            for it in items:
                title = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                src_el = it.find("source")
                source = (src_el.text.strip() if src_el is not None and src_el.text else "Google News")
                pub = (it.findtext("pubDate") or "").strip()[:16]
                if title:
                    out.append({"material": mid, "title": title, "source": source,
                                "date": pub, "url": link})
            print(f"  [live] {mid}: +{len(items)} headlines")
        except Exception as e:  # noqa: BLE001
            print(f"  [live] {mid}: skipped ({e})", file=sys.stderr)
    return out


# --------------------------------------------------------------------------- #
#  HTML template                                                               #
# --------------------------------------------------------------------------- #

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>ORBITAL SUPPLY — Critical Materials for Space Travel</title>
<script src="https://unpkg.com/globe.gl"></script>
<style>
  :root{
    --bg:#070b14; --panel:rgba(12,19,33,.82); --panel-solid:#0c1321;
    --edge:rgba(90,140,200,.22); --edge-bright:rgba(120,180,255,.45);
    --text:#dce6f5; --dim:#8295b0; --faint:#5d6f8c;
    --accent:#3fb6ff; --good:#37d6a0; --warn:#ffb84d; --bad:#ff5a4d;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;background:var(--bg);overflow:hidden;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    color:var(--text);}
  #globeViz{position:fixed;inset:0;z-index:0;}
  /* subtle vignette + grid */
  #vignette{position:fixed;inset:0;z-index:1;pointer-events:none;
    background:radial-gradient(ellipse at 62% 50%,transparent 38%,rgba(3,6,12,.65) 100%);}

  /* top bar */
  #topbar{position:fixed;top:0;left:0;right:0;height:44px;z-index:5;
    display:flex;align-items:center;gap:14px;padding:0 16px;
    background:linear-gradient(180deg,rgba(8,13,22,.95),rgba(8,13,22,.4));
    border-bottom:1px solid var(--edge);backdrop-filter:blur(6px);}
  #topbar .logo{font-weight:700;letter-spacing:3px;font-size:13px;color:#eaf2ff;}
  #topbar .logo span{color:var(--accent);}
  #topbar .meta{margin-left:auto;font-size:11px;color:var(--faint);letter-spacing:.5px;}
  #topbar .dot{display:inline-block;width:7px;height:7px;border-radius:50%;
    background:var(--good);margin-right:6px;box-shadow:0 0 8px var(--good);
    animation:pulse 2s infinite;}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}

  /* sidebar */
  #sidebar{position:fixed;top:44px;left:0;bottom:0;width:380px;max-width:90vw;z-index:4;
    background:var(--panel);backdrop-filter:blur(10px);
    border-right:1px solid var(--edge);display:flex;flex-direction:column;}
  .tabs{display:flex;border-bottom:1px solid var(--edge);}
  .tab{flex:1;padding:13px 6px;text-align:center;font-size:12px;letter-spacing:1.5px;
    color:var(--dim);cursor:pointer;border-bottom:2px solid transparent;user-select:none;
    transition:.15s;}
  .tab:hover{color:var(--text);}
  .tab.active{color:#fff;border-bottom-color:var(--accent);
    background:linear-gradient(180deg,rgba(63,182,255,.10),transparent);}
  .panel-scroll{overflow-y:auto;padding:14px;flex:1;}
  .panel-scroll::-webkit-scrollbar{width:8px}
  .panel-scroll::-webkit-scrollbar-thumb{background:rgba(120,160,220,.25);border-radius:4px}

  /* material cards */
  .card{border:1px solid var(--edge);border-radius:8px;padding:13px 14px;margin-bottom:12px;
    background:rgba(10,16,28,.5);cursor:pointer;transition:.16s;position:relative;overflow:hidden;}
  .card:hover{border-color:var(--edge-bright);transform:translateY(-1px);
    background:rgba(14,22,38,.7);}
  .card.active{border-color:var(--mat-color);box-shadow:0 0 0 1px var(--mat-color) inset,0 6px 24px rgba(0,0,0,.4);}
  .card .stripe{position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--mat-color);}
  .card h3{margin:0 0 2px;font-size:15px;color:#fff;display:flex;align-items:center;gap:8px;}
  .badge{font-size:9px;letter-spacing:1px;padding:2px 6px;border-radius:3px;font-weight:700;
    border:1px solid currentColor;}
  .badge.CRITICAL{color:#ff5a4d}.badge.HIGH{color:#ffb84d}.badge.MODERATE{color:#37d6a0}
  .card .sub{font-size:11px;color:var(--dim);margin:0 0 10px;}
  .row{display:flex;justify-content:space-between;font-size:11px;margin:5px 0;}
  .row .k{color:var(--faint);letter-spacing:.5px;}
  .row .v{color:var(--text);font-weight:600;text-align:right;}
  .v .chg{font-size:10px;color:var(--warn);margin-left:6px;}

  /* reuse bar */
  .reuse{margin-top:10px;}
  .reuse .lab{display:flex;justify-content:space-between;font-size:10px;color:var(--faint);
    letter-spacing:1px;margin-bottom:4px;}
  .reuse .lab b{color:var(--mat-color);font-size:12px;}
  .bar{height:7px;border-radius:4px;background:rgba(255,255,255,.07);overflow:hidden;}
  .bar > i{display:block;height:100%;border-radius:4px;
    background:linear-gradient(90deg,var(--mat-color),var(--mat-accent));
    box-shadow:0 0 10px var(--mat-color);transition:width .9s cubic-bezier(.2,.8,.2,1);}

  /* detail panel */
  #detail{padding:2px 2px 18px;}
  #detail h2{font-size:17px;margin:4px 0 2px;}
  #detail .small{font-size:11px;color:var(--dim);line-height:1.55;margin:8px 0;}
  #detail .section-h{font-size:10px;letter-spacing:2px;color:var(--accent);
    margin:16px 0 6px;border-bottom:1px solid var(--edge);padding-bottom:4px;}
  #detail ul{margin:6px 0;padding-left:16px;}
  #detail li{font-size:11px;color:var(--text);margin:4px 0;}
  .back{font-size:11px;color:var(--accent);cursor:pointer;letter-spacing:1px;}
  .back:hover{text-decoration:underline;}

  /* news */
  .news-item{border:1px solid var(--edge);border-left:3px solid var(--n-color);
    border-radius:6px;padding:10px 12px;margin-bottom:10px;background:rgba(10,16,28,.45);
    text-decoration:none;display:block;transition:.15s;}
  .news-item:hover{background:rgba(16,24,42,.75);border-color:var(--edge-bright);}
  .news-item .ttl{font-size:12.5px;color:#eaf2ff;line-height:1.45;}
  .news-item .src{font-size:10px;color:var(--faint);margin-top:6px;letter-spacing:.5px;
    display:flex;justify-content:space-between;}
  .ntag{font-size:9px;font-weight:700;letter-spacing:1px;color:var(--n-color);}

  /* data table */
  table{width:100%;border-collapse:collapse;font-size:11px;}
  th,td{text-align:left;padding:8px 6px;border-bottom:1px solid var(--edge);vertical-align:top;}
  th{color:var(--accent);font-size:10px;letter-spacing:1px;text-transform:uppercase;}
  td .mini-bar{height:5px;border-radius:3px;background:rgba(255,255,255,.08);margin-top:4px;}
  td .mini-bar > i{display:block;height:100%;border-radius:3px;}

  .footer-note{font-size:9.5px;color:var(--faint);line-height:1.5;margin-top:8px;}

  /* legend bottom-right */
  #legend{position:fixed;right:16px;bottom:16px;z-index:4;background:var(--panel);
    border:1px solid var(--edge);border-radius:8px;padding:11px 14px;backdrop-filter:blur(8px);
    font-size:11px;}
  #legend .lh{font-size:9px;letter-spacing:2px;color:var(--faint);margin-bottom:8px;}
  #legend .li{display:flex;align-items:center;gap:8px;margin:5px 0;color:var(--dim);}
  #legend .li i{width:9px;height:9px;border-radius:50%;box-shadow:0 0 8px currentColor;}
  #legend .li b{color:var(--text);font-weight:500;}

  /* tooltip */
  #tip{position:fixed;z-index:9;pointer-events:none;background:rgba(8,13,22,.95);
    border:1px solid var(--edge-bright);border-radius:6px;padding:7px 10px;font-size:11px;
    color:var(--text);display:none;max-width:240px;box-shadow:0 6px 24px rgba(0,0,0,.5);}
  #tip b{color:#fff;}#tip .s{color:var(--faint);font-size:10px;}

  @media(max-width:620px){
    #topbar .meta{font-size:9px;}
    #topbar .meta br{display:none;}
    #sidebar{top:auto;bottom:0;left:0;right:0;width:100%;height:60vh;
      border-right:none;border-top:1px solid var(--edge-bright);
      border-radius:16px 16px 0 0;box-shadow:0 -8px 30px rgba(0,0,0,.5);}
    #sidebar::before{content:"";position:absolute;top:7px;left:50%;transform:translateX(-50%);
      width:42px;height:4px;border-radius:3px;background:rgba(150,180,220,.4);}
    .tabs{margin-top:8px;}
    #legend{display:none;}
  }
</style>
</head>
<body>
<div id="globeViz"></div>
<div id="vignette"></div>

<div id="topbar">
  <div class="logo">ORBITAL<span>·</span>SUPPLY</div>
  <div class="meta"><span class="dot"></span>CRITICAL MATERIALS FOR SPACE TRAVEL &nbsp;·&nbsp; data as of __AS_OF__</div>
</div>

<div id="sidebar">
  <div class="tabs">
    <div class="tab active" data-tab="materials">MATERIALS</div>
    <div class="tab" data-tab="craft">CRAFT</div>
    <div class="tab" data-tab="news">NEWS</div>
    <div class="tab" data-tab="data">DATA</div>
  </div>
  <div class="panel-scroll">
    <div id="view-materials"></div>
    <div id="view-detail" style="display:none"></div>
    <div id="view-craft" style="display:none"></div>
    <div id="view-news" style="display:none"></div>
    <div id="view-data" style="display:none"></div>
  </div>
</div>

<div id="legend">
  <div class="lh">MARKER KEY</div>
  <div id="legend-items"></div>
  <div class="li" style="margin-top:8px"><i style="background:#fff;color:#fff"></i><b>pulsing ring = dominant / highest-risk source</b></div>
</div>

<div id="tip"></div>

<script>
const DATA = __DATA_JSON__;
const M = {};
DATA.materials.forEach(m => M[m.id] = m);

/* ---------------- Globe ---------------- */
function hexToRgb(h){const n=parseInt(h.slice(1),16);return [(n>>16)&255,(n>>8)&255,n&255];}

const points = [];
DATA.materials.forEach(m => {
  m.sites.forEach(s => {
    points.push({...s, mat:m.id, color:m.color,
      size:0.18 + (s.share/100)*0.9, name:m.name, symbol:m.symbol});
  });
});

const world = Globe()(document.getElementById('globeViz'))
  .backgroundColor('rgba(0,0,0,0)')
  .showGlobe(true)
  .showAtmosphere(true).atmosphereColor('#3a7fd0').atmosphereAltitude(0.18)
  .pointsData(points)
  .pointLat('lat').pointLng('lng').pointColor('color')
  .pointAltitude(d => 0.02 + (d.share/100)*0.32)
  .pointRadius('size')
  .pointsMerge(false)
  .pointLabel(() => '')   // we use a custom tooltip
  .ringsData(points.filter(p=>p.primary))
  .ringColor(d => (t => `rgba(${hexToRgb(d.color).join(',')},${1-t})`))
  .ringMaxRadius(5).ringPropagationSpeed(2.2).ringRepeatPeriod(900)
  .arcsData(buildArcs())
  .arcColor('color').arcStroke(0.4)
  .arcDashLength(0.5).arcDashGap(0.25).arcDashAnimateTime(4500)
  .arcAltitudeAutoScale(0.4)
  .onPointHover(handleHover)
  .onPointClick(p => selectMaterial(p.mat));

function buildArcs(){
  // draw faint links from each non-primary site to its material's primary site
  const arcs=[];
  DATA.materials.forEach(m=>{
    const prim=m.sites.find(s=>s.primary)||m.sites[0];
    m.sites.forEach(s=>{ if(s!==prim){
      arcs.push({startLat:s.lat,startLng:s.lng,endLat:prim.lat,endLng:prim.lng,color:m.color});
    }});
  });
  return arcs;
}

world.controls().autoRotate = true;
world.controls().autoRotateSpeed = 0.45;
world.pointOfView({lat:25, lng:-30, altitude:2.4}, 0);

/* dark water + bright land */
world.globeMaterial().color.set('#04111e');          // deep, dark ocean
world.globeMaterial().shininess = 6;
fetch('https://raw.githubusercontent.com/vasturiano/globe.gl/master/example/datasets/ne_110m_admin_0_countries.geojson')
  .then(r => r.json())
  .then(geo => {
    world.polygonsData(geo.features)
      .polygonCapColor(()    => 'rgba(150,190,228,0.94)')   // bright land
      .polygonSideColor(()   => 'rgba(60,100,150,0.35)')
      .polygonStrokeColor(() => 'rgba(200,226,252,0.55)')
      .polygonAltitude(0.004);
  })
  .catch(() => { /* offline: globe stays a dark sphere */ });

function resize(){ world.width(window.innerWidth).height(window.innerHeight); }
window.addEventListener('resize', resize); resize();

/* custom tooltip */
const tip = document.getElementById('tip');
function handleHover(p){
  if(!p){tip.style.display='none';world.controls().autoRotate=true;return;}
  world.controls().autoRotate=false;
  tip.style.display='block';
  tip.innerHTML = `<b>${p.label}</b><br><span class="s">${p.name} · ~${p.share}% of supply`
    + (p.primary?' · <span style="color:#ff8a7a">PRIMARY SOURCE</span>':'') + `</span>`;
}
document.addEventListener('mousemove', e=>{
  if(tip.style.display==='block'){
    tip.style.left = Math.min(e.clientX+14, window.innerWidth-260)+'px';
    tip.style.top  = (e.clientY+14)+'px';
  }
});

/* ---------------- Sidebar rendering ---------------- */
function matCardHTML(m){
  return `<div class="card" data-mat="${m.id}"
      style="--mat-color:${m.color};--mat-accent:${m.accent}">
    <div class="stripe"></div>
    <h3>${m.name} <span class="badge ${m.risk}">${m.risk}</span></h3>
    <div class="sub">${m.symbol} — ${m.subtitle}</div>
    <div class="row"><span class="k">CURRENT PRICE</span>
      <span class="v">${m.price_main}<span class="chg">${m.price_change}</span></span></div>
    <div class="row"><span class="k">DOMINANT SOURCE</span>
      <span class="v">${m.sites.find(s=>s.primary).label.split('(')[0].trim()}</span></div>
    <div class="reuse">
      <div class="lab"><span>MATERIAL REUSED TODAY</span><b>${m.reuse_pct}%</b></div>
      <div class="bar"><i style="width:0%" data-w="${m.reuse_pct}"></i></div>
    </div>
  </div>`;
}

function renderMaterials(){
  document.getElementById('view-materials').innerHTML =
    `<div class="footer-note" style="margin-bottom:12px">Select a material to focus the globe on its
     producers and pull its headlines &amp; manufacturers.</div>`
    + DATA.materials.map(matCardHTML).join('');
  document.querySelectorAll('.card').forEach(c=>{
    c.addEventListener('click',()=>selectMaterial(c.dataset.mat));
  });
  // animate reuse bars
  requestAnimationFrame(()=>setTimeout(()=>{
    document.querySelectorAll('.bar > i').forEach(i=>i.style.width=i.dataset.w+'%');
  },120));
}

function renderDetail(id){
  const m=M[id];
  const news=DATA.news.filter(n=>n.material===id);
  document.getElementById('view-detail').innerHTML = `
    <div style="--mat-color:${m.color};--mat-accent:${m.accent}">
      <div class="back" onclick="showTab('materials')">‹ ALL MATERIALS</div>
      <h2 style="color:${m.color}">${m.name} <span style="font-size:12px;color:var(--dim)">(${m.symbol})</span></h2>
      <div class="small">${m.subtitle}</div>

      <div class="row" style="margin-top:12px"><span class="k">CURRENT PRICE</span>
        <span class="v">${m.price_main}</span></div>
      <div class="footer-note">${m.price_note}</div>

      <div class="reuse" style="margin-top:14px">
        <div class="lab"><span>SHARE REUSED / RECYCLED TODAY</span><b>${m.reuse_pct}%</b></div>
        <div class="bar"><i style="width:${m.reuse_pct}%"></i></div>
      </div>
      <div class="footer-note">${m.reuse_note}</div>

      <div class="section-h">ROLE IN SPACE TRAVEL</div>
      <div class="small">${m.space_use}</div>

      <div class="section-h">SUPPLY CONCENTRATION</div>
      <div class="small">${m.supply_conc}</div>

      <div class="section-h">DOMINANT MANUFACTURERS</div>
      <ul>${m.producers.map(p=>`<li>${p}</li>`).join('')}</ul>

      <div class="section-h">HEADLINES</div>
      ${news.length? news.map(n=>newsHTML(n)).join('') :
        '<div class="small">No headlines tagged for this material.</div>'}
    </div>`;
  document.querySelectorAll('#view-detail .bar > i').forEach(i=>{
    const w=i.style.width;i.style.width='0%';requestAnimationFrame(()=>setTimeout(()=>i.style.width=w,120));
  });
}

function newsHTML(n){
  const m=M[n.material];
  return `<a class="news-item" href="${n.url}" target="_blank" rel="noopener"
      style="--n-color:${m.color}">
      <div class="ttl">${n.title}</div>
      <div class="src"><span class="ntag">${m.symbol}</span><span>${n.source} · ${n.date}</span></div>
    </a>`;
}

function renderNews(){
  document.getElementById('view-news').innerHTML =
    `<div class="footer-note" style="margin-bottom:12px">${DATA.news.length} headlines across all tracked materials. Click to open the source.</div>`
    + DATA.news.map(newsHTML).join('');
}

function renderData(){
  const rows = DATA.materials.map(m=>`
    <tr>
      <td><b style="color:${m.color}">${m.symbol}</b><br>
        <span style="color:var(--dim);font-size:10px">${m.name}</span></td>
      <td>${m.price_main}<br><span style="color:var(--faint);font-size:10px">${m.price_change}</span></td>
      <td>${m.reuse_pct}%
        <div class="mini-bar"><i style="width:${m.reuse_pct}%;background:${m.color}"></i></div></td>
      <td><span class="badge ${m.risk}" style="font-size:8px">${m.risk}</span></td>
    </tr>`).join('');
  document.getElementById('view-data').innerHTML = `
    <table>
      <thead><tr><th>Material</th><th>Price</th><th>Reused</th><th>Risk</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="section-h" style="color:var(--accent)">SOURCES</div>
    ${DATA.sources.map(s=>`<div class="footer-note">• ${s}</div>`).join('')}
    <div class="footer-note" style="margin-top:10px">Generated ${DATA.generated}.
      Figures are snapshots for orientation, not trading advice — commodity prices move daily.</div>`;
}

/* ---------------- Tabs / selection ---------------- */
function showTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.tab===name));
  ['materials','craft','news','data'].forEach(v=>{
    document.getElementById('view-'+v).style.display = (v===name)?'block':'none';
  });
  document.getElementById('view-detail').style.display='none';
  if(name==='materials') highlightMaterial(null);
  if(name==='craft'){ renderCraft(); highlightMaterial(null);
    world.controls().autoRotate=true; world.pointOfView({lat:20,lng:0,altitude:2.5},900); }
}
document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>showTab(t.dataset.tab)));

function selectMaterial(id){
  const m=M[id];
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  ['materials','craft','news','data'].forEach(v=>document.getElementById('view-'+v).style.display='none');
  renderDetail(id);
  document.getElementById('view-detail').style.display='block';
  highlightMaterial(id);
  const prim=m.sites.find(s=>s.primary)||m.sites[0];
  world.controls().autoRotate=false;
  world.pointOfView({lat:prim.lat, lng:prim.lng, altitude:1.7}, 1100);
}

function highlightMaterial(id){
  // dim non-selected points; restore when id is null
  world.pointColor(d=>{
    if(!id) return d.color;
    if(d.mat===id) return d.color;
    const [r,g,b]=hexToRgb(d.color);return `rgba(${r},${g},${b},0.16)`;
  });
  world.arcColor(d=>{
    if(!id) return d.color;
    const [r,g,b]=hexToRgb(d.color);return d.color && M[id] && d.color===M[id].color
      ? d.color : `rgba(${r},${g},${b},0.07)`;
  });
}

/* ---------------- Spacecraft / material requirements ---------------- */
function fmtUSD(n){
  if(n>=1e9) return '$'+(n/1e9).toFixed(2)+'B';
  if(n>=1e6) return '$'+(n/1e6).toFixed(2)+'M';
  if(n>=1e3) return '$'+(n/1e3).toFixed(1)+'k';
  return '$'+Math.round(n);
}
function craftCost(c){
  let total=0; const lines=[];
  Object.entries(c.needs).forEach(([mid,kg])=>{
    const m=M[mid]; const cost=kg*m.price_per_kg; total+=cost;
    lines.push({m,kg,cost});
  });
  return {total, lines};
}
function craftCardHTML(c){
  const {total}=craftCost(c);
  return `<div class="card craft-card" data-craft="${c.id}"
      style="--mat-color:var(--accent);--mat-accent:#9bd6ff">
    <div class="stripe"></div>
    <h3>${c.name}</h3>
    <div class="sub">${c.type}</div>
    <div class="row"><span class="k">DRY MASS</span><span class="v">${c.dry_mass}</span></div>
    <div class="row"><span class="k">VEHICLE COST</span><span class="v">${c.vehicle_cost}</span></div>
    <div class="row"><span class="k">RAW COST · TRACKED MATERIALS</span>
      <span class="v" style="color:var(--accent)">${fmtUSD(total)}</span></div>
  </div>`;
}
function renderCraft(){
  document.getElementById('view-craft').innerHTML =
    `<div class="footer-note" style="margin-bottom:12px">Estimated requirement of the three tracked
     materials per vehicle, priced at the current rates from the Materials tab.
     <b>These are engineering estimates, not published bills of materials</b> — real BOMs are
     proprietary. Tap a craft for the full breakdown.</div>`
    + DATA.spacecraft.map(craftCardHTML).join('');
  document.querySelectorAll('.craft-card').forEach(c=>
    c.addEventListener('click',()=>selectCraft(c.dataset.craft)));
}
function selectCraft(id){
  const c=DATA.spacecraft.find(x=>x.id===id);
  const {total,lines}=craftCost(c);
  const maxKg=Math.max(...lines.map(l=>l.kg));
  const rows=lines.map(l=>`
    <tr>
      <td><b style="color:${l.m.color}">${l.m.symbol}</b><br>
        <span style="color:var(--faint);font-size:10px">${l.m.name}</span></td>
      <td>${l.kg.toLocaleString()} kg
        <div class="mini-bar"><i style="width:${(l.kg/maxKg*100).toFixed(0)}%;background:${l.m.color}"></i></div></td>
      <td>${fmtUSD(l.cost)}<br>
        <span style="color:var(--faint);font-size:10px">@ $${l.m.price_per_kg.toLocaleString()}/kg</span></td>
    </tr>`).join('');
  document.getElementById('view-craft').innerHTML = `
    <div class="back" onclick="renderCraft()">‹ ALL CRAFT</div>
    <h2 style="color:var(--accent)">${c.name}</h2>
    <div class="small">${c.type}</div>
    <div class="row" style="margin-top:10px"><span class="k">DRY MASS</span><span class="v">${c.dry_mass}</span></div>
    <div class="row"><span class="k">PRIMARY MATERIAL</span><span class="v">${c.primary_material}</span></div>

    <div class="section-h">TRACKED CRITICAL MATERIALS NEEDED</div>
    <table><thead><tr><th>Material</th><th>Mass</th><th>Cost now</th></tr></thead>
      <tbody>${rows}</tbody></table>
    <div class="row" style="margin-top:8px;border-top:1px solid var(--edge);padding-top:10px">
      <span class="k" style="color:var(--text)">RAW COST · 3 TRACKED MATERIALS</span>
      <span class="v" style="color:var(--accent);font-size:15px">${fmtUSD(total)}</span></div>
    <div class="footer-note">Covers only Nd, Ti and PGMs — not steel, aluminium, engines,
      avionics, heat shielding or labour.</div>

    <div class="section-h">VEHICLE COST</div>
    <div class="small" style="font-size:13px;color:#fff">${c.vehicle_cost}</div>
    <div class="footer-note">${c.vehicle_cost_note} The tracked-material bill above is a rounding
      error against this — almost the entire price is engines, avionics, structure, testing and labour.</div>

    <div class="section-h">NOTES</div>
    <div class="small">${c.note}</div>`;
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.tab==='craft'));
  highlightMaterial(null);
  world.controls().autoRotate=true;
  world.pointOfView({lat:20,lng:0,altitude:2.5},900);
  document.querySelector('.panel-scroll').scrollTop=0;
}

function renderLegend(){
  document.getElementById('legend-items').innerHTML = DATA.materials.map(m=>
    `<div class="li"><i style="background:${m.color};color:${m.color}"></i>
       <b>${m.symbol}</b> &nbsp;${m.name}</div>`).join('');
}

/* init */
renderMaterials(); renderNews(); renderData(); renderCraft(); renderLegend();
</script>
</body>
</html>
"""


def build_html(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return (HTML_TEMPLATE
            .replace("__DATA_JSON__", payload)
            .replace("__AS_OF__", html.escape(data.get("as_of", ""))))


def main():
    ap = argparse.ArgumentParser(description="Build the space-materials command-center map.")
    ap.add_argument("--live", action="store_true",
                    help="Append fresh headlines from Google News RSS (needs internet).")
    ap.add_argument("--no-open", action="store_true", help="Do not auto-open the browser.")
    ap.add_argument("-o", "--out", default="space_materials_map.html", help="Output HTML path.")
    args = ap.parse_args()

    data = json.loads(json.dumps(DATA))  # deep copy

    if args.live:
        print("Fetching live headlines…")
        live = fetch_live_news()
        # live headlines go first, snapshot stays as fallback context
        data["news"] = live + data["news"]
        print(f"  total headlines: {len(data['news'])}")

    out_path = Path(args.out)
    out_path.write_text(build_html(data), encoding="utf-8")
    print(f"Wrote {out_path.resolve()}")

    if not args.no_open:
        try:
            webbrowser.open(out_path.resolve().as_uri())
        except Exception:  # noqa: BLE001
            print("Open the file manually in your browser.")


if __name__ == "__main__":
    main()
