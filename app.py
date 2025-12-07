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
st.caption("Demo pedagógica en tema claro: tres construcciones, arrastre con snapping y alineado automático.")

if "generated" not in st.session_state:
    st.session_state.generated = False

col_a, col_b = st.columns([1, 1], gap="large")

with col_a:
    st.subheader("Entradas")
    secret_file = st.file_uploader("Secreto B/N", type=["png", "jpg", "jpeg"], key="secret_in")
    cover_file = st.file_uploader("Imagen de cobertura (Color)", type=["png", "jpg", "jpeg"], key="cover_in")
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


tab_main1, tab_main2 = st.tabs(["2 participantes", "+2 participantes"])

with tab_main1:
    run2 = st.button("🚀 Generar sombras (2)", use_container_width=True, type="primary")
    if run2:
        _generate()

    if st.session_state.get("generated"):
        st.subheader("Cómo funciona el esquema elegido")
        if "Básico" in algo:
            st.markdown("- Construcción 1 (RGB, m=2): cada píxel se expande a dos subpíxeles horizontales. Si el secreto es blanco, ambos participantes reciben el mismo patrón; si es negro, reciben patrones complementarios que bloquean la luz al superponerse.")
        elif "Complementarios" in algo:
            st.markdown("- Construcción 2 (RGB+CMY, m=2): usa el color y su complementario en cada par de subpíxeles para aumentar contraste. Blanco: patrones iguales; negro: patrones invertidos, logrando opacidad.")
        else:
            st.markdown("- Construcción 3 (Perfect Black, m=4): cada píxel se convierte en un bloque 2x2. Blanco: ambos comparten el mismo patrón diagonal; negro: se intercambian las diagonales, produciendo negro sólido al superponer.")

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
        tab_manual, = st.tabs(["👆 Demostración"])

        with tab_manual:
            st.caption("Arrastra y alinea; con 'Ajustar automáticamente' se superponen al centro sin desplazamiento.")
            b1 = components.image_to_base64(st.session_state["s1"])
            b2 = components.image_to_base64(st.session_state["s2"])
            w, h = st.session_state["s1"].size
            components.render_drag_drop_demo(b1, b2, width=w, height=h)
    else:
        st.info("Sube las imágenes, elige construcción y pulsa Generar sombras (2 participantes).")

with tab_main2:
    n_part = st.slider("Número de participantes", 3, 5, 3, 1)
    run_multi = st.button("🚀 Generar sombras (n participantes)", use_container_width=True, type="secondary")
    if run_multi:
        if not secret_file or not cover_file:
            st.warning("Carga una imagen de secreto y otra de cobertura para continuar.")
        elif "Perfect Black" in algo:
            st.warning("Perfect Black está disponible solo para 2 participantes en esta demo. Usa Básico o Complementarios.")
        else:
            secret_preview, cover_img, mask, cover_arr = logic.prepare_inputs(
                secret_file, cover_file, invert=invert_secret, size=size, dither=dither
            )
            if "Básico" in algo:
                shares = logic.generate_basic_multi(mask, cover_arr, n_part)
            else:
                shares = logic.generate_basic_multi(mask, cover_arr, n_part)  # usamos básica extendida como demo
            st.session_state.update({
                "secret_prev_multi": secret_preview,
                "cover_prev_multi": cover_img,
                "shares_multi": shares,
                "generated_multi": True,
                "n_part": n_part,
            })

    if st.session_state.get("generated_multi"):
        st.subheader("Sombras generadas (n participantes)")
        st.caption("Demo k=n: todas las sombras son necesarias. Para contrastes óptimos, recomendamos n≤5.")
        cols = st.columns(min(st.session_state["n_part"], 3))
        for idx, share in enumerate(st.session_state["shares_multi"]):
            target_col = cols[idx % len(cols)]
            with target_col:
                st.image(share, caption=f"Participante {idx+1}", use_container_width=True)

        st.markdown("---")
        st.subheader("Laboratorio n participantes")
        st.caption("Arrastra múltiples sombras. Usa los botones para alinear todo (n) o todas menos una (n-1).")
        b_list = [components.image_to_base64(img) for img in st.session_state["shares_multi"]]
        components.render_multi_drag_demo(b_list, height=820)
    else:
        st.info("Elige n (3-5) y pulsa Generar sombras (n participantes).")