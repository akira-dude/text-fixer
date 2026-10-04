"""Local wrong-keyboard-layout fix (EN <-> RU, ЙЦУКЕН), no network.

Text is split into runs of words that could have been typed in the wrong
layout. Each run is scored with tiny character-bigram models of both languages
and converted only if the converted version looks clearly more natural.
"""

import math
import re
from collections import Counter

from .lang_data import EN_WORDS, RU_WORDS, words

_EN_KEYS = "`qwertyuiop[]asdfghjkl;'zxcvbnm,./" + '~QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?' + '@#$^&|'
_RU_KEYS = "ёйцукенгшщзхъфывапролджэячсмитьбю." + 'ЁЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,' + '"№;:?/'

EN_TO_RU = dict(zip(_EN_KEYS, _RU_KEYS))
RU_TO_EN = dict(zip(_RU_KEYS, _EN_KEYS))

# Characters that are the same in both layouts.
NEUTRAL = set("0123456789!-_=+()*%")

EN_ALPHA = "abcdefghijklmnopqrstuvwxyz"
RU_ALPHA = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"

_PROTECTED = re.compile(
    r"^(?:[a-z][a-z0-9+.-]*://|www\.)\S*$"  # links
    r"|^\S+@\S+\.\S+$"  # e-mails
    r"|^[@#]\w+$"  # mentions, hashtags
    r"|^<[@#:a-z][^>]*>$"  # discord mentions / emoji
    r"|^:[\w+-]+:$",  # :emoji:
    re.IGNORECASE,
)

# A run is converted when the converted text scores better by this margin
# (average log-probability per bigram).
THRESHOLD = 1.0


class _BigramModel:
    def __init__(self, alphabet: str, vocabulary: list[str], edge_lead: str, edge_trail: str):
        self.alpha = set(alphabet)
        self.vocab = set(vocabulary)
        self.edge_lead = edge_lead
        self.edge_trail = edge_trail
        self.pairs: Counter = Counter()
        self.totals: Counter = Counter()
        for w in vocabulary:
            s = "^" + w.replace("-", "") + "$"
            for a, b in zip(s, s[1:]):
                self.pairs[a, b] += 1
                self.totals[a] += 1
        self.k = 0.1
        self.v = len(alphabet) + 1
        self.junk = math.log(self.k / (max(self.totals.values()) + self.k * self.v)) - 2

    def _logp(self, a: str, b: str) -> float:
        return math.log((self.pairs[a, b] + self.k) / (self.totals[a] + self.k * self.v))

    def score(self, token: str) -> tuple[float, int]:
        """Average log-probability of a token and its weight (letter count)."""
        core = token.strip(self.edge_lead + " ").rstrip(self.edge_trail).lower()
        if not core:
            return 0.0, 0
        if core in self.vocab:
            return -1.0, len(core)
        total, n, letters = 0.0, 0, 0
        prev = "^"
        for ch in core:
            if ch in self.alpha:
                total += self._logp(prev, ch)
                prev = ch
                letters += 1
            elif ch in NEUTRAL or ch == "'":
                continue
            else:
                total += self.junk
                prev = "^"
            n += 1
        total += self._logp(prev, "$")
        n += 1
        return total / n, max(letters, 1)


_EN = _BigramModel(EN_ALPHA, words(EN_WORDS), "\"'([{", ".,!?;:'\")]}")
_RU = _BigramModel(RU_ALPHA, words(RU_WORDS), "\"«(", ".,!?;:\")»…")


def _convert(token: str, table: dict[str, str]) -> str:
    return "".join(table.get(ch, ch) for ch in token)


def _direction(token: str) -> str | None:
    """'en' if the token may be Russian typed on EN layout, 'ru' for the reverse."""
    if _PROTECTED.match(token):
        return None
    has_en = any(c in EN_ALPHA for c in token.lower())
    has_ru = any(c in RU_ALPHA for c in token.lower())
    if has_en and not has_ru and all(c in EN_TO_RU or c in NEUTRAL for c in token):
        return "en"
    if has_ru and not has_en and all(c in RU_TO_EN or c in NEUTRAL for c in token):
        return "ru"
    return None


def _should_convert(tokens: list[str], direction: str) -> bool:
    src, dst, table = (_EN, _RU, EN_TO_RU) if direction == "en" else (_RU, _EN, RU_TO_EN)
    gain, weight = 0.0, 0
    for t in tokens:
        orig, w = src.score(t)
        conv, _ = dst.score(_convert(t, table))
        gain += (conv - orig) * w
        weight += w
    return weight > 0 and gain / weight > THRESHOLD


def fix_layout(text: str) -> str:
    parts = re.split(r"(\s+)", text)
    out: list[str] = []
    run: list[str] = []  # word tokens of the current run
    run_parts: list[str] = []  # tokens + whitespace of the current run
    run_dir: str | None = None

    def flush() -> None:
        nonlocal run, run_parts, run_dir
        if run and run_dir and _should_convert(run, run_dir):
            table = EN_TO_RU if run_dir == "en" else RU_TO_EN
            out.extend(p if p.isspace() else _convert(p, table) for p in run_parts)
        else:
            out.extend(run_parts)
        run, run_parts, run_dir = [], [], None

    for part in parts:
        if not part:
            continue
        if part.isspace():
            (run_parts if run else out).append(part)
            continue
        d = _direction(part)
        if d is None or (run_dir and d != run_dir):
            trailing_ws = []
            while run_parts and run_parts[-1].isspace():
                trailing_ws.insert(0, run_parts.pop())
            flush()
            out.extend(trailing_ws)
        if d is None:
            out.append(part)
            continue
        run_dir = d
        run.append(part)
        run_parts.append(part)

    trailing_ws = []
    while run_parts and run_parts[-1].isspace():
        trailing_ws.insert(0, run_parts.pop())
    flush()
    out.extend(trailing_ws)
    return "".join(out)


# --------------------------------------------------------- language detection

# Average bigram score a text must reach to be called English / Russian. Calibrated on
# samples: English -1.0..-1.6 vs German/Spanish -2.8..-3.2; Russian -1.0..-2.3 overlaps
# with Bulgarian (-2.3..-2.7), so Russian also needs distinctive letters (or a very
# Russian score) and no Ukrainian ones.
_EN_MIN = -2.2
_RU_STRONG = -1.6
_RU_MIN = -2.2
_RU_ONLY = set("ыэё")
_UK_ONLY = set("іїєґ")


def _avg_score(model: _BigramModel, words_: list[str]) -> float:
    total, weight = 0.0, 0
    for w in words_:
        s, n = model.score(w)
        total += s * n
        weight += n
    return total / weight if weight else -99.0


def detect_language(text: str) -> str | None:
    """'en', 'ru', 'mixed' (both scripts) or None when unsure. Used only as a hint for the LLM."""
    tokens = [tok for tok in text.split() if not _PROTECTED.match(tok)]
    letters = [c for c in "".join(tokens).lower() if c.isalpha()]
    lat = [c for c in letters if c in EN_ALPHA]
    cyr = [c for c in letters if "а" <= c <= "я" or c in "ёіїєґ"]
    if len(lat) >= 3 and len(cyr) >= 3 and min(len(lat), len(cyr)) / len(letters) >= 0.25:
        return "mixed"
    words_ = re.findall(r"[^\W\d_]+", " ".join(tokens).lower())
    if lat and len(lat) / len(letters) >= 0.8:
        return "en" if _avg_score(_EN, words_) >= _EN_MIN else None
    if cyr and len(cyr) / len(letters) >= 0.8:
        if _UK_ONLY & set(cyr):
            return None
        score = _avg_score(_RU, words_)
        if score >= _RU_STRONG or (_RU_ONLY & set(cyr) and score >= _RU_MIN):
            return "ru"
    return None
