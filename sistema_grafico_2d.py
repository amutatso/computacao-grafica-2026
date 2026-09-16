"""
Sistema Gráfico Interativo - Trabalho 1.1
==========================================
Sistema básico de Computação Gráfica 2D com:
    - Display File (pontos, retas e wireframes/polígonos)
    - Window (região do mundo visualizada)
    - Viewport (transformação window -> tela, sem distorção)
    - Panning (mover a window)
    - Zooming (redimensionar a window)

O código é dividido em 4 partes bem separadas:
    1) DISPLAY FILE  -> o que existe no mundo
    2) WINDOW        -> o que está sendo visualizado do mundo
    3) VIEWPORT       -> como converter mundo -> pixels de tela
    4) INTERFACE (Tkinter) -> junta tudo e desenha na tela

Só usamos canvas.create_line() para desenhar (pontos, retas e
wireframes). Não usamos create_polygon nem create_oval.
"""

import ast
import tkinter as tk
from tkinter import messagebox


# =============================================================
# 1) DISPLAY FILE
# =============================================================
# O Display File é a lista de todos os objetos gráficos que
# existem no mundo. Cada objeto tem:
#   - nome           : identifica o objeto na lista
#   - tipo            : "ponto", "reta" ou "wireframe"
#   - coordenadas     : lista de tuplas (x, y), em coordenadas do MUNDO

class Objeto2D:
    def __init__(self, nome, tipo, coordenadas):
        self.nome = nome
        self.tipo = tipo                  # "ponto" | "reta" | "wireframe"
        self.coordenadas = coordenadas    # [(x1, y1), (x2, y2), ...]

    def __repr__(self):
        return f"{self.nome} [{self.tipo}]"


class DisplayFile:
    """Guarda a lista de todos os objetos do mundo."""

    def __init__(self):
        self.objetos = []

    def adicionar(self, nome, tipo, coordenadas):
        objeto = Objeto2D(nome, tipo, coordenadas)
        self.objetos.append(objeto)
        return objeto

    def remover_por_indice(self, indice):
        del self.objetos[indice]


# =============================================================
# 2) WINDOW
# =============================================================
# A Window é a "câmera": define qual pedaço do mundo está sendo
# visualizado no momento, em coordenadas do MUNDO.

class Window:
    def __init__(self, xmin, ymin, xmax, ymax):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax

    @property
    def largura(self):
        return self.xmax - self.xmin

    @property
    def altura(self):
        return self.ymax - self.ymin

    @property
    def centro(self):
        return (self.xmin + self.xmax) / 2, (self.ymin + self.ymax) / 2

    def mover(self, dx, dy):
        """Panning: desloca a window pelo mundo, sem mudar seu tamanho."""
        self.xmin += dx
        self.xmax += dx
        self.ymin += dy
        self.ymax += dy

    def aplicar_zoom(self, fator):
        """
        Zooming: muda o tamanho da window mantendo o mesmo centro.
        fator < 1 -> aproxima (zoom in, vê menos mundo, objetos maiores)
        fator > 1 -> afasta   (zoom out, vê mais mundo, objetos menores)
        """
        cx, cy = self.centro
        nova_largura = self.largura * fator
        nova_altura = self.altura * fator
        self.xmin = cx - nova_largura / 2
        self.xmax = cx + nova_largura / 2
        self.ymin = cy - nova_altura / 2
        self.ymax = cy + nova_altura / 2


# =============================================================
# 3) VIEWPORT
# =============================================================
# Converte um ponto em coordenadas do MUNDO (dentro da window)
# para coordenadas de TELA (pixels dentro do canvas).
#
# Ponto importante: para NÃO distorcer os objetos, usamos a MESMA
# escala nos eixos X e Y (a menor das duas escalas possíveis).

class Viewport:
    def __init__(self, largura_tela, altura_tela, margem=20):
        self.largura_tela = largura_tela
        self.altura_tela = altura_tela
        self.margem = margem  # espaço (em pixels) que deixamos livre nas bordas

    def transformar(self, ponto_mundo, window: Window):
        x_mundo, y_mundo = ponto_mundo

        area_util_x = self.largura_tela - 2 * self.margem
        area_util_y = self.altura_tela - 2 * self.margem

        # Mesma escala nos dois eixos -> não distorce o objeto
        escala_x = area_util_x / window.largura
        escala_y = area_util_y / window.altura
        escala = min(escala_x, escala_y)

        # Centraliza o conteúdo dentro da área útil do canvas
        largura_usada = window.largura * escala
        altura_usada = window.altura * escala
        offset_x = self.margem + (area_util_x - largura_usada) / 2
        offset_y = self.margem + (area_util_y - altura_usada) / 2

        x_tela = offset_x + (x_mundo - window.xmin) * escala
        # Eixo Y da tela cresce para baixo; eixo Y do mundo cresce para
        # cima -> por isso o Y é invertido aqui.
        y_tela = offset_y + (window.ymax - y_mundo) * escala

        return x_tela, y_tela


# =============================================================
# 4) INTERFACE GRÁFICA (Tkinter)
# =============================================================

class Aplicacao:
    LARGURA_CANVAS = 640
    ALTURA_CANVAS = 640

    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title("Sistema Gráfico Interativo 2D")

        self.display_file = DisplayFile()
        self.window = Window(xmin=-100, ymin=-100, xmax=100, ymax=100)
        self.viewport = Viewport(self.LARGURA_CANVAS, self.ALTURA_CANVAS)

        self._montar_interface()
        self._redesenhar()

    # ---------------------------------------------------------
    # Montagem da interface (canvas + painel lateral)
    # ---------------------------------------------------------
    def _montar_interface(self):
        # --- Canvas (à esquerda) ---
        self.canvas = tk.Canvas(
            self.raiz,
            width=self.LARGURA_CANVAS,
            height=self.ALTURA_CANVAS,
            bg="white",
        )
        self.canvas.grid(row=0, column=0, rowspan=20, padx=10, pady=10)

        # --- Painel lateral (à direita) ---
        painel = tk.Frame(self.raiz)
        painel.grid(row=0, column=1, sticky="n", padx=10, pady=10)

        # Lista de objetos existentes
        tk.Label(painel, text="Objetos").pack(anchor="w")
        self.lista_objetos = tk.Listbox(painel, width=30, height=8)
        self.lista_objetos.pack()

        # --- Formulário de novo objeto ---
        tk.Label(painel, text="Novo objeto").pack(anchor="w", pady=(15, 0))

        tk.Label(painel, text="Nome:").pack(anchor="w")
        self.entrada_nome = tk.Entry(painel, width=30)
        self.entrada_nome.pack()

        tk.Label(painel, text="Tipo:").pack(anchor="w")
        self.tipo_selecionado = tk.StringVar(value="ponto")
        tk.OptionMenu(
            painel, self.tipo_selecionado, "ponto", "reta", "wireframe"
        ).pack(anchor="w")

        tk.Label(painel, text="Coordenadas (ex: (10,10),(50,50)):").pack(
            anchor="w"
        )
        self.entrada_coordenadas = tk.Entry(painel, width=30)
        self.entrada_coordenadas.pack()

        tk.Button(
            painel, text="Adicionar objeto", command=self._adicionar_objeto
        ).pack(pady=5)

        # --- Controles de navegação (panning) ---
        tk.Label(painel, text="Navegação (Pan)").pack(anchor="w", pady=(15, 0))
        frame_pan = tk.Frame(painel)
        frame_pan.pack()
        passo_pan = 10
        tk.Button(
            frame_pan, text="▲", width=3,
            command=lambda: self._pan(0, passo_pan)
        ).grid(row=0, column=1)
        tk.Button(
            frame_pan, text="◀", width=3,
            command=lambda: self._pan(-passo_pan, 0)
        ).grid(row=1, column=0)
        tk.Button(
            frame_pan, text="▶", width=3,
            command=lambda: self._pan(passo_pan, 0)
        ).grid(row=1, column=2)
        tk.Button(
            frame_pan, text="▼", width=3,
            command=lambda: self._pan(0, -passo_pan)
        ).grid(row=2, column=1)

        # --- Controles de zoom ---
        tk.Label(painel, text="Zoom").pack(anchor="w", pady=(15, 0))
        frame_zoom = tk.Frame(painel)
        frame_zoom.pack()
        tk.Button(
            frame_zoom, text="Zoom +", command=lambda: self._zoom(0.9)
        ).grid(row=0, column=0, padx=2)
        tk.Button(
            frame_zoom, text="Zoom -", command=lambda: self._zoom(1.1)
        ).grid(row=0, column=1, padx=2)

    # ---------------------------------------------------------
    # Ações do usuário
    # ---------------------------------------------------------
    def _adicionar_objeto(self):
        nome = self.entrada_nome.get().strip()
        tipo = self.tipo_selecionado.get()
        texto_coordenadas = self.entrada_coordenadas.get().strip()

        if not nome:
            messagebox.showerror("Erro", "Informe um nome para o objeto.")
            return

        try:
            coordenadas = self._parsear_coordenadas(texto_coordenadas)
        except (ValueError, SyntaxError):
            messagebox.showerror(
                "Erro",
                "Coordenadas inválidas.\nUse o formato: (x1,y1),(x2,y2),...",
            )
            return

        if tipo == "ponto" and len(coordenadas) != 1:
            messagebox.showerror("Erro", "Um ponto precisa de exatamente 1 coordenada.")
            return
        if tipo == "reta" and len(coordenadas) != 2:
            messagebox.showerror("Erro", "Uma reta precisa de exatamente 2 coordenadas.")
            return
        if tipo == "wireframe" and len(coordenadas) < 3:
            messagebox.showerror("Erro", "Um wireframe precisa de pelo menos 3 coordenadas.")
            return

        self.display_file.adicionar(nome, tipo, coordenadas)
        self.entrada_nome.delete(0, tk.END)
        self.entrada_coordenadas.delete(0, tk.END)
        self._redesenhar()

    @staticmethod
    def _parsear_coordenadas(texto):
        """
        Converte um texto como "(10,10),(50,50)" em
        [(10.0, 10.0), (50.0, 50.0)].

        Usamos ast.literal_eval em vez de eval() puro: o resultado é o
        mesmo (uma tupla de tuplas), mas literal_eval só aceita dados
        literais (números, tuplas, listas...), nunca código arbitrário,
        o que é mais seguro para ler entrada do usuário.
        """
        tupla_de_pontos = ast.literal_eval(texto)

        # Caso especial: se o usuário digitou só UM ponto, ex: "(0,0)",
        # o literal_eval devolve (0, 0) -- uma tupla de dois números --
        # em vez de ((0, 0),) -- uma tupla contendo um ponto. Detectamos
        # esse caso e "envelopamos" o ponto numa tupla externa.
        if isinstance(tupla_de_pontos[0], (int, float)):
            tupla_de_pontos = (tupla_de_pontos,)

        pontos = [(float(x), float(y)) for x, y in tupla_de_pontos]
        return pontos

    def _pan(self, dx, dy):
        self.window.mover(dx, dy)
        self._redesenhar()

    def _zoom(self, fator):
        self.window.aplicar_zoom(fator)
        self._redesenhar()

    # ---------------------------------------------------------
    # Desenho
    # ---------------------------------------------------------
    def _redesenhar(self):
        self.canvas.delete("all")
        self.lista_objetos.delete(0, tk.END)

        for objeto in self.display_file.objetos:
            self.lista_objetos.insert(tk.END, repr(objeto))
            pontos_tela = [
                self.viewport.transformar(p, self.window)
                for p in objeto.coordenadas
            ]

            if objeto.tipo == "ponto":
                self._desenhar_ponto(pontos_tela[0])
            elif objeto.tipo == "reta":
                self._desenhar_linha(pontos_tela[0], pontos_tela[1])
            elif objeto.tipo == "wireframe":
                self._desenhar_wireframe(pontos_tela)

    def _desenhar_ponto(self, ponto, tamanho=3):
        """Um ponto é desenhado como uma pequena cruz (duas linhas)."""
        x, y = ponto
        self.canvas.create_line(x - tamanho, y, x + tamanho, y, fill="blue")
        self.canvas.create_line(x, y - tamanho, x, y + tamanho, fill="blue")

    def _desenhar_linha(self, p1, p2):
        self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="black")

    def _desenhar_wireframe(self, pontos):
        """Um wireframe é uma sequência de retas ligando os vértices,
        incluindo a reta que fecha o polígono (do último ao primeiro)."""
        n = len(pontos)
        for i in range(n):
            p1 = pontos[i]
            p2 = pontos[(i + 1) % n]  # (i+1) % n fecha o polígono no final
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="red")


# =============================================================
# PONTO DE ENTRADA
# =============================================================
if __name__ == "__main__":
    raiz = tk.Tk()
    app = Aplicacao(raiz)
    raiz.mainloop()
