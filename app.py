import streamlit as st
import numpy as np
import components
import logic

st.set_page_config(
    page_title="EVCS Demo",
    layout="wide",
    page_icon="🔐",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root {color-scheme: light;}
      body {background: #f6f7fb;}
      .stButton > button {background: #111827; color: white; border-radius: 6px; border: none; font-weight: 500;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("EVCS Demo - Criptografía Visual")
st.caption("Implementación técnica de esquemas de secreto visual.")

if "generated" not in st.session_state:
    st.session_state.generated = False

col_a, col_b = st.columns([1, 1], gap="large")

with col_a:
    st.subheader("Secreto")
    secret_file = st.file_uploader("Imagen de secreto B/N", type=["png", "jpg", "jpeg"], key="secret_in")
    invert_secret = st.checkbox("Invertir secreto", value=False)
    dither = st.checkbox("Dithering suave (recomendado)", value=True)

with col_b:
    st.subheader("Configuración del Algoritmo")
    
    c_algo_sel, c_algo_info = st.columns([0.6, 0.4], gap="medium")
    
    with c_algo_sel:
        algo_selection = st.radio(
            "Seleccione construcción:",
            (
                "Construcción 1: VCS - Black and White",
                "Construcción 2: Color Black White - VCS (CBW)",
                "Construcción 3: CBW-EVCS (Esquema extendido)",
                "Construcción 4: CBW-EVCS aumentado",
            ),
            index=0,
            label_visibility="collapsed"
        )
        
        

        # --- SLIDER N (Solo para Métodos 1 y 2) ---
        n_manual = 2
        if "Construcción 1" in algo_selection or "Construcción 2" in algo_selection:
            st.write("")
            n_manual = st.slider("Número de Sombras (N)", min_value=2, max_value=5, value=2)
            st.caption("⚠️ Nota: El algoritmo está mejor optimizado para n=2.")
            
        st.write("") 

        size_help = "Define el ancho de la imagen procesada. La altura se ajusta proporcionalmente. A más alto mayor calidad, pero más tiempo de procesamiento."

        # Sliders de tamaño específicos por método (aviso incluido)
        if "Construcción 1" in algo_selection:
            size = st.slider("Tamaño base (px) — Método 1", 320, 900, 640, step=40, help=size_help, key="size_m1")
        elif "Construcción 2" in algo_selection:
            size = st.slider("Tamaño base (px) — Método 2", 320, 900, 640, step=40, help=size_help, key="size_m2")
        elif "Construcción 4" in algo_selection:
            size = st.slider("Tamaño base (px) — Método 4", 320, 900, 640, step=40, help=size_help, key="size_m4")
        else:
            # Método 3 u otros: slider genérico con el mismo aviso
            size = st.slider("Tamaño base (px)", 320, 900, 640, step=40, help=size_help, key="size_default")
            
        # --- SLIDER DARKEN FACTOR (Solo Método 3) ---
        darken_factor = 0.2
        if "Construcción 3" in algo_selection:
            st.write("")
            darken_factor = st.slider(
                "Factor de Luminosidad (Fondo)", 
                min_value=0.01, 
                max_value=1.0, 
                value=0.2, 
                step=0.05,
                help="Controla la densidad de ruido en el fondo. Valores más bajos generan sombras más oscuras."
            )
            st.caption("⚠️ Nota: Punto optimo de luminosidad: entre 20 y 30%.")

    info_texts = {
        "Construcción 1": """
        <b>Clásico Naor-Shamir (B/N)</b><br><br>
        Algoritmo original de 1994. Utiliza matrices de píxeles blanco y negro puro. 
        Garantiza seguridad perfecta teórica.
        <br><i>Genera N sombras distribuyendo pares canónicos.</i>
        """,
        
        "Construcción 2": """
        <b>CBW Puro (Ruido de Color)</b><br><br>
        Prioriza el contraste absoluto. Ignora imágenes de cobertura, generando sombras 
        de ruido aleatorio cromático.
        <br><i>Genera N sombras distribuyendo pares canónicos.</i>
        """,
        
        "Construcción 3": """
        <b>CBW Extendido</b><br><br>
        Variante que permite ocultar imágenes dentro de las sombras. Utiliza un algoritmo 
        de 'preferencia suave' y ajuste de luminosidad para reducir el rastro (ghosting) 
        de la imagen de cobertura.
        """,
        
        "Construcción 4": """
        <b>CBW Aumentado</b><br><br>
        Evolución del esquema estándar RGB. Aplica rotación de canales de color en el 
        píxel negro para aumentar la oscuridad resultante.
        """
    }

    current_key = next((k for k in info_texts if k in algo_selection), "Construcción 1")
    description = info_texts[current_key]

    with c_algo_info:
        st.markdown(
            f"""
            <div style="
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 15px;
                font-size: 13px;
                color: #475569;
                line-height: 1.5;
            ">
                {description}
        
            """,
            unsafe_allow_html=True
        )

st.markdown("---")

# Lógica para determinar si necesitamos uploads de covers
is_basic_method = "Construcción 1" in algo_selection or "Construcción 2" in algo_selection
needs_covers = not is_basic_method

cover_files = []
n_final = 2

if needs_covers:
    st.subheader("Imágenes de Cobertura")
    cols = st.columns(5)
    raw_files = [None] * 5
    for i in range(5):
        with cols[i]:
            cf = st.file_uploader(f"Participante {i+1}", type=["png","jpg"], key=f"c_{i}")
            if cf: raw_files[i] = cf
    cover_files = [f for f in raw_files if f is not None]
    n_final = len(cover_files)
    if n_final < 2:
        st.info("Para los métodos extendidos, suba al menos 2 imágenes de cobertura.")
else:
    # Si es método básico, usamos el valor del slider manual
    n_final = n_manual

st.markdown("---")

def _generate_multi():
    if not secret_file:
        st.warning("Se requiere el archivo del secreto.")
        return

    # Validación estricta solo para métodos que requieren covers
    if needs_covers and n_final < 2:
        st.error("Se requieren al menos 2 imágenes de cobertura.")
        return

    with st.spinner("Procesando..."):
        # Preparamos el secreto
        c_file = cover_files[0] if cover_files else None
        
        secret_preview, _, mask, _ = logic.prepare_inputs(
            secret_file, c_file, invert=invert_secret, size=size, dither=dither
        )
        
        # Preparamos las coberturas (o los dummies vacíos)
        if needs_covers:
            cover_arrs = [
                logic.prepare_inputs(secret_file, f, invert=invert_secret, size=size, dither=dither)[3]
                for f in cover_files
            ]
        else:
            # Generamos N lienzos vacíos según el slider
            h, w = mask.shape
            dummy_arr = np.zeros((h, w, 3), dtype=np.uint8)
            cover_arrs = [dummy_arr] * n_final

        shares = []
        
        if "Construcción 1" in algo_selection:
            shares = logic.generate_bw_vcs(mask, cover_arrs)
            
        elif "Construcción 2" in algo_selection:
            shares = logic.generate_simple_6color(mask, cover_arrs)
            
        elif "Construcción 3" in algo_selection:
            shares = logic.generate_evcs_colored(mask, cover_arrs, darken_factor=darken_factor)
            
        elif "Construcción 4" in algo_selection:
            shares = logic.generate_basic_evcs_augmented(mask, cover_arrs)
        
    st.session_state.update({
        "secret_prev": secret_preview,
        "shares": shares,
        "generated": True
    })

run_btn = st.button("Generar Sombras", type="primary", use_container_width=True)

if run_btn:
    _generate_multi()

if st.session_state.get("generated"):
    
    # --- VISUALIZACIÓN ---
    col_secret, col_shares = st.columns([1, 3])
    with col_secret:
        st.markdown("**Secreto original:**")
        st.image(st.session_state["secret_prev"], width=size)
    
    with col_shares:
        st.markdown("**Sombras generadas:**")
        cols = st.columns(len(st.session_state["shares"]))
        for idx, (c, share) in enumerate(zip(cols, st.session_state["shares"])):
            with c:
                caption_txt = f"Sombra {idx+1}"
                if needs_covers:
                    caption_txt += " (Con Cover)"
                st.image(share, caption=caption_txt, width=size)

    st.markdown("---")
    st.subheader("Zona de Pruebas (Interactivo)")
    b_list = [components.image_to_base64(img) for img in st.session_state["shares"]]
    components.render_multi_drag_demo(b_list)