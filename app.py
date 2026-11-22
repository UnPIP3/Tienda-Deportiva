"""Interfaz Streamlit del inventario de la tienda deportiva."""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

import logic

OPCIONES = [
    "Cargar producto",
    "Ver inventario",
    "Generar datos de prueba",
    "Exportar a Excel",
    "Importar desde Excel",
    "Análisis por categoría",
    "Clusterización K-Means",
]


def iniciar_estado() -> None:
    if "inventario" not in st.session_state:
        st.session_state.inventario = []


def aplicar_estilos() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; padding-bottom: 2.5rem; }
        section[data-testid="stSidebar"] { background: #0f172a; }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        section[data-testid="stSidebar"] [role="radiogroup"] label {
            color: #e2e8f0;
        }
        section[data-testid="stSidebar"] hr { border-color: #334155; }
        div[data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 0.7rem 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def mostrar_metricas(inventario: list[dict]) -> None:
    metricas = logic.metricas_inventario(inventario)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Productos", f"{metricas['total_productos']:,}")
    c2.metric("Unidades", f"{metricas['total_unidades']:,}")
    c3.metric("Valor del inventario", f"${metricas['valor_total']:,.2f}")
    c4.metric("Categorías", f"{metricas['categorias']:,}")


def vaciar_inventario() -> None:
    st.session_state.inventario = []
    st.session_state.ultimo_lote = None


def menu_lateral() -> str:
    st.sidebar.title("Tienda deportiva")
    st.sidebar.caption("Inventario, ETL y segmentación")
    return st.sidebar.radio("Menú", OPCIONES, index=1, label_visibility="collapsed")


def resumen_lateral() -> None:
    """Se dibuja después de las acciones para reflejar el inventario ya actualizado."""
    st.sidebar.divider()
    metricas = logic.metricas_inventario(st.session_state.inventario)
    st.sidebar.metric("Productos en sesión", metricas["total_productos"])
    st.sidebar.metric("Valor total", f"${metricas['valor_total']:,.2f}")
    st.sidebar.button(
        "Vaciar inventario",
        width="stretch",
        on_click=vaciar_inventario,
    )


def pagina_cargar() -> None:
    st.header("Cargar producto")
    st.write("Registra un producto con código, nombre, categoría, precio y stock.")

    with st.form("alta_producto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        codigo = col1.text_input("Código del producto")
        nombre = col2.text_input("Nombre del producto")
        categoria = st.text_input(
            "Categoría",
            placeholder="Calzado, Ropa, Accesorios, Equipamiento",
        )
        col3, col4 = st.columns(2)
        precio = col3.number_input("Precio ($)", min_value=0.0, step=0.01, format="%.2f")
        cantidad = col4.number_input("Cantidad en stock", min_value=0, step=1)
        enviar = st.form_submit_button("Agregar al inventario", type="primary")

    if not enviar:
        return

    if not codigo.strip() or not nombre.strip() or not categoria.strip():
        st.error("Código, nombre y categoría no pueden estar vacíos.")
        return

    st.session_state.inventario.append(
        {
            "codigo": codigo.strip(),
            "nombre": nombre.strip(),
            "categoria": categoria.strip(),
            "precio": float(precio),
            "cantidad": int(cantidad),
        }
    )
    st.success(f"Producto «{nombre.strip()}» cargado. El inventario conserva los datos de esta sesión.")


def pagina_inventario() -> None:
    st.header("Inventario completo")
    inventario = st.session_state.inventario
    mostrar_metricas(inventario)

    if not inventario:
        st.info("El inventario está vacío. Cargue productos o genere datos de prueba.")
        return

    df = logic.inventario_a_dataframe(inventario)
    categorias = sorted(df["categoria"].dropna().astype(str).unique())
    col1, col2 = st.columns([2, 1])
    busqueda = col1.text_input("Buscar por código o nombre", placeholder="Ej. running, botas, a1b2")
    filtro = col2.multiselect("Categoría", categorias, placeholder="Todas")

    vista = df
    if busqueda.strip():
        texto = busqueda.strip().lower()
        vista = vista[
            vista["codigo"].astype(str).str.lower().str.contains(texto, na=False)
            | vista["nombre"].astype(str).str.lower().str.contains(texto, na=False)
        ]
    if filtro:
        vista = vista[vista["categoria"].isin(filtro)]

    st.caption(f"{len(vista)} de {len(df)} productos")
    st.dataframe(
        vista,
        width="stretch",
        hide_index=True,
        column_config={
            "codigo": st.column_config.TextColumn("Código"),
            "nombre": st.column_config.TextColumn("Producto"),
            "categoria": st.column_config.TextColumn("Categoría"),
            "precio": st.column_config.NumberColumn("Precio", format="$%.2f"),
            "cantidad": st.column_config.NumberColumn("Stock", format="%d"),
            "precio_total": st.column_config.NumberColumn("Valor", format="$%.2f"),
        },
    )


def pagina_faker() -> None:
    st.header("Datos de prueba")
    st.write(
        "Genera 50 productos sintéticos con Faker (español), nombres del catálogo deportivo "
        "y precios dentro del rango de cada categoría."
    )
    if st.button("Generar 50 productos", type="primary"):
        nuevos = logic.generar_datos_prueba(50)
        st.session_state.inventario.extend(nuevos)
        st.session_state.ultimo_lote = nuevos
        st.success("Se generaron 50 productos de prueba y se añadieron al inventario.")

    lote = st.session_state.get("ultimo_lote")
    if lote:
        st.subheader("Último lote generado")
        st.dataframe(
            logic.inventario_a_dataframe(lote),
            width="stretch",
            hide_index=True,
        )


def pagina_exportar() -> None:
    st.header("Exportar a Excel")
    inventario = st.session_state.inventario
    if not inventario:
        st.warning("El inventario está vacío.")
        return

    st.write(
        "El archivo incluye las columnas del producto y `precio_total` (precio × cantidad), "
        "igual que la exportación original con openpyxl."
    )
    mostrar_metricas(inventario)
    contenido = logic.exportar_a_excel(inventario)
    st.download_button(
        "Descargar inventario_tienda.xlsx",
        data=contenido,
        file_name="inventario_tienda.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


def pagina_importar() -> None:
    st.header("Importar y limpiar Excel")
    st.write(
        "El ETL descarta filas sin código, nombre, precio o cantidad, "
        "convierte precio y cantidad a número y añade el resultado al inventario actual."
    )
    archivo = st.file_uploader("Archivo Excel", type=["xlsx", "xls"])
    if st.button("Importar y añadir al inventario", type="primary"):
        if archivo is None:
            st.warning("Seleccione un archivo Excel primero.")
            return
        try:
            nuevos = logic.limpiar_y_cargar_excel(archivo)
        except Exception as exc:
            st.error(f"No se pudo importar el archivo. {exc}")
            return
        if not nuevos:
            st.warning("El archivo no dejó filas válidas después de la limpieza.")
            return
        st.session_state.inventario.extend(nuevos)
        st.success(
            f"Archivo importado y datos limpiados. Se añadieron {len(nuevos)} productos."
        )
        st.dataframe(
            logic.inventario_a_dataframe(nuevos),
            width="stretch",
            hide_index=True,
        )


def pagina_analisis() -> None:
    st.header("Valor total por categoría")
    inventario = st.session_state.inventario
    if not inventario:
        st.warning("El inventario está vacío.")
        return

    agrupado = logic.analisis_agrupado(inventario)
    mostrar_metricas(inventario)
    st.dataframe(
        agrupado,
        width="stretch",
        hide_index=True,
        column_config={
            "categoria": st.column_config.TextColumn("Categoría"),
            "valor_total": st.column_config.NumberColumn("Valor total", format="$%.2f"),
        },
    )
    figura = logic.figura_analisis(agrupado)
    st.pyplot(figura)
    plt.close(figura)


def pagina_kmeans() -> None:
    st.header("Clusterización K-Means")
    st.write(
        "Estandariza cantidad y precio con StandardScaler y forma 3 grupos "
        "(random_state=42, n_init=10)."
    )
    inventario = st.session_state.inventario
    detalle, conteo, figura, error = logic.clusterizacion_kmeans(inventario)
    if error:
        st.warning(error)
        return

    columnas = st.columns(len(conteo))
    for columna, (cluster, cantidad) in zip(columnas, conteo.items()):
        columna.metric(f"Cluster {cluster}", int(cantidad))

    st.subheader("Resultados ordenados por cluster")
    st.dataframe(
        detalle,
        width="stretch",
        hide_index=True,
        column_config={
            "precio": st.column_config.NumberColumn("Precio", format="$%.2f"),
            "cantidad": st.column_config.NumberColumn("Stock", format="%d"),
            "Cluster": st.column_config.NumberColumn("Cluster", format="%d"),
        },
    )
    st.pyplot(figura)
    plt.close(figura)


def main() -> None:
    st.set_page_config(
        page_title="Inventario tienda deportiva",
        page_icon="🏃",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    iniciar_estado()
    aplicar_estilos()
    pagina = menu_lateral()

    vistas = {
        "Cargar producto": pagina_cargar,
        "Ver inventario": pagina_inventario,
        "Generar datos de prueba": pagina_faker,
        "Exportar a Excel": pagina_exportar,
        "Importar desde Excel": pagina_importar,
        "Análisis por categoría": pagina_analisis,
        "Clusterización K-Means": pagina_kmeans,
    }
    vistas[pagina]()
    resumen_lateral()


if __name__ == "__main__":
    main()
