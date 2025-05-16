import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import kagglehub
from kagglehub import KaggleDatasetAdapter
import json
import sys

# Grafo y estructuras globales
G = nx.DiGraph()
nodo_index = {}
ultimo_bfs_result = []

def cargar_datos_y_grafo():
    global G, nodo_index
    G.clear()
    nodo_index.clear()

    file_path = "multilevel_causality_deaths.csv"
    df = kagglehub.load_dataset(
        KaggleDatasetAdapter.PANDAS,
        "cedricschicklin/multilevel-causality-relations-deaths-age-sex",
        file_path,
    )

    df.columns = df.columns.str.strip()
    sexos = ['male', 'female']
    edades = {
        '<=4yo': '=<_4yo',
        '5-64yo': '>=5yo,_<=64yo',
        '>=65yo': '>=_65'
    }
    pais = 'FRANCE'
    anios = df['total_deaths_source_year_FRANCE'].dropna().unique().astype(int)

    for index, row in df.iterrows():
        causa = row['concept_id'].strip().lower()
        for sexo in sexos:
            for edad_desc, edad_col in edades.items():
                col_base = f"{sexo}_yr_deaths_{edad_col}_{pais}"
                if col_base in df.columns and not pd.isna(row[col_base]):
                    for anio in anios:
                        nodo = f"{causa} - {sexo} - {edad_desc} - {pais} - {anio}"
                        G.add_node(nodo)
                        if causa not in nodo_index:
                            nodo_index[causa] = []
                        nodo_index[causa].append(nodo)

    for index, row in df.iterrows():
        origen = row['concept_id'].strip().lower()
        if pd.isna(row['successor_array']):
            continue
        try:
            sucesores_json = json.loads(row['successor_array'].replace("'", '"'))
        except json.JSONDecodeError:
            continue
        for s in sucesores_json:
            sucesor = s.get("successor_id", "").strip().lower()
            if origen in nodo_index and sucesor in nodo_index:
                for nodo_o in nodo_index[origen]:
                    for nodo_s in nodo_index[sucesor]:
                        o_attrs = nodo_o.split(" - ")[1:4]
                        s_attrs = nodo_s.split(" - ")[1:4]
                        if o_attrs == s_attrs:
                            G.add_edge(nodo_o, nodo_s)

def salir_completo():
    sys.exit()

def show_welcome_screen():
    root = tk.Tk()
    root.title("Sistema de Estadísticas de Mortalidad")
    root.geometry("500x200")
    tk.Label(root, text="Bienvenido al Sistema de Estadísticas de Mortalidad", font=("Arial", 14)).pack(pady=30)
    tk.Button(root, text="Continuar", bg="#FFA500", fg="white", font=("Arial", 12),
              command=lambda: [root.destroy(), show_main_menu()]).pack()
    root.mainloop()

def show_main_menu():
    menu = tk.Tk()
    menu.title("Menú Principal")
    menu.geometry("400x300")
    tk.Label(menu, text="Menú Principal", font=("Arial", 14)).pack(pady=10)
    tk.Button(menu, text="Buscar Relaciones (BFS)", bg="#2196F3", fg="white", font=("Arial", 12),
              command=lambda: [menu.destroy(), show_bfs_screen()]).pack(pady=10)
    tk.Button(menu, text="Ver Gráfico del Último BFS", bg="#9C27B0", fg="white", font=("Arial", 12),
              command=lambda: [menu.destroy(), show_graph_screen()]).pack(pady=10)
    tk.Button(menu, text="Salir", bg="#f44336", fg="white", font=("Arial", 12),
              command=salir_completo).pack(pady=10)
    menu.mainloop()

def show_graph_screen():
    global ultimo_bfs_result
    if not ultimo_bfs_result:
        messagebox.showinfo("Info", "Primero ejecuta un BFS.")
        return
    window = tk.Tk()
    window.title("Subgrafo del último BFS")
    window.geometry("1000x700")

    sub = G.subgraph(ultimo_bfs_result)

    # Mostrar causa, sexo, país y año
    sub_abreviado = nx.relabel_nodes(
        sub,
        lambda n: f"{n.split(' - ')[0]} ({n.split(' - ')[1]}, {n.split(' - ')[3]}, {n.split(' - ')[4]})"
    )
    pos = nx.spring_layout(sub_abreviado, seed=42)

    fig, ax = plt.subplots(figsize=(12, 9))
    nx.draw(sub_abreviado, pos, with_labels=True, node_size=700, font_size=8, arrows=True, ax=ax)
    plt.title("Subgrafo generado por relaciones directas")
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    tk.Button(window, text="⬅ Volver al Menú", bg="#FFA500", fg="white", font=("Arial", 10),
              command=lambda: [window.destroy(), show_main_menu()]).pack(pady=10)

def show_bfs_screen():
    bfs_window = tk.Tk()
    bfs_window.title("Búsqueda en Anchura (Relaciones Directas)")
    bfs_window.geometry("450x300")
    tk.Label(bfs_window, text="Selecciona una causa de muerte:", font=("Arial", 11)).pack(pady=10)
    causas = list(nodo_index.keys())[:50]
    combo = ttk.Combobox(bfs_window, values=causas, font=("Arial", 10))
    combo.pack()

    def ejecutar_bfs():
        global ultimo_bfs_result
        causa = combo.get().strip().lower()
        if causa not in nodo_index:
            messagebox.showerror("Error", "Selecciona una causa válida.")
            return

        nodo_inicio = nodo_index[causa][0]
        bfs_result = [nodo_inicio] + list(G.successors(nodo_inicio))
        ultimo_bfs_result = bfs_result

        result_window = tk.Tk()
        result_window.title("Resultado de Relaciones Directas")
        result_window.geometry("800x500")
        tk.Label(result_window, text=f"Relaciones directas desde '{causa}':", font=("Arial", 12)).pack()
        text = tk.Text(result_window, wrap=tk.WORD, height=20, width=90, font=("Courier", 9))
        text.insert(tk.END, f"{'Causa':30} {'Sexo':8} {'Edad':10} {'País':8} {'Año':6}\n")
        text.insert(tk.END, "-"*70 + "\n")
        for nodo in bfs_result:
            partes = nodo.split(" - ")
            if len(partes) == 5:
                causa_n, sexo, edad, pais, anio = partes
                text.insert(tk.END, f"{causa_n[:28]:30} {sexo:8} {edad:10} {pais:8} {anio:6}\n")
        text.pack()

        tk.Button(result_window, text="⬅ Volver al Menú", bg="#FFA500", fg="white", font=("Arial", 10),
                  command=lambda: [result_window.destroy(), show_main_menu()]).pack(pady=10)

    tk.Button(bfs_window, text="Ejecutar BFS", bg="#FFA500", fg="white", font=("Arial", 12),
              command=ejecutar_bfs).pack(pady=20)
    tk.Button(bfs_window, text="⬅ Volver al Menú", bg="#FFA500", fg="white", font=("Arial", 10),
              command=lambda: [bfs_window.destroy(), show_main_menu()]).pack(pady=5)

# Entry point
if __name__ == "__main__":
    cargar_datos_y_grafo()
    print("✅ NODOS:", G.number_of_nodes())
    print("✅ ARISTAS:", G.number_of_edges())
    show_welcome_screen()
