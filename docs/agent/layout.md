# Wrong-layout detection (`layout.py`)

- `EN_TO_RU` / `RU_TO_EN`: ЙЦУКЕН ↔ QWERTY key tables incl. shifted symbols
  (`?`↔`,`, `/`↔`.`, `@`↔`"`, `#`↔`№` …). `NEUTRAL` chars are identical in both.
- Text is split on whitespace; each token gets a direction (`en` = Latin that could be
  mistyped Russian, `ru` = the reverse) or `None` (protected: URLs, e-mails, `@mentions`,
  `#tags`, Discord `<@…>`, `:emoji:`, mixed scripts).
- Consecutive tokens with the same direction form a **run**; a run is converted as a
  whole only if the converted text scores better by `THRESHOLD` (avg log-prob per
  bigram). Run-level decisions handle short ambiguous words (`z` → `я`, `lf` → `да`).
- Scores come from tiny character-bigram models trained at import time on the word
  lists in `lang_data.py` (+ a dictionary bonus for exact hits, penalty for junk
  characters inside a word).

Why: instant, offline, good enough for whole messages typed in the wrong layout
(the real use case). Single rare words may stay unconverted — acceptable.

## Language detection (`detect_language`)

Used only to add an explicit language line to the LLM prompt. Returns `en`, `ru`,
`mixed` (≥25 % of letters in each script) or `None`. It must never claim a wrong
language — a wrong "Russian" hint could make the model russify Bulgarian/Ukrainian text —
so it is deliberately conservative: English needs an average EN bigram score ≥ −2.2
(German/Spanish score ≈ −3); Russian needs a very Russian score or ы/э/ё, and no
Ukrainian letters. `None` falls back to "same language as the message".
Cases live in `DETECT_CASES` in `tests/test_layout.py`.

Changing word lists or the threshold: run `python -m tests.test_layout` and keep all
cases passing; add a case for every bug you fix. Things that must stay untouched:
`ok`, `lol`, `xD`, `gg wp`, `npm install`, git commands, links.
