# E2E sample documents

Place your test files here. The platform E2E suite will pick them up automatically.

## Supported files

| File | Used when |
|------|-----------|
| `sample-invoice.pdf` | Preferred — full document upload test |
| `sample-invoice.png` | Image invoice |
| `sample-invoice.jpg` | Image invoice |
| Any `*.pdf` / `*.png` / `*.jpg` in this folder | First match wins |

## Override path

Set an explicit path before running tests:

```powershell
$env:E2E_SAMPLE_DOCUMENT = "C:\path\to\your-invoice.pdf"
pnpm test:e2e
```

## What gets tested

1. **API journey** — health, workflows, dry-run, test-run, audit detail, deploy + API run (live stack)
2. **UI journey** — dashboard, workflow builder, test run, audit report, optional file upload

## Prerequisites

Stack must be running:

```powershell
pnpm compose up --stack=dev --detach
pnpm dev
# or full Docker web: pnpm compose up --stack=dev --only=web --profile=web-docker --build --detach
```

Then:

```powershell
pnpm test:platform
```
