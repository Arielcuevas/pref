import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO
import re

# Configuración de la página
st.set_page_config(
    page_title="Análisis de Eficiencia de Túneles de Prefrío",
    page_icon="❄️",
    layout="wide"
)

# Título y descripción
st.title("Análisis de Eficiencia de Túneles de Prefrío")
st.markdown("""
Esta aplicación analiza datos de operación de túneles de prefrío, 
centrándose en la duración y temperatura de inicio como factores clave de eficiencia.
""")

# Función para procesar el archivo cargado
def procesar_datos(archivo):
    # Leer el archivo
    try:
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo, sep=',', decimal='.', encoding='utf-8-sig')
        elif archivo.name.endswith('.xlsx') or archivo.name.endswith('.xls'):
            df = pd.read_excel(archivo)
        else:
            st.error("Formato de archivo no soportado. Por favor, sube un archivo CSV o Excel.")
            return None
        
        # Verificar si las columnas necesarias están presentes
        columnas_requeridas = ["Ubicación", "Duración (Horas)", "T° Inicio"]
        
        # Comprueba si las columnas existen, permitiendo variaciones en el nombre
        columnas_disponibles = df.columns.str.strip().str.upper().tolist()
        for col in columnas_requeridas:
            col_upper = col.upper()
            if not any(col_upper in col_disp for col_disp in columnas_disponibles):
                # Buscar columnas similares
                for col_disp in df.columns:
                    if "UBICACION" in col_disp.upper() or "PREFRIO" in col_disp.upper():
                        df.rename(columns={col_disp: "Ubicación"}, inplace=True)
                    elif "DURACION" in col_disp.upper() or "HORAS" in col_disp.upper():
                        df.rename(columns={col_disp: "Duración (Horas)"}, inplace=True)
                    elif "TEMP" in col_disp.upper() or "INICIO" in col_disp.upper() or "T°" in col_disp.upper():
                        df.rename(columns={col_disp: "T° Inicio"}, inplace=True)
        
        # Volver a verificar después de intentar arreglar los nombres
        for col in columnas_requeridas:
            if col not in df.columns:
                st.error(f"Columna '{col}' no encontrada en el archivo.")
                st.write("Columnas disponibles:", list(df.columns))
                return None
        
        # Asegurarse de que las columnas numéricas estén en formato correcto
        # Convertir comas a puntos en columnas numéricas si es necesario
        for col in ["Duración (Horas)", "T° Inicio"]:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '.').astype(float)
        
        return df
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
        return None

# Sidebar para cargar datos
st.sidebar.header("Cargar Datos")

# Cargar archivo
archivo = st.sidebar.file_uploader("Cargar archivo CSV o Excel", type=["csv", "xlsx", "xls"])
if archivo is not None:
    df = procesar_datos(archivo)
else:
    st.info("Por favor, carga un archivo Excel o CSV con los datos de los túneles de prefrío.")
    st.stop()

# Verificar si tenemos datos para trabajar
if df is None:
    st.stop()

# Mostrar los datos cargados
st.subheader("Datos cargados")
st.dataframe(df)

# Asegurarse de que las columnas numéricas estén en formato correcto
for col in ["Duración (Horas)", "T° Inicio", "#Pallet"]:
    if df[col].dtype == 'object':
        df[col] = df[col].astype(str).str.replace(',', '.').astype(float)

# Convertir columnas de fechas si es necesario
# Esto podría requerir ajustes según el formato exacto de tus datos

# ----- ANÁLISIS DE DATOS -----

# Dividir la pantalla en columnas
col1, col2 = st.columns(2)

with col1:
    st.subheader("Estadísticas por Túnel de Prefrío")
    
    # Calcular estadísticas por túnel
    stats_tunel = df.groupby('Ubicación').agg({
        'Duración (Horas)': ['mean', 'min', 'max', 'count'],
        'T° Inicio': ['mean', 'min', 'max'],
        '#Pallet': ['mean', 'sum']
    }).round(2)
    
    # Formatear para mejor visualización
    stats_tunel.columns = ['Duración Promedio (h)', 'Duración Mínima (h)', 'Duración Máxima (h)', 
                          'Cantidad de Procesos', 'Temperatura Promedio (°C)', 'Temperatura Mínima (°C)',
                          'Temperatura Máxima (°C)', 'Pallets Promedio', 'Total Pallets']
    st.dataframe(stats_tunel)

with col2:
    st.subheader("Distribución de Duración por Túnel")
    
    # Gráfico de barras para comparar duración promedio por túnel
    fig_duracion = px.bar(
        df.groupby('Ubicación')['Duración (Horas)'].mean().reset_index(),
        x='Ubicación',
        y='Duración (Horas)',
        color='Ubicación',
        title='Duración Promedio por Túnel',
        labels={'Duración (Horas)': 'Duración Promedio (horas)'}
    )
    st.plotly_chart(fig_duracion, use_container_width=True)

# Análisis de relación entre temperatura y duración
st.subheader("Relación entre Temperatura de Inicio y Duración")

# Gráfico de dispersión
fig_scatter = px.scatter(
    df, 
    x='T° Inicio', 
    y='Duración (Horas)',
    color='Ubicación',
    size='#Pallet',
    hover_data=['N° Proceso Prefrío', 'ID Estiba', 'Fecha Inicio'],
    title='Relación entre Temperatura de Inicio y Duración del Proceso',
    labels={
        'T° Inicio': 'Temperatura de Inicio (°C)',
        'Duración (Horas)': 'Duración (horas)',
        '#Pallet': 'Cantidad de Pallets'
    }
)
st.plotly_chart(fig_scatter, use_container_width=True)

# Calcular correlación
correlacion = df['T° Inicio'].corr(df['Duración (Horas)'])
st.info(f"Correlación entre Temperatura de Inicio y Duración: {correlacion:.2f}")

# ----- ANÁLISIS DE EFICIENCIA -----

st.subheader("Análisis de Eficiencia de Túneles")

# Definir métricas de eficiencia
# Primero, calculamos valores normalizados para poder comparar
df['Eficiencia_Temp'] = 1 - ((df['T° Inicio'] - df['T° Inicio'].min()) / (df['T° Inicio'].max() - df['T° Inicio'].min()))
df['Eficiencia_Duracion'] = 1 - ((df['Duración (Horas)'] - df['Duración (Horas)'].min()) / (df['Duración (Horas)'].max() - df['Duración (Horas)'].min()))

# Calculamos una puntuación de eficiencia combinada (podemos ajustar los pesos según la importancia)
peso_temp = st.slider("Peso de la Temperatura en el cálculo de eficiencia", 0.0, 1.0, 0.5, 0.1)
peso_duracion = 1 - peso_temp

df['Eficiencia_Total'] = (df['Eficiencia_Temp'] * peso_temp) + (df['Eficiencia_Duracion'] * peso_duracion)

# Calculamos la eficiencia promedio por túnel
eficiencia_tunel = df.groupby('Ubicación')['Eficiencia_Total'].mean().reset_index()
eficiencia_tunel = eficiencia_tunel.sort_values('Eficiencia_Total', ascending=False)

# Visualización de la eficiencia
fig_eficiencia = px.bar(
    eficiencia_tunel,
    x='Ubicación',
    y='Eficiencia_Total',
    color='Eficiencia_Total',
    color_continuous_scale='viridis',
    title='Eficiencia Total por Túnel de Prefrío',
    labels={'Eficiencia_Total': 'Puntuación de Eficiencia (0-1)'}
)
st.plotly_chart(fig_eficiencia, use_container_width=True)

# Mostrar el túnel más eficiente
tunel_mas_eficiente = eficiencia_tunel.iloc[0]['Ubicación']
st.success(f"El túnel más eficiente según los parámetros seleccionados es: **{tunel_mas_eficiente}**")

# ----- ANÁLISIS DETALLADO POR TÚNEL -----

st.subheader("Análisis Detallado por Túnel")

# Selector de túnel
tunel_seleccionado = st.selectbox("Seleccionar túnel para análisis detallado:", df['Ubicación'].unique())

# Filtrar datos para el túnel seleccionado
datos_tunel = df[df['Ubicación'] == tunel_seleccionado]

# Mostrar estadísticas del túnel seleccionado
col1, col2, col3, col4 = st.columns(4)
col1.metric("Procesos", len(datos_tunel))
col2.metric("Duración Promedio", f"{datos_tunel['Duración (Horas)'].mean():.2f} h")
col3.metric("Temperatura Promedio", f"{datos_tunel['T° Inicio'].mean():.2f} °C")
col4.metric("Pallets Totales", int(datos_tunel['#Pallet'].sum()))

# Gráfico detallado del túnel
st.subheader(f"Detalle de procesos para {tunel_seleccionado}")
fig_detalle = px.scatter(
    datos_tunel,
    x='Fecha Inicio',
    y='Duración (Horas)',
    size='#Pallet',
    color='T° Inicio',
    hover_data=['ID Estiba', 'N° Proceso Prefrío'],
    title=f'Detalle de procesos para {tunel_seleccionado}',
)
st.plotly_chart(fig_detalle, use_container_width=True)

# ----- RECOMENDACIONES -----

st.subheader("Recomendaciones para Mejora de Eficiencia")

# Calcular métricas para recomendaciones
duracion_media = df['Duración (Horas)'].mean()
temp_media = df['T° Inicio'].mean()

# Identificar los procesos más eficientes (menor duración y menor temperatura inicial)
df_ordenado = df.sort_values(by=['Duración (Horas)', 'T° Inicio'])
mejores_procesos = df_ordenado.head(3)

st.markdown("""
### Recomendaciones basadas en el análisis:
""")

# Generar recomendaciones basadas en los datos
st.info(f"""
1. **Temperatura de inicio óptima**: Los datos sugieren que mantener la temperatura de inicio 
   alrededor de {mejores_procesos['T° Inicio'].mean():.1f}°C puede ayudar a optimizar la duración del proceso.

2. **Carga de pallets**: Los túneles con mejor rendimiento manejan un promedio de 
   {mejores_procesos['#Pallet'].mean():.0f} pallets por proceso. Considere ajustar la carga de acuerdo a esto.

3. **Túnel recomendado**: El túnel {tunel_mas_eficiente} muestra la mejor eficiencia general
   según los parámetros analizados.
""")

# Identificar si existe correlación entre factores
if abs(correlacion) > 0.5:
    if correlacion > 0:
        st.warning("Se observa una correlación positiva entre temperatura de inicio y duración, lo que sugiere que temperaturas iniciales más altas resultan en procesos más largos.")
    else:
        st.success("Se observa una correlación negativa entre temperatura de inicio y duración, lo que sugiere que optimizar la temperatura inicial podría reducir la duración del proceso.")

# Pie de página
st.markdown("---")
st.markdown("### Notas sobre el Análisis")
st.markdown("""
- Este análisis se basa únicamente en los datos proporcionados y puede requerir ajustes según otros factores operativos.
- La puntuación de eficiencia combina tanto la temperatura inicial como la duración, con los pesos definidos por el usuario.
- Para un análisis más completo, considere incluir datos sobre el tipo de producto, temperatura de salida y consumo energético.
""")