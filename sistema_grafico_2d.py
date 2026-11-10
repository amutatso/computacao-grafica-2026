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


# CURVAS DE BÉZIER (via Forward Differences)
#
# Uma curva de Bézier composta é definida por 3n+1 pontos de
# controle: o 1º segmento usa os pontos 0,1,2,3; o 2º usa 3,4,5,6
# (reaproveitando o ponto 3); e assim por diante. Reaproveitar o
# último ponto de um segmento como primeiro do próximo garante
# continuidade G(0) -- a curva não tem "buracos" entre segmentos.
#
# Cada segmento (4 pontos) é transformado em uma sequência de
# pequenos pontos ao longo da curva usando forward differences --
# a mesma técnica já usada no exercício da B-spline, só trocando a
# matriz do método (aqui, a matriz de Bézier).

def matriz_bezier():
    return ((-1, 3, -3, 1), (3, -6, 3, 0), (-3, 3, 0, 0), (1, 0, 0, 0))


def _matriz_diferencas(delta):
    """E(delta), tal que D = E(delta) . C, onde D = [f0, Δf0, Δ²f0, Δ³f0]."""
    return (
        (0, 0, 0, 1),
        (delta ** 3, delta ** 2, delta, 0),
        (6 * delta ** 3, 2 * delta ** 2, 0, 0),
        (6 * delta ** 3, 0, 0, 0),
    )


def _multiplicar_matriz4_vetor4(matriz, vetor):
    return [sum(matriz[i][j] * vetor[j] for j in range(4)) for i in range(4)]


def gerar_pontos_bezier(p0, p1, p2, p3, passos=20):
    """Gera os pontos de UM segmento de Bézier (4 pontos de controle),
    usando forward differences, para x e y separadamente."""
    delta = 1 / passos
    M = matriz_bezier()
    E = _matriz_diferencas(delta)

    Gx = [p0[0], p1[0], p2[0], p3[0]]
    Gy = [p0[1], p1[1], p2[1], p3[1]]

    Cx = _multiplicar_matriz4_vetor4(M, Gx)
    Cy = _multiplicar_matriz4_vetor4(M, Gy)

    Dx = _multiplicar_matriz4_vetor4(E, Cx)  # [f0, Δf0, Δ²f0, Δ³f0] em x
    Dy = _multiplicar_matriz4_vetor4(E, Cy)  # idem em y

    x, dx, d2x, d3x = Dx
    y, dy, d2y, d3y = Dy

    pontos = [(x, y)]
    for _ in range(passos):
        x += dx;  dx += d2x;  d2x += d3x
        y += dy;  dy += d2y;  d2y += d3y
        pontos.append((x, y))
    return pontos


def gerar_curva_bezier_composta(pontos_controle, passos_por_segmento=20):
    """
    pontos_controle: lista com 3n+1 pontos (n segmentos). Devolve a
    lista de pontos de TODA a curva, já concatenada -- pronta para
    ser tratada como uma polilinha (útil tanto para desenhar quanto
    para clipar, reaproveitando o clip de reta já existente).
    """
    n_segmentos = (len(pontos_controle) - 1) // 3
    pontos_curva = []

    for i in range(n_segmentos):
        p0, p1, p2, p3 = pontos_controle[3 * i: 3 * i + 4]
        segmento = gerar_pontos_bezier(p0, p1, p2, p3, passos_por_segmento)
        if i > 0:
            segmento = segmento[1:]  # evita repetir o ponto de junção
        pontos_curva.extend(segmento)

    return pontos_curva


# B-Splines utilizando Forward Differences
def matriz_bspline():
    return ((-1/6, 3/6, -3/6, 1/6), (3/6, -6/6, 3/6, 0/6), (-3/6, 0/6, 3/6, 0/6), (1/6, 4/6, 1/6, 0/6))


def _matriz_diferencas(delta):
    """E(delta), tal que D = E(delta) . C, onde D = [f0, Δf0, Δ²f0, Δ³f0]."""
    return (
        (0, 0, 0, 1),
        (delta ** 3, delta ** 2, delta, 0),
        (6 * delta ** 3, 2 * delta ** 2, 0, 0),
        (6 * delta ** 3, 0, 0, 0),
    )


def _multiplicar_matriz4_vetor4(matriz, vetor):
    return [sum(matriz[i][j] * vetor[j] for j in range(4)) for i in range(4)]


def gerar_pontos_bspline(p0, p1, p2, p3, passos=20):
    """Gera os pontos de UM segmento de B-spline (4 pontos de controle),
    usando forward differences, para x e y separadamente."""
    delta = 1 / passos
    M = matriz_bspline()
    E = _matriz_diferencas(delta)

    Gx = [p0[0], p1[0], p2[0], p3[0]]
    Gy = [p0[1], p1[1], p2[1], p3[1]]

    Cx = _multiplicar_matriz4_vetor4(M, Gx)
    Cy = _multiplicar_matriz4_vetor4(M, Gy)

    Dx = _multiplicar_matriz4_vetor4(E, Cx)  # [f0, Δf0, Δ²f0, Δ³f0] em x
    Dy = _multiplicar_matriz4_vetor4(E, Cy)  # idem em y

    x, dx, d2x, d3x = Dx
    y, dy, d2y, d3y = Dy

    pontos = [(x, y)]
    for _ in range(passos):
        x += dx;  dx += d2x;  d2x += d3x
        y += dy;  dy += d2y;  d2y += d3y
        pontos.append((x, y))
    return pontos


def gerar_bspline(pontos_controle, passos_por_segmento=20):
    """
    pontos_controle: lista com 3n+1 pontos (n segmentos). Devolve a
    lista de pontos de TODA a curva, já concatenada -- pronta para
    ser tratada como uma polilinha (útil tanto para desenhar quanto
    para clipar, reaproveitando o clip de reta já existente).
    """
    n_segmentos = (len(pontos_controle) - 1) // 3
    pontos_curva = []

    for i in range(3, len(pontos_controle)):
        p0, p1, p2, p3 = pontos_controle[i - 3: i + 1]
        segmento = gerar_pontos_bspline(p0, p1, p2, p3, passos_por_segmento)
        if i > 3:
            segmento = segmento[1:]  # evita repetir o ponto de junção
        pontos_curva.extend(segmento)

    return pontos_curva


# COMPUTAÇÃO GRÁFICA 3D: PONTO3D, OBJETO3D E PROJEÇÃO PARALELA ORTOGONAL
#
# A partir daqui tudo passa a trabalhar com matrizes 4x4 em
# coordenadas homogêneas (x, y, z, 1) -- o equivalente em 3D das
# matrizes 3x3 usadas lá em cima para as transformações 2D.

def matriz_identidade4():
    return ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))


def multiplicar_matrizes4(a, b):
    resultado = [[0, 0, 0, 0] for _ in range(4)]
    for i in range(4):
        for j in range(4):
            resultado[i][j] = sum(a[i][k] * b[k][j] for k in range(4))
    return tuple(tuple(linha) for linha in resultado)


def aplicar_matriz4_no_ponto(matriz, ponto):
    x, y, z = ponto
    vetor = (x, y, z, 1)
    resultado = [sum(matriz[i][k] * vetor[k] for k in range(4)) for i in range(4)]
    return (resultado[0], resultado[1], resultado[2])


def matriz_translacao3d(dx, dy, dz):
    return ((1, 0, 0, dx), (0, 1, 0, dy), (0, 0, 1, dz), (0, 0, 0, 1))


class Ponto3D:
    """
    Um ponto no espaço 3D, capaz de sofrer as 3 transformações
    básicas (translação, escala, rotação) através de matrizes 4x4 em
    coordenadas homogêneas -- o mesmo princípio do Objeto2D lá em
    cima, só que com uma dimensão a mais.
    """

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def como_tupla(self):
        return (self.x, self.y, self.z)

    def aplicar_matriz(self, matriz):
        self.x, self.y, self.z = aplicar_matriz4_no_ponto(matriz, self.como_tupla())

    def __repr__(self):
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"


def centro_geometrico_3d(pontos):
    n = len(pontos)
    cx = sum(p.x for p in pontos) / n
    cy = sum(p.y for p in pontos) / n
    cz = sum(p.z for p in pontos) / n
    return cx, cy, cz


def matriz_escala_natural_3d(pontos, sx, sy, sz):
    cx, cy, cz = centro_geometrico_3d(pontos)
    para_origem = matriz_translacao3d(-cx, -cy, -cz)
    escala = ((sx, 0, 0, 0), (0, sy, 0, 0), (0, 0, sz, 0), (0, 0, 0, 1))
    de_volta = matriz_translacao3d(cx, cy, cz)
    return multiplicar_matrizes4(de_volta, multiplicar_matrizes4(escala, para_origem))


def matriz_rotacao_x(graus):
    rad = math.radians(graus)
    c, s = math.cos(rad), math.sin(rad)
    return ((1, 0, 0, 0), (0, c, -s, 0), (0, s, c, 0), (0, 0, 0, 1))


def matriz_rotacao_y(graus):
    rad = math.radians(graus)
    c, s = math.cos(rad), math.sin(rad)
    return ((c, 0, s, 0), (0, 1, 0, 0), (-s, 0, c, 0), (0, 0, 0, 1))


def matriz_rotacao_z(graus):
    rad = math.radians(graus)
    c, s = math.cos(rad), math.sin(rad)
    return ((c, -s, 0, 0), (s, c, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))


def matriz_rotacao_centro_objeto_3d(pontos, eixo, graus):
    """Rotação (uma das 3 transformações básicas) em torno de um dos
    eixos X/Y/Z, passando pelo centro geométrico do objeto -- mesma
    ideia da rotação "centro do objeto" que já existe em 2D."""
    cx, cy, cz = centro_geometrico_3d(pontos)
    rotacoes = {"x": matriz_rotacao_x, "y": matriz_rotacao_y, "z": matriz_rotacao_z}
    R = rotacoes[eixo](graus)
    return multiplicar_matrizes4(
        matriz_translacao3d(cx, cy, cz),
        multiplicar_matrizes4(R, matriz_translacao3d(-cx, -cy, -cz)),
    )


def _normalizar_vetor(vetor):
    x, y, z = vetor
    norma = math.sqrt(x * x + y * y + z * z)
    return (x / norma, y / norma, z / norma)


def matriz_rotacao_eixo_arbitrario(ponto_do_eixo, direcao, graus):
    """
    Rotação em torno de uma RETA qualquer no espaço (não necessariamente
    um dos eixos X/Y/Z), definida por um ponto que ela passa
    (ponto_do_eixo) e sua direção (direcao). Usa a fórmula de
    Euler-Rodrigues:

        R = cos(a)*I + (1 - cos(a))*(e . e^T) + sin(a)*E

    onde "e" é o vetor unitário da direção do eixo, "a" é o ângulo de
    rotação, e E é a matriz anti-simétrica tal que E.v = e x v (o
    produto vetorial de e com qualquer vetor v). [Fonte: Brannon,
    "Rotation: A review of useful theorems involving proper orthogonal
    matrices...", eq. 3.19]

    Como o eixo não passa necessariamente pela origem, usamos o mesmo
    truque de sempre: translada o ponto do eixo para a origem,
    rotaciona, e translada de volta.
    """
    ex, ey, ez = _normalizar_vetor(direcao)
    rad = math.radians(graus)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    # cos(a) * I  +  (1 - cos(a)) * (e . e^T)
    produto_externo = ((ex * ex, ex * ey, ex * ez),
                        (ey * ex, ey * ey, ey * ez),
                        (ez * ex, ez * ey, ez * ez))
    rotacao3x3 = [[0.0, 0.0, 0.0] for _ in range(3)]
    for i in range(3):
        for j in range(3):
            identidade_ij = 1.0 if i == j else 0.0
            rotacao3x3[i][j] = cos_a * identidade_ij + (1 - cos_a) * produto_externo[i][j]

    # + sin(a) * E  (E é a matriz anti-simétrica do eixo: E.v = e x v)
    E = ((0, -ez, ey), (ez, 0, -ex), (-ey, ex, 0))
    for i in range(3):
        for j in range(3):
            rotacao3x3[i][j] += sin_a * E[i][j]

    rotacao4x4 = (
        (rotacao3x3[0][0], rotacao3x3[0][1], rotacao3x3[0][2], 0),
        (rotacao3x3[1][0], rotacao3x3[1][1], rotacao3x3[1][2], 0),
        (rotacao3x3[2][0], rotacao3x3[2][1], rotacao3x3[2][2], 0),
        (0, 0, 0, 1),
    )

    px, py, pz = ponto_do_eixo
    return multiplicar_matrizes4(
        matriz_translacao3d(px, py, pz),
        multiplicar_matrizes4(rotacao4x4, matriz_translacao3d(-px, -py, -pz)),
    )


class Objeto3D:
    """
    Um modelo de arame (wireframe) 3D: uma lista de ARESTAS, cada uma
    um par de Ponto3D -- exatamente como pedido no enunciado. É
    construído a partir de uma lista de vértices, na ordem digitada
    pelo usuário, ligando cada vértice ao próximo e fechando do
    último ao primeiro (igual ao wireframe 2D).
    """

    def __init__(self, nome, vertices, cor="#008000"):
        self.nome = nome
        self.cor = cor
        n = len(vertices)
        self.arestas = [(vertices[i], vertices[(i + 1) % n]) for i in range(n)]

    def pontos(self):
        """Todos os Ponto3D do objeto, sem repetição -- é sobre eles
        que as transformações são aplicadas (cada aresta guarda
        REFERÊNCIAS a esses pontos, não cópias, então transformar um
        ponto afeta automaticamente as duas arestas que o usam)."""
        vistos = []
        for p1, p2 in self.arestas:
            if p1 not in vistos:
                vistos.append(p1)
            if p2 not in vistos:
                vistos.append(p2)
        return vistos

    def aplicar_matriz(self, matriz):
        for ponto in self.pontos():
            ponto.aplicar_matriz(matriz)

    def __repr__(self):
        return f"{self.nome} [objeto3d, {len(self.arestas)} arestas]"


# PROJEÇÃO PARALELA ORTOGONAL (VRP / VPN)
#
# Algoritmo (visto em aula):
#   1. Translade VRP para a origem.
#   2. Determine VPN.
#   3. Decomponha e determine os ângulos de VPN com X e Y; rotacione
#      o mundo em torno de X e depois de Y, de forma a alinhar o VPN
#      com o eixo Z.
#   4. Ignore todas as coordenadas Z dos objetos.
#   5. Normalize o resto (coordenadas de window).
#   6. Clipe.
#   7. Transforme para coordenadas de viewport.
#
# Os passos 1-4 (a parte realmente 3D) são feitos pelas funções
# abaixo. Os passos 5-7 são feitos reaproveitando o Window/Viewport/
# clipping 2D que já existe lá em cima: depois do passo 4 sobra um
# ponto (x, y) comum, e como o passo 1 já jogou o VRP para a origem,
# a window 2D (centrada em 0,0) cuida do resto exatamente como já
# cuidava dos objetos 2D -- normalizar a window nada mais é do que
# window.mundo_para_local() + os limites_locais() de sempre.

def matriz_sru_para_src(vrp, vpn):
    """Monta a matriz 4x4 que faz os passos 1-3 do algoritmo: translada
    por -VRP e depois rotaciona em torno de X e de Y para alinhar o
    VPN com o eixo Z."""
    translacao = matriz_translacao3d(-vrp[0], -vrp[1], -vrp[2])

    nx, ny, nz = vpn

    # Passo 3a: rotação em X, que leva o VPN para o plano XZ (zera o Y).
    d_yz = math.sqrt(ny * ny + nz * nz)
    if d_yz < 1e-9:
        # VPN já está no plano XZ (aponta só em X) -- nada a fazer aqui.
        cos_x, sin_x = 1.0, 0.0
    else:
        cos_x, sin_x = nz / d_yz, ny / d_yz
    rotacao_x = ((1, 0, 0, 0), (0, cos_x, -sin_x, 0), (0, sin_x, cos_x, 0), (0, 0, 0, 1))

    # Depois da rotação em X, o VPN vira (nx, 0, d_yz).
    # Passo 3b: rotação em Y, que leva esse vetor para o eixo Z (zera o X).
    d_total = math.sqrt(nx * nx + d_yz * d_yz)  # == |VPN|
    if d_total < 1e-9:
        cos_y, sin_y = 1.0, 0.0
    else:
        cos_y, sin_y = d_yz / d_total, -nx / d_total
    rotacao_y = ((cos_y, 0, sin_y, 0), (0, 1, 0, 0), (-sin_y, 0, cos_y, 0), (0, 0, 0, 1))

    return multiplicar_matrizes4(rotacao_y, multiplicar_matrizes4(rotacao_x, translacao))


def projetar_paralela_ortogonal(ponto3d, vrp, vpn):
    """Passos 1-4 do algoritmo, aplicados a UM ponto: leva o ponto
    para o sistema onde o VPN é o eixo Z (SRU -> SRC) e então ignora
    o Z -- a definição de projeção ORTOGONAL é justamente essa:
    descartar a coordenada perpendicular ao plano de projeção, sem
    nenhuma distorção de perspectiva."""
    matriz = matriz_sru_para_src(vrp, vpn)
    x, y, _z = aplicar_matriz4_no_ponto(matriz, ponto3d.como_tupla())
    return (x, y)


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
        elif objeto.tipo == "curva":
            # salva os PONTOS DE CONTROLE (não os pontos gerados pela
            # curva) -- ao carregar de volta, a curva é regenerada a
            # partir deles.
            sequencia = " ".join(str(i) for i in indices)
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


# JANELA DE TRANSFORMAÇÕES 2D (herdada das entregas anteriores)

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


# JANELA DE TRANSFORMAÇÕES 3D
#
# Mesma lógica da JanelaTransformacao 2D (empilha transformações,
# "Aplicar tudo" faz tudo de uma vez), mas para Objeto3D: translação,
# escala e rotação em torno do centro do objeto são as 3 básicas, e a
# rotação em eixo arbitrário é a 4ª opção extra pedida no enunciado.

class JanelaTransformacao3D(tk.Toplevel):
    def __init__(self, raiz, objeto3d, ao_aplicar):
        super().__init__(raiz)
        self.title(f"Transformações 3D - {objeto3d.nome}")
        self.objeto3d = objeto3d
        self.ao_aplicar = ao_aplicar
        self.pendentes = []
        self._montar_interface()

    def _montar_interface(self):
        tk.Label(self, text="Transformações a aplicar:").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 0)
        )
        self.lista_pendentes = tk.Listbox(self, width=48, height=6)
        self.lista_pendentes.grid(row=1, column=0, columnspan=2, padx=10)

        self.tipo = tk.StringVar(value="translacao")
        frame_tipo = tk.Frame(self)
        frame_tipo.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        for texto, valor in [
            ("Translação", "translacao"),
            ("Escala", "escala"),
            ("Rotação (eixo X/Y/Z)", "rotacao"),
            ("Rotação (eixo arbitrário)", "rotacao_arbitraria"),
        ]:
            tk.Radiobutton(
                frame_tipo, text=texto, variable=self.tipo, value=valor,
                command=self._atualizar_campos_visiveis,
            ).pack(anchor="w")

        self.frame_translacao = tk.Frame(self)
        for i, rotulo in enumerate(("dx:", "dy:", "dz:")):
            tk.Label(self.frame_translacao, text=rotulo).grid(row=0, column=2 * i)
        self.entrada_dx = tk.Entry(self.frame_translacao, width=6)
        self.entrada_dx.grid(row=0, column=1)
        self.entrada_dy = tk.Entry(self.frame_translacao, width=6)
        self.entrada_dy.grid(row=0, column=3)
        self.entrada_dz = tk.Entry(self.frame_translacao, width=6)
        self.entrada_dz.grid(row=0, column=5)

        self.frame_escala = tk.Frame(self)
        tk.Label(self.frame_escala, text="Escala natural, em torno do centro do objeto").grid(
            row=0, column=0, columnspan=6
        )
        for i, rotulo in enumerate(("sx:", "sy:", "sz:")):
            tk.Label(self.frame_escala, text=rotulo).grid(row=1, column=2 * i)
        self.entrada_sx = tk.Entry(self.frame_escala, width=6)
        self.entrada_sx.grid(row=1, column=1)
        self.entrada_sy = tk.Entry(self.frame_escala, width=6)
        self.entrada_sy.grid(row=1, column=3)
        self.entrada_sz = tk.Entry(self.frame_escala, width=6)
        self.entrada_sz.grid(row=1, column=5)

        self.frame_rotacao = tk.Frame(self)
        tk.Label(self.frame_rotacao, text="Eixo (passando pelo centro do objeto):").grid(
            row=0, column=0, columnspan=4, sticky="w"
        )
        self.eixo_rotacao = tk.StringVar(value="x")
        for i, eixo in enumerate(("x", "y", "z")):
            tk.Radiobutton(
                self.frame_rotacao, text=eixo.upper(), variable=self.eixo_rotacao, value=eixo,
            ).grid(row=1, column=i, sticky="w")
        tk.Label(self.frame_rotacao, text="ângulo (graus):").grid(row=2, column=0, columnspan=2, sticky="w")
        self.entrada_angulo = tk.Entry(self.frame_rotacao, width=8)
        self.entrada_angulo.grid(row=2, column=2, columnspan=2)

        self.frame_rotacao_arbitraria = tk.Frame(self)
        tk.Label(self.frame_rotacao_arbitraria, text="Ponto do eixo (px,py,pz):").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        self.entrada_eixo_px = tk.Entry(self.frame_rotacao_arbitraria, width=5)
        self.entrada_eixo_px.grid(row=1, column=0)
        self.entrada_eixo_py = tk.Entry(self.frame_rotacao_arbitraria, width=5)
        self.entrada_eixo_py.grid(row=1, column=1)
        self.entrada_eixo_pz = tk.Entry(self.frame_rotacao_arbitraria, width=5)
        self.entrada_eixo_pz.grid(row=1, column=2)
        tk.Label(self.frame_rotacao_arbitraria, text="Direção (dx,dy,dz):").grid(
            row=2, column=0, columnspan=3, sticky="w"
        )
        self.entrada_eixo_dx = tk.Entry(self.frame_rotacao_arbitraria, width=5)
        self.entrada_eixo_dx.grid(row=3, column=0)
        self.entrada_eixo_dy = tk.Entry(self.frame_rotacao_arbitraria, width=5)
        self.entrada_eixo_dy.grid(row=3, column=1)
        self.entrada_eixo_dz = tk.Entry(self.frame_rotacao_arbitraria, width=5)
        self.entrada_eixo_dz.grid(row=3, column=2)
        tk.Label(self.frame_rotacao_arbitraria, text="ângulo (graus):").grid(row=4, column=0, columnspan=2, sticky="w")
        self.entrada_angulo_arbitrario = tk.Entry(self.frame_rotacao_arbitraria, width=8)
        self.entrada_angulo_arbitrario.grid(row=4, column=2)

        self._atualizar_campos_visiveis()

        frame_botoes = tk.Frame(self)
        frame_botoes.grid(row=5, column=0, columnspan=2, pady=15)
        tk.Button(frame_botoes, text="Adicionar", command=self._adicionar_pendente).pack(side="left", padx=5)
        tk.Button(frame_botoes, text="Aplicar tudo", command=self._aplicar_tudo).pack(side="left", padx=5)
        tk.Button(frame_botoes, text="Cancelar", command=self.destroy).pack(side="left", padx=5)

    def _atualizar_campos_visiveis(self):
        self.frame_translacao.grid_forget()
        self.frame_escala.grid_forget()
        self.frame_rotacao.grid_forget()
        self.frame_rotacao_arbitraria.grid_forget()

        tipo = self.tipo.get()
        if tipo == "translacao":
            self.frame_translacao.grid(row=3, column=0, columnspan=2, pady=5)
        elif tipo == "escala":
            self.frame_escala.grid(row=3, column=0, columnspan=2, pady=5)
        elif tipo == "rotacao":
            self.frame_rotacao.grid(row=3, column=0, columnspan=2, pady=5)
        else:
            self.frame_rotacao_arbitraria.grid(row=3, column=0, columnspan=2, pady=5)

    def _adicionar_pendente(self):
        try:
            tipo = self.tipo.get()
            pontos = self.objeto3d.pontos()

            if tipo == "translacao":
                dx = float(self.entrada_dx.get())
                dy = float(self.entrada_dy.get())
                dz = float(self.entrada_dz.get())
                matriz = matriz_translacao3d(dx, dy, dz)
                descricao = f"Translação (dx={dx}, dy={dy}, dz={dz})"

            elif tipo == "escala":
                sx = float(self.entrada_sx.get())
                sy = float(self.entrada_sy.get())
                sz = float(self.entrada_sz.get())
                matriz = matriz_escala_natural_3d(pontos, sx, sy, sz)
                descricao = f"Escala natural (sx={sx}, sy={sy}, sz={sz})"

            elif tipo == "rotacao":
                eixo = self.eixo_rotacao.get()
                angulo = float(self.entrada_angulo.get())
                matriz = matriz_rotacao_centro_objeto_3d(pontos, eixo, angulo)
                descricao = f"Rotação {angulo}° em torno do eixo {eixo.upper()} (centro do objeto)"

            else:  # rotacao_arbitraria
                ponto_eixo = (
                    float(self.entrada_eixo_px.get()),
                    float(self.entrada_eixo_py.get()),
                    float(self.entrada_eixo_pz.get()),
                )
                direcao = (
                    float(self.entrada_eixo_dx.get()),
                    float(self.entrada_eixo_dy.get()),
                    float(self.entrada_eixo_dz.get()),
                )
                angulo = float(self.entrada_angulo_arbitrario.get())
                matriz = matriz_rotacao_eixo_arbitrario(ponto_eixo, direcao, angulo)
                descricao = f"Rotação {angulo}° em eixo arbitrário (ponto={ponto_eixo}, direção={direcao})"

        except (ValueError, ZeroDivisionError):
            messagebox.showerror("Erro", "Preencha os campos numéricos corretamente.")
            return

        self.pendentes.append((descricao, matriz))
        self.lista_pendentes.insert(tk.END, descricao)

    def _aplicar_tudo(self):
        if not self.pendentes:
            self.destroy()
            return

        matriz_final = matriz_identidade4()
        for _, matriz in self.pendentes:
            matriz_final = multiplicar_matrizes4(matriz, matriz_final)

        self.objeto3d.aplicar_matriz(matriz_final)
        self.ao_aplicar()
        self.destroy()


# APLICAÇÃO (Tkinter)

class Aplicacao:
    LARGURA_CANVAS = 640
    ALTURA_CANVAS = 640

    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title("Sistema Gráfico Interativo")

        self.display_file = DisplayFile()
        self.window = Window(centro_x=0, centro_y=0, largura=200, altura=200)
        # margem grande de propósito: a viewport fica visivelmente
        # menor que o canvas, com uma moldura entre as duas -- assim,
        # se o clipping falhar, o objeto "vaza" pra fora da moldura e
        # o erro fica óbvio (sugestão do próprio enunciado).
        self.viewport = Viewport(self.LARGURA_CANVAS, self.ALTURA_CANVAS, margem=40)
        self.cor_selecionada = "#000000"

        # Objetos 3D (Trabalho 1.7) e a câmera (VRP/VPN) usada na
        # Projeção Paralela Ortogonal. Depois de projetados em 2D,
        # eles passam pela MESMA window/viewport/clipping acima --
        # é por isso que o VRP vira a origem no passo 1 do algoritmo:
        # assim a window 2D (centrada em 0,0) já funciona sem mudar
        # nada.
        self.objetos_3d = []
        self.vrp = (0.0, 0.0, -100.0)
        self.vpn = (0.0, 0.0, 1.0)

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

        # Painel lateral COM ROLAGEM: depois que a seção de objetos 3D
        # foi adicionada, o painel ficou mais alto do que a tela em
        # muitos monitores -- sem isso, o conteúdo de baixo (navegação
        # de câmera) simplesmente sumia pra fora da janela. A solução
        # clássica em Tkinter: um Canvas + Scrollbar servindo de
        # "moldura com rolagem" em volta de um Frame comum (o
        # `painel`), que continua sendo usado exatamente como antes.
        frame_painel_externo = tk.Frame(self.raiz)
        frame_painel_externo.grid(row=0, column=1, sticky="ns", padx=10, pady=10)

        canvas_painel = tk.Canvas(frame_painel_externo, width=300, height=self.ALTURA_CANVAS, highlightthickness=0)
        barra_rolagem = tk.Scrollbar(frame_painel_externo, orient="vertical", command=canvas_painel.yview)
        canvas_painel.configure(yscrollcommand=barra_rolagem.set)
        canvas_painel.pack(side="left", fill="both", expand=True)
        barra_rolagem.pack(side="right", fill="y")

        painel = tk.Frame(canvas_painel)
        # width=300 trava a largura do painel no mesmo valor do canvas
        # que o contém -- sem isso, um texto comprido demais (como um
        # VRP/VPN com várias casas decimais) empurra o painel pra uma
        # largura maior, e como só criamos rolagem VERTICAL, esse
        # excesso "vaza" pra direita sem jeito de rolar até lá.
        canvas_painel.create_window((0, 0), window=painel, anchor="nw", width=300)

        def _atualizar_area_rolagem(_evento=None):
            canvas_painel.configure(scrollregion=canvas_painel.bbox("all"))

        painel.bind("<Configure>", _atualizar_area_rolagem)

        def _rolar_com_roda_do_mouse(evento):
            canvas_painel.yview_scroll(int(-1 * (evento.delta / 120)), "units")

        # Só rola quando o mouse está sobre o painel (não o mundo todo),
        # senão rolar a lista de objetos, por exemplo, também rolaria o painel.
        canvas_painel.bind("<Enter>", lambda _e: canvas_painel.bind_all("<MouseWheel>", _rolar_com_roda_do_mouse))
        canvas_painel.bind("<Leave>", lambda _e: canvas_painel.unbind_all("<MouseWheel>"))

        # Lista de objetos existentes
        tk.Label(painel, text="Objetos 2D").pack(anchor="w")
        self.lista_objetos = tk.Listbox(painel, width=32, height=6)
        self.lista_objetos.pack()

        tk.Button(
            painel, text="Transformar objeto selecionado",
            command=self._abrir_janela_transformacao,
        ).pack(pady=(5, 0))

        # Formulário de novo objeto
        tk.Label(painel, text="Novo objeto 2D").pack(anchor="w", pady=(15, 0))

        tk.Label(painel, text="Nome:").pack(anchor="w")
        self.entrada_nome = tk.Entry(painel, width=32)
        self.entrada_nome.pack()

        tk.Label(painel, text="Tipo:").pack(anchor="w")
        self.tipo_selecionado = tk.StringVar(value="ponto")
        tk.OptionMenu(
            painel, self.tipo_selecionado, "ponto", "reta", "wireframe", "curva", "bspline"
        ).pack(anchor="w")

        tk.Label(
            painel,
            text="Coordenadas. Curva: 3n+1 pontos (4, 7, 10...)",
        ).pack(anchor="w")
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

        # ---- Objetos 3D (Trabalho 1.7) ----
        tk.Label(painel, text="— Objetos 3D (projeção paralela) —").pack(anchor="w", pady=(20, 0))

        self.lista_objetos_3d = tk.Listbox(painel, width=32, height=5)
        self.lista_objetos_3d.pack()

        tk.Button(
            painel, text="Transformar objeto 3D selecionado",
            command=self._abrir_janela_transformacao_3d,
        ).pack(pady=(5, 0))

        tk.Label(painel, text="Nome do objeto 3D:").pack(anchor="w", pady=(10, 0))
        self.entrada_nome_3d = tk.Entry(painel, width=32)
        self.entrada_nome_3d.pack()

        tk.Label(
            painel, text="Vértices (x,y,z): (0,0,0),(50,0,0),...\n"
                         "(forma um wireframe fechado, como em 2D)",
            justify="left",
        ).pack(anchor="w")
        self.entrada_coordenadas_3d = tk.Entry(painel, width=32)
        self.entrada_coordenadas_3d.pack()

        tk.Button(
            painel, text="Adicionar objeto 3D", command=self._adicionar_objeto_3d
        ).pack(pady=5)

        # Câmera: VRP / VPN -- definir direto (digitando) OU navegar
        tk.Label(painel, text="Câmera: VRP e VPN").pack(anchor="w", pady=(10, 0))
        frame_vrp = tk.Frame(painel)
        frame_vrp.pack(anchor="w")
        tk.Label(frame_vrp, text="VRP (x,y,z):").grid(row=0, column=0, sticky="w")
        self.entrada_vrp = tk.Entry(frame_vrp, width=18)
        self.entrada_vrp.insert(0, "0,0,-100")
        self.entrada_vrp.grid(row=0, column=1)
        tk.Label(frame_vrp, text="VPN (x,y,z):").grid(row=1, column=0, sticky="w")
        self.entrada_vpn = tk.Entry(frame_vrp, width=18)
        self.entrada_vpn.insert(0, "0,0,1")
        self.entrada_vpn.grid(row=1, column=1)
        tk.Button(
            frame_vrp, text="Definir câmera", command=self._definir_camera
        ).grid(row=2, column=0, columnspan=2, pady=5)
        tk.Button(
            frame_vrp, text="Usar 1º vértice do objeto 3D selecionado como VRP",
            command=self._usar_primeiro_vertice_como_vrp,
        ).grid(row=3, column=0, columnspan=2, pady=(0, 5))

        self.label_camera_atual = tk.Label(
            painel, text="VRP=(0,0,-100)\nVPN=(0,0,1)", justify="left", wraplength=260,
        )
        self.label_camera_atual.pack(anchor="w")

        # Navegação da window no espaço 3D: mover a câmera (VRP) e
        # girar pra onde ela olha (VPN) -- o equivalente, em código,
        # de "arrastar o botão do meio do mouse" no Blender. O zoom
        # da window 2D (botão lá em cima) também vale aqui, porque os
        # objetos 3D projetados passam pela MESMA window.
        tk.Label(painel, text="Navegar câmera (mover VRP)").pack(anchor="w", pady=(10, 0))
        frame_mover_camera = tk.Frame(painel)
        frame_mover_camera.pack()
        passo_camera = 10
        tk.Button(frame_mover_camera, text="X+", width=3,
                  command=lambda: self._mover_camera(passo_camera, 0, 0)).grid(row=0, column=0)
        tk.Button(frame_mover_camera, text="X-", width=3,
                  command=lambda: self._mover_camera(-passo_camera, 0, 0)).grid(row=0, column=1)
        tk.Button(frame_mover_camera, text="Y+", width=3,
                  command=lambda: self._mover_camera(0, passo_camera, 0)).grid(row=0, column=2)
        tk.Button(frame_mover_camera, text="Y-", width=3,
                  command=lambda: self._mover_camera(0, -passo_camera, 0)).grid(row=0, column=3)
        tk.Button(frame_mover_camera, text="Z+", width=3,
                  command=lambda: self._mover_camera(0, 0, passo_camera)).grid(row=1, column=0)
        tk.Button(frame_mover_camera, text="Z-", width=3,
                  command=lambda: self._mover_camera(0, 0, -passo_camera)).grid(row=1, column=1)

        tk.Label(painel, text="Girar câmera (rotacionar VPN)").pack(anchor="w", pady=(10, 0))
        frame_girar_camera = tk.Frame(painel)
        frame_girar_camera.pack()
        passo_graus = 15
        tk.Button(frame_girar_camera, text="X+", width=3,
                  command=lambda: self._girar_camera("x", passo_graus)).grid(row=0, column=0)
        tk.Button(frame_girar_camera, text="X-", width=3,
                  command=lambda: self._girar_camera("x", -passo_graus)).grid(row=0, column=1)
        tk.Button(frame_girar_camera, text="Y+", width=3,
                  command=lambda: self._girar_camera("y", passo_graus)).grid(row=0, column=2)
        tk.Button(frame_girar_camera, text="Y-", width=3,
                  command=lambda: self._girar_camera("y", -passo_graus)).grid(row=0, column=3)
        tk.Button(frame_girar_camera, text="Z+", width=3,
                  command=lambda: self._girar_camera("z", passo_graus)).grid(row=1, column=0)
        tk.Button(frame_girar_camera, text="Z-", width=3,
                  command=lambda: self._girar_camera("z", -passo_graus)).grid(row=1, column=1)

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
        if tipo == "curva" and (len(coordenadas) < 4 or (len(coordenadas) - 1) % 3 != 0):
            messagebox.showerror(
                "Erro",
                "Uma curva precisa de 3n+1 pontos (4 para 1 segmento, 7 para 2, 10 para 3...).",
            )
            return
        if tipo == "bspline" and len(coordenadas) < 4:
            messagebox.showerror(
                "Erro",
                "Uma B-spline precisa de pelo menos 4 pontos de controle.",
            )
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

    @staticmethod
    def _parsear_coordenadas_3d(texto):
        """Igual ao parser 2D, só que exigindo 3 números por ponto
        em vez de 2 -- usado para os vértices dos objetos 3D."""
        tupla_de_pontos = ast.literal_eval(texto)
        if isinstance(tupla_de_pontos[0], (int, float)):
            tupla_de_pontos = (tupla_de_pontos,)
        return [Ponto3D(float(x), float(y), float(z)) for x, y, z in tupla_de_pontos]

    def _abrir_janela_transformacao(self):
        selecionado = self.lista_objetos.curselection()
        if not selecionado:
            messagebox.showerror("Erro", "Selecione um objeto 2D na lista primeiro.")
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

    # ---- Ações do usuário: objetos 3D ----
    def _adicionar_objeto_3d(self):
        nome = self.entrada_nome_3d.get().strip()
        texto_coordenadas = self.entrada_coordenadas_3d.get().strip()

        if not nome:
            messagebox.showerror("Erro", "Informe um nome para o objeto 3D.")
            return

        try:
            vertices = self._parsear_coordenadas_3d(texto_coordenadas)
        except (ValueError, SyntaxError):
            messagebox.showerror(
                "Erro",
                "Coordenadas inválidas.\nUse o formato: (x1,y1,z1),(x2,y2,z2),...",
            )
            return

        if len(vertices) < 2:
            messagebox.showerror("Erro", "Um objeto 3D precisa de pelo menos 2 vértices.")
            return

        objeto3d = Objeto3D(nome, vertices, cor=self.cor_selecionada)
        self.objetos_3d.append(objeto3d)
        self.entrada_nome_3d.delete(0, tk.END)
        self.entrada_coordenadas_3d.delete(0, tk.END)
        self._redesenhar()

    def _abrir_janela_transformacao_3d(self):
        selecionado = self.lista_objetos_3d.curselection()
        if not selecionado:
            messagebox.showerror("Erro", "Selecione um objeto 3D na lista primeiro.")
            return
        objeto3d = self.objetos_3d[selecionado[0]]
        JanelaTransformacao3D(self.raiz, objeto3d, ao_aplicar=self._redesenhar)

    def _definir_camera(self):
        try:
            vrp = tuple(float(v) for v in self.entrada_vrp.get().split(","))
            vpn = tuple(float(v) for v in self.entrada_vpn.get().split(","))
            if len(vrp) != 3 or len(vpn) != 3:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Use o formato x,y,z para VRP e VPN (ex: 0,0,-100).")
            return

        self.vrp = vrp
        self.vpn = vpn
        self._redesenhar()

    def _usar_primeiro_vertice_como_vrp(self):
        """Atalho citado no próprio enunciado: 'o primeiro ponto pode
        ser o VRP' -- usa o 1º vértice do objeto 3D selecionado como
        a posição da câmera."""
        selecionado = self.lista_objetos_3d.curselection()
        if not selecionado:
            messagebox.showerror("Erro", "Selecione um objeto 3D na lista primeiro.")
            return
        objeto3d = self.objetos_3d[selecionado[0]]
        primeiro_ponto = objeto3d.arestas[0][0]
        self.vrp = primeiro_ponto.como_tupla()
        self._redesenhar()

    def _mover_camera(self, dx, dy, dz):
        """Navegação da window no espaço 3D: reposiciona o observador
        (translada o VRP), mantendo a direção para onde ele olha
        (VPN) -- equivalente a arrastar a câmera no Blender."""
        self.vrp = (self.vrp[0] + dx, self.vrp[1] + dy, self.vrp[2] + dz)
        self._redesenhar()

    def _girar_camera(self, eixo, graus):
        """Navegação da window no espaço 3D: gira a direção para onde
        o observador olha (VPN) em torno de um dos eixos do mundo --
        equivalente a orbitar a câmera (mudar o ângulo de visão) sem
        mudar de onde ela está olhando."""
        matriz = {"x": matriz_rotacao_x, "y": matriz_rotacao_y, "z": matriz_rotacao_z}[eixo](graus)
        # VPN é uma DIREÇÃO, não um ponto -- mas como essas matrizes de
        # rotação em torno dos eixos do mundo não têm componente de
        # translação, aplicá-las com aplicar_matriz4_no_ponto rotaciona
        # o vetor corretamente, sem deslocá-lo.
        self.vpn = aplicar_matriz4_no_ponto(matriz, self.vpn)
        self._redesenhar()

    # Desenho
    def _redesenhar(self):
        self.canvas.delete("all")
        self.lista_objetos.delete(0, tk.END)
        self.lista_objetos_3d.delete(0, tk.END)
        self.label_angulo_atual.config(text=f"Ângulo atual: {self.window.angulo % 360:.1f}°")
        # Arredonda pra exibição -- o valor de verdade (self.vrp/self.vpn,
        # usado nos cálculos) continua com a precisão cheia; isso é só
        # pra não deixar o texto gigantesco de casas decimais quebrar
        # o layout do painel.
        vrp_arredondado = tuple(round(v, 3) for v in self.vrp)
        vpn_arredondado = tuple(round(v, 3) for v in self.vpn)
        self.label_camera_atual.config(text=f"VRP={vrp_arredondado}\nVPN={vpn_arredondado}")

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

            elif objeto.tipo == "curva":
                # gera a curva (já em coordenadas locais, a partir dos
                # pontos de controle transformados) como uma sequência
                # de pontos -- ou seja, uma polilinha
                pontos_curva = gerar_curva_bezier_composta(pontos_locais, passos_por_segmento=20)

                # clipa cada pequeno segmento da polilinha com a MESMA
                # técnica de clip de reta já usada para objetos "reta"
                # -- é assim que o material da disciplina recomenda:
                # recorte de curva = recorte de linha aplicado durante
                # o desenho da curva, já que ela é um modelo de arame
                for i in range(len(pontos_curva) - 1):
                    p1, p2 = pontos_curva[i], pontos_curva[i + 1]
                    if usar_liang_barsky:
                        resultado = clipar_reta_liang_barsky(p1, p2, xmin, xmax, ymin, ymax)
                    else:
                        resultado = clipar_reta_cohen_sutherland(p1, p2, xmin, xmax, ymin, ymax)

                    if resultado is not None:
                        p1_tela = self.viewport.local_para_tela(resultado[0], self.window)
                        p2_tela = self.viewport.local_para_tela(resultado[1], self.window)
                        self._desenhar_linha(p1_tela, p2_tela, objeto.cor)

            elif objeto.tipo == "bspline":
                # gera a B-spline (já em coordenadas locais, a partir dos
                # pontos de controle transformados) como uma sequência
                # de pontos -- ou seja, uma polilinha
                pontos_curva = gerar_bspline(pontos_locais, passos_por_segmento=20)

                # clipa cada pequeno segmento da polilinha com a MESMA
                # técnica de clip de reta já usada para objetos "reta"
                # -- é assim que o material da disciplina recomenda:
                # recorte de bspline = recorte de linha aplicado durante
                # o desenho da bspline, já que ela é um modelo de arame
                for i in range(len(pontos_curva) - 1):
                    p1, p2 = pontos_curva[i], pontos_curva[i + 1]
                    if usar_liang_barsky:
                        resultado = clipar_reta_liang_barsky(p1, p2, xmin, xmax, ymin, ymax)
                    else:
                        resultado = clipar_reta_cohen_sutherland(p1, p2, xmin, xmax, ymin, ymax)

                    if resultado is not None:
                        p1_tela = self.viewport.local_para_tela(resultado[0], self.window)
                        p2_tela = self.viewport.local_para_tela(resultado[1], self.window)
                        self._desenhar_linha(p1_tela, p2_tela, objeto.cor)

        # ---- Objetos 3D: projeção paralela ortogonal (Trabalho 1.7) ----
        for objeto3d in self.objetos_3d:
            self.lista_objetos_3d.insert(tk.END, repr(objeto3d))

            for p1_3d, p2_3d in objeto3d.arestas:
                # passos 1-4 do algoritmo: SRU -> SRC e descarta o Z
                p1_2d = projetar_paralela_ortogonal(p1_3d, self.vrp, self.vpn)
                p2_2d = projetar_paralela_ortogonal(p2_3d, self.vrp, self.vpn)

                # passos 5-7: a partir daqui é um ponto 2D comum --
                # reaproveita window/clipping/viewport já prontos
                p1_local = self.window.mundo_para_local(p1_2d)
                p2_local = self.window.mundo_para_local(p2_2d)

                if usar_liang_barsky:
                    resultado = clipar_reta_liang_barsky(p1_local, p2_local, xmin, xmax, ymin, ymax)
                else:
                    resultado = clipar_reta_cohen_sutherland(p1_local, p2_local, xmin, xmax, ymin, ymax)

                if resultado is not None:
                    p1_tela = self.viewport.local_para_tela(resultado[0], self.window)
                    p2_tela = self.viewport.local_para_tela(resultado[1], self.window)
                    self._desenhar_linha(p1_tela, p2_tela, objeto3d.cor)

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