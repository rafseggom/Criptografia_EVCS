import numpy as np
from PIL import Image, ImageChops, ImageOps

def prepare_inputs(secret_file, cover_file, *, invert=False, size=640, dither=True):
    """
    Preprocesamiento de imágenes para el algoritmo criptográfico.
    
    Lógica Matemática:
    1. Redimensionado para igualar matrices.
    2. Binarización del secreto: EVCS requiere que el mensaje sea binario (0 o 1).
       Se aplica un umbral (thresholding) o dithering para convertir escala de grises a 1-bit.
    3. Normalización del cover: Se mantiene en RGB (uint8) para aplicar mezcla de color.
    """
    secret = Image.open(secret_file).convert("L").resize((size, size))
    if invert:
        secret = ImageOps.invert(secret)

    if dither:
        secret_bw = secret.convert("1")
    else:
        # Umbral matemático: x >= 128 -> 1 (Blanco), x < 128 -> 0 (Negro)
        secret_bw = secret.point(lambda x: 255 if x >= 128 else 0, mode="1")

    cover = Image.open(cover_file).convert("RGB").resize((size, size))
    
    # Conversión a matrices booleanas y numéricas para operaciones vectoriales
    # secret_mask: True=Blanco (Luz), False=Negro (Tinta/Opacidad)
    secret_mask = np.array(secret_bw, dtype=bool) 
    cover_arr = np.array(cover, dtype=np.uint8)
    
    return secret_bw.convert("L"), cover, secret_mask, cover_arr


def overlay(share1, share2):
    """
    Simulación del proceso físico de superposición de transparencias.
    
    Matemática:
    Se modela como una mezcla sustractiva de colores.
    Operación: R = S1 * S2 (Multiply Blend Mode).
    Si un píxel es negro (0) en S1, el resultado será negro (0) independientemente de S2.
    """
    return ImageChops.multiply(share1.convert("RGB"), share2.convert("RGB"))


def generate_basic(secret_mask, cover_arr, *, seed=None):
    """
    Construcción 1: EVCS Básico RGB con expansión m=2.
    Referencia: Yang et al. (2015), Ec. 2.
    
    Principio Matemático:
    - Se definen dos conjuntos de colores ortogonales S(1) y S(2).
    - Para generar NEGRO, se superpone un color C con un color de "choque" (Clash).
      Rojo * Verde ~= Negro (en modelo sustractivo ideal).
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    white = np.array([255, 255, 255], dtype=np.uint8)

    # Cálculo vectorial del "Color de Choque" (Clash)
    # Se rota el array de colores 1 posición en el eje de canales: (R,G,B) -> (G,B,R).
    # Esto asegura que S1 y S2 tengan colores diferentes en el mismo píxel para el caso negro.
    cover_clash = np.roll(cover_arr, 1, axis=2)

    for r in range(h):
        for c in range(w):
            color = cover_arr[r, c]
            clash = cover_clash[r, c]
            
            # Matriz base S1: [Color, Blanco]
            block_u1 = np.stack([color, white])
            
            # Matriz S2 dependiente del secreto:
            if secret_mask[r, c]: 
                # Caso BLANCO (Fondo):
                # S2 = [Color, Blanco]. Coincide espacial y cromáticamente con S1.
                # Resultado: [C*C, W*W] = [C, W] -> Se percibe el color original (Luz).
                block_u2 = np.stack([color, white])
            else: 
                # Caso NEGRO (Secreto):
                # S2 = [Clash, Blanco].
                # Colocamos el color de choque (Clash) en la misma posición que el color de S1.
                # Resultado: [C * Clash, W * W] = [NEGRO, BLANCO].
                # El contraste se logra por la colisión de colores en el subpíxel 0.
                block_u2 = np.stack([clash, white])

            # Permutación aleatoria de columnas para seguridad criptográfica
            flip = rng.random() > 0.5
            
            base = block_u1
            other = block_u2

            if flip:
                s1[r, c*2 : c*2+2] = base
                s2[r, c*2 : c*2+2] = other
            else:
                s1[r, c*2 : c*2+2] = base[::-1]
                s2[r, c*2 : c*2+2] = other[::-1]

    return Image.fromarray(s1), Image.fromarray(s2)

def generate_complementary(secret_mask, cover_arr, *, seed=None):
    """
    Construcción 2: EVCS con Inversos Matemáticos.
    Referencia: Yang et al. (2015), Ec. 3.
    
    Mejora del contraste usando el complemento aritmético:
    Inv = 255 - Color.
    Color * Inv ~= 0 (Negro casi perfecto).
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            color = cover_arr[r, c]
            inv_color = 255 - color # Operación vectorizada de inversión
            
            # Definición de pares base [Color, Inverso]
            pair_a = np.stack([color, inv_color])
            pair_b = np.stack([inv_color, color])
            
            flip = rng.random() > 0.5
            
            if secret_mask[r, c]: 
                # Caso BLANCO: Ambas sombras comparten la misma distribución.
                # Se ve la mezcla del color y su inverso, pero idéntica en ambas láminas.
                base = pair_a if flip else pair_b
                other = base
            else: 
                # Caso NEGRO: Las sombras tienen distribuciones opuestas.
                # S1 = [C, I], S2 = [I, C]
                # Superposición: [C*I, I*C] -> [NEGRO, NEGRO].
                # Bloqueo total de luz en ambos subpíxeles.
                base = pair_a if flip else pair_b
                other = pair_b if flip else pair_a 
            
            s1[r, c * 2 : c * 2 + 2] = base
            s2[r, c * 2 : c * 2 + 2] = other

    return Image.fromarray(s1), Image.fromarray(s2)


def generate_perfect_black(secret_mask, cover_arr, *, seed=None):
    """
    Construcción 4: "True Perfect Black" (Forzado).
    
    Lógica Matemática:
    A diferencia del esquema estándar que confía en el promedio visual, este método 
    fuerza matemáticamente el valor (0,0,0) en la superposición del secreto.
    
    Expansión m=4 (Bloque 2x2):
    - Se definen matrices diagonales y antidiagonales.
    - Se introduce 'tinta negra' (0,0,0) explícita en las sombras para garantizar
      que al multiplicar las matrices, el resultado sea cero en todas las posiciones.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    s1 = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
    white = np.array([255, 255, 255], dtype=np.uint8)
    black = np.array([0, 0, 0], dtype=np.uint8) # Elemento absorbente del grupo multiplicativo
    inv_cover = 255 - cover_arr

    for r in range(h):
        for c in range(w):
            color = cover_arr[r, c]
            inv   = inv_cover[r, c]
            flip = rng.random() > 0.5

            # Matriz Diagonal Base (Fondo)
            # [C, W]
            # [W, C]
            mat_diag = np.stack([
                np.stack([color, white]),
                np.stack([white, color])
            ])

            # Matriz Antidiagonal Base
            # [W, C]
            # [C, W]
            mat_anti_spatial = np.stack([
                np.stack([white, color]),
                np.stack([color, white])
            ])

            if secret_mask[r, c]:  
                # Caso BLANCO: Ambas sombras idénticas.
                # La luz pasa a través de las coincidencias.
                base = mat_diag if flip else mat_anti_spatial
                s1[r*2:r*2+2, c*2:c*2+2] = base
                s2[r*2:r*2+2, c*2:c*2+2] = base
            else:  
                # Caso NEGRO: Construcción de matrices de aniquilación.
                # Objetivo: S1 * S2 = Matriz de ceros (Negro total).
                
                # S1 contiene el color y tinta negra:
                # [C, K]
                # [K, C]
                s1_blk = np.stack([
                    np.stack([color, black]),
                    np.stack([black, color])
                ])
                
                # S2 contiene tinta negra y el inverso (para matar al color C):
                # [K, I]
                # [I, K]
                s2_blk = np.stack([
                    np.stack([black, inv]),
                    np.stack([inv, black])
                ])
                
                # Verificación algebraica de la superposición (elemento a elemento):
                # Pos (0,0): C * K = C * 0 = 0 (Negro)
                # Pos (0,1): K * I = 0 * I = 0 (Negro)
                # Pos (1,0): K * I = 0 * I = 0 (Negro)
                # Pos (1,1): C * K = C * 0 = 0 (Negro)
                # Resultado: Bloque 2x2 completamente negro.

                # Rotación de matrices para aleatoriedad espacial
                if flip:
                    s1_blk = np.rot90(s1_blk, k=1, axes=(0,1))
                    s2_blk = np.rot90(s2_blk, k=1, axes=(0,1))

                s1[r*2:r*2+2, c*2:c*2+2] = s1_blk
                s2[r*2:r*2+2, c*2:c*2+2] = s2_blk

    return Image.fromarray(s1), Image.fromarray(s2)


def generate_basic_multi(secret_mask, cover_arrs, *, seed=None):
    """
    Extensión de EVCS para n participantes (k=n).
    
    Lógica Matemática:
    - Píxel NEGRO: Principio de Acumulación.
      Todas las sombras tienen el mismo patrón base [C, W].
      Al multiplicar n sombras: C1 * C2 * ... * Cn.
      Si los colores son aleatorios o cubren el espectro, la mezcla tiende al negro (teoría sustractiva).
      
    - Píxel BLANCO: Principio de Cancelación por Paridad.
      Las sombras alternan patrones [C, W] y [W, C] basados en su índice (par/impar).
      S_par = [C, W], S_impar = [W, C].
      Al superponer: Pos 0 tiene Cs de pares y Ws de impares -> C.
      Pos 1 tiene Ws de pares y Cs de impares -> C.
      Resultado: [C, C]. Se percibe como luz/color uniforme, diferenciándose del negro acumulado.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs)
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(n)]
    white = np.array([255, 255, 255], dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            flip = rng.random() > 0.5
            
            if secret_mask[r, c]:  
                # Caso BLANCO (Fondo): Distribución complementaria
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    block_color = np.stack([color, white])
                    block_white = np.stack([white, color])
                    
                    # El patrón depende de la paridad del participante para asegurar
                    # que se cubran ambos subpíxeles entre el grupo.
                    if i % 2 == 0:
                        pattern = block_color if flip else block_white
                    else:
                        pattern = block_white if flip else block_color
                    
                    shares[i][r, c*2 : c*2+2] = pattern
            
            else:  
                # Caso NEGRO (Secreto): Distribución uniforme
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    block_color = np.stack([color, white])
                    block_white = np.stack([white, color])
                    
                    # Todos reciben el mismo patrón espacial.
                    # La oscuridad surge de la multiplicación de múltiples pigmentos en la misma posición.
                    pattern = block_color if flip else block_white
                    shares[i][r, c*2 : c*2+2] = pattern

    return [Image.fromarray(s) for s in shares]


def generate_complementary_multi(secret_mask, cover_arrs, *, seed=None):
    """
    Extensión (n, n) usando colores complementarios.
    
    Similar a la construcción básica multi, pero usa el par [Color, Inverso]
    en lugar de [Color, Blanco]. Esto aumenta drásticamente el contraste
    porque C * Inv tiende a cero más rápido que C * Blanco.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs)
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(n)]

    for r in range(h):
        for c in range(w):
            flip = rng.random() > 0.5
            
            if secret_mask[r, c]:  # PIXEL BLANCO
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    inv_color = 255 - color
                    pair_a = np.stack([color, inv_color])
                    pair_b = np.stack([inv_color, color])
                    
                    # Alternancia para evitar bloqueo total
                    if i % 2 == 0:
                        pattern = pair_a if flip else pair_b
                    else:
                        pattern = pair_b if flip else pair_a
                    
                    shares[i][r, c*2 : c*2+2] = pattern
            
            else:  # PIXEL NEGRO
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    inv_color = 255 - color
                    pair_a = np.stack([color, inv_color])
                    pair_b = np.stack([inv_color, color])
                    
                    # Acumulación en fase para lograr máxima oscuridad
                    pattern = pair_a if flip else pair_b
                    shares[i][r, c*2 : c*2+2] = pattern

    return [Image.fromarray(s) for s in shares]