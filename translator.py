import tkinter as tk
from PIL import ImageGrab, Image, ImageEnhance, ImageFilter, ImageTk
import pytesseract
from deep_translator import GoogleTranslator
import keyboard
import datetime
import threading

# Caminho do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Variáveis globais
start_x = start_y = end_x = end_y = 0
texto_original_linhas = []
texto_traduzido_linhas = []
caixas_linha = []
imagem_colorida_global = None
offset_x_global = offset_y_global = 0
canvas_ref = None
modo_traducao = True
imagem_tk_global = None
janela_traducao = None


def iniciar_selecao():
    selecao_win = tk.Toplevel(root)
    selecao_win.attributes("-alpha", 0.3)
    selecao_win.attributes("-fullscreen", True)
    selecao_win.attributes("-topmost", True)
    selecao_win.config(cursor="cross")

    canvas = tk.Canvas(selecao_win, cursor="cross", bg="gray")
    canvas.pack(fill=tk.BOTH, expand=True)

    def registrar_inicio(event):
        global start_x, start_y
        start_x = selecao_win.winfo_pointerx()
        start_y = selecao_win.winfo_pointery()
        canvas.delete("selecionado")

    def atualizar_selecao(event):
        atual_x = selecao_win.winfo_pointerx()
        atual_y = selecao_win.winfo_pointery()
        canvas.delete("selecionado")
        canvas.create_rectangle(start_x, start_y, atual_x, atual_y, outline='red', width=2, tag="selecionado")

    def finalizar_selecao(event):
        global end_x, end_y
        end_x = selecao_win.winfo_pointerx()
        end_y = selecao_win.winfo_pointery()
        selecao_win.destroy()
        processar_imagem()

    canvas.bind("<Button-1>", registrar_inicio)
    canvas.bind("<B1-Motion>", atualizar_selecao)
    canvas.bind("<ButtonRelease-1>", finalizar_selecao)


def processar_imagem():
    global texto_original_linhas, texto_traduzido_linhas, caixas_linha
    global imagem_colorida_global, offset_x_global, offset_y_global

    x1, y1 = min(start_x, end_x), min(start_y, end_y)
    x2, y2 = max(start_x, end_x), max(start_y, end_y)

    offset_x_global, offset_y_global = x1, y1
    imagem_colorida_global = ImageGrab.grab(bbox=(x1, y1, x2, y2)).convert("RGB")
    imagem = imagem_colorida_global.convert("L")
    imagem = imagem.filter(ImageFilter.SHARPEN)
    imagem = ImageEnhance.Contrast(imagem).enhance(2.0)

    print(texto_original_linhas)

    dados = pytesseract.image_to_data(imagem, lang='por', output_type=pytesseract.Output.DICT)

    linhas = {}
    for i in range(len(dados['text'])):
        texto = dados['text'][i].strip()
        if texto:
            chave = (dados['block_num'][i], dados['par_num'][i], dados['line_num'][i])
            if chave not in linhas:
                linhas[chave] = {'textos': [], 'coords': []}
            linhas[chave]['textos'].append(texto)
            linhas[chave]['coords'].append((dados['left'][i], dados['top'][i], dados['width'][i], dados['height'][i]))

    texto_original_linhas.clear()
    caixas_linha.clear()
    for linha in linhas.values():
        texto_linha = " ".join(linha['textos'])
        texto_original_linhas.append(texto_linha)

        xs = [c[0] for c in linha['coords']]
        ys = [c[1] for c in linha['coords']]
        ws = [c[2] for c in linha['coords']]
        hs = [c[3] for c in linha['coords']]
        x_min = min(xs)
        y_min = min(ys)
        x_max = max([xs[i] + ws[i] for i in range(len(ws))])
        y_max = max([ys[i] + hs[i] for i in range(len(hs))])
        caixas_linha.append((x_min, y_min, x_max, y_max))

    tradutor = GoogleTranslator(source='auto', target='pt')
    texto_traduzido_linhas.clear()
    for texto in texto_original_linhas:
        try:
            texto_traduzido_linhas.append(tradutor.translate(texto))
        except:
            texto_traduzido_linhas.append("[erro]")

    salvar_em_arquivo(texto_original_linhas, texto_traduzido_linhas)
    exibir_interface()


def salvar_em_arquivo(originais, traduzidos):
    agora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"texto_original_{agora}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(originais))
    with open(f"texto_traduzido_{agora}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(traduzidos))


def exibir_interface():
    global canvas_ref, imagem_tk_global, janela_traducao

    if janela_traducao is not None:
        try:
            janela_traducao.destroy()
        except:
            pass

    x_min = min(c[0] for c in caixas_linha)
    y_min = min(c[1] for c in caixas_linha)
    x_max = max(c[2] for c in caixas_linha)
    y_max = max(c[3] for c in caixas_linha)

    largura = x_max - x_min
    altura = y_max - y_min

    imagem_blur = imagem_colorida_global.copy()
    for caixa in caixas_linha:
        x1, y1, x2, y2 = caixa
        region = imagem_blur.crop((x1, y1, x2, y2)).filter(ImageFilter.GaussianBlur(radius=4))
        imagem_blur.paste(region, (x1, y1))

    imagem_cortada = imagem_blur.crop((x_min, y_min, x_max, y_max))

    janela_traducao = tk.Toplevel(root)
    janela_traducao.attributes("-topmost", True)
    janela_traducao.attributes("-transparentcolor", "white")
    janela_traducao.overrideredirect(True)
    janela_traducao.config(bg="white")
    janela_traducao.geometry(f"{largura}x{altura}+{offset_x_global + x_min}+{offset_y_global + y_min}")

    canvas = tk.Canvas(janela_traducao, width=largura, height=altura, bg="white", highlightthickness=0)
    canvas.pack()
    canvas_ref = canvas

    imagem_tk_global = ImageTk.PhotoImage(imagem_cortada)
    canvas.create_image(0, 0, anchor="nw", image=imagem_tk_global)

    desenhar_texto(canvas)
    canvas.bind("<Button-1>", alternar_texto)


def desenhar_texto(canvas):
    import tkinter.font as tkFont
    canvas.delete("textos")

    textos = texto_traduzido_linhas if modo_traducao else texto_original_linhas

    for i, texto in enumerate(textos):
        x1, y1, x2, y2 = caixas_linha[i]
        largura_caixa = x2 - x1
        altura_caixa = y2 - y1
        x_rel = x1 - min(c[0] for c in caixas_linha)
        y_rel = y1 - min(c[1] for c in caixas_linha)

        tamanho_fonte = 14
        fonte = tkFont.Font(family="Arial", size=tamanho_fonte, weight="bold")

        while True:
            palavras = texto.split()
            linhas = []
            linha = ""
            for palavra in palavras:
                teste = linha + (" " if linha else "") + palavra
                if fonte.measure(teste) > largura_caixa:
                    linhas.append(linha)
                    linha = palavra
                else:
                    linha = teste
            if linha:
                linhas.append(linha)

            altura_total = fonte.metrics("linespace") * len(linhas)
            if altura_total <= altura_caixa or tamanho_fonte <= 8:
                break

            tamanho_fonte -= 1
            fonte = tkFont.Font(family="Arial", size=tamanho_fonte, weight="bold")

        canvas.create_text(
            x_rel, y_rel,
            text=texto,
            anchor="nw",
            fill="black",
            font=fonte,
            width=largura_caixa,
            tags="textos"
        )


def alternar_texto(event):
    global modo_traducao
    modo_traducao = not modo_traducao
    desenhar_texto(canvas_ref)


def executar_selecao_thread():
    t = threading.Thread(target=iniciar_selecao, daemon=True)
    t.start()


def reiniciar_traducao():
    global modo_traducao
    modo_traducao = True
    executar_selecao_thread()


def fechar_traducao():
    global janela_traducao
    if janela_traducao is not None:
        try:
            janela_traducao.destroy()
            janela_traducao = None
            print("🛑 Tradução oculta.")
        except:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    executar_selecao_thread()

    keyboard.add_hotkey('ctrl+shift+m', reiniciar_traducao)
    keyboard.add_hotkey('ctrl+shift+x', fechar_traducao)

    print("🖱️ Pressione Ctrl+Shift+M para capturar e traduzir texto da tela.")
    print("🛑 Pressione Ctrl+Shift+X para ocultar a tradução da tela.")

    root.mainloop()
