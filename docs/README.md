# Documentation

Read in this order:

1. [design.md](design.md) — durable product and geometry contract.
2. [status.md](status.md) — current scene authority and immediate work.
3. [validation.md](validation.md) — reusable promotion gates.
4. [glossary.md](glossary.md) — authoritative terminology.
5. [history.md](history.md) — rejected approaches and retained lessons.

Document roles are intentionally narrow:

| File | Owns | Does not own |
| --- | --- | --- |
| `design.md` | accepted product and architecture decisions | live progress |
| `status.md` | current facts, risks, and next milestone | experiment chronology |
| `validation.md` | reusable gates and evidence requirements | one-off results |
| `glossary.md` | stable meanings | design arguments |
| `history.md` | rejected methods and lessons | active instructions |

Local run notes, generated reports, and images stay together under ignored
`.work/runs/<name>/`. Promote only concise milestone conclusions into
`validation_reviews/`.
