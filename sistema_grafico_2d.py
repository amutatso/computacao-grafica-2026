import ast
import math
import tkinter as tk
from tkinter import colorchooser, messagebox


# DISPLAY FILE
# O Display File é a lista de todos os objetos gráficos que
# existem no mundo. Cada objeto tem nome, tipo (ponto, reta ou
# wireframe), coordenadas e a cor usada para desenhar as linhas.


class Objeto2D:
    def __init__(self, nome, tipo, coordenadas, cor="#000000"):
        self.nome = nome
        self.tipo = tipo                  # "ponto" | "reta" | "wireframe"
        self.coordenadas = coordenadas    # [(x1, y1), (x2, y2), ...]
        self.cor = cor                    # cor das linhas, em hexadecimal

    def __repr__(self):
        return f"{self.nome} [{self.tipo}]"


class DisplayFile:
    """Guarda a lista de todos os objetos do mundo."""

    def __init__(self):
        self.objetos = []

    def adicionar(self, nome, tipo, coordenadas, cor="#000000"):
        objeto = Objeto2D(nome, tipo, coordenadas, cor)
        self.objetos.append(objeto)
        return objeto

    def remover_por_indice(self, indice):
        del self.objetos[indice]


# WINDOW
# A Window define qual pedaço do mundo está sendo visualizado no
# momento, em coordenadas do mundo.

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


# VIEWPORT
# Converte um ponto em coordenadas do mundo (dentro da window)
# para coordenadas de tela (pixels dentro do canvas).
#
# Para não distorcer os objetos, usamos a mesma escala nos eixos
# X e Y (a menor das duas escalas possíveis).

class Viewport:
    def __init__(self, largura_tela, altura_tela, margem=20):
        self.largura_tela = largura_tela
        self.altura_tela = altura_tela
        self.margem = margem  # espaço (em pixels) que deixamos livre nas bordas

    def transformar(self, ponto_mundo, window: Window):
        x_mundo, y_mundo = ponto_mundo

        area_util_x = self.largura_tela - 2 * self.margem
        area_util_y = self.altura_tela - 2 * self.margem

        escala_x = area_util_x / window.largura
        escala_y = area_util_y / window.altura
        escala = min(escala_x, escala_y)

        largura_usada = window.largura * escala
        altura_usada = window.altura * escala
        offset_x = self.margem + (area_util_x - largura_usada) / 2
        offset_y = self.margem + (area_util_y - altura_usada) / 2

        x_tela = offset_x + (x_mundo - window.xmin) * escala
        y_tela = offset_y + (window.ymax - y_mundo) * escala

        return x_tela, y_tela


# TRANSFORMAÇÕES 2D EM COORDENADAS HOMOGÊNEAS
#
# Cada matriz é uma tupla de 3 tuplas (3x3). Um ponto (x, y) é
# tratado como o vetor homogêneo (x, y, 1).
#
# Existe UMA rotina genérica (aplicar_transformacao) que recebe
# qualquer matriz pronta e aplica no objeto. As demais funções
# abaixo dela são "rotinas de preparo": cada uma monta a matriz
# certa para um tipo de transformação específico.

def matriz_identidade():
    return ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def multiplicar_matrizes(a, b):
    """Multiplica duas matrizes 3x3 (a x b)."""
    resultado = [[0, 0, 0] for _ in range(3)]
    for i in range(3):
        for j in range(3):
            resultado[i][j] = sum(a[i][k] * b[k][j] for k in range(3))
    return tuple(tuple(linha) for linha in resultado)


def aplicar_matriz_no_ponto(matriz, ponto):
    x, y = ponto
    x2 = matriz[0][0] * x + matriz[0][1] * y + matriz[0][2]
    y2 = matriz[1][0] * x + matriz[1][1] * y + matriz[1][2]
    return (x2, y2)


def aplicar_transformacao(objeto, matriz):
    """Rotina genérica: aplica a matriz homogênea em cada ponto do objeto."""
    objeto.coordenadas = [
        aplicar_matriz_no_ponto(matriz, ponto) for ponto in objeto.coordenadas
    ]


def centro_geometrico(coordenadas):
    """Centroide simples: média das coordenadas dos vértices do objeto."""
    n = len(coordenadas)
    cx = sum(p[0] for p in coordenadas) / n
    cy = sum(p[1] for p in coordenadas) / n
    return cx, cy


# --- rotinas de preparo ---

def matriz_translacao(dx, dy):
    return ((1, 0, dx), (0, 1, dy), (0, 0, 1))


def matriz_escala_natural(coordenadas, sx, sy):
    """Escala em torno do centro do próprio objeto: leva o centro pra
    origem, escala, e devolve o centro pro lugar."""
    cx, cy = centro_geometrico(coordenadas)
    para_origem = matriz_translacao(-cx, -cy)
    escala = ((sx, 0, 0), (0, sy, 0), (0, 0, 1))
    de_volta = matriz_translacao(cx, cy)
    return multiplicar_matrizes(de_volta, multiplicar_matrizes(escala, para_origem))


def matriz_rotacao(graus):
    rad = math.radians(graus)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    return ((cos_a, -sin_a, 0), (sin_a, cos_a, 0), (0, 0, 1))


def matriz_rotacao_centro_mundo(graus):
    """Centro do mundo = origem (0, 0), então é a rotação "pura"."""
    return matriz_rotacao(graus)


def matriz_rotacao_centro_objeto(coordenadas, graus):
    cx, cy = centro_geometrico(coordenadas)
    return multiplicar_matrizes(
        matriz_translacao(cx, cy),
        multiplicar_matrizes(matriz_rotacao(graus), matriz_translacao(-cx, -cy)),
    )


def matriz_rotacao_ponto_arbitrario(px, py, graus):
    return multiplicar_matrizes(
        matriz_translacao(px, py),
        multiplicar_matrizes(matriz_rotacao(graus), matriz_translacao(-px, -py)),
    )


# JANELA DE TRANSFORMAÇÕES
#
# Deixa o usuário empilhar várias transformações sobre um objeto.
# Cada "Adicionar" só prepara e guarda a matriz; nada é aplicado
# no objeto de verdade até o usuário clicar em "Aplicar tudo".

class JanelaTransformacao(tk.Toplevel):
    def __init__(self, raiz, objeto, ao_aplicar):
        super().__init__(raiz)
        self.title(f"Transformações - {objeto.nome}")
        self.objeto = objeto
        self.ao_aplicar = ao_aplicar

        # transformações já preparadas: lista de (descricao, matriz)
        self.pendentes = []
        # cópia "de trabalho" das coordenadas, só pra pré-visualizar
        # onde fica o centro do objeto após as transformações já
        # empilhadas (não mexe no objeto real)
        self.coordenadas_preview = list(objeto.coordenadas)

        self._montar_interface()

    def _montar_interface(self):
        tk.Label(self, text="Transformações a aplicar:").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 0)
        )
        self.lista_pendentes = tk.Listbox(self, width=45, height=6)
        self.lista_pendentes.grid(row=1, column=0, columnspan=2, padx=10)

        self.tipo = tk.StringVar(value="translacao")
        frame_tipo = tk.Frame(self)
        frame_tipo.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        for texto, valor in [
            ("Translação", "translacao"),
            ("Escala", "escala"),
            ("Rotação", "rotacao"),
        ]:
            tk.Radiobutton(
                frame_tipo, text=texto, variable=self.tipo, value=valor,
                command=self._atualizar_campos_visiveis,
            ).pack(side="left")

        # --- campos de translação ---
        self.frame_translacao = tk.Frame(self)
        tk.Label(self.frame_translacao, text="dx:").grid(row=0, column=0)
        self.entrada_dx = tk.Entry(self.frame_translacao, width=8)
        self.entrada_dx.grid(row=0, column=1)
        tk.Label(self.frame_translacao, text="dy:").grid(row=0, column=2)
        self.entrada_dy = tk.Entry(self.frame_translacao, width=8)
        self.entrada_dy.grid(row=0, column=3)

        # --- campos de escala ---
        self.frame_escala = tk.Frame(self)
        tk.Label(self.frame_escala, text="Escala natural, em torno do centro do objeto").grid(
            row=0, column=0, columnspan=4
        )
        tk.Label(self.frame_escala, text="sx:").grid(row=1, column=0)
        self.entrada_sx = tk.Entry(self.frame_escala, width=8)
        self.entrada_sx.grid(row=1, column=1)
        tk.Label(self.frame_escala, text="sy:").grid(row=1, column=2)
        self.entrada_sy = tk.Entry(self.frame_escala, width=8)
        self.entrada_sy.grid(row=1, column=3)

        # --- campos de rotação ---
        self.frame_rotacao = tk.Frame(self)
        tk.Label(self.frame_rotacao, text="ângulo (graus):").grid(row=0, column=0)
        self.entrada_angulo = tk.Entry(self.frame_rotacao, width=8)
        self.entrada_angulo.grid(row=0, column=1)

        self.modo_rotacao = tk.StringVar(value="mundo")
        tk.Radiobutton(
            self.frame_rotacao, text="Centro do mundo", variable=self.modo_rotacao,
            value="mundo", command=self._atualizar_campos_visiveis,
        ).grid(row=1, column=0, columnspan=2, sticky="w")
        tk.Radiobutton(
            self.frame_rotacao, text="Centro do objeto", variable=self.modo_rotacao,
            value="objeto", command=self._atualizar_campos_visiveis,
        ).grid(row=2, column=0, columnspan=2, sticky="w")
        tk.Radiobutton(
            self.frame_rotacao, text="Ponto arbitrário", variable=self.modo_rotacao,
            value="arbitrario", command=self._atualizar_campos_visiveis,
        ).grid(row=3, column=0, columnspan=2, sticky="w")

        self.frame_ponto_arbitrario = tk.Frame(self.frame_rotacao)
        tk.Label(self.frame_ponto_arbitrario, text="px:").grid(row=0, column=0)
        self.entrada_px = tk.Entry(self.frame_ponto_arbitrario, width=6)
        self.entrada_px.grid(row=0, column=1)
        tk.Label(self.frame_ponto_arbitrario, text="py:").grid(row=0, column=2)
        self.entrada_py = tk.Entry(self.frame_ponto_arbitrario, width=6)
        self.entrada_py.grid(row=0, column=3)
        self.frame_ponto_arbitrario.grid(row=4, column=0, columnspan=2)

        self._atualizar_campos_visiveis()

        frame_botoes = tk.Frame(self)
        frame_botoes.grid(row=6, column=0, columnspan=2, pady=15)
        tk.Button(frame_botoes, text="Adicionar", command=self._adicionar_pendente).pack(side="left", padx=5)
        tk.Button(frame_botoes, text="Aplicar tudo", command=self._aplicar_tudo).pack(side="left", padx=5)
        tk.Button(frame_botoes, text="Cancelar", command=self.destroy).pack(side="left", padx=5)

    def _atualizar_campos_visiveis(self):
        self.frame_translacao.grid_forget()
        self.frame_escala.grid_forget()
        self.frame_rotacao.grid_forget()

        if self.tipo.get() == "translacao":
            self.frame_translacao.grid(row=3, column=0, columnspan=2, pady=5)
        elif self.tipo.get() == "escala":
            self.frame_escala.grid(row=3, column=0, columnspan=2, pady=5)
        elif self.tipo.get() == "rotacao":
            self.frame_rotacao.grid(row=3, column=0, columnspan=2, pady=5)

        if self.modo_rotacao.get() == "arbitrario":
            self.frame_ponto_arbitrario.grid(row=4, column=0, columnspan=2)
        else:
            self.frame_ponto_arbitrario.grid_forget()

    def _adicionar_pendente(self):
        try:
            tipo = self.tipo.get()

            if tipo == "translacao":
                dx = float(self.entrada_dx.get())
                dy = float(self.entrada_dy.get())
                matriz = matriz_translacao(dx, dy)
                descricao = f"Translação (dx={dx}, dy={dy})"

            elif tipo == "escala":
                sx = float(self.entrada_sx.get())
                sy = float(self.entrada_sy.get())
                matriz = matriz_escala_natural(self.coordenadas_preview, sx, sy)
                descricao = f"Escala natural (sx={sx}, sy={sy})"

            else:  # rotacao
                angulo = float(self.entrada_angulo.get())
                modo = self.modo_rotacao.get()
                if modo == "mundo":
                    matriz = matriz_rotacao_centro_mundo(angulo)
                    descricao = f"Rotação {angulo}° em torno do centro do mundo"
                elif modo == "objeto":
                    matriz = matriz_rotacao_centro_objeto(self.coordenadas_preview, angulo)
                    descricao = f"Rotação {angulo}° em torno do centro do objeto"
                else:
                    px = float(self.entrada_px.get())
                    py = float(self.entrada_py.get())
                    matriz = matriz_rotacao_ponto_arbitrario(px, py, angulo)
                    descricao = f"Rotação {angulo}° em torno de ({px}, {py})"

        except ValueError:
            messagebox.showerror("Erro", "Preencha os campos numéricos corretamente.")
            return

        self.pendentes.append((descricao, matriz))
        self.lista_pendentes.insert(tk.END, descricao)

        # atualiza a pré-visualização, usada como base para o próximo
        # cálculo de centro do objeto (caso o usuário empilhe mais
        # transformações antes de aplicar)
        self.coordenadas_preview = [
            aplicar_matriz_no_ponto(matriz, p) for p in self.coordenadas_preview
        ]

    def _aplicar_tudo(self):
        if not self.pendentes:
            self.destroy()
            return

        matriz_final = matriz_identidade()
        for _, matriz in self.pendentes:
            matriz_final = multiplicar_matrizes(matriz, matriz_final)

        aplicar_transformacao(self.objeto, matriz_final)
        self.ao_aplicar()
        self.destroy()


# APLICAÇÃO (Tkinter)

class Aplicacao:
    LARGURA_CANVAS = 640
    ALTURA_CANVAS = 640

    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title("Sistema Gráfico Interativo 2D")

        self.display_file = DisplayFile()
        self.window = Window(xmin=-100, ymin=-100, xmax=100, ymax=100)
        self.viewport = Viewport(self.LARGURA_CANVAS, self.ALTURA_CANVAS)
        self.cor_selecionada = "#000000"

        self._montar_interface()
        self._redesenhar()

    # Montagem da interface (canvas + painel lateral)
    def _montar_interface(self):
        self.canvas = tk.Canvas(
            self.raiz,
            width=self.LARGURA_CANVAS,
            height=self.ALTURA_CANVAS,
            bg="white",
        )
        self.canvas.grid(row=0, column=0, rowspan=20, padx=10, pady=10)

        painel = tk.Frame(self.raiz)
        painel.grid(row=0, column=1, sticky="n", padx=10, pady=10)

        # Lista de objetos existentes
        tk.Label(painel, text="Objetos").pack(anchor="w")
        self.lista_objetos = tk.Listbox(painel, width=30, height=8)
        self.lista_objetos.pack()

        tk.Button(
            painel, text="Transformar objeto selecionado",
            command=self._abrir_janela_transformacao,
        ).pack(pady=(5, 0))

        # Formulário de novo objeto
        tk.Label(painel, text="Novo objeto").pack(anchor="w", pady=(15, 0))

        tk.Label(painel, text="Nome:").pack(anchor="w")
        self.entrada_nome = tk.Entry(painel, width=30)
        self.entrada_nome.pack()

        tk.Label(painel, text="Tipo:").pack(anchor="w")
        self.tipo_selecionado = tk.StringVar(value="ponto")
        tk.OptionMenu(
            painel, self.tipo_selecionado, "ponto", "reta", "wireframe"
        ).pack(anchor="w")

        tk.Label(painel, text="Coordenadas (ex: (10,10),(50,50)):").pack(anchor="w")
        self.entrada_coordenadas = tk.Entry(painel, width=30)
        self.entrada_coordenadas.pack()

        frame_cor = tk.Frame(painel)
        frame_cor.pack(anchor="w", pady=(5, 0))
        tk.Button(frame_cor, text="Escolher cor", command=self._escolher_cor).pack(side="left")
        self.amostra_cor = tk.Label(frame_cor, text="   ", bg=self.cor_selecionada, relief="sunken")
        self.amostra_cor.pack(side="left", padx=5)

        tk.Button(
            painel, text="Adicionar objeto", command=self._adicionar_objeto
        ).pack(pady=5)

        # Navegação (panning)
        tk.Label(painel, text="Navegação (Pan)").pack(anchor="w", pady=(15, 0))
        frame_pan = tk.Frame(painel)
        frame_pan.pack()
        passo_pan = 10
        tk.Button(frame_pan, text="▲", width=3, command=lambda: self._pan(0, passo_pan)).grid(row=0, column=1)
        tk.Button(frame_pan, text="◀", width=3, command=lambda: self._pan(-passo_pan, 0)).grid(row=1, column=0)
        tk.Button(frame_pan, text="▶", width=3, command=lambda: self._pan(passo_pan, 0)).grid(row=1, column=2)
        tk.Button(frame_pan, text="▼", width=3, command=lambda: self._pan(0, -passo_pan)).grid(row=2, column=1)

        # Zoom
        tk.Label(painel, text="Zoom").pack(anchor="w", pady=(15, 0))
        frame_zoom = tk.Frame(painel)
        frame_zoom.pack()
        tk.Button(frame_zoom, text="Zoom +", command=lambda: self._zoom(0.9)).grid(row=0, column=0, padx=2)
        tk.Button(frame_zoom, text="Zoom -", command=lambda: self._zoom(1.1)).grid(row=0, column=1, padx=2)

    # Ações do usuário
    def _escolher_cor(self):
        cor = colorchooser.askcolor(color=self.cor_selecionada, title="Escolha a cor do objeto")
        if cor[1]:  # cor[1] é o código hexadecimal; None se o usuário cancelar
            self.cor_selecionada = cor[1]
            self.amostra_cor.config(bg=self.cor_selecionada)

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

        self.display_file.adicionar(nome, tipo, coordenadas, self.cor_selecionada)
        self.entrada_nome.delete(0, tk.END)
        self.entrada_coordenadas.delete(0, tk.END)
        self._redesenhar()

    @staticmethod
    def _parsear_coordenadas(texto):
        """
        Converte um texto como "(10,10),(50,50)" em
        [(10.0, 10.0), (50.0, 50.0)]. Usamos ast.literal_eval em vez de
        eval() puro: mesmo resultado, mas sem risco de executar código
        arbitrário vindo do campo de texto.
        """
        tupla_de_pontos = ast.literal_eval(texto)

        # Se o usuário digitou só um ponto, ex: "(0,0)", o literal_eval
        # devolve (0, 0) em vez de ((0, 0),) -- corrigimos aqui.
        if isinstance(tupla_de_pontos[0], (int, float)):
            tupla_de_pontos = (tupla_de_pontos,)

        return [(float(x), float(y)) for x, y in tupla_de_pontos]

    def _abrir_janela_transformacao(self):
        selecionado = self.lista_objetos.curselection()
        if not selecionado:
            messagebox.showerror("Erro", "Selecione um objeto na lista primeiro.")
            return
        objeto = self.display_file.objetos[selecionado[0]]
        JanelaTransformacao(self.raiz, objeto, ao_aplicar=self._redesenhar)

    def _pan(self, dx, dy):
        self.window.mover(dx, dy)
        self._redesenhar()

    def _zoom(self, fator):
        self.window.aplicar_zoom(fator)
        self._redesenhar()

    # Desenho
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
                self._desenhar_ponto(pontos_tela[0], objeto.cor)
            elif objeto.tipo == "reta":
                self._desenhar_linha(pontos_tela[0], pontos_tela[1], objeto.cor)
            elif objeto.tipo == "wireframe":
                self._desenhar_wireframe(pontos_tela, objeto.cor)

    def _desenhar_ponto(self, ponto, cor, tamanho=3):
        """Um ponto é desenhado como uma pequena cruz (duas linhas)."""
        x, y = ponto
        self.canvas.create_line(x - tamanho, y, x + tamanho, y, fill=cor)
        self.canvas.create_line(x, y - tamanho, x, y + tamanho, fill=cor)

    def _desenhar_linha(self, p1, p2, cor):
        self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=cor)

    def _desenhar_wireframe(self, pontos, cor):
        """Sequência de retas ligando os vértices, incluindo a reta que
        fecha o polígono (do último ao primeiro) -- só a borda é
        desenhada, sem preenchimento."""
        n = len(pontos)
        for i in range(n):
            p1 = pontos[i]
            p2 = pontos[(i + 1) % n]
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=cor)


if __name__ == "__main__":
    raiz = tk.Tk()
    app = Aplicacao(raiz)
    raiz.mainloop()
