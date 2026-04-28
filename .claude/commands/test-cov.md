---
description: Roda suite de testes com cobertura e mostra gaps.
---

Rode a suite completa com cobertura:

```bash
uv run pytest --cov=apps --cov-report=term-missing --cov-report=html
```

Depois:

1. Mostre o summary de cobertura.
2. Liste os 5 arquivos com menor cobertura.
3. Para cada um, sugira 1-2 testes que fecham os gaps mais relevantes (não force 100%).
4. Se algum teste falhou, mostre o erro e proponha a correção — mas não aplique sem confirmação.
