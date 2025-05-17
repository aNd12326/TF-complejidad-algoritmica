# ... [IMPORTS Y CARGA DEL DATASET COMO YA TENÍAS] ...
import kagglehub
from kagglehub import KaggleDatasetAdapter
import pandas as pd
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import networkx as nx

file_path = "multilevel_causality_deaths.csv"
df = kagglehub.load_dataset(
    KaggleDatasetAdapter.PANDAS,
    "cedricschicklin/multilevel-causality-relations-deaths-age-sex",
    file_path,
)

# Limpiar ambos arrays
def limpiar_array(texto):
    if pd.isna(texto):
        return None
    try:
        limpio = texto.replace("'", '"')
        limpio = re.sub(r'}\s*{', '},{', limpio)
        limpio = limpio.replace('\xa0', ' ')
        return json.loads(limpio)
    except Exception:
        return None

df['successor_array_limpio'] = df['successor_array'].apply(limpiar_array)
df['predecessors_array_limpio'] = df['predecessors_array'].apply(limpiar_array)

def claves_validas(lista):
    if lista is None:
        return False
    for item in lista:
        if not isinstance(item, dict) or "successor_id" not in item:
            return False
    return True

def es_valido_predecesores(lista):
    if lista is None:
        return False
    for item in lista:
        if not isinstance(item, dict) or "predecessor_id" not in item:
            return False
    return True

df['estructura_valida'] = df['successor_array_limpio'].apply(claves_validas)
df['estructura_predecesores'] = df['predecessors_array_limpio'].apply(es_valido_predecesores)
df['total_yr_deaths_FRANCE'] = pd.to_numeric(df['total_yr_deaths_FRANCE'], errors='coerce').fillna(0)

# Grafo basado en successor_array
G = nx.DiGraph()
for _, row in df[df['estructura_valida']].iterrows():
    origen = row['concept_id']
    for rel in row['successor_array_limpio']:
        destino = rel['successor_id']
        impacto = rel.get('impact', 0.1)  # <- aquí está el cambio
        G.add_edge(origen, destino, weight=impacto)


print(f"🔢 Total de nodos en el grafo: {len(G.nodes)}")
print(f"🔗 Total de conexiones (aristas): {len(G.edges)}")

# Interfaz gráfica
ventana = tk.Tk()
ventana.title("Explorador de Enfermedades")
ventana.geometry("900x700")

tk.Label(ventana, text="Selecciona una enfermedad:").pack(pady=5)
lista_enfermedades = sorted(G.nodes)
enfermedad_combo = ttk.Combobox(ventana, values=lista_enfermedades, width=50)
enfermedad_combo.pack(pady=5)
enfermedad_combo.set("Selecciona una enfermedad...")

frame_grafo = tk.Frame(ventana)
frame_grafo.pack(fill=tk.BOTH, expand=True)

def dibujar_subgrafo():
    enfermedad = enfermedad_combo.get().strip()
    if enfermedad not in G.nodes:
        messagebox.showerror("Error", "Enfermedad no encontrada en el grafo")
        return

    sucesores = list(G.successors(enfermedad))
    if not sucesores:
        messagebox.showinfo("Sin relaciones", "No se encontraron relaciones para esta enfermedad")
        return

    subG = G.subgraph([enfermedad] + sucesores)

    fig = plt.figure(figsize=(6, 5))
    plt.clf()
    pos = nx.spring_layout(subG)
    nx.draw(subG, pos, with_labels=True, node_color="lightgreen", node_size=1600, font_size=9, arrows=True)
    edge_labels = nx.get_edge_attributes(subG, 'weight')
    nx.draw_networkx_edge_labels(subG, pos, edge_labels=edge_labels)

    for widget in frame_grafo.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=frame_grafo)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

def mostrar_grafo_completo():
    import random

    fig = plt.figure(figsize=(12, 10))
    plt.clf()
    pos = nx.spring_layout(G, k=0.1, iterations=40)
    nx.draw_networkx_nodes(G, pos, node_size=50, node_color='skyblue', alpha=0.8)
    nx.draw_networkx_edges(G, pos, edge_color='gray', alpha=0.3)
    subset_labels = {n: n for n in random.sample(list(G.nodes), min(100, len(G.nodes)))}
    nx.draw_networkx_labels(G, pos, labels=subset_labels, font_size=6)
    plt.title("🌐 Grafo completo de relaciones entre causas de muerte", fontsize=14)

    for widget in frame_grafo.winfo_children():
        widget.destroy()
    canvas = FigureCanvasTkAgg(fig, master=frame_grafo)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

def mostrar_grafo_jerarquico():
    G_jerarquico = nx.DiGraph()
    for _, row in df[df['estructura_predecesores']].iterrows():
        destino = row['concept_id']
        deaths = row['total_yr_deaths_FRANCE']
        for causa in row['predecessors_array_limpio']:
            origen = causa['predecessor_id']
            try:
                impacto = float(causa.get('impact', 0.1))
            except (ValueError, TypeError):
                impacto = 0.1
            peso = impacto * deaths / 1200
            G_jerarquico.add_edge(origen, destino, weight=peso)

    pos = nx.spring_layout(G_jerarquico, k=0.3, iterations=100)
    node_sizes = []
    node_colors = []
    for n in G_jerarquico.nodes():
        if n in df['concept_id'].values:
            deaths = df.loc[df['concept_id'] == n, 'total_yr_deaths_FRANCE'].values[0]
            size = deaths / 10
        else:
            size = 30
        node_sizes.append(size)
        node_colors.append("red" if size > 200 else "orange" if size > 100 else "yellow")

    edge_widths = [G_jerarquico[u][v]['weight'] if G_jerarquico[u][v]['weight'] else 0.1 for u, v in G_jerarquico.edges()]
    fig = plt.figure(figsize=(12, 10))
    plt.clf()
    nx.draw_networkx_edges(G_jerarquico, pos, alpha=0.4, edge_color='gray', width=edge_widths)
    nx.draw_networkx_nodes(G_jerarquico, pos, node_size=node_sizes, node_color=node_colors, alpha=0.6)
    nx.draw_networkx_labels(G_jerarquico, pos, font_size=7)
    plt.title("📊 Grafo Jerárquico (predecessors → enfermedades)", fontsize=14)
    plt.axis('off')

    for widget in frame_grafo.winfo_children():
        widget.destroy()
    canvas = FigureCanvasTkAgg(fig, master=frame_grafo)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Botones
tk.Button(ventana, text="Mostrar relaciones", command=dibujar_subgrafo).pack(pady=5)
tk.Button(ventana, text="Mostrar grafo completo", command=mostrar_grafo_completo).pack(pady=5)
tk.Button(ventana, text="Mostrar grafo jerárquico", command=mostrar_grafo_jerarquico).pack(pady=5)

ventana.mainloop()
