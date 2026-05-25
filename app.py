import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

# ==========================================
# CONFIGURACIÓN Y ESTILO RESPONSIVO MÓVIL
# ==========================================
st.set_page_config(page_title="Nave los Masegales", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    :root { --primary-color: #166534; }
    .big-font { font-size:22px !important; font-weight: bold; color: #166534; text-align: center; }
    .stButton>button { 
        width: 100%; 
        height: 3.5em; 
        font-size: 16px !important; 
        font-weight: bold; 
        background-color: #166534; 
        color: white; 
        border-radius: 12px;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .metric-card { 
        background-color: #f8fafc; 
        padding: 16px; 
        border-radius: 12px; 
        border: 1px solid #e2e8f0; 
        text-align: center; 
        margin-bottom: 12px;
    }
    .metric-card h2 { margin: 5px 0 0 0; color: #1e293b; font-size: 26px; }
    .metric-card p { margin: 0; color: #64748b; font-size: 12px; font-weight: 600; letter-spacing: 0.5px; }
    
    @media (max-width: 768px) {
        .stHorizontalBlock { flex-direction: column !important; }
        .metric-card h2 { font-size: 22px; }
        .stButton>button { height: 3.8em; font-size: 15px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# CONEXIÓN SEGURA CON GOOGLE SHEETS
# ==========================================
@st.cache_resource(ttl=60)
def inicializar_gspread():
    # Convertimos los secretos en un diccionario tradicional para poder limpiarlo
    credentials = dict(st.secrets["gcp_service_account"])
    # Reparación automática: convierte el texto '\n' en verdaderos saltos de línea
    if "private_key" in credentials:
        credentials["private_key"] = credentials["private_key"].replace("\\n", "\n")
    gc = gspread.service_account_from_dict(credentials)
    return gc

try:
    gc = inicializar_gspread()
    sh = gc.open_by_key(st.secrets["spreadsheet_key"])
except Exception as e:
    st.error(f"❌ Error de autenticación o conexión con Google Sheets: {e}")
    st.stop()

def leer_pestana(nombre_pestana):
    try:
        worksheet = sh.worksheet(nombre_pestana)
        records = worksheet.get_all_records()
        # Calculamos dinámicamente la fila real de Google Sheets para poder editarla/borrarla luego
        for i, r in enumerate(records):
            r['sheet_row'] = i + 2
        return worksheet, pd.DataFrame(records)
    except Exception as e:
        st.error(f"Error al acceder a la pestaña '{nombre_pestana}': {e}")
        return None, pd.DataFrame()

# Variables de Negocio
MIEMBROS_FAMILIA = ["Felipe y Maribel", "Isabel y Jaime", "Roberto"]

st.sidebar.markdown("<p class='big-font'>🚜 NAVE LOS MASEGALES</p>", unsafe_allow_html=True)
opcion = st.sidebar.radio("Menú de Gestión:", ["📈 Resumen y Bote", "📋 Lista de Tareas", "🧱 Control de Obras", "🌱 Huerta Ecológica", "🔧 Inventario"])

# ==========================================
# 1. PESTAÑA: RESUMEN Y BOTE
# ==========================================
if opcion == "📈 Resumen y Bote":
    st.title("📈 Contabilidad General")
    ws_finanzas, df_finanzas = leer_pestana("finanzas")
    ws_tareas, df_tareas = leer_pestana("tareas")
    
    df_tareas_p = df_tareas[df_tareas['estado'] == 'Pendiente'] if not df_tareas.empty else pd.DataFrame()
    
    total_aportado = df_finanzas[df_finanzas['tipo'] == 'Aportación Bote']['importe'].sum() if not df_finanzas.empty else 0.0
    total_gastado = df_finanzas[df_finanzas['tipo'] == 'Gasto']['importe'].sum() if not df_finanzas.empty else 0.0
    saldo_bote = total_aportado - total_gastado

    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f"<div class='metric-card'><p>FONDO TOTAL APORTADO</p><h2 style='color:#166534;'>{total_aportado:,.2f} €</h2></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='metric-card'><p>TOTAL GASTADO</p><h2 style='color:#991b1b;'>{total_gastado:,.2f} €</h2></div>", unsafe_allow_html=True)
    color_saldo = "#166534" if saldo_bote >= 0 else "#991b1b"
    col3.markdown(f"<div class='metric-card'><p>SALDO DISPONIBLE</p><h2 style='color:{color_saldo};'>{saldo_bote:,.2f} €</h2></div>", unsafe_allow_html=True)
    col4.markdown(f"<div class='metric-card'><p>TAREAS PENDIENTES</p><h2>{len(df_tareas_p)}</h2></div>", unsafe_allow_html=True)
    
    st.write("---")
    col_f1, col_f2 = st.columns([1, 1.5])
    
    with col_f1:
        st.subheader("💰 Añadir Fondos")
        with st.form("form_bote", clear_on_submit=True):
            quien_aporta = st.selectbox("¿Quién aporta el dinero?", MIEMBROS_FAMILIA)
            cuanto_aporta = st.number_input("Cantidad (€)", min_value=0.0, step=5.0, format="%.2f")
            if st.form_submit_button("INGRESAR EN EL BOTE"):
                if cuanto_aporta <= 0:
                    st.error("⚠️ El importe debe ser mayor que 0 €.")
                else:
                    ws_finanzas.append_row([str(datetime.now().date()), f"Aportación de {quien_aporta}", "Fondo Común", "Bote", cuanto_aporta, quien_aporta, "Aportación Bote"])
                    st.success("¡Ingreso registrado!")
                    st.invalidate_resource(inicializar_gspread)
                    st.rerun()
                    
    with col_f2:
        st.subheader("📋 Historial de Caja")
        if not df_finanzas.empty:
            df_mostrar = df_finanzas[['fecha', 'concepto', 'importe', 'pagado_por', 'tipo']].copy().sort_index(ascending=False)
            st.dataframe(df_mostrar, use_container_width=True, height=250)
        else:
            st.info("Sin movimientos registrados.")

# ==========================================
# 2. PESTAÑA: LISTA DE TAREAS
# ==========================================
elif opcion == "📋 Lista de Tareas":
    st.title("📋 Tareas de la Finca")
    col_t1, col_t2 = st.columns([1, 1.5])
    ws_tareas, df_t = leer_pestana("tareas")
    
    with col_t1:
        st.subheader("Nueva Tarea")
        with st.form("form_tareas", clear_on_submit=True):
            tarea = st.text_input("¿Qué hay que hacer?")
            prioridad = st.selectbox("Urgencia", ["Alta (Urgente)", "Media", "Baja"])
            responsable = st.selectbox("Asignar a", MIEMBROS_FAMILIA + ["Todos"])
            if st.form_submit_button("Guardar Tarea"):
                if not tarea.strip():
                    st.error("⚠️ La descripción no puede estar vacía.")
                else:
                    ws_tareas.append_row([tarea, prioridad, "Pendiente", responsable])
                    st.success("¡Tarea anotada!")
                    st.invalidate_resource(inicializar_gspread)
                    st.rerun()

    with col_t2:
        st.subheader("Pendientes")
        if not df_t.empty:
            df_pendientes = df_t[df_t['estado'] == 'Pendiente']
            if not df_pendientes.empty:
                for index, row in df_pendientes.iterrows():
                    col_row1, col_row2 = st.columns([3, 1])
                    col_row1.markdown(f"**📌 {row['tarea']}**\n<small>{row['responsable']} | Pr: {row['prioridad']}</small>", unsafe_allow_html=True)
                    if col_row2.button("✓ Ok", key=f"t_{row['sheet_row']}"):
                        ws_tareas.update_cell(int(row['sheet_row']), 3, "Completado")
                        st.invalidate_resource(inicializar_gspread)
                        st.rerun()
                    st.write("---")
            else:
                st.success("🎉 ¡Todo al día!")
        else:
            st.success("🎉 ¡Todo al día!")

# ==========================================
# 3. PESTAÑA: CONTROL DE OBRAS
# ==========================================
elif opcion == "🧱 Control de Obras":
    st.title("🧱 Estado de Obras")
    col_o1, col_o2 = st.columns([1, 1.5])
    ws_obras, df_o = leer_pestana("obras")
    ws_finanzas, _ = leer_pestana("finanzas")
    
    with col_o1:
        st.subheader("Registrar Avance")
        with st.form("form_obras", clear_on_submit=True):
            proyecto = st.selectbox("Zona", ["Construcción Nave", "Piscina", "Vallado Perimetral", "Acondicionamiento Terreno", "Instalación Riego"])
            fase = st.selectbox("Fase", ["Planificación", "Movimiento de Tierras", "Estructura", "Acabados", "Finalizado"])
            fecha_i = st.date_input("Fecha")
            coste_obra = st.number_input("Coste Material (€)", min_value=0.0, step=5.0)
            quien_paga = st.selectbox("¿Quién lo pagó?", MIEMBROS_FAMILIA)
            notas = st.text_area("Notas / Materiales")
            
            if st.form_submit_button("REGISTRAR"):
                ws_obras.append_row([proyecto, fase, str(fecha_i), notas])
                if coste_obra > 0:
                    ws_finanzas.append_row([str(fecha_i), f"Obra {proyecto} ({fase})", "Obras", proyecto, coste_obra, quien_paga, "Gasto"])
                st.success("Sincronizado correctamente.")
                st.invalidate_resource(inicializar_gspread)
                st.rerun()

    with col_o2:
        st.subheader("Historial")
        if not df_o.empty:
            st.dataframe(df_o.drop(columns=['sheet_row'], errors='ignore').sort_index(ascending=False), use_container_width=True, height=350)
        else:
            st.info("Sin registros.")

# ==========================================
# 4. PESTAÑA: HUERTA ECOLÓGICA
# ==========================================
elif opcion == "🌱 Huerta Ecológica":
    st.title("🌱 Cuaderno de Campo")
    col_h1, col_h2 = st.columns([1, 1.5])
    ws_huerta, df_h = leer_pestana("huerta")
    ws_finanzas, _ = leer_pestana("finanzas")
    
    with col_h1:
        st.subheader("Nueva Siembra")
        with st.form("form_huerta", clear_on_submit=True):
            cultivo = st.text_input("Variedad (Ej: Tomate de colgar)")
            familia = st.selectbox("Familia Botánica", ["Solanáceas", "Cucurbitáceas", "Leguminosas", "Crucíferas", "Liliáceas"])
            fecha_s = st.date_input("Fecha")
            abono = st.selectbox("Abono", ["Compost", "Estiércol", "Humus", "Ninguno"])
            tratamiento = st.text_input("Tratamiento preventivo")
            coste_h = st.number_input("Gasto Semillas (€)", min_value=0.0, step=1.0)
            quien_h = st.selectbox("Comprado por", MIEMBROS_FAMILIA)
            
            if st.form_submit_button("REGISTRAR"):
                if not cultivo.strip():
                    st.error("⚠️ Especifica el cultivo.")
                else:
                    ws_huerta.append_row([cultivo, familia, str(fecha_s), abono, tratamiento, "Activo"])
                    if coste_h > 0:
                        ws_finanzas.append_row([str(fecha_s), f"Semillas: {cultivo}", "Huerta", "Huerto", coste_h, quien_h, "Gasto"])
                    st.success("¡Cultivo registrado!")
                    st.invalidate_resource(inicializar_gspread)
                    st.rerun()

    with col_h2:
        st.subheader("Historial del Huerto")
        if not df_h.empty:
            st.dataframe(df_h.drop(columns=['sheet_row'], errors='ignore').sort_index(ascending=False), use_container_width=True, height=350)
        else:
            st.info("Sin registros.")

# ==========================================
# 5. PESTAÑA: INVENTARIO
# ==========================================
elif opcion == "🔧 Inventario":
    st.title("🔧 Inventario y Herramientas")
    col_i1, col_i2 = st.columns([1, 1.5])
    ws_inventario, df_i = leer_pestana("inventario")
    ws_finanzas, _ = leer_pestana("finanzas")
    
    with col_i1:
        st.subheader("Añadir Objeto")
        with st.form("form_inv", clear_on_submit=True):
            articulo = st.text_input("Nombre de la herramienta")
            cat_inv = st.selectbox("Categoría", ["Herramientas", "Maquinaria", "Mobiliario", "Riego", "Otros"])
            cantidad = st.number_input("Cantidad", min_value=1, value=1)
            ubicacion = st.selectbox("Ubicación", ["Nave Principal", "Caseta de Riego", "Exterior", "Por determinar"])
            estado_art = st.selectbox("Estado", ["Perfecto", "Usado", "Reparar"])
            aportado_por = st.selectbox("Dueño / Aportado por", MIEMBROS_FAMILIA)
            estado_traslado = st.selectbox("¿Ya está en la finca?", ["Ya en la finca", "Pendiente de llevar"])
            valor_estimado = st.number_input("Valor Estimado (€)", min_value=0.0, step=5.0)
            es_compra_nueva = st.checkbox("¿Es compra nueva pagada con el Bote?")
            
            if st.form_submit_button("REGISTRAR ARTÍCULO"):
                if not articulo.strip():
                    st.error("⚠️ Nombre obligatorio.")
                else:
                    ws_inventario.append_row([articulo, cat_inv, int(cantidad), ubicacion, estado_art, aportado_por, estado_traslado, valor_estimado])
                    if es_compra_nueva and valor_estimado > 0:
                        ws_finanzas.append_row([str(datetime.now().date()), f"Compra: {articulo}", "Inventario", "Herramientas", valor_estimado, aportado_por, "Gasto"])
                    st.success("¡Inventario actualizado!")
                    st.invalidate_resource(inicializar_gspread)
                    st.rerun()

    with col_i2:
        st.subheader("Almacén")
        if not df_i.empty:
            st.metric("Patrimonio Estimado", f"{df_i['valor_estimado'].sum():,.2f} €")
            st.dataframe(df_i[['articulo', 'cantidad', 'aportado_por', 'estado_traslado']], use_container_width=True, height=350)
        else:
            st.info("Sin registros.")
