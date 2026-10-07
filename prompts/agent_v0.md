Answer the question below by reading a collection of encyclopedia pages with two tools:

- search(query, k): the k best-matching page sections for a query (k at most 5).
- open_page(title, section, offset): a page by its exact title, read from its top; section keeps only the sections whose header contains that text; offset skips that many sections, to read further.

Section headers start each result. Links to other pages appear as [[Title]]. You can make at most 6 tool calls, and the results together hold at most 4,000 tokens. When you stop calling tools, reply with your answer.

Costs: a correct answer costs 0; not answering (abstaining) costs 1; a wrong answer costs 4 — four times not answering.

Reply with JSON only: {"answer": "<your answer>", "abstain": false}, or {"answer": null, "abstain": true} to abstain. Write names exactly as they appear in the question or evidence; give numbers as digits; for several names, separate them with commas; for two types, write "A / B"; for a damage factor, write ×2, ×0.5 and so on.

Question: {question}
