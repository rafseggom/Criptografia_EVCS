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
      #MainMenu {display: none;}
      header {visibility: hidden;}
      footer {visibility: hidden;}
      .block-container {padding-top: 1rem; padding-bottom: 2.5rem;}
      .stButton > button {background: #111827; color: white; border-radius: 10px; padding: 0.65rem 1.1rem; border: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔐 EVCSdemo · Criptografía Visual Extendida")
st.caption("Demo pedagógica para mostrar el funcionamiento de EVCS con diferentes construcciones.")

if "generated" not in st.session_state:
    st.session_state.generated = False

col_a, col_b = st.columns([1, 1], gap="large")

with col_a:
    st.subheader("Secreto")
    secret_file = st.file_uploader("Imagen de secreto B/N", type=["png", "jpg", "jpeg"], key="secret_in")
    invert_secret = st.checkbox("Invertir secreto", value=False)
    dither = st.checkbox("Dithering suave (recomendado)", value=True)

with col_b:
    st.subheader("Construcción")
    algo = st.radio(
        "Elige esquema",
        (
            "Construcción 1 · Básico RGB",
            "Construcción 2 · Complementarios",
            "Construcción 3 · Perfect Black",
        ),
        index=2,
    )
    size = st.slider("Tamaño base (px)", 320, 900, 640, step=40)
    if "Básico" in algo:
        st.caption("m=2 horizontal, contraste estándar y colores originales.")
    elif "Complementarios" in algo:
        st.caption("m=2 horizontal, usa color y complementarios para mayor contraste.")
    else:
        st.caption("m=4 (2x2), negro sólido y revelado nítido.")

st.markdown("---")

# Sección de imágenes de cobertura personalizadas
st.subheader("📸 Imágenes de cobertura (una por participante)")
st.caption("Sube una imagen de cobertura para cada participante. El número de imágenes determina el número de participantes.")

# Usar columnas para mostrar los uploader de forma horizontal
cover_files = [None] * 5 
max_participants = 5
cols = st.columns(max_participants)

for i in range(max_participants):
    with cols[i]:
        cover_file = st.file_uploader(
            f"Persona {i+1}",
            type=["png", "jpg", "jpeg"],
            key=f"cover_person_{i}"
        )
        if cover_file is not None:
            cover_files[i] = cover_file

# Filtrar solo los archivos cargados (mantener el orden)
cover_files = [f for f in cover_files if f is not None]

# Determinar número de participantes según archivos subidos
n_participants = len(cover_files)

st.markdown("---")

def _generate_2():
    if not secret_file or n_participants != 2:
        st.warning("Carga el secreto y exactamente 2 imágenes de cobertura para continuar.")
        return
    with st.spinner("Aplicando EVCS y expansión de píxel..."):
        secret_preview, cover_img1, mask, cover_arr1 = logic.prepare_inputs(
            secret_file, cover_files[0], invert=invert_secret, size=size, dither=dither
        )
        _, cover_img2, _, cover_arr2 = logic.prepare_inputs(
            secret_file, cover_files[1], invert=invert_secret, size=size, dither=dither
        )
        
        if "Básico" in algo:
            s1, s2 = logic.generate_basic(mask, cover_arr1)
            s1_p2, s2_p2 = logic.generate_basic(mask, cover_arr2)
        elif "Complementarios" in algo:
            s1, s2 = logic.generate_complementary(mask, cover_arr1)
            s1_p2, s2_p2 = logic.generate_complementary(mask, cover_arr2)
        else:
            s1, s2 = logic.generate_perfect_black(mask, cover_arr1)
            s1_p2, s2_p2 = logic.generate_perfect_black(mask, cover_arr2)
        
        merged = logic.overlay(s1, s2)
    
    st.session_state.update(
        {
            "secret_prev": secret_preview,
            "cover_prev": [cover_img1, cover_img2],
            "s1": s1,
            "s2": s2,
            "merged": merged,
            "generated": True,
        }
    )


def _generate_multi():
    if not secret_file or n_participants < 2:
        st.warning(f"Carga el secreto y al menos 2 imágenes de cobertura para continuar.")
        return
    
    if "Perfect Black" in algo and n_participants != 2:
        st.warning("Perfect Black está disponible solo para 2 participantes en esta demo. Usa Básico o Complementarios.")
        return
    
    with st.spinner("Aplicando EVCS con sombras personalizadas..."):
        secret_preview, _, mask, _ = logic.prepare_inputs(
            secret_file, cover_files[0], invert=invert_secret, size=size, dither=dither
        )
        # Preparar todas las imágenes de cobertura
        cover_arrs = [
            logic.prepare_inputs(secret_file, cover_file, invert=invert_secret, size=size, dither=dither)[3]
            for cover_file in cover_files
        ]
        
        cover_previews = [
            logic.prepare_inputs(secret_file, cover_file, invert=invert_secret, size=size, dither=dither)[1]
            for cover_file in cover_files
        ]
        
        if "Básico" in algo:
            shares = logic.generate_basic_multi(mask, cover_arrs)
        elif "Complementarios" in algo:
            shares = logic.generate_complementary_multi(mask, cover_arrs)
        else:
            # Perfect Black solo para 2 participantes
            shares = logic.generate_basic_multi(mask, cover_arrs)
    
    st.session_state.update({
        "secret_prev_multi": secret_preview,
        "cover_prev_multi": cover_previews,
        "shares_multi": shares,
        "generated_multi": True,
        "n_part": n_participants,
    })


# Mostrar botones según número de participantes
if n_participants == 2:
    run2 = st.button("🚀 Generar sombras (2 participantes)", width='stretch', type="primary")
    if run2:
        _generate_multi()

    if st.session_state.get("generated_multi"):
        with st.expander("ℹ️ Cómo funciona el esquema elegido", expanded=False):
            if "Básico" in algo:
                st.markdown("""
                **Construcción 1: Básico RGB (m=2)**
                
                Para cada píxel del secreto:
                - **Píxel NEGRO**: Ambas sombras generan el mismo patrón [Color | Blanco]
                  - Al superponer: Color × Blanco = **Negro** ✓
                - **Píxel BLANCO**: Las sombras generan patrones complementarios
                  - Sombra 1: [Color | Blanco] | Sombra 2: [Blanco | Color]
                  - Al superponer: Todos los píxeles se cancelan = **Blanco** ✓
                
                Cada participante usa su propia imagen de cobertura, garantizando privacidad.
                """)
            elif "Complementarios" in algo:
                st.markdown("""
                **Construcción 2: Complementarios RGB+CMY (m=2)**
                
                Utiliza colores complementarios para mayor contraste:
                - **Píxel NEGRO**: Ambas sombras: [Color | Color_Inverso]
                  - Al superponer: Color × Inverso = **Negro** ✓
                - **Píxel BLANCO**: Patrones cruzados que se anulan
                  - Sombra 1: [Color | Inverso] | Sombra 2: [Inverso | Color]
                  - Resultado final: **Blanco** ✓
                
                Mayor separación de valores garantiza mejor visibilidad del secreto.
                """)
            else:
                st.markdown("""
                **Construcción 3: Perfect Black (m=4)**
                
                Expansión 2×2 con máximo contraste:
                - **Píxel NEGRO**: Ambas sombras comparten diagonal = **Negro puro**
                - **Píxel BLANCO**: Diagonales intercambiadas = **Blanco puro**
                
                Resultado: Revelado nítido sin grises intermedios.
                """)

        st.subheader("Resultado")
        col_secret, col_shares = st.columns([1, 3])
        
        with col_secret:
            st.markdown("**Secreto:**")
            st.image(st.session_state["secret_prev_multi"], width='stretch')
        
        with col_shares:
            st.markdown("**Sombras:**")
            shares = st.session_state["shares_multi"]
            n_cols = min(4, len(shares))
            
            for row_start in range(0, len(shares), n_cols):
                row_end = min(row_start + n_cols, len(shares))
                cols = st.columns(row_end - row_start)
                for idx, col in enumerate(cols):
                    share_idx = row_start + idx
                    with col:
                        st.image(shares[share_idx], caption=f"P{share_idx+1}", width='stretch')

        st.markdown("---")
        st.subheader("Recuperación del secreto")
        st.caption("Arrastra y alinea las sombras para revelar el secreto.")
        b_list = [components.image_to_base64(img) for img in st.session_state["shares_multi"]]
        components.render_multi_drag_demo(b_list, height=820)

elif n_participants > 2:
    run_multi = st.button("🚀 Generar sombras (n participantes)", width='stretch', type="secondary")
    if run_multi:
        _generate_multi()

    if st.session_state.get("generated_multi"):
        with st.expander("ℹ️ Cómo funciona el esquema elegido", expanded=False):
            if "Básico" in algo:
                st.markdown("""
                **Construcción 1: Básico RGB (m=2, n participantes)**
                
                Extensión de Yang et al. (2015) para n participantes:
                - **Píxel NEGRO**: TODAS las sombras generan el mismo patrón
                  - Al multiplicar n sombras: Color^n = **Negro** ✓
                - **Píxel BLANCO**: Cada sombra genera un patrón diferente (índice par/impar)
                  - Patrones complementarios se cancelan al multiplicar todas = **Blanco** ✓
                
                Cada participante i recibe una sombra única generada con su imagen de cobertura.
                Solo al superponer TODAS se recupera el secreto.
                """)
            elif "Complementarios" in algo:
                st.markdown("""
                **Construcción 2: Complementarios (m=2, n participantes)**
                
                Adaptación a múltiples participantes:
                - **Píxel NEGRO**: Todas: [Color | Inverso]
                  - Multiplicación de n sombras = **Negro sólido** ✓
                - **Píxel BLANCO**: Patrones alterados por índice
                  - La distribución par/impar garantiza cancelación = **Blanco** ✓
                
                Mejor contraste que Básico para revelado visual claro.
                """)

        st.subheader("Resultado")
        col_secret, col_shares = st.columns([1, 3])
        
        with col_secret:
            st.markdown("**Secreto:**")
            st.image(st.session_state["secret_prev_multi"], width='stretch')
        
        with col_shares:
            st.markdown("**Sombras:**")
            shares = st.session_state["shares_multi"]
            n_cols = min(4, len(shares))
            
            for row_start in range(0, len(shares), n_cols):
                row_end = min(row_start + n_cols, len(shares))
                cols = st.columns(row_end - row_start)
                for idx, col in enumerate(cols):
                    share_idx = row_start + idx
                    with col:
                        st.image(shares[share_idx], caption=f"P{share_idx+1}", width='stretch')

        st.markdown("---")
        st.subheader("Laboratorio n participantes")
        st.caption("Arrastra múltiples sombras. Usa los botones para alinear todo (n) o todas menos una (n-1).")
        b_list = [components.image_to_base64(img) for img in st.session_state["shares_multi"]]
        components.render_multi_drag_demo(b_list, height=820)

else:
    st.info("👆 Sube imágenes de cobertura en los campos de arriba. El número de imágenes determina el número de participantes.")