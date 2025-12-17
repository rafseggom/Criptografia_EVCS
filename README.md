# EVCS Demo - Visual Cryptography Schemes Implementation

Este proyecto es una implementación interactiva y educacional de varios esquemas de **Criptografía Visual (VCS)** y **Criptografía Visual Extendida (EVCS)**. La aplicación permite descomponer una imagen secreta en varias "sombras" (shares) que, por separado, parecen ruido aleatorio o imágenes inocentes, pero al superponerse revelan el secreto original sin necesidad de computación digital (desencriptación por el sistema visual humano).

Desarrollado en **Python** utilizando **Streamlit** para la interfaz y **NumPy/Pillow** para el procesamiento matricial de imágenes.

##  Instalación y Ejecución Local

Sigue estos pasos para ejecutar la aplicación en tu máquina local.

### Prerrequisitos
* Python 3.8 o superior.
* pip (gestor de paquetes de Python).

### Pasos
1.  **Clonar o descargar el repositorio** con los archivos `app.py`, `logic.py`, `components.py` y `requirements.txt`.

2.  **Instalar dependencias**:
    Se recomienda usar un entorno virtual (`venv`).
    ```bash
    pip install -r requirements.txt
    ```

3.  **Ejecutar la aplicación**:
    ```bash
    streamlit run app.py
    ```

4.  La aplicación se abrirá automáticamente en tu navegador (usualmente en `http://localhost:8501`).

---

##  Fundamentos Teóricos y Algoritmos

El proyecto implementa diferentes "Construcciones" basadas en álgebra lineal sobre cuerpos finitos y manipulación de píxeles. A continuación se detalla la lógica matemática de cada método disponible en el archivo `logic.py`.

### 1. Construcción 1: VCS Clásico (Naor-Shamir, 1994)
Es el esquema $(2,2)$ fundamental en Blanco y Negro.
* **Lógica:** Cada píxel del secreto se expande en un bloque de $2$ subpíxeles (factor de expansión $m=2$).
* **Matemática:**
    * Se define una matriz base $S^0$ (para píxeles blancos) y $S^1$ (para negros).
    * Si el píxel secreto es **Blanco (0)**: Las sombras $S_1$ y $S_2$ tienen patrones idénticos. Al superponerse (operación OR lógica), el peso de Hamming es 1 (gris visual).
    * Si el píxel secreto es **Negro (1)**: Las sombras tienen patrones complementarios. Al superponerse, el peso de Hamming es 2 (negro total).
    * **Seguridad:** Individualmente, cada sombra es ruido aleatorio perfectamente distribuido; no filtra información de Shannon sobre el secreto.

### 2. Construcción 2: Color Black White - VCS (CBW)
Variante del esquema anterior adaptada a color aditivo/sustractivo simulado.
* **Lógica:** En lugar de blanco y negro puro, utiliza una paleta de 6 colores (R, G, B, C, M, Y).
* **Funcionamiento:**
    * Se genera un par de colores aleatorios para la Sombra 1.
    * Si el secreto es **Blanco**, la Sombra 2 copia los colores de la Sombra 1.
    * Si el secreto es **Negro**, la Sombra 2 selecciona el color **complementario** (ej. Rojo $\leftrightarrow$ Cian) para asegurar el máximo contraste ("negro" visual por mezcla sustractiva) al superponerse.

### 3. Construcción 3: CBW-EVCS (Esquema Extendido)
Este es el algoritmo más complejo (basado en *Yang et al.*). A diferencia de los anteriores, las sombras no son ruido, sino que muestran imágenes visibles ("Covers") para engañar a un censor.
* **Matrices de Acceso:** El algoritmo decide el color de los subpíxeles basándose en 3 bits de entrada para cada posición $(x,y)$:
    1.  Bit del Secreto.
    2.  Bit de la Imagen de Cobertura 1.
    3.  Bit de la Imagen de Cobertura 2.
* **Prevención de Ghosting (Ajuste Gamma):**
    En `logic.py`, se aplica una transformación a las imágenes de cobertura antes de procesarlas: `pixel = pixel * 1.5 + 50`.
    * *¿Por qué?* Si las coberturas son muy oscuras (mucha tinta), interferirán con el secreto recuperado. Al aclararlas y reducir su densidad, el secreto (que es negro puro al recuperarse) resalta sobre el "ruido" de las coberturas.
* **Permutación de Columnas:** Para evitar artefactos visuales verticales, las columnas dentro de cada bloque de expansión se permutan aleatoriamente.

### 4. Construcción 4 — CBW‑EVCS Aumentado (Propuesta propia)

Esta construcción es una extensión práctica y experimental inspirada en la Construcción 3 (Yang et al.) pero diseñada para trabajar con imágenes de cobertura “reales” y dividir la carga visual entre N participantes.

- Propósito: permitir que cada participante suba una imagen grande y “realista” (fotografías, logos, páginas) y obtener N sombras que sean individuales y legibles, pero que al superponerse revelen el secreto con alto contraste.
- Idea principal (cómo mejora la Construcción 3):
  - Cada píxel secreto se expande horizontalmente (m=2) y se decide localmente según tres fuentes: secreto, preferencia local de cada cover (texto vs fondo) y la necesidad de mantener el secreto oscuro en la superposición.
  - Para píxeles de fondo (secreto blanco): distribuir colores entre participantes por paridad (por ejemplo, participantes pares obtienen el color y los impares blanco, o viceversa). Esta paridad hace que las contribuciones tiendan a cancelarse visualmente en la superposición, manteniendo el fondo “no-negro”.
  - Para píxeles de secreto (negro): asignar patrones coherentes entre todos los participantes (mismo patrón) para acumular “tinta” y producir negro puro al overlay.
  - Anti‑ghosting: combinación de pre‑aclarado de covers, dithering y permutación aleatoria de subcolumnas para reducir que una cover “se vea” dentro de otra tras superponer.
- Ventajas:
  - Escala a N participantes (cada cover aporta su propia sombra).
  - Funciona con imágenes grandes y con texturas reales (no requiere covers artificiales).
  - Reduce ghosting respecto a un simple mapeo color/compl.
- Limitaciones y notas:
  - Es una proposición práctica — parámetros (preaclarado, paleta, política de paridad) son heurísticos y pueden ajustarse según dataset.
  - El secreto solo es 100% fiable donde la lógica obliga a producir negro puro (complementarios); en regiones mixtas la visibilidad depende de la combinación de covers.
  - Recomendado probar con coberturas que tengan zonas claras/oscuras separadas para maximizar contraste con el secreto.

---

## Resumen de las construcciones

- **Construcción 1** — VCS clásico (Naor–Shamir, 2,2):
  - B/N puro, expansión m=2, seguridad teórica: cada sombra individual no filtra información del secreto.
  - Uso: casos pedagógicos y secretos estrictamente binarios.

- **Construcción 2** — CBW (6 colores: R,G,B,C,M,Y):
  - Versión a color del (2,2): usa pares complementarios para generar negro por mezcla sustractiva.
  - Uso: cuando se quiere contraste fuerte en color; exige 2 sombras.

- **Construcción 3** — CBW‑EVCS (Yang et al., adaptado):
  - Permite sombras que muestran imágenes (covers) y revelan secreto en la superposición.
  - Técnicas clave: pre‑aclarado de covers (reduce tinta), Floyd–Steinberg dithering y permutación de subcolumnas.
  - Objetivo: mantener las coberturas legibles en sus sombras, minimizar ghosting y asegurar que el secreto sea dominante en el overlay.

- **Construcción** 4 : propuesta propia para N participantes y coberturas realistas.

##  Dithering — explicación práctica y motivo de uso

- Método usado: `PIL.Image.convert("1")` → Floyd–Steinberg por defecto en Pillow.
- Por qué: convierte tonos continuos en patrones B/N que el ojo integra como gradientes, preservando bordes y detalles finos tras binarizar. Reduce artefactos que aparecen con un umbral fijo y mejora la legibilidad de secretos y covers tras la generación de sombras.
- Cuándo desactivarlo: si tus entradas ya son binarias (estrictamente B/N) o si quieres un comportamiento determinista sin textura de dithering.

---

##  Estructura del Proyecto

* **`app.py`**: Controlador principal. Maneja la interfaz de Streamlit, la subida de archivos, la selección de algoritmos y la orquestación del flujo.
* **`logic.py`**: El "cerebro" matemático. Contiene las funciones puras que transforman las matrices de imágenes (`generate_bw_vcs`, `generate_evcs_colored`, etc.).
* **`components.py`**: Utilidades de Frontend. Inyecta HTML y JavaScript personalizado para permitir la **demo interactiva de arrastrar y soltar** (Drag & Drop) dentro de Streamlit, permitiendo al usuario probar la superposición manualmente.

##  Notas de Uso
* Para los métodos extendidos (Construcción 3), es crucial subir imágenes de cobertura con buen contraste.
* La "Inversión del secreto" es útil si tu imagen original tiene fondo negro y letras blancas, ya que el algoritmo suele asumir que la información importante es la oscura (tinta).
* Recomendamos usar las imágenes de la carpeta _media_ ya que estan pensadas para facilitar el uso de la aplicación.

---
*Proyecto realizado con fines académicos sobre seguridad visual y esteganografía.*
