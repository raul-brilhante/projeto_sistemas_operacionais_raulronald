import tkinter as tk
from tkinter import messagebox
from threading import Thread, Semaphore, Lock, Event
import time
import math

# Variáveis globais
tv_semaphore = Semaphore(1)  # Semáforo binário para garantir exclusividade ao trocar de canal
assistindo_mutex = Semaphore(1)
canal_atual_mutex = Semaphore (1)
canal_atual = None
assistindo_count = 0
quantidade_canais = 0  # Armazenar a quantidade de canais informada

# Lista para armazenar os hóspedes
hospedes = []
hospede_ids = set()  # Conjunto para armazenar IDs únicos dos hóspedes


class Hospede(Thread):
    def __init__(self, id_hospede, nome, canal_favorito, ttv, td, log, canvas, x, y):
        super().__init__()
        self.id_hospede = id_hospede
        self.nome = nome
        self.canal_favorito = int(canal_favorito)
        self.ttv = int(ttv)
        self.td = int(td)
        self.log = log
        self.canvas = canvas
        self.x = x
        self.y = y
        self.estado = "Descansando"
        self.running = True
        self.block_event = Event()  # Evento para bloquear/desbloquear a thread

        # Desenhar a bolinha e os textos de identificação
        self.bolinha = self.canvas.create_oval(x, y, x + 30, y + 30, fill="red", tags=self.nome)
        self.label_id = self.canvas.create_text(x + 15, y - 20, text=f"Hóspede: {self.id_hospede}\nCanal: {self.canal_favorito}", font=("Arial", 8))
        self.label_tempo = self.canvas.create_text(x + 15, y + 50, text="", font=("Arial", 8))

    def log_event(self, message):
        self.log.insert(tk.END, message)
        self.log.yview(tk.END)

    def update_bolinha(self, color):
        self.canvas.itemconfig(self.bolinha, fill=color)

    def update_tempo(self, tempo, acao):
        if acao == "Bloqueado":
            self.canvas.itemconfig(self.label_tempo, text=f"{acao}")
        else:
            self.canvas.itemconfig(self.label_tempo, text=f"{acao}: {tempo}s")

    def piscar(self, cores, tempo_total):
        tempo_inicial = time.perf_counter()
        tempo_decorrido = 0  # Inicializa o tempo decorrido

        while tempo_decorrido < tempo_total:
            tempo_decorrido = time.perf_counter() - tempo_inicial
            self.update_tempo(tempo_total - int(tempo_decorrido), self.estado)

            # Ajusta o número de iterações com base no tempo decorrido
            # O número de iterações será proporcional ao tempo decorrido (mas com um máximo)
            iterations = min(30000, int(tempo_decorrido * 30000))  # Ajuste dinâmico
            # Simula um cálculo pesado a cada iteração
            for i in range(iterations):  # Realizando um cálculo pesado para aumentar o uso de CPU
                _ = math.sqrt(i)

            cor_atual = cores[int(tempo_decorrido) % 2]
            self.update_bolinha(cor_atual)

    def run(self):
        global canal_atual, assistindo_count

        while self.running:
            # Descansando
            self.estado = "Descansando"
            self.log_event(f"{self.nome} está descansando.")
            self.piscar(["red", "white"], self.td)
            assistindo = False

            # Tentando assistir TV
            while not assistindo:
                canal_atual_mutex.acquire()
                if canal_atual is None or canal_atual == self.canal_favorito:
                    if canal_atual is None:
                        tv_semaphore.acquire()  # Adquire exclusividade para trocar de canal
                        canal_atual = self.canal_favorito
                        canal_atual_mutex.release()
                        update_tv_display(canal_atual)
                    else:
                        canal_atual_mutex.release()
                    assistindo_mutex.acquire()
                    assistindo_count += 1
                    assistindo_mutex.release()
                    assistindo = True 

            # Se a TV está ocupada com outro canal, ele fica bloqueado
                else:
                    canal_atual_mutex.release() 
                    if self.estado != "Bloqueado":
                        self.estado = "Bloqueado"
                        self.log_event(f"{self.nome} está bloqueado aguardando a TV ficar disponível.")
                        self.update_tempo(0.001, self.estado)  # Atualiza para mostrar "Bloqueado: 0s"
                        self.update_bolinha("gray")  # Atualiza a bolinha para cinza
                        tv_semaphore.acquire()
                        tv_semaphore.release()                       

                # Aguarda até ser notificado ou até o tempo limite
                self.block_event.wait(timeout=0.1)

            # Assistindo TV
            self.estado = "Assistindo"
            self.log_event(f"{self.nome} está assistindo ao canal {self.canal_favorito}.")
            self.piscar(["green", "white"], self.ttv)

            # Finalizando a sessão de assistir TV
            
            assistindo_mutex.acquire()
            assistindo_count -= 1

            if assistindo_count == 0:
                assistindo_mutex.release()
                canal_atual_mutex.acquire()
                canal_atual = None
                canal_atual_mutex.release()
                tv_semaphore.release()  # Libera exclusividade após trocar o canal
                update_tv_display("Nenhum")

            else:
                assistindo_mutex.release()


    def stop(self):
        self.running = False
        self.block_event.set()  # Desbloqueia a thread caso esteja aguardando


def configurar_canais():
    global quantidade_canais

    quantidade = entry_quantidade_canais.get()
    if not quantidade.isdigit() or int(quantidade) <= 0:
        messagebox.showerror("Erro", "Por favor, insira um número válido de canais.")
        return

    quantidade_canais = int(quantidade)

    # Fecha a janela de configuração e abre a janela principal
    janela_config.destroy()
    janela_principal()


def criar_hospede():
    global hospede_ids

    # Obter valores das entradas
    id_hospede = entry_id.get()
    nome = f"Hóspede {id_hospede}"
    canal_favorito = entry_canal.get()
    ttv = entry_ttv.get()
    td = entry_td.get()

    # Verificar se os valores são válidos
    if not (id_hospede.isdigit() and canal_favorito.isdigit() and ttv.isdigit() and td.isdigit()):
        log.insert(tk.END, "Erro: Insira valores numéricos válidos.")
        return

    if id_hospede in hospede_ids:
        log.insert(tk.END, f"Erro: O ID {id_hospede} já está em uso.")
        return

    canal_favorito = int(canal_favorito)
    if not (1 <= canal_favorito <= quantidade_canais):
        log.insert(tk.END, f"Erro: O canal favorito deve estar entre 1 e {quantidade_canais}.")
        return

    hospede_ids.add(id_hospede)

    # Criar instância de hóspede
    x_pos = 50 + (len(hospedes) % 5) * 100
    y_pos = 150 + (len(hospedes) // 5) * 100
    hospede = Hospede(id_hospede, nome, canal_favorito, int(ttv), int(td), log, canvas, x_pos, y_pos)
    hospedes.append(hospede)

    # Iniciar a thread
    hospede.start()
    log.insert(tk.END, f"{nome} foi criado com Canal Favorito {canal_favorito}, Ttv={ttv}s, Td={td}s.")
    log.yview(tk.END)


def fechar_aplicacao():
    for hospede in hospedes:
        hospede.stop()
    root.destroy()


def update_tv_display(canal):
    tv_canvas.itemconfig(tv_display, text=f"Canal: {canal}")


# Tela de configuração inicial
janela_config = tk.Tk()
janela_config.title("Configurar Quantidade de Canais")

tk.Label(janela_config, text="Informe a quantidade de canais:").pack(pady=10)
entry_quantidade_canais = tk.Entry(janela_config, width=5)
entry_quantidade_canais.pack(pady=5)

btn_confirmar = tk.Button(janela_config, text="Confirmar", command=configurar_canais)
btn_confirmar.pack(pady=10)

janela_config.mainloop()


# Janela principal
def janela_principal():
    global root, canvas, log, entry_id, entry_canal, entry_ttv, entry_td, tv_canvas, tv_display

    root = tk.Tk()
    root.title("Gerenciamento de Hóspedes na TV")

    # Layout principal
    frame_principal = tk.Frame(root)
    frame_principal.pack(padx=10, pady=10)

    # Frame esquerdo
    frame_esquerdo = tk.Frame(frame_principal)
    frame_esquerdo.pack(side=tk.LEFT)

    # Entrada para ID do Hóspede
    tk.Label(frame_esquerdo, text="ID do Hóspede:").pack()
    entry_id = tk.Entry(frame_esquerdo, width=5)
    entry_id.pack()

    # Entrada para Canal Favorito
    tk.Label(frame_esquerdo, text="Canal Favorito:").pack()
    entry_canal = tk.Entry(frame_esquerdo, width=5)
    entry_canal.pack()

    # Entrada para Ttv
    tk.Label(frame_esquerdo, text="Tempo Assistindo (Ttv):").pack()
    entry_ttv = tk.Entry(frame_esquerdo, width=5)
    entry_ttv.pack()

    # Entrada para Td
    tk.Label(frame_esquerdo, text="Tempo Descansando (Td):").pack()
    entry_td = tk.Entry(frame_esquerdo, width=5)
    entry_td.pack()

    # Botão para criar hóspedes
    btn_criar = tk.Button(frame_esquerdo, text="Criar Hóspede", command=criar_hospede)
    btn_criar.pack(pady=10)

    # Canvas para mostrar hóspedes
    canvas = tk.Canvas(frame_esquerdo, width=600, height=400, bg="white")
    canvas.pack(pady=20)

    # Canvas para a TV
    tv_canvas = tk.Canvas(frame_esquerdo, width=200, height=100, bg="lightblue")
    tv_canvas.pack(pady=10)
    tv_display = tv_canvas.create_text(100, 50, text="Canal: Nenhum", font=("Arial", 12))

    # Frame direito para o LOG
    frame_direito = tk.Frame(frame_principal)
    frame_direito.pack(side=tk.RIGHT, padx=10)

    # Log de eventos
    tk.Label(frame_direito, text="Log de Eventos").pack()
    log = tk.Listbox(frame_direito, width=50, height=30)
    log.pack()

    # Botão para sair
    btn_sair = tk.Button(root, text="Sair", command=fechar_aplicacao)
    btn_sair.pack(pady=10)

    root.protocol("WM_DELETE_WINDOW", fechar_aplicacao)
    root.mainloop()


janela_principal()
