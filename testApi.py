#cause of deaths diseases and accidents => enfermedades y accidentes 

# concept_id	Causa específica de muerte (enfermedad, accidente, etc.)
# successor_array	Lista de causas que provoca esta causa
# Otras columnas	Estadísticas por sexo, edad, país, año (cuántas muertes, fuentes, etc.)

import kagglehub
from kagglehub import KaggleDatasetAdapter
import pandas as pd
import json
import re

# Ruta interna del CSV dentro del dataset
file_path = "multilevel_causality_deaths.csv"

# Cargar el dataset
df = kagglehub.load_dataset(
    KaggleDatasetAdapter.PANDAS,
    "cedricschicklin/multilevel-causality-relations-deaths-age-sex",
    file_path,
)

# Función de limpieza del campo successor_array
def limpiar_successor_array(texto):
    if pd.isna(texto):
        return None
    try:
        limpio = texto.replace("'", '"')
        limpio = re.sub(r'}\s*{', '},{', limpio)
        limpio = limpio.replace('\xa0', ' ')
        return json.loads(limpio)
    except Exception:
        return None

# Aplicar limpieza
df['successor_array_limpio'] = df['successor_array'].apply(limpiar_successor_array)

# Validar formato correcto
def claves_validas(lista):
    if lista is None:
        return False
    for item in lista:
        if not isinstance(item, dict) or "successor_id" not in item or "impact" not in item:
            return False
    return True

df['estructura_valida'] = df['successor_array_limpio'].apply(claves_validas)

# ----------------- CREAR GRAFO Y GUI -----------------

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import networkx as nx

# Crear grafo dirigido
G = nx.DiGraph()
for _, row in df[df['estructura_valida']].iterrows():
    origen = row['concept_id']
    for rel in row['successor_array_limpio']:
        destino = rel['successor_id']
        impacto = rel['impact']
        G.add_edge(origen, destino, weight=impacto)

print(f"🔢 Total de nodos en el grafo: {len(G.nodes)}")
print(f"🔗 Total de conexiones (aristas): {len(G.edges)}")


# Lista ordenada de enfermedades
lista_enfermedades = sorted(G.nodes)

# Crear ventana principal
ventana = tk.Tk()
ventana.title("Explorador de Enfermedades")
ventana.geometry("900x700")

# Selector desplegable
tk.Label(ventana, text="Selecciona una enfermedad:").pack(pady=5)
enfermedad_combo = ttk.Combobox(ventana, values=lista_enfermedades, width=50)
enfermedad_combo.pack(pady=5)
enfermedad_combo.set("Selecciona una enfermedad...")

# Frame para grafo
frame_grafo = tk.Frame(ventana)
frame_grafo.pack(fill=tk.BOTH, expand=True)

# Función para graficar
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

    # Posición de los nodos usando spring layout
    pos = nx.spring_layout(G, k=0.1, iterations=40)

    # Dibujar nodos más grandes y aristas
    nx.draw_networkx_nodes(G, pos, node_size=50, node_color='skyblue', alpha=0.8)
    nx.draw_networkx_edges(G, pos, edge_color='gray', alpha=0.3, arrows=True)

    # Mostrar etiquetas de 100 nodos aleatorios
    subset_labels = {n: n for n in random.sample(list(G.nodes), min(100, len(G.nodes)))}
    nx.draw_networkx_labels(G, pos, labels=subset_labels, font_size=6)

    plt.title("🌐 Grafo completo de relaciones entre causas de muerte", fontsize=14)

    # Limpiar el frame y mostrar en la interfaz
    for widget in frame_grafo.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=frame_grafo)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)



# Botón para mostrar sub grafo
tk.Button(ventana, text="Mostrar relaciones", command=dibujar_subgrafo).pack(pady=10)
tk.Button(ventana, text="Mostrar grafo completo", command=mostrar_grafo_completo).pack(pady=5)


ventana.mainloop()


# # Mostrar primeras filas
# print("🧠 Primeras filas del dataset:")
# print(df.head())

# # Ver columnas
# print("\n📌 Columnas disponibles:")
# print(df.columns.tolist())

# # Ver valores únicos de una columna clave
# print("\n📊 Valores únicos en 'concept_id':")
# print(df["concept_id"].dropna().unique())

# # Ver ejemplo de relaciones causales
# print("\n🔁 Ejemplos de relaciones (successor_array no vacío):")
# no_vacios = df[df["successor_array"].notna()][["concept_id", "successor_array"]].head(5)
# print(no_vacios.to_string(index=False))
