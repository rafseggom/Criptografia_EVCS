# EVCSdemo · Criptografía Visual Extendida (Color para secretos B/N)

Demo pedagógica en Streamlit que implementa esquemas de **Extended Visual Cryptography** (EVCS) para ocultar un secreto binario (B/N) dentro de sombras a color con imágenes de cobertura significativas. Incluye un visor interactivo para superponer sombras manualmente o con autoajuste.

---

## 1. ¿Qué resuelve?
La criptografía visual clásica produce sombras con “ruido” sospechoso. EVCS permite que cada sombra sea una imagen a color con sentido (cover), manteniendo seguridad: con una sola sombra no se puede extraer el secreto.

---

## 2. Cómo funciona (resumen teórico)
- **Modelo sustractivo de color:** Las sombras actúan como filtros; el negro se logra bloqueando luz combinando colores diferentes, el “blanco” deja pasar la luz si los colores coinciden.
- **Matrices base:** Se usan dos colecciones: una para píxeles blancos (patrones iguales entre sombras) y otra para píxeles negros (patrones complementarios). Al superponer, los negros bloquean luz y revelan el contorno del secreto.
- **Expansión de píxel (m):** Un píxel del secreto se expande a subpíxeles en cada sombra:
  - Construcción 1 (Básica RGB): m = 2 (horizontal), contraste estándar.
  - Construcción 2 (Complementarios): m = 2 (horizontal), usa color y complementario para más contraste.
  - Construcción 3 (Perfect Black): m = 4 (2×2), negros sólidos y revelado más nítido.
- **k, n (extensión experimental en la app):** Para n≤5 se generan sombras múltiples (demo k=n). Para 2 participantes se muestran también visor y autoajuste.

Referencia principal: C.-N. Yang et al., “Extended color visual cryptography for black and white secret image,” *Theoretical Computer Science*, 2015.

---

## 3. Funcionalidades
- Tema claro (apto para proyector).
- Tres esquemas: Básico, Complementarios, Perfect Black (2 participantes).
- Generación de sombras con imágenes de cobertura cargadas por el usuario.
- Visor interactivo:
  - Pestaña **2 participantes**: arrastre y botón de **Ajustar automáticamente**.
  - Pestaña **+2 participantes**: slider de hasta 5 sombras, con visor multi-arrastre y autoajuste n y n−1.
- Previsualización de secreto binarizado y cobertura normalizada.

---

## 4. Requisitos
- Python 3.10+ (probado en Windows)
- Paquetes: `streamlit`, `Pillow`, `numpy` (añade otros si tu entorno lo requiere)

---

## 5. Instalación y ejecución local
1) Crea y activa un entorno (opcional, recomendado).
2) Instala dependencias:
```bash
pip install streamlit pillow numpy
```
3) Ejecuta la app:
```bash
streamlit run app.py
```
4) Abre el enlace local que muestra Streamlit (por defecto http://localhost:8501).

---

## 6. Uso rápido
1) Sube la imagen **Secreto B/N** y la **Cobertura** (color).
2) Elige la **Construcción** y el **Tamaño base**.
3) En la pestaña **2 participantes**, pulsa **Generar sombras (2)** y usa la demostración.
4) En **+2 participantes**, selecciona n (3–5) y pulsa **Generar sombras (n participantes)**; usa el laboratorio para mover/autoajustar.

---

## 7. Estructura del repo (principal)
- `app.py` — UI Streamlit, pestañas de 2 y n participantes, autoajuste.
- `logic.py` — Preparación de imágenes, generadores de sombras para 2 y multi.
- `components.py` — Visores HTML (drag/drop, autoajuste).
- `resumen.md` — Resumen técnico del paper.
- `README.md` — Este documento.

---

## 8. Limitaciones actuales
- Perfect Black solo en modo 2 participantes.
- La demo multiusa un esquema básico extendido (k=n). El contraste puede variar según n y covers.
- No se incluyen matrices optimizadas para todos los (k, n); foco pedagógico.

---

## 9. Despliegue
- Local: `streamlit run app.py`.
- Streamlit Community Cloud: sube a GitHub y crea la app en https://share.streamlit.io.
- Otros PaaS: configura el entrypoint apuntando a `streamlit run app.py`.

---

## 10. Créditos
Implementación basada en la idea de **Extended Color Visual Cryptography** (Yang et al., 2015) adaptada a una demo educativa con Streamlit.