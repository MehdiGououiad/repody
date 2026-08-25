# OvisOCR2 GGUF (research)

Official model: [ATH-MaaS/OvisOCR2](https://huggingface.co/ATH-MaaS/OvisOCR2)  
GGUF: [Abiray/OvisOCR2-GGUF](https://huggingface.co/Abiray/OvisOCR2-GGUF)

Stable local pack: **`OvisOCR2-Q8_0.gguf` + `mmproj-F16.gguf`** (Abiray: Q8 ≈ F16 text quality; F16 projector recommended).

```powershell
llama-server `
  -m deploy/research/ovisocr2/models/OvisOCR2-Q8_0.gguf `
  --mmproj deploy/research/ovisocr2/models/mmproj-F16.gguf `
  --port 8091 -c 8192 -ngl 99 -a OvisOCR2 --temp 0.0 --jinja
```

Official document-parse prompt (ATH-MaaS): see model card — reading-order Markdown, LaTeX formulas, HTML tables, no translation; `temperature=0.0`.

## Local result (2026-08-06)

| Doc | Field hit-rate | Notes |
|---|---|---|
| Facture.pdf | **2/2 (100%)** · ~18s | Totals/TVA correct |
| hopital-devis-agadir.png | **5/6 (83%)** · ~85–150s | ICE + totals OK; INPE read `040063564` vs `040063554`; long runs can hit max_tokens with trailing repeats |

Not wired into the product catalog yet — research only.
