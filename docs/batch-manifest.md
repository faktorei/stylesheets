# Batch manifest (JSONL)

A manifest lets one batch mix languages, profiles, and output names per document.
It is **JSONL** — one JSON object per line — chosen because it streams at 100k
rows, diffs cleanly, and makes the resume checkpoint trivial. It is *generated
output*, not a config file: **one wire format, one parser, no comment syntax.**

## Fields

| field | required | meaning |
|---|---|---|
| `input` | **yes** | source document, a safe basename resolved in the job's input root |
| `output` | no | output filename; omitted → derived from `input` (`a.xml → a.pdf`) |
| `lang` | no | label language; omitted → job default → engine default |
| `profile` | no | `peppol` / `xrechnung` / …; omitted → job default → engine default (`auto`) |

**The cascade is row → job → engine.** Omitted `lang`/`profile` fall back to the
job-level defaults supplied at submission (CLI `--lang`/`--profile`; HTTP query
params), then to engine defaults. So a single-language batch is just bare rows:

```jsonl
{"input":"invoice-001.xml"}
{"input":"invoice-002.xml"}
{"input":"invoice-003.xml","lang":"de","profile":"xrechnung","output":"rechnung-003.pdf"}
```

## Rules (all enforced at submission, not mid-job)

- **UTF-8**; blank lines are skipped; there is no comment syntax.
- Any non-blank line that is not a valid JSON object is **rejected with its line
  number** — the whole job fails before rendering starts.
- A known field present with a non-string value is rejected.
- **Duplicate `output` names are a hard rejection** — two rows writing one file is
  silent data loss under concurrency.
- `input`/`output` are reduced to a safe basename (the same zip-slip defense the
  zip surface uses); `..` and traversal are rejected.
- **Unknown fields are ignored with a warning**, counted once per field name in
  `report.json` under `warnings.unknown_manifest_fields`. This is the
  forward-compatibility valve: a manifest written for a newer engine still runs on
  an older one.

## Running it

**CLI** — the manifest lives alongside (or references) the input dir; the
checkpoint is written into the output dir:

```sh
faktorei-engine batch ./in ./out --manifest ./manifest.jsonl [--lang en] [--profile peppol]
faktorei-engine batch ./in ./out --manifest ./manifest.jsonl --resume   # continue a partial job
```

**HTTP** — include a `manifest.jsonl` entry in the POST /batch zip and the engine
switches to manifest mode automatically (one-shot; job defaults come from the
`lang`/`profile` query params). Without it, every `*.xml` in the zip is rendered
with the job defaults.

## Resume safety

`--resume` continues from a `.checkpoint` in the output dir: rows whose `input` is
already recorded are skipped (a recorded name always means a completely written
PDF, because outputs are atomic-renamed into place). The checkpoint stores the
manifest's content hash and **resume refuses, clearly and at startup, if the
manifest on disk no longer matches** — resuming against an edited manifest
(reordered rows, a fixed typo, a changed output mapping) is undefined behavior, so
the answer is "start a new job or restore the original manifest," never a silent
mis-resume.

## Have a spreadsheet? Convert it.

Keep your file list in Excel and export CSV (a header row with an `input` column;
`lang`/`profile`/`output` optional). One converter, no second wire format:

```sh
python3 tools/csv_to_jsonl.py files.csv > manifest.jsonl
```

Empty cells are omitted (so the cascade applies) and unknown columns pass through
(the engine ignores unknown fields).
