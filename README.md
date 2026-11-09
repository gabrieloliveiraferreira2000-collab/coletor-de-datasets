# Coletor de Datasets

Aplicativo desktop gratuito e de código aberto para montar coletas simples de páginas web, aplicar filtros e salvar os resultados em CSV. A interface e a documentação estão em português; os dados são salvos localmente.

Desenvolvido por **Gabriel Oliveira Ferreira** — [GitHub: gabrieloliveiraferreira2000-collab](https://github.com/gabrieloliveiraferreira2000-collab).

O projeto começou como um coletor de preços de hardware para um TCC. Agora está evoluindo para aceitar perfis configuráveis de coleta. O leitor da KaBuM! da primeira versão continua incluído como exemplo de integração específica.

> Esta é uma versão inicial. Ela funciona melhor com páginas cujo conteúdo já vem no HTML. Sites que carregam os dados apenas depois de executar JavaScript ainda precisam de um conector específico.

## O que dá para fazer

- Definir a URL de busca e uma lista de termos pela interface.
- Usar tema escuro azul-petróleo numa janela centralizada de tamanho fixo.
- Indicar os resultados e campos com seletores CSS.
- Aplicar filtros por campo: contém, igual ou não contém.
- Limitar páginas e definir uma pausa entre requisições.
- Salvar e abrir perfis de coleta em JSON.
- Exportar os resultados para CSV com data, fonte e termo de busca.
- Rodar uma coleta offline específica da KaBuM! pela linha de comando.

## Requisitos

- Python 3.10 ou superior.
- Tkinter, incluído na maioria das instalações do Python. Em algumas distribuições Linux, ele precisa ser instalado pelo gerenciador de pacotes do sistema.
- Conexão com a internet para coletar páginas online.

## Instalação

### Windows

1. Instale Python 3.10 ou superior em [python.org](https://www.python.org/downloads/). Durante a instalação, marque **Add Python to PATH**.
2. Baixe este repositório pelo botão **Code → Download ZIP** no GitHub e extraia a pasta.
3. Abra o PowerShell dentro da pasta extraída e rode:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -e .
coletor-datasets
```

Se o comando `py` não estiver disponível, use `python` no lugar.

### macOS e Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
coletor-datasets
```

Também é possível iniciar com `python -m coletor_datasets`.

### Gerar executável no Windows

Com Python instalado, abra o PowerShell na pasta do projeto e rode:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_windows.ps1
```

O executável ficará em `Aplicativo\ColetorDeDatasets.exe`, junto com um pequeno guia. O primeiro início pode levar alguns segundos; o Windows também pode exibir um aviso por o arquivo ainda não ter assinatura digital.

## Primeiro perfil

1. Abra o aplicativo e informe o endereço de busca do site. Use `{termo}` no lugar do texto pesquisado e `{pagina}` para paginação. Exemplo: `https://exemplo.com/busca?q={termo}&pagina={pagina}`.
2. Informe o seletor CSS de cada resultado, por exemplo `.produto`.
3. Liste os campos, um por linha, no formato `nome | seletor CSS`. Exemplo:

```text
titulo | h2 a
preco | .preco
link | a | href
```

O terceiro item é opcional e indica o atributo HTML a extrair. Sem ele, o aplicativo guarda o texto visível. Para um link, use `a | href`; para uma imagem, `img | src`.

4. Digite os termos de busca, um por linha. Para abrir sempre a mesma página, deixe a URL sem `{termo}` e sem termos de busca.
5. Adicione filtros opcionais no formato `campo | operador | valor`:

```text
preco | contém | R$
titulo | não contém | recondicionado
```

Os operadores disponíveis são `contém`, `igual` e `não contém`. A comparação não diferencia maiúsculas de minúsculas.

6. Escolha o caminho do CSV e clique em **Iniciar coleta**. O aplicativo pede confirmação antes de substituir um arquivo existente.

Os nomes dos campos `coletado_em`, `fonte` e `termo_busca` são reservados para metadados da coleta.

## Perfil de exemplo

O arquivo [`perfis/lista_exemplo.json`](perfis/lista_exemplo.json) demonstra um perfil para uma página de catálogo. Ele é um modelo: substitua o endereço e os seletores pelos da fonte que você tem autorização para consultar.

## Como funciona a KaBuM! incluída

A coleta original de preços continua disponível pela linha de comando. Ela usa os filtros JSON existentes e é útil como exemplo de conector dedicado:

```bash
python -m pip install -e .
copy filtros.example.json filtros.json   # PowerShell
coletor-hardware --filtros filtros.json
```

Para testar sem acessar a loja, use o HTML sintético incluído:

```bash
coletor-hardware --filtros filtros.example.json --html tests/fixtures/kabum_busca_sintetica.html
```

Esse caminho legado ainda gera o CSV de hardware em `data/dataset_hardware.csv`.

## Limitações conhecidas

- A coleta genérica analisa HTML recebido por HTTP; não executa JavaScript, não interage com formulários e não acessa conteúdo atrás de login.
- Cada site pode alterar seu HTML e quebrar seletores. Faça uma coleta pequena primeiro e confira os dados.
- Os campos são salvos como texto no CSV. A conversão de preços, datas e outros tipos deve ser feita na análise posterior.
- O CSV é substituído quando você confirma a substituição de um arquivo existente; cada execução não cria automaticamente uma série histórica.
- Ainda não há instalador gráfico. O executável pode ser gerado no Windows pelo script de build.

## Próximas melhorias

- Assistente visual para selecionar elementos da página sem escrever seletores CSS.
- Prévia dos registros antes de iniciar uma coleta maior.
- Exportação para JSONL e mais opções para organizar execuções anteriores.
- Conectores prontos para outras fontes e páginas que dependem de JavaScript.

## Coleta responsável

- Antes de coletar, leia os termos do site e verifique o `robots.txt`. O aplicativo interrompe a coleta se o site proibir o acesso ou se não for possível consultar as regras.
- Use pausas, volumes pequenos e apenas dados públicos que você tenha autorização para usar. Não tente contornar logins, CAPTCHAs, bloqueios, limites técnicos ou controles de acesso.
- Respeite direitos autorais, privacidade e regras de proteção de dados aplicáveis. A responsabilidade pela escolha da fonte e pelo uso dos dados coletados é de quem executa a coleta.
- Confira se você tem direito de redistribuir os dados antes de publicar um dataset no GitHub.

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
ruff check .
python -m unittest discover -s tests -v
```

Os testes da versão inicial usam uma fixture sintética da KaBuM! e não acessam a internet. O GitHub Actions roda lint e testes em cada pull request e em envios para `main`.

## Como contribuir

Leia [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir uma issue ou pull request. Sugestões de novos conectores, melhorias de acessibilidade e traduções são bem-vindas.

## Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE).

