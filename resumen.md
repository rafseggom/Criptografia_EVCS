# Resumen Técnico: Extended Color Visual Cryptography for Black and White Secret Image

**Asignatura:** Criptografía  
**Referencia del Paper:** Yang, C.N., et al. (2015). *Theoretical Computer Science*.

---

## 1. Introducción y Objetivo del Trabajo

### El Problema
 La **Criptografía Visual (VCS)** tradicional permite compartir un secreto dividiéndolo en transparencias (*shadows*) que, al superponerse, revelan la información sin necesidad de computación.
 Sin embargo, los esquemas clásicos tienen un defecto: las transparencias parecen **ruido aleatorio** ("nieve"), lo cual es sospechoso y alerta a un atacante de la existencia de un secreto.

### La Solución Propuesta (CBW-EVCS)
El artículo presenta un esquema de **Criptografía Visual Extendida (EVCS)** con las siguientes características:
1.   **Secreto:** Una imagen en **Blanco y Negro** (binaria).
2.   **Sombras:** Transparencias a **Color** que muestran imágenes con significado (*cover images*) en lugar de ruido.
3.  **Mecanismo:** Usa la mezcla sustractiva de colores para ocultar el secreto dentro de imágenes visibles.

---

## 2. Fundamentos Técnicos

### 2.1. Mezcla de Colores (Modelo Sustractivo)
A diferencia de las pantallas (que suman luz), las transparencias funcionan como filtros o tintas: **bloquean la luz**.
* **Negro ($\bullet$):** Se consigue mediante el bloqueo total de luz.  Esto ocurre al superponer colores opuestos o diferentes (ej. Rojo + Verde).
* **"Blanco" ($\circ$):** En este contexto, significa "paso de luz/color".  Se consigue cuando las transparencias coinciden en el mismo color (ej. Rojo sobre Rojo deja pasar luz roja).

### 2.2. Matrices Base
 El sistema utiliza dos colecciones de matrices para repartir los píxeles:
* **$C_{\bullet}$ (Para cifrar un píxel Negro):** Las columnas contienen colores diferentes para asegurar el bloqueo de luz.
* **$C_{\circ}$ (Para cifrar un píxel Blanco):** Las columnas contienen colores iguales para permitir el paso de luz.

---

## 3. El Algoritmo Principal: Construcción 1 (RGB)

Este es el núcleo matemático del trabajo para un esquema $(2, 2)$ (2 usuarios, ambos necesarios).

### Características
*  **Colores usados:** Conjunto $S^{(1)} = \{R, G, B\}$.
* **Expansión de Píxel ($m=2$):** Cada píxel original se convierte en **2 subpíxeles** en la transparencia.  Esto es necesario para tener "espacio de maniobra" y poder mostrar la imagen de cubierta sin romper el secreto.

### Lógica de Asignación (La Ecuación 2)
 El algoritmo decide qué colores poner en los subpíxeles basándose en tres variables: el color deseado para el Secreto, para el Usuario 1 y para el Usuario 2.

#### Ejemplo de Funcionamiento (Caso 1: Ambas cubiertas son color)
* **Si el Secreto es Negro:** El algoritmo asigna un color al Usuario 1 y un color **diferente** ($S^{(2)}$) al Usuario 2. Al juntarse, chocan y producen negro.
* **Si el Secreto es Blanco:** El algoritmo asigna el **mismo** color ($=$) al Usuario 1 y al 2 en el primer subpíxel. Al juntarse, pasa la luz.

> **Nota Técnica Importante:** En la Construcción 1, el "Blanco" del secreto tiene un brillo del 50% (1 subpíxel con luz, 1 negro) para igualar la calidad con las zonas oscuras de la imagen.  El contraste resultante es $\alpha = 1/2$.

---

## 4. Mejoras y Generalización

### 4.1. Construcción 2: Añadiendo CMY
 Para mejorar la calidad visual, se expande la paleta de colores a $\{R, G, B, C, M, Y\}$.
* **Ventaja:** Al tener más colores y sus complementarios, se mejora la flexibilidad para generar las imágenes de cubierta.
*  **Resultado:** El contraste de las sombras mejora del 33% al **50%**, haciendo las imágenes más nítidas.

### 4.2. Esquemas Perfect Black (PB)
 En construcciones más complejas (Construcción 5 y 6), se garantiza que el negro del secreto sea **oscuridad absoluta** (sin fugas de luz), lo que maximiza el contraste del mensaje recuperado.

### 4.3. Escalabilidad $(k, n)$
 El *paper* demuestra que el sistema puede escalar a más usuarios (ej. 3 de 3, 2 de n) aumentando el tamaño de las matrices de forma logarítmica, lo que mantiene la expansión de píxel ($m$) controlada.

---

## 5. Resultados y Conclusiones

### Evidencia Experimental
* **Fig. 4 (RGB):** Muestra cómo las sombras "S1" y "S2" revelan el secreto "EVCS".  El fondo tiene cierto ruido.
* **Fig.  5 (RGB+CMY):** Muestra una mejora significativa en la claridad de las imágenes de cubierta.
* **Fig.  9 (Perfect Black):** Muestra el secreto "EVCS" con un negro sólido y perfecto contraste.

### Conclusión Final
El esquema propuesto consigue resolver el problema de las "sombras sospechosas" de la criptografía visual clásica.  Permite esconder un secreto en B/N dentro de imágenes a color con significado, manteniendo la seguridad matemática (un usuario por sí solo no ve nada del secreto) y con una expansión de píxel muy eficiente ($m=2$ en el caso básico).