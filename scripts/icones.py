# -*- coding: utf-8 -*-
"""Ícones do Sentinela (traço fino, herdam a cor do texto) no lugar dos emojis de interface.
Os emojis de STATUS (🟢🟡🟠🔴 ✅ ❌ ⛔) continuam: eles fazem parte do dado, não do enfeite.

  sprite(nomes=None)  -> <svg> escondido com os <symbol>, para colar no começo do <body>
  ico(nome)           -> <svg class="ico"><use href="#i-nome"/></svg>
  iconizar(html)      -> troca os emojis de interface do HTML por ícones (não mexe em <script>/<style>;
                         dentro de <option> e de atributos title/aria-label o emoji só é removido)
"""
import re

ICONES = {
    "print": '<path d="M7 9V3h10v6"/><rect x="4" y="9" width="16" height="8" rx="2"/><path d="M7 14h10v7H7z"/>',
    "book": '<path d="M5 4h7a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H5z"/><path d="M12 4h7v14h-4"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "trend": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "trophy": '<path d="M8 4h8v6a4 4 0 0 1-8 0z"/><path d="M8 6H4v2a3 3 0 0 0 4 2M16 6h4v2a3 3 0 0 1-4 2"/><path d="M12 14v4M8 21h8M10 18h4"/>',
    "list": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4h6v3H9zM9 12h6M9 16h6"/>',
    "warning": '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/>',
    "receipt": '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>',
    "bot": '<rect x="5" y="8" width="14" height="11" rx="3"/><path d="M12 4v4M9.5 13.5h.01M14.5 13.5h.01"/>',
    "chart": '<path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/>',
    "cone": '<path d="M3 20h18M7 20l3-14h4l3 14M8.5 14h7"/>',
    "coin": '<circle cx="12" cy="12" r="9"/><path d="M12 7v10M9.5 9.5c0-1 1-1.6 2.5-1.6s2.5.6 2.5 1.6-1 1.4-2.5 1.7-2.5.7-2.5 1.8 1 1.6 2.5 1.6 2.5-.6 2.5-1.6"/>',
    "pin": '<path d="M12 21s7-6.2 7-11a7 7 0 0 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "utensils": '<path d="M7 3v18M4 3v5a3 3 0 0 0 6 0V3M17 3c-2.5 2-3 5-2.5 9H17v9"/>',
    "monitor": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 21h8M12 16v5"/>',
    "ban": '<circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/>',
    "question": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.3a2.6 2.6 0 1 1 3.6 2.4c-.8.4-1.1.9-1.1 1.8M12 17h.01"/>',
    "down": '<path d="M5 8h14l-7 9z"/>',
    "home": '<path d="M4 11l8-7 8 7M6 10v10h12V10"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "pencil": '<path d="M4 20l1-4L16 5l3 3L8 19z"/>',
    "bulb": '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c1 1 1 2 1 3.5h6c0-1.500 0-2.500 1-3.500A6 6 0 0 0 12 3z"/>',
    "download": '<path d="M12 3v12M7 11l5 5 5-5M4 20h16"/>',
    "table": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 15h18M9 4v16"/>',
    "play": '<path d="M8 5l11 7-11 7z"/>',
    "pause": '<path d="M8 5v14M16 5v14"/>',
    "expand": '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
    "screen": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M9 20h6M12 16v4"/><path d="M8 10l2.500 2.500L16 8"/>',
    "compare": '<path d="M4 8h13M13 4l4 4-4 4M20 16H7M11 12l-4 4 4 4"/>',
    "arrow-up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "arrow-down": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "minus": '<path d="M5 12h14"/>',
    "timeline": '<path d="M12 3v18"/><circle cx="12" cy="7" r="2"/><circle cx="12" cy="17" r="2"/><path d="M14 7h6M4 17h6"/>',
    "cards": '<rect x="3" y="6" width="11" height="15" rx="2"/><path d="M7 3h10a2 2 0 0 1 2 2v13"/><path d="M6.500 12h4M6.500 16h4"/>',
    "share": '<circle cx="6" cy="12" r="2.500"/><circle cx="18" cy="6" r="2.500"/><circle cx="18" cy="18" r="2.500"/><path d="M8.200 10.800l7.600-3.600M8.200 13.200l7.600 3.600"/>',
    "eye": '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
}

MAPA = {
    "📅": "calendar", "📆": "calendar", "📈": "trend", "🏠": "home", "🖨️": "print", "🖨": "print", "🚧": "cone",
    "🏆": "trophy", "📋": "list", "⚠️": "warning", "⚠": "warning", "🤖": "bot", "🧾": "receipt", "📊": "chart",
    "📖": "book", "📑": "layers", "🔻": "down", "🕐": "clock", "🍽️": "utensils", "🍽": "utensils",
    "🖥️": "monitor", "🖥": "monitor", "🚫": "ban", "❓": "question", "💰": "coin", "📍": "pin", "🎯": "target",
    "🌴": "sun", "📺": "screen", "🔁": "compare", "🃏": "cards", "🕒": "timeline", "⬇️": "download", "⬇": "download", "✕": "close", "✏️": "pencil", "✏": "pencil", "💡": "bulb",
}
SO_REMOVER = {"🎉"}  # sem equivalente: some

_EMOJIS = sorted(list(MAPA) + list(SO_REMOVER), key=len, reverse=True)
_RX_EMOJI = re.compile("(" + "|".join(re.escape(e) for e in _EMOJIS) + ")️?")
_RX_BLOCOS = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>)", re.S | re.I)
_RX_OPTION = re.compile(r"(<option\b[^>]*>)(.*?)(</option>)", re.S | re.I)
_RX_TITLE = re.compile(r"(<title\b[^>]*>)(.*?)(</title>)", re.S | re.I)
_RX_ATTR = re.compile(r'(\s(?:title|aria-label|alt|placeholder)=")([^"]*)(")')


def ico(nome, extra=""):
    return f'<svg class="ico{(" " + extra) if extra else ""}" aria-hidden="true" focusable="false"><use href="#i-{nome}"/></svg>'


def sprite(nomes=None):
    itens = ICONES if nomes is None else {n: ICONES[n] for n in nomes}
    sym = "".join(f'<symbol id="i-{n}" viewBox="0 0 24 24">{d}</symbol>' for n, d in itens.items())
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">{sym}</svg>'


def _sem_emoji(txt):
    return re.sub(r"[  ]*$", "", _RX_EMOJI.sub("", txt)).lstrip() if _RX_EMOJI.search(txt) else txt


def _troca(m):
    e = m.group(1)
    return "" if e in SO_REMOVER else ico(MAPA[e])


def iconizar(html):
    partes = _RX_BLOCOS.split(html)
    for i in range(0, len(partes), 2):
        t = partes[i]
        t = _RX_OPTION.sub(lambda m: m.group(1) + _sem_emoji(m.group(2)) + m.group(3), t)
        t = _RX_TITLE.sub(lambda m: m.group(1) + _sem_emoji(m.group(2)) + m.group(3), t)
        t = _RX_ATTR.sub(lambda m: m.group(1) + _sem_emoji(m.group(2)) + m.group(3), t)
        partes[i] = _RX_EMOJI.sub(_troca, t)
    return "".join(partes)
