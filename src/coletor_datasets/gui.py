"""Interface gráfica simples para configurar e executar perfis de coleta."""

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from coletor_datasets.coleta_web import Perfil, Regra, coletar

CORES = {
    "fundo": "#09171C",
    "superficie": "#10252C",
    "superficie_clara": "#17343C",
    "entrada": "#0B1E24",
    "borda": "#294750",
    "texto": "#E6F1F3",
    "texto_suave": "#A3B8BE",
    "destaque": "#087E8B",
    "destaque_ativo": "#0A6875",
    "log": "#0C2026",
}


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Coletor de Datasets")
        largura_tela = self.root.winfo_screenwidth()
        altura_tela = self.root.winfo_screenheight()
        # Janela maior para aproveitar monitores de alta resolução, mantendo
        # uma dimensão fixa e respeitando a área disponível do monitor.
        largura = min(2400, largura_tela - 80)
        altura = min(1600, altura_tela - 120)
        self.root.geometry(f"{largura}x{altura}")
        self.root.minsize(largura, altura)
        self.root.maxsize(largura, altura)
        self.root.resizable(False, False)
        self.root.configure(bg=CORES["fundo"])
        self.eventos: queue.Queue = queue.Queue()
        self.executando = False
        self.saida_var = tk.StringVar(value=str(Path("data") / "meu_dataset.csv"))
        self._estilo()
        self._montar()
        self.root.update_idletasks()
        x = max(0, (largura_tela - largura) // 2)
        y = max(0, (altura_tela - altura) // 2)
        self.root.geometry(f"{largura}x{altura}+{x}+{y}")
        self.root.after(120, self._ler_eventos)

    def _estilo(self) -> None:
        estilo = ttk.Style(self.root)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("TFrame", background=CORES["fundo"])
        estilo.configure("Card.TFrame", background=CORES["superficie"])
        estilo.configure(
            "TLabel",
            background=CORES["fundo"],
            foreground=CORES["texto"],
            font=("Segoe UI", 11),
        )
        estilo.configure(
            "Title.TLabel",
            background=CORES["fundo"],
            foreground=CORES["texto"],
            font=("Segoe UI Semibold", 28),
        )
        estilo.configure(
            "Sub.TLabel",
            background=CORES["fundo"],
            foreground=CORES["texto_suave"],
            font=("Segoe UI", 12),
        )
        estilo.configure(
            "Eyebrow.TLabel",
            background=CORES["fundo"],
            foreground="#59C5C5",
            font=("Segoe UI Semibold", 11),
        )
        estilo.configure(
            "CardTitle.TLabel",
            background=CORES["superficie"],
            foreground=CORES["texto"],
            font=("Segoe UI Semibold", 14),
        )
        estilo.configure(
            "CardText.TLabel",
            background=CORES["superficie"],
            foreground=CORES["texto_suave"],
        )
        estilo.configure(
            "TEntry",
            fieldbackground=CORES["entrada"],
            foreground=CORES["texto"],
            bordercolor=CORES["borda"],
            lightcolor=CORES["borda"],
            darkcolor=CORES["borda"],
            padding=10,
        )
        estilo.configure(
            "Coleta.Horizontal.TProgressbar",
            troughcolor=CORES["superficie_clara"],
            background="#20B6B4",
            bordercolor=CORES["superficie"],
            lightcolor="#20B6B4",
            darkcolor="#20B6B4",
        )

    def _montar(self) -> None:
        base = ttk.Frame(self.root, padding=(24, 16))
        base.pack(fill="both", expand=True)
        ttk.Label(base, text="COLETOR DE DATASETS", style="Eyebrow.TLabel").pack(
            anchor="w", pady=(0, 3)
        )
        ttk.Label(base, text="Monte seu próximo dataset", style="Title.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            base,
            text=(
                "Configure uma fonte, escolha os campos e filtre os resultados. "
                "Seu arquivo fica no computador."
            ),
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(4, 12))

        colunas = ttk.Frame(base)
        colunas.pack(fill="both", expand=True)
        esquerda = ttk.Frame(colunas, style="Card.TFrame", padding=18)
        direita = ttk.Frame(colunas, style="Card.TFrame", padding=18)
        esquerda.pack(side="left", fill="both", expand=True, padx=(0, 8))
        direita.pack(side="left", fill="both", expand=True, padx=(8, 0))
        cabecalho = ttk.Frame(esquerda, style="Card.TFrame")
        cabecalho.pack(fill="x")
        ttk.Label(cabecalho, text="01  ·  Fonte e campos", style="CardTitle.TLabel").pack(
            side="left", anchor="w"
        )
        self._botao(cabecalho, "Ajuda", self._ajuda_seletores).pack(side="right")
        ttk.Label(
            esquerda,
            text="Use seletores CSS para indicar onde cada dado aparece.",
            style="CardText.TLabel",
            wraplength=400,
        ).pack(anchor="w", pady=(3, 12))

        self.nome = self._campo(esquerda, "Nome da fonte", "Minha fonte")
        self.url = self._campo(
            esquerda,
            "URL da busca",
            "https://exemplo.com/busca?q={termo}&pagina={pagina}",
        )
        self.seletor = self._campo(esquerda, "Seletor CSS de cada resultado", ".produto")
        ttk.Label(
            esquerda,
            text="Campos (um por linha: nome | seletor CSS | atributo opcional)",
            style="CardText.TLabel",
            wraplength=390,
        ).pack(anchor="w", pady=(7, 4))
        self.campos = self._texto(esquerda, height=4)
        self.campos.insert("1.0", "titulo | h2 a\npreco | .preco\nlink | a | href")
        ttk.Label(
            esquerda,
            text="Use {termo} e {pagina} na URL. Sem {termo}, a página será aberta uma vez.",
            style="CardText.TLabel",
            wraplength=390,
        ).pack(anchor="w", pady=(5, 8))
        self.termos = self._texto(esquerda, height=2)
        self.termos.insert("1.0", "produto para pesquisar")

        ttk.Label(direita, text="02  ·  Filtros e saída", style="CardTitle.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            direita,
            text="As regras usam os nomes que você definiu na lista de campos.",
            style="CardText.TLabel",
            wraplength=390,
        ).pack(anchor="w", pady=(3, 12))
        ttk.Label(
            direita,
            text="Regras (campo | contém/igual/não contém | valor)",
            style="CardText.TLabel",
            wraplength=390,
        ).pack(anchor="w", pady=(4, 4))
        self.regras = self._texto(direita, height=4)
        self.regras.insert("1.0", "preco | contém | R$\nlink | não contém | /anuncio/antigo")
        self.paginas = self._campo(direita, "Máximo de páginas por termo", "2")
        self.pausa = self._campo(direita, "Pausa entre páginas (segundos, mínimo 1)", "2")
        ttk.Label(direita, text="Arquivo CSV de saída", style="CardText.TLabel").pack(
            anchor="w", pady=(7, 4)
        )
        saida_linha = ttk.Frame(direita, style="Card.TFrame")
        saida_linha.pack(fill="x")
        ttk.Entry(saida_linha, textvariable=self.saida_var).pack(side="left", fill="x", expand=True)
        self._botao(saida_linha, "Escolher…", self._escolher_saida).pack(
            side="left", padx=(6, 0)
        )

        acoes = ttk.Frame(base)
        acoes.pack(fill="x", pady=(10, 5))
        self.btn_carregar = self._botao(acoes, "Abrir perfil…", self._abrir_perfil)
        self.btn_carregar.pack(side="left")
        self.btn_salvar = self._botao(acoes, "Salvar perfil…", self._salvar_perfil)
        self.btn_salvar.pack(side="left", padx=8)
        self.btn_coletar = self._botao(
            acoes, "Iniciar coleta", self._iniciar, principal=True
        )
        self.btn_coletar.pack(side="right")
        self.status = tk.StringVar(value="Pronto para configurar uma coleta.")
        self.progress = ttk.Progressbar(
            base,
            mode="indeterminate",
            style="Coleta.Horizontal.TProgressbar",
            maximum=100,
        )
        self.status_label = ttk.Label(base, textvariable=self.status, style="Sub.TLabel")
        self.status_label.pack(anchor="w", pady=(0, 5))
        self.progress.pack(fill="x", pady=(0, 6))
        self.progress.pack_forget()
        self.log = self._texto(base, height=3)
        self.log.configure(
            state="disabled",
            bg=CORES["log"],
            fg=CORES["texto_suave"],
            insertbackground=CORES["texto"],
            selectbackground=CORES["destaque"],
            highlightbackground=CORES["borda"],
            highlightcolor=CORES["destaque"],
            highlightthickness=1,
            relief="flat",
        )

        # Posiciona o rótulo acima do campo mesmo após o formulário ser montado.
        ttk.Label(
            esquerda, text="Termos de busca (um por linha)", style="CardText.TLabel"
        ).pack(anchor="w", pady=(3, 4), before=self.termos)

    def _campo(self, pai, rotulo: str, valor: str) -> ttk.Entry:
        ttk.Label(pai, text=rotulo, style="CardText.TLabel", wraplength=390).pack(
            anchor="w", pady=(6, 4)
        )
        entrada = ttk.Entry(pai)
        entrada.insert(0, valor)
        entrada.pack(fill="x")
        return entrada

    @staticmethod
    def _botao(pai, rotulo: str, comando, principal: bool = False) -> tk.Button:
        cor_fundo = CORES["destaque"] if principal else CORES["superficie_clara"]
        cor_ativo = CORES["destaque_ativo"] if principal else CORES["borda"]
        return tk.Button(
            pai,
            text=rotulo,
            command=comando,
            bg=cor_fundo,
            fg="#FFFFFF" if principal else CORES["texto"],
            activebackground=cor_ativo,
            activeforeground="#FFFFFF",
            disabledforeground=CORES["texto_suave"],
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=CORES["borda"],
            highlightcolor=CORES["destaque"],
            padx=13,
            pady=8,
            font=("Segoe UI Semibold", 10),
        )

    @staticmethod
    def _texto(pai, height: int) -> tk.Text:
        caixa = tk.Text(
            pai,
            height=height,
            wrap="word",
            font=("Segoe UI", 11),
            bg=CORES["entrada"],
            fg=CORES["texto"],
            insertbackground=CORES["texto"],
            selectbackground=CORES["destaque"],
            highlightbackground=CORES["borda"],
            highlightcolor=CORES["destaque"],
            highlightthickness=1,
            relief="flat",
            padx=9,
            pady=7,
        )
        caixa.pack(fill="x")
        return caixa

    def _escolher_saida(self) -> None:
        caminho = filedialog.asksaveasfilename(
            title="Salvar dataset", defaultextension=".csv",
            filetypes=[("Planilha CSV", "*.csv"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            self.saida_var.set(caminho)

    def _ajuda_seletores(self) -> None:
        texto = (
            "O seletor CSS aponta para partes do HTML da página. Exemplos:\n\n"
            "• .produto — elemento com a classe produto\n"
            "• h2 a — link dentro de um título h2\n"
            "• .preco — elemento com a classe preco\n\n"
            "Para encontrar um seletor, abra a página no navegador, clique com o botão direito "
            "no dado e escolha Inspecionar. O aplicativo lê o HTML recebido; ele não executa "
            "JavaScript. Se os dados só aparecem depois de a página carregar, este perfil pode "
            "não funcionar.\n\n"
            "Para extrair texto, use: titulo | h2 a\n"
            "Para extrair um atributo: link | a | href"
        )
        messagebox.showinfo("Ajuda com seletores", texto, parent=self.root)

    def _regras_da_tela(self) -> list[Regra]:
        regras = []
        texto = self.regras.get("1.0", "end").strip()
        for numero, linha in enumerate(texto.splitlines(), 1):
            if not linha.strip():
                continue
            partes = [parte.strip() for parte in linha.split("|", 2)]
            if len(partes) != 3:
                raise ValueError(f"Regra na linha {numero}: use campo | operador | valor.")
            regras.append(Regra(*partes))
        return regras

    def _perfil_da_tela(self) -> Perfil:
        campos = {}
        for numero, linha in enumerate(self.campos.get("1.0", "end").strip().splitlines(), 1):
            if not linha.strip():
                continue
            partes = [parte.strip() for parte in linha.split("|", 2)]
            if len(partes) not in (2, 3):
                raise ValueError(
                    f"Campo na linha {numero}: use nome | seletor CSS | atributo opcional."
                )
            chave, seletor = partes[:2]
            if len(partes) == 3:
                seletor = f"{seletor} :: {partes[2]}"
            campos[chave] = seletor
        termos = [t.strip() for t in self.termos.get("1.0", "end").splitlines() if t.strip()]
        try:
            paginas = int(self.paginas.get())
            pausa = float(self.pausa.get())
        except ValueError as erro:
            raise ValueError("Páginas e pausa precisam ser números.") from erro
        return Perfil.de_dict({
            "nome": self.nome.get(), "url_busca": self.url.get(),
            "seletor_item": self.seletor.get(), "campos": campos,
            "termos_busca": termos, "max_paginas": paginas,
            "pausa_segundos": pausa, "regras": [r.__dict__ for r in self._regras_da_tela()],
        })

    def _salvar_perfil(self) -> None:
        try:
            perfil = self._perfil_da_tela()
        except ValueError as erro:
            messagebox.showerror("Revise os campos", str(erro), parent=self.root)
            return
        caminho = filedialog.asksaveasfilename(
            title="Salvar perfil de coleta", defaultextension=".json",
            filetypes=[("Perfil do coletor", "*.json")],
        )
        if caminho:
            texto = json.dumps(perfil.para_dict(), ensure_ascii=False, indent=2)
            try:
                Path(caminho).write_text(texto, encoding="utf-8")
            except OSError as erro:
                messagebox.showerror("Não foi possível salvar", str(erro), parent=self.root)
                return
            self.status.set(f"Perfil salvo em {caminho}")

    def _abrir_perfil(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Abrir perfil", filetypes=[("Perfil do coletor", "*.json")]
        )
        if not caminho:
            return
        try:
            perfil = Perfil.de_arquivo(caminho)
        except (OSError, ValueError) as erro:
            messagebox.showerror("Não foi possível abrir", str(erro), parent=self.root)
            return
        self.nome.delete(0, "end")
        self.nome.insert(0, perfil.nome)
        self.url.delete(0, "end")
        self.url.insert(0, perfil.url_busca)
        self.seletor.delete(0, "end")
        self.seletor.insert(0, perfil.seletor_item)
        campos = "\n".join(f"{nome} | {seletor}" for nome, seletor in perfil.campos.items())
        self._substituir_texto(self.campos, campos)
        self._substituir_texto(self.termos, "\n".join(perfil.termos_busca))
        regras = "\n".join(
            f"{regra.campo} | {regra.operador} | {regra.valor}"
            for regra in perfil.regras
        )
        self._substituir_texto(self.regras, regras)
        self.paginas.delete(0, "end")
        self.paginas.insert(0, str(perfil.max_paginas))
        self.pausa.delete(0, "end")
        self.pausa.insert(0, str(perfil.pausa_segundos))
        self.status.set(f"Perfil carregado: {perfil.nome}")

    @staticmethod
    def _substituir_texto(widget: tk.Text, valor: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", valor)

    def _iniciar(self) -> None:
        try:
            perfil = self._perfil_da_tela()
        except ValueError as erro:
            messagebox.showerror("Revise a configuração", str(erro), parent=self.root)
            return
        destino = Path(self.saida_var.get()).expanduser()
        if not destino.name:
            messagebox.showerror(
                "Escolha onde salvar",
                "Informe um caminho para o arquivo CSV.",
                parent=self.root,
            )
            return
        existe = destino.exists()
        confirmar = messagebox.askyesno(
            "Substituir arquivo?",
            f"{destino} já existe. Deseja substituir?",
            parent=self.root,
        ) if existe else True
        if not confirmar:
            return
        self.executando = True
        self.btn_coletar.configure(state="disabled")
        self.btn_carregar.configure(state="disabled")
        self.btn_salvar.configure(state="disabled")
        self.status.set("Coleta em andamento…")
        self.progress.pack(fill="x", pady=(0, 6), before=self.status_label)
        self.progress.start(12)
        self._registrar(f"Iniciando perfil: {perfil.nome}")
        threading.Thread(target=self._trabalhador, args=(perfil, destino), daemon=True).start()

    def _trabalhador(self, perfil: Perfil, destino: Path) -> None:
        try:
            resultado = coletar(
                perfil,
                destino,
                ao_atualizar=lambda texto: self.eventos.put(("log", texto)),
            )
            self.eventos.put(("concluido", resultado, str(destino)))
        except Exception as erro:
            self.eventos.put(("erro", str(erro)))

    def _ler_eventos(self) -> None:
        try:
            while True:
                evento = self.eventos.get_nowait()
                if evento[0] == "log":
                    self.status.set(evento[1])
                    self._registrar(evento[1])
                elif evento[0] == "erro":
                    self.executando = False
                    self.progress.stop()
                    self.progress.pack_forget()
                    self._botoes(True)
                    self.status.set("A coleta foi interrompida.")
                    self._registrar("Falha: " + evento[1])
                    messagebox.showerror("Falha na coleta", evento[1], parent=self.root)
                elif evento[0] == "concluido":
                    self.executando = False
                    self.progress.stop()
                    self.progress.pack_forget()
                    self._botoes(True)
                    gravados, descartados = evento[1]
                    self.status.set(
                        f"Pronto: {gravados} registros coletados; "
                        f"{descartados} filtrados."
                    )
                    self._registrar(f"Arquivo salvo em {evento[2]}")
                    resumo = (
                        f"Registros salvos: {gravados}\n"
                        f"Removidos pelos filtros: {descartados}\n\n"
                        f"Arquivo: {evento[2]}"
                    )
                    messagebox.showinfo(
                        "Coleta concluída", resumo, parent=self.root
                    )
        except queue.Empty:
            pass
        self.root.after(120, self._ler_eventos)

    def _botoes(self, habilitar: bool) -> None:
        estado = "normal" if habilitar else "disabled"
        for botao in (self.btn_coletar, self.btn_carregar, self.btn_salvar):
            botao.configure(state=estado)

    def _registrar(self, texto: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", texto + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

