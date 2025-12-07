import streamlit as st
import logic
import components
import os

st.set_page_config(
    page_title="Lab Criptografía Visual",
    layout="wide",
    page_icon="🧪",
    initial_sidebar_state="expanded"
)

# --- SIDEBAR ---
st.sidebar.title("🧪 Lab Criptográfico")
st.sidebar.markdown("---")

algoritmo = st.sidebar.radio(
    "Selecciona Algoritmo:",
    [
        "1. Construction 1 (Básico)",
        "2. Construction 2 (Complementarios)",
        "3. Perfect Black (Recomendado)"
    ]
)

st.sidebar.info("Sube las imágenes para comenzar.")
secret_file = st.sidebar.file_uploader("1. Imagen Secreta (B/N)", type=["png", "jpg", "jpeg"], key="sec")
cover_file = st.sidebar.file_uploader("2. Imagen Cobertura (Color)", type=["png", "jpg", "jpeg"], key="cov")

# --- APP ---
st.title("🔐 Criptografía Visual Extendida")
st.markdown("### Simulación de Esquema (2,2) - Dos Participantes")

# Mensajes de ayuda según algoritmo
if "Construction 1" in algoritmo:
    st.info("🔹 **Construcción 1:** Expansión $m=2$. Usa transparencia. El contraste es moderado.")
elif "Construction 2" in algoritmo:
    st.warning("🔸 **Construcción 2:** Usa colores invertidos. **Nota:** Las sombras se verán con colores extraños (tipo negativo) para maximizar el contraste al superponerse. Es normal que parezcan 'Marte'.")
else:
    st.success("✅ **Perfect Black:** Expansión $m=4$. Garantiza opacidad total en el negro. Es el método más seguro y visualmente limpio.")

if secret_file and cover_file:
    # 1. Previsualización
    col1, col2 = st.columns(2)
    s_img, c_img = logic.process_images(secret_file, cover_file)
    with col1:
        st.image(s_img, caption="Secreto Original", width=150)
    with col2:
        st.image(c_img, caption="Cobertura Original", width=150)
    
    if st.button("🚀 Generar Sombras para 2 Personas", type="primary", use_container_width=True):
        with st.spinner("Cifrando..."):
            if "Construction 1" in algoritmo:
                share1, share2 = logic.generate_rgb_basic(s_img, c_img)
            elif "Construction 2" in algoritmo:
                share1, share2 = logic.generate_cmy_complementary(s_img, c_img)
            else:
                share1, share2 = logic.generate_perfect_black(s_img, c_img)
            
            st.session_state['s1'] = share1
            st.session_state['s2'] = share2
            st.session_state['generated'] = True

    # 2. Resultados
    if st.session_state.get('generated'):
        st.divider()
        st.subheader("1. Distribución de Sombras (Shares)")
        st.markdown("""
        Cada participante recibe **una imagen aleatoria**. Por separado parecen ruido o la imagen de cobertura, 
        pero **ninguno puede ver el secreto** sin el otro.
        """)
        
        c1, c2 = st.columns(2)
        with c1:
            st.image(st.session_state['s1'], caption="👤 Participante 1 (Sombra A)", use_container_width=True)
        with c2:
            st.image(st.session_state['s2'], caption="👤 Participante 2 (Sombra B)", use_container_width=True)
            
        st.divider()
        st.subheader("2. Reconstrucción del Secreto")
        
        tab1, tab2 = st.tabs(["👆 Manual (Arrastrar)", "🪄 Automático (Botón)"])
        
        with tab1:
            st.write("Arrastra la imagen del **borde ROJO** sobre la del **borde AZUL**.")
            b64_1 = components.image_to_base64(st.session_state['s1'])
            b64_2 = components.image_to_base64(st.session_state['s2'])
            components.render_drag_drop_demo(b64_1, b64_2)
            
        with tab2:
            st.write("Si el arrastre es difícil, pulsa aquí para ver la superposición matemática perfecta.")
            if st.button("🪄 Revelar Secreto (Unir Sombras)"):
                final_img = logic.superimpose_images(st.session_state['s1'], st.session_state['s2'])
                st.image(final_img, caption="Secreto Revelado (Superposición Perfecta)", use_container_width=True)

else:
    st.info("Sube las imágenes para empezar.")