import re
import sys

PHOTO = dict(x=257, y=84, w=686, h=484)
STICKS = {"stkL": (492.5, 310), "stkR": (706.5, 310)}


def image(href, x=None, y=None, extra=""):
    x = PHOTO["x"] if x is None else x
    y = PHOTO["y"] if y is None else y
    return (f'<image href="{href}" x="{x}" y="{y}" width="{PHOTO["w"]}" height="{PHOTO["h"]}" '
            f'preserveAspectRatio="none"{extra}/>')


def replace_group(html, gid, inner):
    start = html.find(f'<g id="{gid}"')
    if start < 0:
        raise SystemExit(f"grupo {gid} não encontrado")
    open_end = html.index(">", start) + 1
    depth, pos = 1, open_end
    tag = re.compile(r"<g[\s>]|</g>")
    while depth:
        m = tag.search(html, pos)
        if not m:
            raise SystemExit(f"grupo {gid} sem fechamento")
        depth += -1 if m.group(0) == "</g>" else 1
        pos = m.end()
    return html[:open_end] + inner + "</g>" + html[pos:]


def sub_once(html, pattern, repl, label, count=1):
    new, n = re.subn(pattern, repl, html, count=0 if count is None else count)
    if n == 0:
        raise SystemExit(f"não achei: {label}")
    return new


def patch_layers(html):
    shoulders = '<use href="#ds-l1" class="pz" data-btn="l1"/><use href="#ds-r1" class="pz" data-btn="r1"/>'
    triggers = re.search(r'<g id="tL2">.*?</g><g id="tR2">.*?</g>', html)
    if shoulders not in html or not triggers:
        raise SystemExit("não achei as camadas de ombro e gatilho")
    moved = triggers.group(0) + shoulders
    html = html.replace(triggers.group(0), "", 1).replace(shoulders, "", 1)
    return sub_once(html, r'(<g id="pressLayer")', lambda m: moved + m.group(1), "pressLayer")


def patch_tester(html):
    rules = [
        (r"function record\(\) \{\n  let changed = false;",
         "function record() {\n  if (view !== 'teste') return;\n  let changed = false;"),
        (r"  for \(const k of BTN_KEYS\) if \(IN\.buttons\[k\]",
         "  if (ttab === 'botoes') for (const k of BTN_KEYS) if (IN.buttons[k]"),
        (r"  for \(const k of \['l2', 'r2'\]\) if \(IN\.triggers\[k\] > T\.max\[k\]\)",
         "  if (ttab === 'gatilhos') for (const k of ['l2', 'r2']) if (IN.triggers[k] > T.max[k])"),
        (r"  sampleStick\(T\.stick\.l, IN\.sticks\.lx, IN\.sticks\.ly\);\n  sampleStick\(T\.stick\.r, IN\.sticks\.rx, IN\.sticks\.ry\);",
         "  if (ttab === 'analog') { sampleStick(T.stick.l, IN.sticks.lx, IN.sticks.ly); "
         "sampleStick(T.stick.r, IN.sticks.rx, IN.sticks.ry); }"),
        (r"  if \(act\.length > T\.touchSeen\)", "  if (ttab === 'touch' && act.length > T.touchSeen)"),
        (r"  if \(IN\.buttons\.touchpad\) T\.clickSeen = true;",
         "  if (ttab === 'touch' && IN.buttons.touchpad) T.clickSeen = true;"),
        (r"  for \(const f of act\) \{", "  for (const f of ttab === 'touch' ? act : []) {"),
        (r"  if \(Math\.hypot\(IN\.gyro\[0\], IN\.gyro\[1\], IN\.gyro\[2\]\) > 3\)",
         "  if (ttab === 'motion' && Math.hypot(IN.gyro[0], IN.gyro[1], IN.gyro[2]) > 3)"),
        (r"  if \(am > 0\.5 && am < 1\.8\) T\.accelSeen", "  if (ttab === 'motion' && am > 0.5 && am < 1.8) T.accelSeen"),
    ]
    for pattern, repl in rules:
        html = sub_once(html, pattern, lambda m, r=repl: r, pattern[:40])
    return html


SEND_JS = (
    "function send(type, payload) {\n"
    "  payload = payload || {};\n"
    "  const msg = JSON.stringify({ type, payload });\n"
    "  const h = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.ds;\n"
    "  if (h) { try { h.postMessage(msg); } catch (e) { console.error(e); } return; }\n"
    "  if (window.pywebview && window.pywebview.api) { window.pywebview.api.send(msg); return; }\n"
    "  if (/host=pywebview/.test(location.search)) { (window.dsQueue = window.dsQueue || []).push(msg); return; }\n"
    "  Mock.handle(type, payload);\n"
    "}\n"
    "window.addEventListener('pywebviewready', () => { const q = window.dsQueue || []; window.dsQueue = []; "
    "q.forEach(m => window.pywebview.api.send(m)); });\n"
)


def patch_host(html):
    pattern = (r"function send\(type, payload\) \{\n  payload = payload \|\| \{\};\n  const h = window\.webkit.*?\n"
               r"  else Mock\.handle\(type, payload\);\n\}\n")
    new, n = re.subn(pattern, lambda m: SEND_JS, html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("não achei a função send")
    return new


def patch_info(html):
    html = sub_once(html, r"const SPEC = \[\['model', 'Modelo'\], ",
                    "const SPEC = [['model', 'Modelo'], ['color', 'Cor de fábrica'], ['board', 'Placa (BDM)'], "
                    "['serial', 'Número de série'], ", "lista SPEC")
    html = sub_once(html, r"  if \(k === 'model'\) return ",
                    "  if (k === 'color') { const i = INFO || {}; if (!i.colorPt && !i.colorCode) return null; "
                    "return i.colorPt ? i.colorPt + (i.color && i.color !== i.colorPt ? ' (' + i.color + ')' : '') "
                    ": 'Código ' + i.colorCode; }\n  if (k === 'model') return ", "specValue cor")
    html = sub_once(html, r"(function renderInfo\(\) \{\n)",
                    "\\1  const swEl = $('#sv-color'); if (swEl) { const hex = INFO && INFO.colorHex; "
                    "swEl.classList.toggle('has-sw', !!hex); swEl.style.setProperty('--sw', hex || 'transparent'); }\n",
                    "renderInfo")
    html = sub_once(html, r"\$\('#infoConn'\)\.textContent = S && S\.connected \? \(specValue\('connection'\) \|\| ''\)",
                    "$('#infoConn').textContent = S && S.connected ? [INFO && INFO.colorPt, INFO && INFO.board, "
                    "specValue('connection')].filter(Boolean).join(' · ')", "subtítulo")
    html = sub_once(html, r"'- Modelo: ' \+ v\('model'\), ",
                    "'- Modelo: ' + v('model'), '- Cor de fábrica: ' + v('color'), '- Placa: ' + v('board'), "
                    "'- Número de série: ' + v('serial'), ", "relatório")
    css = (".v.has-sw::before{content:'';display:inline-block;width:12px;height:12px;border-radius:50%;"
           "background:var(--sw);box-shadow:0 0 0 1px rgba(255,255,255,.4);margin-right:9px;vertical-align:-1px}")
    return sub_once(html, r"</style>", css + "</style>", "estilo info")


def patch_marcas(html):
    html = sub_once(html, r'<g transform="translate\(600 305\) scale\(\.62\)" style="fill:url\(#gPsLogo\);(stroke:[^"]*)"[^>]*>.*?</g>',
                    lambda m: f'<circle cx="600" cy="305" r="17" style="fill:url(#gPsLogo);{m.group(1)}" stroke-width="1.2"/>',
                    "logo PS")
    return sub_once(html, r'<g clip-path="url\(#clipBody\)"><rect [^>]*fill="url\(#psTex\)"[^>]*/></g>', "", "textura")


ESTILO = (
    ":root{--bg-deep:#16171a;--bg:#1b1c20;--surface:#222327;--surface-2:#2a2b30;--surface-3:#34353b;"
    "--fg:#ebecef;--muted:#9b9da4;--border:rgba(255,255,255,.07);--border-strong:rgba(255,255,255,.13);"
    "--accent-soft:color-mix(in srgb,var(--accent) 15%,transparent);"
    "--accent-line:color-mix(in srgb,var(--accent) 45%,transparent);"
    "--accent-text:color-mix(in srgb,var(--accent) 65%,#fff);--r-lg:12px;--r-md:8px}"
    "body{background:var(--bg-deep)}"
    ".side{background:#131417;backdrop-filter:none;-webkit-backdrop-filter:none}"
    ".brand-mark{box-shadow:none}"
    ".nav-btn[aria-current=page]{background:var(--surface-2);box-shadow:inset 3px 0 0 var(--accent)}"
    ".glass{background:var(--surface);box-shadow:none;backdrop-filter:none;-webkit-backdrop-filter:none}"
    ".stage{background:#1d1e22}"
    ".stage-fx,.halo,.c-sheen,.c-rim,.batt-fill i,.cs-halo{display:none}"
    ".ctrl{animation:none}"
    ".view.is-active .rise{animation:none}"
    ".lb-glow{opacity:calc(var(--glow) * .3)}"
    ".vh h1{font-size:26px;letter-spacing:0}"
    ".btn-primary,.btn-primary:hover{box-shadow:none;transform:none}"
    ".batt-fill{background:var(--accent)}.batt-fill.is-low{background:var(--warn)}"
    ".meter-cap i,.tbar i{background:var(--accent)}"
    ".wheel,.wheel.sm{box-shadow:0 0 0 1px var(--border-strong)}"
    ".sw i{box-shadow:inset 0 0 0 1px rgba(255,255,255,.25)}"
    "input[type=range]::-webkit-slider-runnable-track{background:linear-gradient(90deg,var(--accent) var(--pct),"
    "rgba(255,255,255,.12) var(--pct))}"
    "input[type=range]::-webkit-slider-thumb{box-shadow:0 1px 3px rgba(0,0,0,.5)}"
    "input[type=range]::-moz-range-thumb{box-shadow:0 1px 3px rgba(0,0,0,.5)}"
    ".led[aria-pressed=true] i,.motor.is-on .motor-viz i,.cl-chip .cl-lit{box-shadow:none}"
    ".mode input:checked + label{background:var(--accent-soft);box-shadow:none}"
    ".cl-style input:checked + label{background:color-mix(in srgb,rgb(var(--cl-rgb)) 14%,transparent)}"
    ".charge-meter i{background:var(--orange)}.charge.is-full .charge-meter i{background:var(--success)}"
    ".chk.is-now{box-shadow:0 0 0 1px var(--accent-line)}"
    ".plot,.motor-viz{background:#17181b}"
    ".tpad{background:#26272c}.tpad.is-click{box-shadow:inset 0 0 0 2px var(--accent-text)}"
    ".mo-scene{background:#1d1e22}.mo-svg{filter:none}"
    ".prof-sw{background:var(--c);box-shadow:none}"
    ".btn-primary{border-radius:var(--r-md);height:50px}"
    ".toast{background:var(--surface-3);backdrop-filter:none;-webkit-backdrop-filter:none;"
    "box-shadow:0 6px 18px rgba(0,0,0,.4)}"
)

SUBTITULOS = (
    "Bateria, conexão e carga do seu DualSense.",
    "Barra de luz, LEDs de jogador e luz do microfone.",
    "Identificação do controle conectado. Use Copiar para levar qualquer valor.",
    "Aperte, gire e toque. Tudo aparece aqui ao vivo.",
    "Atalhos, avisos e economia de energia.",
)


def patch_estilo(html):
    for texto in SUBTITULOS:
        html = sub_once(html, r"\s*<p[^>]*>\s*" + re.escape(texto) + r"\s*</p>", "", texto[:30])
    html = sub_once(html, r"Azul PlayStation", "Azul", "nome da cor", count=None)
    return sub_once(html, r"</style>", ESTILO + "</style>", "estilo sóbrio")


def patch(html):
    defs = (
        f'<mask id="mLightbar" maskUnits="userSpaceOnUse" x="{PHOTO["x"]}" y="{PHOTO["y"]}" '
        f'width="{PHOTO["w"]}" height="{PHOTO["h"]}">{image("dualsense-lightbar.png")}</mask>'
        '<clipPath id="cStick"><circle cx="0" cy="0" r="41"/></clipPath>'
    )
    html = sub_once(html, r"<defs>", "<defs>" + defs, "defs")
    html = replace_group(html, "ds-shell", image("dualsense-base.png"))
    for gid in ("ds-touchpad", "ds-shoulders", "ds-stick"):
        html = replace_group(html, gid, "")

    photo_bar = (f'<rect class="lb-photo" x="{PHOTO["x"]}" y="{PHOTO["y"]}" width="{PHOTO["w"]}" '
                 f'height="{PHOTO["h"]}" mask="url(#mLightbar)"/>')
    html = sub_once(html, r'<use href="#ds-strip-l" class="lb"/>\s*<use href="#ds-strip-r" class="lb"/>',
                    photo_bar, "faixas lb", count=None)
    html = sub_once(html, r'<use href="#ds-strip-l" class="cs-unlit"/>\s*<use href="#ds-strip-r" class="cs-unlit"/>',
                    "", "faixas cs-unlit")
    charge_bar = photo_bar.replace('class="lb-photo"', 'class="cs-bar-photo"')
    html = sub_once(html, r'<use href="#ds-strip-l" class="cs-bar"/>\s*<use href="#ds-strip-r" class="cs-bar"/>',
                    charge_bar, "faixas cs-bar")

    for sid, (cx, cy) in STICKS.items():
        cap = image("dualsense-base.png", PHOTO["x"] - cx, PHOTO["y"] - cy, ' clip-path="url(#cStick)"')
        html = sub_once(html, rf'(<g class="stk-move" id="{sid}">)<use href="#ds-stick"/>',
                        rf'<circle class="stk-well" r="42.5"/>\1{cap}', f"analógico {sid}")

    css = (
        ".lb-photo{fill:rgb(var(--lb-rgb));opacity:calc(.1 + var(--glow) * .9);transition:fill .3s var(--ease)}"
        ".cs-bar-photo{fill:rgb(var(--cl-rgb));transition:fill .3s var(--ease)}"
        ".c-trig,.cs-trig{display:none}"
        ".stk-well{fill:#1d1f24}"
    )
    html = sub_once(html, r"</style>", css + "</style>", "estilo")
    return html


def main():
    args = [a for a in sys.argv[1:] if a != "--foto"]
    src, dst = args
    with open(src, encoding="utf-8") as f:
        html = f.read()
    html = patch_layers(patch(html)) if "--foto" in sys.argv else patch_marcas(html)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(patch_host(patch_tester(patch_info(patch_estilo(html)))))
    print(f"ok: {dst}")


if __name__ == "__main__":
    main()
