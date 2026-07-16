# VOIDFALL — backend

The authoritative game engine, natural-language parser, LLM narration boundary, and
FastAPI service. See the repository root `README.md` for the full picture.

```bash
pip install -e ".[dev]"
uvicorn voidfall.app.main:app --reload
pytest
```
