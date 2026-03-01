Place local `faisalq/EgyBERT` files in this directory before Docker build.

Expected files include:
- `config.json`
- `pytorch_model.bin` (or `model.safetensors`)
- tokenizer files (`tokenizer.json`, `vocab.txt`, etc.)

Download helper:
`python backend/download_egybert.py`
