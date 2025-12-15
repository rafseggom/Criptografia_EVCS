import streamlit as st
import components
import logic

st.set_page_config(
    page_title="EVCSdemo",
    layout="wide",
    page_icon="🔐",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root {color-scheme: light;}
      body {background: #f6f7fb;}
      .stButton > button {background: #111827; color: white; border-radius: 10px; border: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔐 EVCSdemo · Criptografía Visual")
st.caption("Implementación de esquemas de secreto visual.")

if "generated" not in st.session_state:
    st.session_state.generated = False

col_a, col_b = st.columns([1, 1], gap="large")

with col_a:
    st.subheader("Secreto")
    secret_file = st.file_uploader("Imagen de secreto B/N", type=["png", "jpg", "jpeg"], key="secret_in")
    invert_secret = st.checkbox("Invertir secreto", value=False)
    dither = st.checkbox("Dithering suave (recomendado)", value=True)

with col_b:
    st.subheader("Algoritmo")
    
    # Dividimos columna en dos: Selectores (izq) y Explicación (der)
    c_algo_sel, c_algo_info = st.columns([0.6, 0.4], gap="medium")
    
    with c_algo_sel:
        algo_selection = st.radio(
            "Elige la construcción:",
            (
                "Construcción 1 · VCS - Black and White",
                "Construcción 2 · Color Black White - VCS (CBW)",
                "Construcción 3 · CBW-EVCS (Esquema extendido)",
                "Construcción 4 · CBW-EVCS aumentado",
                "Construcción 5 · CBW-EVCS Aumentado Perfect Black",
            ),
            index=0,
            label_visibility="collapsed"
        )
        
        st.write("") # Espaciador visual
        size = st.slider("Tamaño (px)", 320, 900, 640, step=40)

    # Textos actualizados y limpios, coherentes con los nuevos nombres
    info_texts = {
        "Construcción 1": """
        <b>Clásico Naor-Shamir (B/N)</b><br><br>
        El algoritmo original de 1994. Utiliza matrices de píxeles blanco y negro puro. 
        Garantiza seguridad perfecta: cada sombra individual es ruido aleatorio con 
        densidad 50% de negro, matemáticamente indistinguible de la otra.
        """,
        
        "Construcción 2": """
        <b>CBW Puro (Ruido)</b><br><br>
        Esta versión prioriza el contraste absoluto del secreto. 
        Ignora las imágenes de los participantes, generando sombras de 
        ruido aleatorio (pixelado) que al unirse recuperan el mensaje con máxima nitidez.
        """,
        
        "Construcción 3": """
        <b>CBW Extendido</b><br><br>
        Variante del CBW que permite ocultar imágenes dentro de las sombras.
        Utiliza un algoritmo de "preferencia suave" para reducir el rastro (fantasma) 
        que deja una imagen sobre la otra, manteniendo el secreto legible haciendo uso de imágenes cobertura.
        """,
        
        "Construcción 4": """
        <b>CBW Aumentado</b><br><br>
        Evolución del esquema estándar. En lugar de usar blanco para el contraste, 
        aplica una rotación de canales de color en el píxel negro.
        Esto "aumenta" la oscuridad resultante al forzar la mezcla de colores opuestos.
        """,
        
        "Construcción 5": """
        <b>Perfect Black</b><br><br>
        <b>En Desarrollo</b><br>
        Versión avanzada con matrices 2x2. Busca lograr una opacidad 
        del 100% (negro sólido) en la recuperación, eliminando cualquier semitransparencia.
        """
    }

    # Selección dinámica del texto
    current_key = next((k for k in info_texts if k in algo_selection), "Construcción 2")
    description = info_texts[current_key]

    # Renderizado del cuadro de información
    with c_algo_info:
        st.markdown(
            f"""
            <div style="
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 15px;
                font-size: 13px;
                color: #475569;
                line-height: 1.6;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            ">
                {description}
       
            """,
            unsafe_allow_html=True
        )
        
st.markdown("---")

st.subheader("📸 Imágenes de cobertura")
# Lógica dinámica de covers (hasta 5)
cover_files = [None] * 5 
cols = st.columns(5)
for i in range(5):
    with cols[i]:
        cf = st.file_uploader(f"P{i+1}", type=["png","jpg"], key=f"c_{i}")
        if cf: cover_files[i] = cf
cover_files = [f for f in cover_files if f is not None]
n_participants = len(cover_files)

st.markdown("---")

def _generate_multi():
    if not secret_file:
        st.warning("Falta el archivo secreto.")
        return
    if n_participants < 2:
        st.warning("Se requieren al menos 2 imágenes de cobertura (participantes).")
        return

    # Validaciones específicas de métodos
    if "Construcción 2" in algo_selection and n_participants != 2:
         st.error("La Construcción 2 (CBW) es estricta para n=2.")
         return
    
    with st.spinner("Procesando criptografía..."):
        # Preprocesar secreto y covers
        secret_preview, _, mask, _ = logic.prepare_inputs(
            secret_file, cover_files[0], invert=invert_secret, size=size, dither=dither
        )
        cover_arrs = [
            logic.prepare_inputs(secret_file, f, invert=invert_secret, size=size, dither=dither)[3]
            for f in cover_files
        ]
        
        # --- SELECTOR DE LÓGICA ---
        shares = []
        
        if "Construcción 1" in algo_selection:
            shares = logic.generate_bw_vcs(mask, cover_arrs)
            
        elif "Construcción 2" in algo_selection:
            # ANTIGUO MÉTODO 4 (Corregido Naor-Shamir)
            shares = logic.generate_simple_6color(mask, cover_arrs)
            
        elif "Construcción 3" in algo_selection:
            # ANTIGUO MÉTODO 5 (Extendida)
            shares = logic.generate_evcs_colored(mask, cover_arrs)
            
        elif "Construcción 4" in algo_selection:
            # ANTIGUO MÉTODO 1 (Básico RGB)
            shares = logic.generate_basic_evcs_augmented(mask, cover_arrs)
            
        elif "Construcción 5" in algo_selection:
            st.warning("⚠️ Método en construcción (Placeholder).")
            shares = logic.generate_perfect_black_placeholder(mask, cover_arrs)
    
    st.session_state.update({
        "secret_prev": secret_preview,
        "shares": shares,
        "generated": True
    })

run_btn = st.button("🚀 Generar Sombras", type="primary", use_container_width=True)

if run_btn:
    _generate_multi()

if st.session_state.get("generated"):
    
    # --- EXPLICACIONES PEDAGÓGICAS ACTUALIZADAS ---
    with st.expander("ℹ️ Detalle Matemático del Algoritmo", expanded=True):
        if "Construcción 1" in algo_selection:
            st.markdown("""
            **Construcción 1: VCS Clásico (B/N)**
            
            Esquema (2,2) determinista con píxeles puros.
            * **Expansión:** Cada píxel del secreto se convierte en 2 subpíxeles $[p_1, p_2]$.
            * **Seguridad:** Cada sombra tiene siempre 1 negro y 1 blanco ($p_1 \ neq p_2$), pareciendo gris uniforme.
            * **Recuperación:** * Blanco: $[0,1] + [0,1] \to [0,1]$ (50% luz).
                * Negro: $[0,1] + [1,0] \to [0,0]$ (0% luz, negro total).
            """)
            
        elif "Construcción 2" in algo_selection:
            st.markdown("""
            **Construcción 2: Color Black White - VCS (CBW)**
            
            Implementación pura del esquema (2,2) de Naor & Shamir adaptado a color.
            * **Objetivo:** Máximo contraste del secreto, ignorando el contenido de las covers (ruido).
            * **Lógica:**
                * **Secreto Blanco:** $S_1 = S_2$. Al superponer, $C \times C = C$ (Transparente/Visible).
                * **Secreto Negro:** $S_1 = \overline{S_2}$ (Complementario). Al superponer, $C \times \overline{C} = Negro$.
            """)
            
        elif "Construcción 3" in algo_selection:
            st.markdown("""
            **Construcción 3: CBW-EVCS (Esquema extendido)**
            
            Variante del esquema anterior que intenta preservar las imágenes de los participantes.
            * **Anti-Ghosting:** Cuando hay conflicto de intereses (ambos participantes quieren negro en un píxel donde el secreto exige negro), se aleatoriza la asignación.
            * **Paleta:** Usa subconjuntos de colores Claros/Oscuros para simular niveles de gris.
            """)
            
        elif "Construcción 4" in algo_selection:
            st.markdown("""
            **Construcción 4: CBW-EVCS Aumentado**
            
            Esquema clásico RGB con expansión m=2.
            * **Secreto Negro:** Usa el concepto de "Clash" (choque de color). Si la cover es Roja, la sombra usa Verde/Azul para forzar oscuridad.
            * **Secreto Blanco:** Alternancia de paridad para cancelar el color y dejar pasar luz.
            """)

    # --- RESULTADOS ---
    col_secret, col_shares = st.columns([1, 3])
    with col_secret:
        st.markdown("**Secreto original:**")
        st.image(st.session_state["secret_prev"], width=300)
    
    with col_shares:
        st.markdown("**Sombras generadas:**")
        cols = st.columns(len(st.session_state["shares"]))
        for idx, (c, share) in enumerate(zip(cols, st.session_state["shares"])):
            with c:
                st.image(share, caption=f"Participante {idx+1}", width=300)

    st.markdown("---")
    st.subheader("Zona de Pruebas (Drag & Drop)")
    b_list = [components.image_to_base64(img) for img in st.session_state["shares"]]
    components.render_multi_drag_demo(b_list)