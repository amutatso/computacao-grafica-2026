import ast
import math
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox


# DISPLAY FILE
# O Display File é a lista de todos os objetos gráficos que
# existem no mundo. Cada objeto tem nome, tipo (ponto, reta ou
# wireframe), coordenadas (em coordenadas do MUNDO, sempre) e a
# cor usada para desenhar as linhas.


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

    def limpar(self):
        self.objetos = []


# WINDOW
#
# A Window é descrita pelo seu centro, sua largura/altura e um
# ÂNGULO de rotação em relação ao mundo. Isso substitui a antiga
# representação por xmin/xmax/ymin/ymax: uma window rotacionada
# não é mais um retângulo alinhado aos eixos do mundo, então min/
# max deixam de fazer sentido -- centro + tamanho + ângulo é a
# forma padrão de descrever isso (é o que os livros de CG chamam
# de Plano de Projeção / PPC quando aplicado aos objetos).

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
        """
        Panning: desloca o centro da window. dx_local/dy_local são
        deslocamentos no referencial da PRÓPRIA window (ou seja,
        "pra frente"/"pra cima" do ponto de vista de quem está
        navegando), não do mundo. Por isso, se a window estiver
        rotacionada, precisamos girar esse deslocamento pelo ângulo
        atual antes de somar às coordenadas do mundo.
        """
        rad = math.radians(self.angulo)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        self.centro_x += dx_local * cos_a - dy_local * sin_a
        self.centro_y += dx_local * sin_a + dy_local * cos_a

    def aplicar_zoom(self, fator):
        """
        Zooming: muda o tamanho da window mantendo o mesmo centro.
        fator < 1 -> aproxima (zoom in)
        fator > 1 -> afasta   (zoom out)
        Não depende do ângulo: encolher/esticar os dois lados por
        igual não muda de sentido só porque a window está rotacionada.
        """
        self.largura *= fator
        self.altura *= fator

    def rotacionar(self, delta_graus):
        """Gira a window em torno do seu próprio centro."""
        self.angulo += delta_graus

    def mundo_para_local(self, ponto_mundo):
        """
        Converte um ponto do MUNDO para o sistema de coordenadas da
        PRÓPRIA window: centralizado nela e alinhado com sua rotação
        (é o algoritmo de "Gerar Descrição" em PPC). Primeiro tira o
        centro da window do ponto, depois desfaz a rotação da window
        (gira por -ângulo). O resultado: quando a window gira num
        sentido, o mundo parece girar no sentido contrário.
        """
        x, y = ponto_mundo
        dx = x - self.centro_x
        dy = y - self.centro_y

        rad = -math.radians(self.angulo)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        lx = dx * cos_a - dy * sin_a
        ly = dx * sin_a + dy * cos_a
        return lx, ly


# VIEWPORT
#
# Converte um ponto do MUNDO (já passado pelo referencial local da
# window) para coordenadas de tela (pixels no canvas). Como o ponto
# chega centralizado em (0,0) e alinhado com a window, o mapeamento
# fica simétrico em torno do centro do canvas -- não precisamos mais
# saber "onde" a window está no mundo aqui, só o quanto ela mede.

class Viewport:
    def __init__(self, largura_tela, altura_tela, margem=20):
        self.largura_tela = largura_tela
        self.altura_tela = altura_tela
        self.margem = margem

    def transformar(self, ponto_mundo, window: Window):
        local_x, local_y = window.mundo_para_local(ponto_mundo)

        area_util_x = self.largura_tela - 2 * self.margem
        area_util_y = self.altura_tela - 2 * self.margem

        # Mesma escala nos dois eixos -> não distorce o objeto
        escala = min(area_util_x / window.largura, area_util_y / window.altura)

        centro_tela_x = self.margem + area_util_x / 2
        centro_tela_y = self.margem + area_util_y / 2

        x_tela = centro_tela_x + local_x * escala
        # Eixo Y da tela cresce para baixo -> por isso o sinal invertido
        y_tela = centro_tela_y - local_y * escala

        return x_tela, y_tela


# TRANSFORMAÇÕES 2D EM COORDENADAS HOMOGÊNEAS (herdadas do T1.2)
#
# Continuam operando inteiramente em coordenadas do MUNDO. Por isso
# a rotação da window não interfere nelas: transformar um objeto
# funciona exatamente igual, esteja a window rotacionada ou não --
# só o desenho final na tela é que muda.

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


# LEITURA E ESCRITA DE ARQUIVOS .OBJ (Wavefront)
#
# O formato OBJ numera vértices GLOBALMENTE (1, 2, 3, ... ao longo
# de todo o arquivo, não por objeto). O DescritorOBJ sabe transcrever
# UM objeto para linhas de texto .obj, desde que a gente informe em
# qual índice global os vértices dele começam.
#
# Guardamos tipo e cor como comentários (linhas com "#"), já que o
# formato OBJ puro não tem esses campos -- assim conseguimos
# recuperá-los na leitura sem perder informação.

class DescritorOBJ:
    def descrever(self, objeto, indice_inicial):
        """Devolve (linhas_de_texto, quantidade_de_vertices_usados)."""
        linhas = [
            f"o {objeto.nome}",
            f"# tipo {objeto.tipo}",
            f"# cor {objeto.cor}",
        ]
        for x, y in objeto.coordenadas:
            linhas.append(f"v {x} {y} 0.0")

        indices = list(range(indice_inicial, indice_inicial + len(objeto.coordenadas)))

        if objeto.tipo == "ponto":
            linhas.append(f"p {indices[0]}")
        elif objeto.tipo == "reta":
            linhas.append(f"l {indices[0]} {indices[1]}")
        elif objeto.tipo == "wireframe":
            # fecha o polígono citando o primeiro índice de novo no final
            sequencia = " ".join(str(i) for i in indices + [indices[0]])
            linhas.append(f"l {sequencia}")

        return linhas, len(objeto.coordenadas)


def salvar_mundo_obj(display_file, caminho):
    """Percorre o display file e escreve todo o mundo num único .obj."""
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
    """
    Lê um .obj (no formato escrito por salvar_mundo_obj) e devolve uma
    lista de tuplas (nome, tipo, coordenadas, cor), prontas para
    alimentar DisplayFile.adicionar.
    """
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
                atual = {"nome": linha[2:].strip(), "tipo": "wireframe", "cor": "#000000", "indices": []}

            elif linha.startswith("# tipo "):
                if atual is not None:
                    atual["tipo"] = linha[len("# tipo "):].strip()

            elif linha.startswith("# cor "):
                if atual is not None:
                    atual["cor"] = linha[len("# cor "):].strip()

            elif linha.startswith("v "):
                _, x, y, _z = linha.split()
                vertices_globais.append((float(x), float(y)))

            elif linha.startswith(("p ", "l ", "f ")):
                if atual is not None:
                    partes = linha.split()[1:]
                    atual["indices"] = [int(p) - 1 for p in partes]  # obj é 1-based

        if atual is not None:
            objetos_lidos.append(atual)

    resultado = []
    for info in objetos_lidos:
        indices = info["indices"]
        # wireframe foi salvo com o índice inicial repetido no final
        # para fechar o polígono -- removemos a repetição, já que o
        # desenho já fecha o polígono sozinho
        if info["tipo"] == "wireframe" and len(indices) > 1 and indices[0] == indices[-1]:
            indices = indices[:-1]
        coordenadas = [vertices_globais[i] for i in indices]
        resultado.append((info["nome"], info["tipo"], coordenadas, info["cor"]))

    return resultado


# JANELA DE TRANSFORMAÇÕES (herdada do T1.2)

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

        # As coordenadas digitadas aqui são sempre em coordenadas do
        # MUNDO, então não importa se a window está rotacionada ou
        # não nesse momento -- o objeto novo aparece na tela seguindo
        # a mesma rotação de todos os outros automaticamente.
        self.display_file.adicionar(nome, tipo, coordenadas, self.cor_selecionada)
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
        for nome, tipo, coordenadas, cor in objetos_lidos:
            self.display_file.adicionar(nome, tipo, coordenadas, cor)
        self._redesenhar()

    # Desenho
    def _redesenhar(self):
        self.canvas.delete("all")
        self.lista_objetos.delete(0, tk.END)
        self.label_angulo_atual.config(text=f"Ângulo atual: {self.window.angulo % 360:.1f}°")

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


if __name__ == "__main__":
    raiz = tk.Tk()
    app = Aplicacao(raiz)
    raiz.mainloop()
