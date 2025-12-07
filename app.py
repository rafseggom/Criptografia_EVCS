import streamlit as st
import logic
import components
from PIL import Image
import io

st.set_page_config(page_title="ECVC Demo", layout="wide", page_icon="🔐")

# TEMA CLARO
st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1.5rem;}
    body {background: #fff; color: #000;}
    h1, h2, h3 {color: #1a1a1a; font-weight: 600;}
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white; border: none; border-radius: 8px;
        padding: 14px 28px; font-size: 17px; font-weight: 700;
        box-shadow: 0 4px 15px rgba(102,126,234,0.4);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102,126,234,0.6);
    }
</style>
""", unsafe_allow_html=True)

st.title("🔐 Extended Color Visual Cryptography")
st.markdown("**Demo para clase** - Oculta secretos B/N en sombras a color")

st.divider()

col1, col2, col3 = st.columns([1.2, 1, 0.8])

with col1:
    st.subheader("📥 Imágenes")
    secret_file = st.file_uploader("Secreto (B/N)", type=["png", "jpg", "jpeg"], key="secret")
    invert = st.checkbox("Invertir secreto", value=False)
    cover_file = st.file_uploader("Cobertura (Color)", type=["png", "jpg", "jpeg"], key="cover")

with col2:
    st.subheader("⚙️ Algoritmo")
    algo = st.radio("Construcción:", ["RGB Básico (m=2)", "Complementarios (m=2)", "Perfect Black (m=4) ⭐"], index=2)
    st.caption({"RGB Básico (m=2)": "Expansión 1×2, contraste estándar", "Complementarios (m=2)": "Expansión 1×2, usa inversos", "Perfect Black (m=4) ⭐": "Expansión 2×2, negro perfecto"}[algo])

with col3:
    st.subheader("▶️ Acción")
    st.write("")
    run = st.button("🚀 GENERAR", type="primary", use_container_width=True)

st.divider()

# --- RESULTADOS ---
if secret_file and cover_file and run_btn:
    s_img, c_img = logic.process_images(secret_file, cover_file, invert_chk)
    
    with st.spinner("Aplicando criptografía visual (Pixel Expansion)..."):
        if "Construcción 1" in algoritmo:
            s1, s2 = logic.generate_rgb_basic(s_img, c_img)
        elif "Construcción 2" in algoritmo:
            s1, s2 = logic.generate_cmy_complementary(s_img, c_img)
        else:
            s1, s2 = logic.generate_perfect_black(s_img, c_img)
        
        # Guardar en sesión
        st.session_state['s1'] = s1
        st.session_state['s2'] = s2
        st.session_state['generated'] = True

if st.session_state.get('generated'):
    
    st.subheader("📊 Distribución de Sombras")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.image(st.session_state['s1'], caption="Sombra Participante 1", use_container_width=True)
    with col_s2:
        st.image(st.session_state['s2'], caption="Sombra Participante 2", use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("�️‍♂️ Recuperación del Secreto")
    
    # Pestañas limpias
    tab1, tab2 = st.tabs(["👆 Manual (Arrastrar)", "✨ Automático"])
    
    with tab1:
        st.caption("Arrastra la imagen del borde ROJO sobre la del borde AZUL. El fondo blanco simula una mesa de luz.")
        b1 = components.image_to_base64(st.session_state['s1'])
        b2 = components.image_to_base64(st.session_state['s2'])
        components.render_drag_drop_demo(b1, b2)
        
    with tab2:
        st.caption("Superposición matemática perfecta (Multiply).")
        final = logic.superimpose_images(st.session_state['s1'], st.session_state['s2'])
        
        # Centrar la imagen resultante
        col_buf1, col_img, col_buf2 = st.columns([1, 2, 1])
        with col_img:
            st.image(final, caption="Secreto Revelado", use_container_width=True)

elif not secret_file or not cover_file:
    # Mensaje inicial vacío o de bienvenida
    pass