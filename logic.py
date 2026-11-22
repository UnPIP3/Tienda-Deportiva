"""Lógica de inventario, ETL y clusterización de la tienda deportiva.

La estructura de cada producto es:
codigo, nombre, categoria, precio, cantidad.
"""

from __future__ import annotations

import io
import random

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from faker import Faker
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

COLUMNAS = ["codigo", "nombre", "categoria", "precio", "cantidad"]

CATALOGO = {
    "Calzado": [
        "Zapatillas Running",
        "Botas de Fútbol",
        "Zapatillas Baloncesto",
        "Zapatillas Ciclismo",
    ],
    "Ropa": [
        "Camiseta Térmica",
        "Pantalón Corto",
        "Chaqueta Impermeable",
        "Top Deportivo",
    ],
    "Accesorios": [
        "Gafas de Natación",
        "Gorra Deportiva",
        "Muñequeras",
        "Botella de Agua",
    ],
    "Equipamiento": [
        "Balón de Fútbol",
        "Mancuernas 5kg",
        "Esterilla de Yoga",
        "Raqueta de Tenis",
    ],
}

RANGOS_PRECIO = {
    "Calzado": (50, 250),
    "Ropa": (15, 90),
    "Accesorios": (5, 40),
    "Equipamiento": (30, 500),
}


def inventario_a_dataframe(inventario: list[dict]) -> pd.DataFrame:
    """Convierte el inventario a DataFrame y calcula el valor de cada línea."""
    if not inventario:
        return pd.DataFrame(columns=COLUMNAS + ["precio_total"])

    df = pd.DataFrame(inventario)
    for columna in COLUMNAS:
        if columna not in df.columns:
            df[columna] = pd.NA

    df["precio"] = pd.to_numeric(df["precio"], errors="coerce")
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce")
    df["precio_total"] = df["precio"] * df["cantidad"]
    return df[COLUMNAS + ["precio_total"]]


def metricas_inventario(inventario: list[dict]) -> dict:
    """Totales de productos, unidades y valor del inventario."""
    df = inventario_a_dataframe(inventario)
    if df.empty:
        return {
            "total_productos": 0,
            "total_unidades": 0,
            "valor_total": 0.0,
            "categorias": 0,
        }

    return {
        "total_productos": int(len(df)),
        "total_unidades": int(df["cantidad"].fillna(0).sum()),
        "valor_total": float(df["precio_total"].fillna(0).sum()),
        "categorias": int(df["categoria"].nunique(dropna=True)),
    }


def generar_datos_prueba(cantidad: int = 50) -> list[dict]:
    """Genera datos sintéticos coherentes para la tienda deportiva."""
    fake = Faker("es_ES")
    productos = []

    for _ in range(cantidad):
        categoria = random.choice(list(CATALOGO.keys()))
        nombre_producto = random.choice(CATALOGO[categoria])
        precio_asignado = round(random.uniform(*RANGOS_PRECIO[categoria]), 2)
        productos.append(
            {
                "codigo": fake.uuid4()[:8],
                "nombre": nombre_producto,
                "categoria": categoria,
                "precio": precio_asignado,
                "cantidad": random.randint(1, 100),
            }
        )

    return productos


def exportar_a_excel(inventario: list[dict]) -> bytes:
    """Exporta el inventario a un libro Excel en memoria, con precio_total."""
    df = pd.DataFrame(inventario)
    if "precio_total" in df.columns:
        df = df.drop(columns=["precio_total"])
    df["precio_total"] = df["precio"] * df["cantidad"]

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


def limpiar_y_cargar_excel(archivo) -> list[dict]:
    """Importa un Excel y aplica el ETL original (nulos y tipos numéricos)."""
    df = pd.read_excel(archivo, engine="openpyxl")
    requeridas = ["codigo", "nombre", "precio", "cantidad"]
    faltantes = [columna for columna in requeridas if columna not in df.columns]
    if faltantes:
        raise ValueError(
            "El archivo debe incluir las columnas: " + ", ".join(requeridas) + "."
        )

    df = df.dropna(subset=requeridas)
    df["precio"] = pd.to_numeric(df["precio"], errors="coerce")
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce")
    df = df.dropna()
    df["cantidad"] = df["cantidad"].astype(int)
    return df.to_dict("records")


def analisis_agrupado(inventario: list[dict]) -> pd.DataFrame:
    """Suma el valor del inventario agrupado por categoría."""
    df = pd.DataFrame(inventario)
    df["precio_total"] = df["precio"] * df["cantidad"]
    agrupado = (
        df.groupby("categoria", as_index=False)["precio_total"]
        .sum()
        .sort_values("precio_total", ascending=False)
    )
    agrupado = agrupado.rename(columns={"precio_total": "valor_total"})
    return agrupado.reset_index(drop=True)


def figura_analisis(agrupado: pd.DataFrame):
    """Gráfico de barras del valor total por categoría."""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    sns.barplot(
        data=agrupado,
        x="categoria",
        y="valor_total",
        hue="categoria",
        palette="viridis",
        legend=False,
        ax=ax,
    )
    ax.set_title("Valor total del inventario por categoría")
    ax.set_xlabel("Categoría")
    ax.set_ylabel("Valor total ($)")
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    return fig


def clusterizacion_kmeans(inventario: list[dict]):
    """Agrupa productos por cantidad y precio con K-Means (k=3).

    Devuelve el detalle ordenado por cluster, el conteo por grupo y la figura.
    Si hay menos de 3 productos, devuelve un mensaje de error.
    """
    if len(inventario) < 3:
        return None, None, None, "Se necesitan al menos 3 productos para aplicar K-Means."

    df = pd.DataFrame(inventario)
    features = df[["cantidad", "precio"]]

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    df["Cluster"] = kmeans.fit_predict(scaled_features)

    conteo = df["Cluster"].value_counts().sort_index()
    df_ordenado = df.sort_values(by="Cluster").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(8, 5))
    grafico = df_ordenado.copy()
    grafico["Cluster"] = grafico["Cluster"].astype(str)
    sns.scatterplot(
        data=grafico,
        x="precio",
        y="cantidad",
        hue="Cluster",
        palette="viridis",
        s=100,
        ax=ax,
    )
    ax.set_title("Segmentación de Productos (K-Means)")
    ax.set_xlabel("Precio ($)")
    ax.set_ylabel("Unidades en Stock")
    fig.tight_layout()

    columnas = [c for c in ["codigo", "nombre", "categoria", "precio", "cantidad", "Cluster"] if c in df_ordenado.columns]
    return df_ordenado[columnas], conteo, fig, None
