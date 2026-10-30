# Deterministic Classic fixtures

Run the fixture harness with a new private directory outside the project:

```text
python3 examples/run_fixture.py --output-dir /absolute/private/new-fixtures
```

| Scenario | Candidates | Synthetic planned calls |
| --- | ---: | ---: |
| `classic-two` | 2 | 7 |
| `classic-five` | 5 | 25 |

Each scenario exercises draft, attack, defense and judge phases through the final
winner, using deterministic synthetic text. Its private folder includes
`arena.json` and `winner.txt`. These are offline bookkeeping checks: no model or
agent call occurs, and no answer-quality or independent-agent claim is made.
