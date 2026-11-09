# Contribuindo

Obrigado por ajudar a melhorar o Coletor de Datasets.

## Antes de começar

- Procure issues existentes para evitar trabalho duplicado.
- Para mudanças grandes, abra uma issue primeiro e descreva o problema e a solução proposta.
- Não inclua dados pessoais, credenciais, HTML copiado de terceiros ou datasets protegidos no repositório.

## Preparar o ambiente

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Pull requests

1. Faça uma alteração pequena e explique o motivo.
2. Inclua ou ajuste testes quando alterar comportamento.
3. Rode `ruff check .` e `python -m unittest discover -s tests -v`.
4. Descreva como a mudança foi verificada e inclua imagens se alterar a interface.
5. Não envie arquivos gerados, configurações pessoais nem dados coletados.

Conectores novos devem consultar as regras do site, usar identificador claro, incluir dados sintéticos para testes e documentar limites e campos extraídos.

