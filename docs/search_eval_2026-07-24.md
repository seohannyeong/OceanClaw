# Search Evaluation - 2026-07-24

## Test Setup

- PDF: `data/raw/yanmar_6lf_operation_manual.pdf`
- Chunks: `data/processed/pdf_chunks.jsonl`
- Index: `index/pdf.faiss`
- Retriever: Dense retriever
- Embedding: Ollama `nomic-embed-text`
- Top-k: 3

## Summary

English queries mostly retrieved relevant chunks.

Korean queries failed because the source manual is English and the current embedding/search pipeline does not translate or expand Korean queries before retrieval.

## Results

| No. | Query | Top Result | Judgment | Note |
| --- | --- | --- | --- | --- |
| 1 | `engine oil capacity` | p.61 / p.41 | Partial | Retrieved oil/fuel quantity text. Relevant but duplicated pages appeared. |
| 2 | `fuel filter replacement` | p.73, p.78 | Good | Retrieved engine oil filter and fuel filter replacement related chunks. |
| 3 | `coolant level check` | p.70 | Good | Retrieved `Check Coolant Level` directly. |
| 4 | `battery warning` | p.37, p.57, p.70 | Good | Retrieved battery switch warning and battery charging/check content. |
| 5 | `daily checks before operation` | p.64 | Good | Retrieved `The Importance of Daily Checks`. |
| 6 | `엔진 오일 점검 방법` | p.90 | Weak | Retrieved unrelated emergency blank page. Korean query failed. |
| 7 | `연료 필터 교체 방법` | p.14 | Weak | Retrieved unrelated neutral/acceleration text. Korean query failed. |
| 8 | `냉각수 확인 방법` | p.53 | Weak | Retrieved unrelated control panel text. Korean query failed. |
| 9 | `engine overheating warning` | p.22 | Good | Retrieved `High Coolant Temperature` warning. |
| 10 | `replace engine oil filter` | p.73 | Good | Retrieved `Replace Engine Oil Filter` directly. |

## Weak Points

1. Korean natural-language queries are weak.
2. Some English queries retrieve duplicated content from repeated manual sections.
3. Dense retrieval alone may be weak for exact model names, numbers, part names, and maintenance codes.

## Recommended Next Fixes

1. Add query expansion for Korean-to-English maintenance terms. Done.
2. Add a small domain dictionary. Done:
   - `엔진 오일` -> `engine oil`
   - `점검` -> `check inspect`
   - `연료 필터` -> `fuel filter`
   - `교체` -> `replace replacement`
   - `냉각수` -> `coolant`
   - `경고` -> `warning alarm`
3. Re-run the same 10 queries after expansion.
4. Later, add sparse BM25 and combine it with dense retrieval as hybrid search.

## Query Expansion Re-test

| Query | Expanded Query Effect | Judgment |
| --- | --- | --- |
| `엔진 오일 점검 방법` | Expanded to include `engine oil level dipstick MIN MAX check inspect`. Retrieved p.69 `Check Oil Level in Engine` in top-2. | Good |
| `연료 필터 교체 방법` | Expanded to include `fuel filter replace replacement drain water`. Retrieved filter replacement related chunks. | Partial |
| `냉각수 확인 방법` | Expanded to include `coolant level cooling circuit check inspect`. Retrieved p.70 `Check Coolant Level` in top-2. | Good |

Query expansion improved Korean retrieval significantly, but exact ranking still needs improvement. For example, `냉각수 확인 방법` found the correct coolant level chunk at rank 2, not rank 1.
