# Sample Data Toolkit

Generate LR/POD/Invoice demo documents and bulk-upload them to FreightIQ.

## Usage

```bash
cd sample_data
uv run python main.py --count 50 --fraud-count 5 --match
```

Options:
- `--base-url` backend URL (default `http://localhost:8000`)
- `--output-dir` generated files directory
- `--archive` zip path used for batch upload
- `--match` run `/api/triplets/match` after upload
