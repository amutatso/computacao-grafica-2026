import ast
import math
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox


# DISPLAY FILE
# O Display File é a lista de todos os objetos gráficos que
# existem no mundo. Cada objeto tem nome, tipo (ponto, reta ou
# wireframe), coordenadas (em coordenadas do MUNDO, sempre), a cor
# das linhas e, para wireframes, se deve ser desenhado preenchido.


class Objeto2D:
    def __init__(self, nome, tipo, coordenadas, cor="#000000", preenchido=False):
        self.nome = nome
        self.tipo = tipo                  # "ponto" | "reta" | "wireframe"
        self.coordenadas = coordenadas    # [(x1, y1), (x2, y2), ...]
        self.cor = cor                    # cor das linhas, em hexadecimal
        self.preenchido = preenchido      # só relevante para wireframe

    def __repr__(self):
        sufixo = " (preenchido)" if self.preenchido else ""
        return f"{self.nome} [{self.tipo}]{sufixo}"


class DisplayFile:
    """Guarda a lista de todos os objetos do mundo."""

    def __init__(self):
        self.objetos = []

    def adicionar(self, nome, tipo, coordenadas, cor="#000000", preenchido=False):
        objeto = Objeto2D(nome, tipo, coordenadas, cor, preenchido)
        self.objetos.append(objeto)
        return objeto

    def remover_por_indice(self, indice):
        del self.objetos[indice]

    def limpar(self):
        self.objetos = []


# WINDOW
#
# A Window é descrita pelo seu centro, sua largura/altura e um
# ângulo de rotação em relação ao mundo.

class Window:
    def __init__(self, centro_x, centro_y, largura, altura, angulo=0.0):
        self.centro_x = centro_x
        self.centro_y = centro_y
        self.largura = largura
        self.altura = altura
        self.angulo = angulo  # graus, rotação da window em relação ao mundo

    @property
    def centro(self):
        return self.centro_x, self.centro_y

    def mover(self, dx_local, dy_local):
        """Panning: dx_local/dy_local são deslocamentos no referencial
        da PRÓPRIA window (o "pra cima" de quem está navegando)."""
        rad = math.radians(self.angulo)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        self.centro_x += dx_local * cos_a - dy_local * sin_a
        self.centro_y += dx_local * sin_a + dy_local * cos_a

    def aplicar_zoom(self, fator):
        self.largura *= fator
        self.altura *= fator

    def rotacionar(self, delta_graus):
        self.angulo += delta_graus

    def mundo_para_local(self, ponto_mundo):
        """
        Converte um ponto do MUNDO para o sistema de coordenadas da
        PRÓPRIA window: centralizado nela e alinhado com sua rotação.
        Depois desta conversão, a window sempre vira um retângulo
        alinhado aos eixos (de -largura/2 a largura/2, de -altura/2 a
        altura/2), independente de estar rotacionada no mundo ou não
        -- e é exatamente por isso que fazemos o clipping aqui: os
        algoritmos clássicos de clipping assumem uma janela retangular
        alinhada aos eixos.
        """
        x, y = ponto_mundo
        dx = x - self.centro_x
        dy = y - self.centro_y

        rad = -math.radians(self.angulo)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        lx = dx * cos_a - dy * sin_a
        ly = dx * sin_a + dy * cos_a
        return lx, ly

    def limites_locais(self):
        """(xmin, xmax, ymin, ymax) do retângulo da window no seu
        próprio referencial local -- sempre centrado em (0,0)."""
        meia_largura = self.largura / 2
        meia_altura = self.altura / 2
        return -meia_largura, meia_largura, -meia_altura, meia_altura


# VIEWPORT
#
# Mapeia um ponto já em coordenadas LOCAIS da window (centralizado,
# alinhado) para pixels de tela. Não faz mais o passo mundo->local
# sozinho -- isso é feito separadamente ANTES do clipping, e o
# clipping acontece justamente entre esses dois passos.

class Viewport:
    def __init__(self, largura_tela, altura_tela, margem=20):
        self.largura_tela = largura_tela
        self.altura_tela = altura_tela
        self.margem = margem

    def local_para_tela(self, ponto_local, window: Window):
        local_x, local_y = ponto_local

        area_util_x = self.largura_tela - 2 * self.margem
        area_util_y = self.altura_tela - 2 * self.margem

        escala = min(area_util_x / window.largura, area_util_y / window.altura)

        centro_tela_x = self.margem + area_util_x / 2
        centro_tela_y = self.margem + area_util_y / 2

        x_tela = centro_tela_x + local_x * escala
        y_tela = centro_tela_y - local_y * escala  # eixo Y da tela cresce pra baixo

        return x_tela, y_tela

    def transformar(self, ponto_mundo, window: Window):
        """Atalho mundo -> tela direto, sem clipping. Usado só onde
        clipping não se aplica (ex: nada, hoje -- fica aqui de bônus)."""
        return self.local_para_tela(window.mundo_para_local(ponto_mundo), window)


# CLIPPING
#
# Todas as funções abaixo trabalham em coordenadas LOCAIS da window
# (já alinhadas aos eixos), recebendo os limites (xmin, xmax, ymin,
# ymax) do retângulo de clipping.

def ponto_dentro_da_window(ponto, xmin, xmax, ymin, ymax):
    x, y = ponto
    return xmin <= x <= xmax and ymin <= y <= ymax


# --- Cohen-Sutherland ---
# Cada ponto recebe um "código de região" de 4 bits, indicando de
# quais lados do retângulo ele está fora (esquerda/direita/baixo/
# cima). Se os dois códigos forem 0, a reta está inteira dentro; se
# o "and" bit a bit dos dois códigos não for 0, os dois pontos estão
# fora do MESMO lado, então a reta inteira pode ser rejeitada. Caso
# contrário, recorta contra a borda indicada e repete.

ESQUERDA, DIREITA, ABAIXO, ACIMA = 1, 2, 4, 8


def _codigo_regiao(ponto, xmin, xmax, ymin, ymax):
    x, y = ponto
    codigo = 0
    if x < xmin:
        codigo |= ESQUERDA
    elif x > xmax:
        codigo |= DIREITA
    if y < ymin:
        codigo |= ABAIXO
    elif y > ymax:
        codigo |= ACIMA
    return codigo


def clipar_reta_cohen_sutherland(p1, p2, xmin, xmax, ymin, ymax):
    x1, y1 = p1
    x2, y2 = p2
    codigo1 = _codigo_regiao((x1, y1), xmin, xmax, ymin, ymax)
    codigo2 = _codigo_regiao((x2, y2), xmin, xmax, ymin, ymax)

    while True:
        if codigo1 == 0 and codigo2 == 0:
            return (x1, y1), (x2, y2)  # os dois pontos estão dentro
        if codigo1 & codigo2 != 0:
            return None  # os dois estão fora do mesmo lado -> descarta

        codigo_fora = codigo1 if codigo1 != 0 else codigo2

        if codigo_fora & ACIMA:
            x = x1 + (x2 - x1) * (ymax - y1) / (y2 - y1)
            y = ymax
        elif codigo_fora & ABAIXO:
            x = x1 + (x2 - x1) * (ymin - y1) / (y2 - y1)
            y = ymin
        elif codigo_fora & DIREITA:
            y = y1 + (y2 - y1) * (xmax - x1) / (x2 - x1)
            x = xmax
        else:  # ESQUERDA
            y = y1 + (y2 - y1) * (xmin - x1) / (x2 - x1)
            x = xmin

        if codigo_fora == codigo1:
            x1, y1 = x, y
            codigo1 = _codigo_regiao((x1, y1), xmin, xmax, ymin, ymax)
        else:
            x2, y2 = x, y
            codigo2 = _codigo_regiao((x2, y2), xmin, xmax, ymin, ymax)


# --- Liang-Barsky ---
# Trata a reta em forma paramétrica P(t) = P1 + t*(P2-P1), t em
# [0,1], e vai estreitando o intervalo [t0,t1] contra cada uma das
# 4 bordas do retângulo. Se o intervalo fechar (t0 > t1), a reta
# está inteiramente fora.

def clipar_reta_liang_barsky(p1, p2, xmin, xmax, ymin, ymax):
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1

    t0, t1 = 0.0, 1.0
    # cada item é (p, q): a borda impõe p*t <= q
    bordas = ((-dx, x1 - xmin), (dx, xmax - x1), (-dy, y1 - ymin), (dy, ymax - y1))

    for p, q in bordas:
        if p == 0:
            if q < 0:
                return None  # reta paralela a essa borda e do lado de fora
            continue

        r = q / p
        if p < 0:
            if r > t1:
                return None
            t0 = max(t0, r)
        else:
            if r < t0:
                return None
            t1 = min(t1, r)

    if t0 > t1:
        return None

    novo_p1 = (x1 + t0 * dx, y1 + t0 * dy)
    novo_p2 = (x1 + t1 * dx, y1 + t1 * dy)
    return novo_p1, novo_p2


# --- Sutherland-Hodgman (clipping de polígono) ---
# Recorta o polígono contra uma borda do retângulo por vez (esquerda,
# direita, baixo, cima), indo de todas as 4. Em cada passagem, para
# cada aresta do polígono atual, decide se mantém o ponto, adiciona
# uma intersecção com a borda, ou descarta -- e o resultado de uma
# borda alimenta a próxima.

def _intersecao_com_borda(p1, p2, borda, xmin, xmax, ymin, ymax):
    x1, y1 = p1
    x2, y2 = p2
    if borda == "esquerda":
        x = xmin
        y = y1 + (y2 - y1) * (xmin - x1) / (x2 - x1)
    elif borda == "direita":
        x = xmax
        y = y1 + (y2 - y1) * (xmax - x1) / (x2 - x1)
    elif borda == "baixo":
        y = ymin
        x = x1 + (x2 - x1) * (ymin - y1) / (y2 - y1)
    else:  # "cima"
        y = ymax
        x = x1 + (x2 - x1) * (ymax - y1) / (y2 - y1)
    return (x, y)


def _dentro_da_borda(ponto, borda, xmin, xmax, ymin, ymax):
    x, y = ponto
    if borda == "esquerda":
        return x >= xmin
    if borda == "direita":
        return x <= xmax
    if borda == "baixo":
        return y >= ymin
    return y <= ymax  # "cima"


def _recortar_por_uma_borda(pontos, borda, xmin, xmax, ymin, ymax):
    if not pontos:
        return []

    saida = []
    n = len(pontos)
    for i in range(n):
        atual = pontos[i]
        anterior = pontos[i - 1]
        atual_dentro = _dentro_da_borda(atual, borda, xmin, xmax, ymin, ymax)
        anterior_dentro = _dentro_da_borda(anterior, borda, xmin, xmax, ymin, ymax)

        if atual_dentro:
            if not anterior_dentro:
                saida.append(_intersecao_com_borda(anterior, atual, borda, xmin, xmax, ymin, ymax))
            saida.append(atual)
        elif anterior_dentro:
            saida.append(_intersecao_com_borda(anterior, atual, borda, xmin, xmax, ymin, ymax))

    return saida


def clipar_poligono_sutherland_hodgman(pontos, xmin, xmax, ymin, ymax):
    resultado = pontos
    for borda in ("esquerda", "direita", "baixo", "cima"):
        resultado = _recortar_por_uma_borda(resultado, borda, xmin, xmax, ymin, ymax)
    return resultado


# TRANSFORMAÇÕES 2D EM COORDENADAS HOMOGÊNEAS (herdadas das entregas anteriores)
#
# Continuam operando inteiramente em coordenadas do MUNDO -- não são
# afetadas por rotação da window nem por clipping.

def matriz_identidade():
    return ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def multiplicar_matrizes(a, b):
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
    objeto.coordenadas = [
        aplicar_matriz_no_ponto(matriz, ponto) for ponto in objeto.coordenadas
    ]


def centro_geometrico(coordenadas):
    n = len(coordenadas)
    cx = sum(p[0] for p in coordenadas) / n
    cy = sum(p[1] for p in coordenadas) / n
    return cx, cy


def matriz_translacao(dx, dy):
    return ((1, 0, dx), (0, 1, dy), (0, 0, 1))


def matriz_escala_natural(coordenadas, sx, sy):
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


# LEITURA E ESCRITA DE ARQUIVOS .OBJ (herdadas da entrega anterior)

class DescritorOBJ:
    def descrever(self, objeto, indice_inicial):
        linhas = [
            f"o {objeto.nome}",
            f"# tipo {objeto.tipo}",
            f"# cor {objeto.cor}",
            f"# preenchido {objeto.preenchido}",
        ]
        for x, y in objeto.coordenadas:
            linhas.append(f"v {x} {y} 0.0")

        indices = list(range(indice_inicial, indice_inicial + len(objeto.coordenadas)))

        if objeto.tipo == "ponto":
            linhas.append(f"p {indices[0]}")
        elif objeto.tipo == "reta":
            linhas.append(f"l {indices[0]} {indices[1]}")
        elif objeto.tipo == "wireframe":
            sequencia = " ".join(str(i) for i in indices + [indices[0]])
            linhas.append(f"l {sequencia}")

        return linhas, len(objeto.coordenadas)


def salvar_mundo_obj(display_file, caminho):
    descritor = DescritorOBJ()
    linhas = ["# Mundo gerado pelo Sistema Gráfico Interativo"]
    proximo_indice = 1

    for objeto in display_file.objetos:
        linhas_objeto, usados = descritor.descrever(objeto, proximo_indice)
        linhas.extend(linhas_objeto)
        proximo_indice += usados

    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas) + "\n")


def carregar_mundo_obj(caminho):
    vertices_globais = []
    objetos_lidos = []
    atual = None

    with open(caminho, "r", encoding="utf-8") as arquivo:
        for linha_bruta in arquivo:
            linha = linha_bruta.strip()
            if not linha:
                continue

            if linha.startswith("o "):
                if atual is not None:
                    objetos_lidos.append(atual)
                atual = {
                    "nome": linha[2:].strip(), "tipo": "wireframe",
                    "cor": "#000000", "preenchido": False, "indices": [],
                }

            elif linha.startswith("# tipo "):
                if atual is not None:
                    atual["tipo"] = linha[len("# tipo "):].strip()

            elif linha.startswith("# cor "):
                if atual is not None:
                    atual["cor"] = linha[len("# cor "):].strip()

            elif linha.startswith("# preenchido "):
                if atual is not None:
                    atual["preenchido"] = linha[len("# preenchido "):].strip() == "True"

            elif linha.startswith("v "):
                _, x, y, _z = linha.split()
                vertices_globais.append((float(x), float(y)))

            elif linha.startswith(("p ", "l ", "f ")):
                if atual is not None:
                    partes = linha.split()[1:]
                    atual["indices"] = [int(p) - 1 for p in partes]

        if atual is not None:
            objetos_lidos.append(atual)

    resultado = []
    for info in objetos_lidos:
        indices = info["indices"]
        if info["tipo"] == "wireframe" and len(indices) > 1 and indices[0] == indices[-1]:
            indices = indices[:-1]
        coordenadas = [vertices_globais[i] for i in indices]
        resultado.append((info["nome"], info["tipo"], coordenadas, info["cor"], info["preenchido"]))

    return resultado


# JANELA DE TRANSFORMAÇÕES (herdada das entregas anteriores)

class JanelaTransformacao(tk.Toplevel):
    def __init__(self, raiz, objeto, ao_aplicar):
        super().__init__(raiz)
        self.title(f"Transformações - {objeto.nome}")
        self.objeto = objeto
        self.ao_aplicar = ao_aplicar

        self.pendentes = []
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

        self.frame_translacao = tk.Frame(self)
        tk.Label(self.frame_translacao, text="dx:").grid(row=0, column=0)
        self.entrada_dx = tk.Entry(self.frame_translacao, width=8)
        self.entrada_dx.grid(row=0, column=1)
        tk.Label(self.frame_translacao, text="dy:").grid(row=0, column=2)
        self.entrada_dy = tk.Entry(self.frame_translacao, width=8)
        self.entrada_dy.grid(row=0, column=3)

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
        self.window = Window(centro_x=0, centro_y=0, largura=200, altura=200)
        # margem grande de propósito: a viewport fica visivelmente
        # menor que o canvas, com uma moldura entre as duas -- assim,
        # se o clipping falhar, o objeto "vaza" pra fora da moldura e
        # o erro fica óbvio (sugestão do próprio enunciado).
        self.viewport = Viewport(self.LARGURA_CANVAS, self.ALTURA_CANVAS, margem=40)
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
        self.lista_objetos = tk.Listbox(painel, width=32, height=8)
        self.lista_objetos.pack()

        tk.Button(
            painel, text="Transformar objeto selecionado",
            command=self._abrir_janela_transformacao,
        ).pack(pady=(5, 0))

        # Formulário de novo objeto
        tk.Label(painel, text="Novo objeto").pack(anchor="w", pady=(15, 0))

        tk.Label(painel, text="Nome:").pack(anchor="w")
        self.entrada_nome = tk.Entry(painel, width=32)
        self.entrada_nome.pack()

        tk.Label(painel, text="Tipo:").pack(anchor="w")
        self.tipo_selecionado = tk.StringVar(value="ponto")
        tk.OptionMenu(
            painel, self.tipo_selecionado, "ponto", "reta", "wireframe"
        ).pack(anchor="w")

        tk.Label(painel, text="Coordenadas (ex: (10,10),(50,50)):").pack(anchor="w")
        self.entrada_coordenadas = tk.Entry(painel, width=32)
        self.entrada_coordenadas.pack()

        frame_cor = tk.Frame(painel)
        frame_cor.pack(anchor="w", pady=(5, 0))
        tk.Button(frame_cor, text="Escolher cor", command=self._escolher_cor).pack(side="left")
        self.amostra_cor = tk.Label(frame_cor, text="   ", bg=self.cor_selecionada, relief="sunken")
        self.amostra_cor.pack(side="left", padx=5)

        self.preenchido_selecionado = tk.BooleanVar(value=False)
        tk.Checkbutton(
            painel, text="Preenchido (só afeta wireframe)",
            variable=self.preenchido_selecionado,
        ).pack(anchor="w", pady=(5, 0))

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

        # Rotação da window
        tk.Label(painel, text="Rotação da Window").pack(anchor="w", pady=(15, 0))
        frame_rotacao_window = tk.Frame(painel)
        frame_rotacao_window.pack()
        tk.Label(frame_rotacao_window, text="ângulo:").grid(row=0, column=0)
        self.entrada_angulo_window = tk.Entry(frame_rotacao_window, width=6)
        self.entrada_angulo_window.insert(0, "15")
        self.entrada_angulo_window.grid(row=0, column=1)
        tk.Button(
            frame_rotacao_window, text="Girar", command=self._girar_window
        ).grid(row=0, column=2, padx=5)
        self.label_angulo_atual = tk.Label(painel, text="Ângulo atual: 0°")
        self.label_angulo_atual.pack(anchor="w")

        # Técnica de clipping de retas
        tk.Label(painel, text="Clipping de retas").pack(anchor="w", pady=(15, 0))
        self.tecnica_clip_reta = tk.StringVar(value="cohen_sutherland")
        tk.Radiobutton(
            painel, text="Cohen-Sutherland", variable=self.tecnica_clip_reta,
            value="cohen_sutherland", command=self._redesenhar,
        ).pack(anchor="w")
        tk.Radiobutton(
            painel, text="Liang-Barsky", variable=self.tecnica_clip_reta,
            value="liang_barsky", command=self._redesenhar,
        ).pack(anchor="w")

        # Arquivo .obj
        tk.Label(painel, text="Arquivo .obj").pack(anchor="w", pady=(15, 0))
        frame_obj = tk.Frame(painel)
        frame_obj.pack()
        tk.Button(frame_obj, text="Salvar mundo", command=self._salvar_obj).grid(row=0, column=0, padx=2)
        tk.Button(frame_obj, text="Carregar mundo", command=self._carregar_obj).grid(row=0, column=1, padx=2)

    # Ações do usuário
    def _escolher_cor(self):
        cor = colorchooser.askcolor(color=self.cor_selecionada, title="Escolha a cor do objeto")
        if cor[1]:
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

        self.display_file.adicionar(
            nome, tipo, coordenadas, self.cor_selecionada, self.preenchido_selecionado.get()
        )
        self.entrada_nome.delete(0, tk.END)
        self.entrada_coordenadas.delete(0, tk.END)
        self._redesenhar()

    @staticmethod
    def _parsear_coordenadas(texto):
        tupla_de_pontos = ast.literal_eval(texto)
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

    def _girar_window(self):
        try:
            angulo = float(self.entrada_angulo_window.get())
        except ValueError:
            messagebox.showerror("Erro", "Digite um ângulo numérico.")
            return
        self.window.rotacionar(angulo)
        self._redesenhar()

    def _salvar_obj(self):
        if not self.display_file.objetos:
            messagebox.showerror("Erro", "Não há objetos no mundo para salvar.")
            return
        caminho = filedialog.asksaveasfilename(
            defaultextension=".obj", filetypes=[("Wavefront OBJ", "*.obj")]
        )
        if not caminho:
            return
        salvar_mundo_obj(self.display_file, caminho)

    def _carregar_obj(self):
        caminho = filedialog.askopenfilename(filetypes=[("Wavefront OBJ", "*.obj")])
        if not caminho:
            return

        if self.display_file.objetos:
            se_confirma = messagebox.askyesno(
                "Confirmar", "Isso vai substituir os objetos atuais do mundo. Continuar?"
            )
            if not se_confirma:
                return

        try:
            objetos_lidos = carregar_mundo_obj(caminho)
        except (OSError, ValueError, IndexError) as erro:
            messagebox.showerror("Erro", f"Não foi possível ler o arquivo:\n{erro}")
            return

        self.display_file.limpar()
        for nome, tipo, coordenadas, cor, preenchido in objetos_lidos:
            self.display_file.adicionar(nome, tipo, coordenadas, cor, preenchido)
        self._redesenhar()

    # Desenho
    def _redesenhar(self):
        self.canvas.delete("all")
        self.lista_objetos.delete(0, tk.END)
        self.label_angulo_atual.config(text=f"Ângulo atual: {self.window.angulo % 360:.1f}°")

        self._desenhar_moldura_viewport()

        xmin, xmax, ymin, ymax = self.window.limites_locais()
        usar_liang_barsky = self.tecnica_clip_reta.get() == "liang_barsky"

        for objeto in self.display_file.objetos:
            self.lista_objetos.insert(tk.END, repr(objeto))

            # 1) mundo -> local da window (ainda sem cortar nada)
            pontos_locais = [self.window.mundo_para_local(p) for p in objeto.coordenadas]

            # 2) clipping, específico por tipo de objeto
            if objeto.tipo == "ponto":
                if ponto_dentro_da_window(pontos_locais[0], xmin, xmax, ymin, ymax):
                    p_tela = self.viewport.local_para_tela(pontos_locais[0], self.window)
                    self._desenhar_ponto(p_tela, objeto.cor)

            elif objeto.tipo == "reta":
                if usar_liang_barsky:
                    resultado = clipar_reta_liang_barsky(pontos_locais[0], pontos_locais[1], xmin, xmax, ymin, ymax)
                else:
                    resultado = clipar_reta_cohen_sutherland(pontos_locais[0], pontos_locais[1], xmin, xmax, ymin, ymax)

                if resultado is not None:
                    p1_tela = self.viewport.local_para_tela(resultado[0], self.window)
                    p2_tela = self.viewport.local_para_tela(resultado[1], self.window)
                    self._desenhar_linha(p1_tela, p2_tela, objeto.cor)

            elif objeto.tipo == "wireframe":
                poligono_clipado = clipar_poligono_sutherland_hodgman(pontos_locais, xmin, xmax, ymin, ymax)
                if len(poligono_clipado) >= 2:
                    # 3) só o resultado do clipping passa pela viewport
                    pontos_tela = [self.viewport.local_para_tela(p, self.window) for p in poligono_clipado]
                    if objeto.preenchido and len(pontos_tela) >= 3:
                        self._desenhar_wireframe_preenchido(pontos_tela, objeto.cor)
                    else:
                        self._desenhar_wireframe(pontos_tela, objeto.cor)

    def _desenhar_moldura_viewport(self):
        """Desenha o retângulo exato onde a window (já mapeada pra
        tela) deveria terminar. Serve como referência visual: se o
        clipping estiver certo, nada deveria aparecer fora dela."""
        xmin, xmax, ymin, ymax = self.window.limites_locais()
        cantos_locais = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        cantos_tela = [self.viewport.local_para_tela(c, self.window) for c in cantos_locais]
        xs = [c[0] for c in cantos_tela]
        ys = [c[1] for c in cantos_tela]
        self.canvas.create_rectangle(min(xs), min(ys), max(xs), max(ys), outline="gray50")

    def _desenhar_ponto(self, ponto, cor, tamanho=3):
        x, y = ponto
        self.canvas.create_line(x - tamanho, y, x + tamanho, y, fill=cor)
        self.canvas.create_line(x, y - tamanho, x, y + tamanho, fill=cor)

    def _desenhar_linha(self, p1, p2, cor):
        self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=cor)

    def _desenhar_wireframe(self, pontos, cor):
        n = len(pontos)
        for i in range(n):
            p1 = pontos[i]
            p2 = pontos[(i + 1) % n]
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=cor)

    def _desenhar_wireframe_preenchido(self, pontos, cor):
        coordenadas_planas = []
        for x, y in pontos:
            coordenadas_planas.extend((x, y))
        self.canvas.create_polygon(*coordenadas_planas, fill=cor, outline=cor)


if __name__ == "__main__":
    raiz = tk.Tk()
    app = Aplicacao(raiz)
    raiz.mainloop()
