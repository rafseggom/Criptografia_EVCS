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


def generate_2_2_vcs_multi(secret_mask, cover_arrs, *, seed=None):
    """
    (2,2) VCS según Yang et al. (2015): n=2 participantes, k=2 umbral, m=2 expansión.
    
    Matriz base para (2,2) VCS:
    - Píxel BLANCO: C0 = [[C,W], [W,C]] → patrones complementarios
    - Píxel NEGRO: C1 = [[C,W], [C,W]] → mismo patrón
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs)
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(n)]
    white = np.array([255, 255, 255], dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            flip = rng.random() > 0.5
            
            if secret_mask[r, c]:  # BLANCO (fondo)
                # Patrones complementarios: cada participante recibe patrón opuesto
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    
                    if i % 2 == 0:
                        pattern = np.stack([color, white]) if flip else np.stack([white, color])
                    else:
                        pattern = np.stack([white, color]) if flip else np.stack([color, white])
                    
                    shares[i][r, c*2 : c*2+2] = pattern
            
            else:  # NEGRO (secreto)
                # Mismo patrón para todos (cohesión)
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    pattern = np.stack([color, white]) if flip else np.stack([white, color])
                    shares[i][r, c*2 : c*2+2] = pattern

    return [Image.fromarray(s) for s in shares]


def generate_perfect_black(secret_mask, cover_arr, *, seed=None):
    """
    Perfect Black con negro PURO absoluto usando complementarios exactos.
    
    Para PIXEL NEGRO: usamos colores complementarios matemáticos que al
    multiplicarse (modelo sustractivo) dan [0,0,0] (negro puro).
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    s1 = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
    white = np.array([255, 255, 255], dtype=np.uint8)
    black = np.array([0, 0, 0], dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            color = cover_arr[r, c]
            # Complementario matemático para multiplicación = negro
            inv = 255 - color
            flip = rng.random() > 0.5

            if secret_mask[r, c]:  # SECRETO BLANCO (fondo)
                # Patrón diagonal idéntico en ambas sombras
                # Resultado: luz pasa → blanco visible
                mat_base = np.stack([
                    np.stack([color, white]),
                    np.stack([white, color])
                ])
                
                if flip:
                    # Antidiagonal
                    mat_base = np.stack([
                        np.stack([white, color]),
                        np.stack([color, white])
                    ])
                
                s1[r*2:r*2+2, c*2:c*2+2] = mat_base
                s2[r*2:r*2+2, c*2:c*2+2] = mat_base
            
            else:  # SECRETO NEGRO
                # Estrategia: colores complementarios en posiciones coincidentes
                # Color × (255-Color) ≈ 0 → negro puro
                
                # Sombra 1: diagonal con color
                s1_mat = np.stack([
                    np.stack([color, black]),
                    np.stack([black, color])
                ])
                
                # Sombra 2: diagonal con complementario en las MISMAS posiciones
                s2_mat = np.stack([
                    np.stack([inv, white]),
                    np.stack([white, inv])
                ])
                
                # Verificación algebraica de la superposición (elemento a elemento):
                # Pos (0,0): C * K = C * 0 = 0 (Negro)
                # Pos (0,1): K * I = 0 * I = 0 (Negro)
                # Pos (1,0): K * I = 0 * I = 0 (Negro)
                # Pos (1,1): C * K = C * 0 = 0 (Negro)
                # Resultado: Bloque 2x2 completamente negro.

                # Resultado al superponer:
                # pos[0,0]: color × inv = ~0 (negro)
                # pos[0,1]: black × white = 0 (negro)
                # pos[1,0]: black × white = 0 (negro)
                # pos[1,1]: color × inv = ~0 (negro)
                # → Toda la celda 2x2 queda NEGRA
                
                if flip:
                    # Antidiagonal alternativa
                    s1_mat = np.stack([
                        np.stack([black, color]),
                        np.stack([color, black])
                    ])
                    s2_mat = np.stack([
                        np.stack([white, inv]),
                        np.stack([inv, white])
                    ])
                
                s1[r*2:r*2+2, c*2:c*2+2] = s1_mat
                s2[r*2:r*2+2, c*2:c*2+2] = s2_mat

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


def generate_simple_6color(secret_mask, cover_arrs, *, seed=None):
    """
    Construcción 4: Simple 6-Color (Corregida según Naor-Shamir 2-out-of-2).
    
    Implementación rigurosa del esquema (2,2) visual:
    - n=2 participantes.
    - m=2 expansión de píxel (horizontal).
    
    Matemática del Esquema (Fuente: Naor & Shamir, 1994):
    1.  La Sombra 1 (S1) siempre es ruido aleatorio uniforme.
    2.  Si el secreto es BLANCO (0): S2 es IDÉNTICA a S1. 
        -> Superposición: Color X * Color X = Color X (Transparente/Visible).
    3.  Si el secreto es NEGRO (1): S2 es el COMPLEMENTARIO de S1.
        -> Superposición: Color X * Color Comp(X) = Negro (Bloqueo total de luz).
        
    Colores usados (RGB sustractivo simulado):
    - Base: Rojo, Verde, Azul.
    - Complementos: Cian, Magenta, Amarillo.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    
    # Validación estricta de participantes
    if len(cover_arrs) != 2:
        # Nota: Aunque el algoritmo solo usa el secreto, recibimos cover_arrs
        # para mantener la firma de la función compatible con el resto de tu app.
        raise ValueError("Simple 6-Color requiere exactamente 2 participantes (imágenes de cobertura).")
    
    # Pre-reservar memoria para las sombras
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(2)]
    
    # Tabla de colores (RGB)
    # Usamos listas para acceso rápido por índice
    palette = [
        [255, 0, 0],   # 0: Rojo
        [0, 255, 0],   # 1: Verde
        [0, 0, 255],   # 2: Azul
        [0, 255, 255], # 3: Cian    (Comp Rojo)
        [255, 0, 255], # 4: Magenta (Comp Verde)
        [255, 255, 0]  # 5: Amarillo (Comp Azul)
    ]
    
    # Mapa de complementarios: índice -> índice complementario
    # 0(R)<->3(C), 1(G)<->4(M), 2(B)<->5(Y)
    comp_map = {0: 3, 1: 4, 2: 5, 3: 0, 4: 1, 5: 2}
    
    # Optimizamos convirtiendo la paleta a numpy array para asignación rápida
    palette_arr = np.array(palette, dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            # 1. Generar patrón aleatorio para Sombra 1 (S1)
            # Elegimos 2 colores aleatorios para los 2 subpíxeles
            idx_1a = rng.integers(0, 6)
            idx_1b = rng.integers(0, 6)
            
            # Asignar colores a Sombra 1
            shares[0][r, c*2]     = palette_arr[idx_1a]
            shares[0][r, c*2 + 1] = palette_arr[idx_1b]
            
            # 2. Determinar Sombra 2 (S2) basándonos en el secreto
            if secret_mask[r, c]:  # Píxel BLANCO (Fondo / Transparente)
                # Según Naor-Shamir: Las matrices deben ser iguales para recuperar el blanco.
                # S2 = S1
                idx_2a = idx_1a
                idx_2b = idx_1b
                
            else:  # Píxel NEGRO (Tinta / Opaco)
                # Según Naor-Shamir: Las matrices deben ser complementarias.
                # S2 = Complemento(S1)
                idx_2a = comp_map[idx_1a]
                idx_2b = comp_map[idx_1b]
            
            # Asignar colores calculados a Sombra 2
            shares[1][r, c*2]     = palette_arr[idx_2a]
            shares[1][r, c*2 + 1] = palette_arr[idx_2b]

    return [Image.fromarray(s) for s in shares]

def generate_evcs_colored(secret_mask, cover_arrs, *, seed=None):
    """
    Construcción 5: EVCS Coloreado Mejorado (Anti-Ghosting).
    
    Ajuste: cada sombra decide su color según su propia preferencia y azar,
    evitando que una sombra filtre información del secreto o de la otra cobertura.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape

    if len(cover_arrs) != 2:
        raise ValueError("Construcción 5 requiere exactamente 2 coberturas.")

    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)

    palette = np.array([
        [255, 0, 0],   # 0 R
        [0, 255, 0],   # 1 G
        [0, 0, 255],   # 2 B
        [0, 255, 255], # 3 C
        [255, 0, 255], # 4 M
        [255, 255, 0], # 5 Y
    ], dtype=np.uint8)
    comp = {0:3, 1:4, 2:5, 3:0, 4:1, 5:2}
    DARKS, LIGHTS = [0,1,2], [3,4,5]

    # Preferencias por cover: True=fondo (claro), False=texto (oscuro)
    wants_light = []
    for carr in cover_arrs:
        gray = np.mean(carr, axis=2)
        wants_light.append(gray > 128)

    for r in range(h):
        for c in range(w):
            secret_white = secret_mask[r, c]
            c1_pref_light = wants_light[0][r, c]
            c2_pref_light = wants_light[1][r, c]
            pool1 = LIGHTS if c1_pref_light else DARKS
            pool2 = LIGHTS if c2_pref_light else DARKS

            for sub in range(2):
                if secret_white:
                    # Secreto blanco: NO complementarios
                    c1_idx = int(rng.choice(pool1)) if len(pool1) else int(rng.integers(0, 6))
                    # elegir para S2 algo que NO sea complementario de c1
                    noncomp2 = [i for i in pool2 if i != comp[c1_idx]]
                    if not noncomp2:
                        noncomp2 = [i for i in range(6) if i != comp[c1_idx]]
                    c2_idx = int(rng.choice(noncomp2))
                else:
                    # Secreto negro: complementarios, alternando prioridad
                    if rng.random() > 0.5:
                        c1_idx = int(rng.choice(pool1)) if len(pool1) else int(rng.integers(0, 6))
                        c2_idx = comp[c1_idx]
                    else:
                        c2_idx = int(rng.choice(pool2)) if len(pool2) else int(rng.integers(0, 6))
                        c1_idx = comp[c2_idx]

                s1[r, c*2 + sub] = palette[c1_idx]
                s2[r, c*2 + sub] = palette[c2_idx]

    return [Image.fromarray(s1), Image.fromarray(s2)]