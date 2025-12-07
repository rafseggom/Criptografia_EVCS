import streamlit as st
import components
import logic


st.set_page_config(
    page_title="CBW-EVCS Demo",
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

st.title("🔐 Criptografía Visual Extendida (CBW-EVCS)")
st.caption("Demo pedagógica en tema claro: tres construcciones, arrastre con snapping y alineado automático.")

if "generated" not in st.session_state:
    st.session_state.generated = False

col_a, col_b, col_c = st.columns([1, 1, 1], gap="large")

with col_a:
    st.subheader("1. Entradas")
    secret_file = st.file_uploader("Secreto B/N", type=["png", "jpg", "jpeg"])
    cover_file = st.file_uploader("Imagen de cobertura (Color)", type=["png", "jpg", "jpeg"])
    invert_secret = st.checkbox("Invertir secreto", value=False)
    dither = st.checkbox("Dithering suave (recomendado)", value=True)

with col_b:
    st.subheader("2. Construcción")
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

with col_c:
    st.subheader("3. Generar")
    st.write("Crea dos sombras a color para 2 participantes.")
    run = st.button("🚀 Generar sombras", use_container_width=True, type="primary")

st.markdown("---")

def _generate():
    if not secret_file or not cover_file:
        st.warning("Carga una imagen de secreto y otra de cobertura para continuar.")
        return
    with st.spinner("Aplicando EVCS y expansión de píxel..."):
        secret_preview, cover_img, mask, cover_arr = logic.prepare_inputs(
            secret_file, cover_file, invert=invert_secret, size=size, dither=dither
        )
        if "Básico" in algo:
            s1, s2 = logic.generate_basic(mask, cover_arr)
        elif "Complementarios" in algo:
            s1, s2 = logic.generate_complementary(mask, cover_arr)
        else:
            s1, s2 = logic.generate_perfect_black(mask, cover_arr)
        merged = logic.overlay(s1, s2)
    st.session_state.update(
        {
            "secret_prev": secret_preview,
            "cover_prev": cover_img,
            "s1": s1,
            "s2": s2,
            "merged": merged,
            "generated": True,
        }
    )


if run:
    _generate()

if st.session_state.get("generated"):
    prev_col1, prev_col2, prev_col3 = st.columns([1, 1, 1])
    with prev_col1:
        st.image(st.session_state["secret_prev"], caption="Secreto binarizado", use_container_width=True)
    with prev_col2:
        st.image(st.session_state["cover_prev"], caption="Cobertura normalizada", use_container_width=True)
    with prev_col3:
        dims = st.session_state["s1"].size
        st.metric("Resolución sombras", f"{dims[0]}x{dims[1]}")

    st.subheader("Sombras generadas")
    share_a, share_b = st.columns(2)
    with share_a:
        st.image(st.session_state["s1"], caption="Participante 1", use_container_width=True)
    with share_b:
        st.image(st.session_state["s2"], caption="Participante 2", use_container_width=True)

    st.markdown("---")
    st.subheader("Recuperación del secreto")
    tab_manual, tab_auto = st.tabs(["👆 Manual con snapping", "✨ Auto-merge"])

    with tab_manual:
        st.caption("Arrastra y alinea; con 'Ajustar automáticamente' se superponen al centro sin desplazamiento.")
        b1 = components.image_to_base64(st.session_state["s1"])
        b2 = components.image_to_base64(st.session_state["s2"])
        w, h = st.session_state["s1"].size
        components.render_drag_drop_demo(b1, b2, width=w, height=h, snap=16)

    with tab_auto:
        st.caption("Superposición matemática perfecta (Multiply).")
        st.image(st.session_state["merged"], caption="Secreto revelado", use_container_width=True)
else:
    st.info("Sube las imágenes, elige construcción y pulsa Generar sombras.")