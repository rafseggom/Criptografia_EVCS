import numpy as np
from PIL import Image, ImageChops, ImageOps

def prepare_inputs(secret_file, cover_file, *, invert=False, size=640, dither=True):
    """
    Preprocesamiento estándar: Redimensión, Binarización y Normalización.
    """
    secret = Image.open(secret_file).convert("L").resize((size, size))
    if invert:
        secret = ImageOps.invert(secret)

    if dither:
        secret_bw = secret.convert("1")
    else:
        secret_bw = secret.point(lambda x: 255 if x >= 128 else 0, mode="1")

    cover = Image.open(cover_file).convert("RGB").resize((size, size))
    
    secret_mask = np.array(secret_bw, dtype=bool) 
    cover_arr = np.array(cover, dtype=np.uint8)
    
    return secret_bw.convert("L"), cover, secret_mask, cover_arr


def overlay(share1, share2):
    """ Simulación de superposición (Multiply). No tocar. """
    return ImageChops.multiply(share1.convert("RGB"), share2.convert("RGB"))


# --- MÉTODO 1 ---
def generate_bw_vcs(secret_mask, cover_arrs, *, seed=None):
    """
    Construcción 1: VCS - Black and White.
    Implementación clásica de Naor & Shamir (2,2) monocromática.
    
    Lógica:
    - Expansión de píxel m=2 (1x2).
    - S1 siempre es un patrón aleatorio equilibrado (1 negro, 1 blanco).
    - Si secreto es BLANCO: S2 es IDÉNTICA a S1.
    - Si secreto es NEGRO: S2 es COMPLEMENTARIA a S1.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    
    if len(cover_arrs) != 2:
        raise ValueError("VCS B/N requiere exactamente 2 participantes.")

    # 1. Generar la matriz base para Sombra 1 (S1)
    s1_left = rng.integers(0, 2, size=(h, w), dtype=np.bool_)
    s1_right = ~s1_left 
    
    # 2. Calcular Sombra 2 (S2) basada en el Secreto
    s2_left = np.zeros((h, w), dtype=np.bool_)
    s2_right = np.zeros((h, w), dtype=np.bool_)
    
    # CASO A: Secreto Blanco (True) -> S2 igual a S1
    s2_left[secret_mask]  = s1_left[secret_mask]
    s2_right[secret_mask] = s1_right[secret_mask]
    
    # CASO B: Secreto Negro (False) -> S2 inversa a S1
    s2_left[~secret_mask]  = ~s1_left[~secret_mask]
    s2_right[~secret_mask] = ~s1_right[~secret_mask]

    # 3. Construir las imágenes finales expandidas
    share1_img = np.zeros((h, w * 2), dtype=np.uint8)
    share2_img = np.zeros((h, w * 2), dtype=np.uint8)
    
    share1_img[:, 0::2] = s1_left.astype(np.uint8) * 255
    share1_img[:, 1::2] = s1_right.astype(np.uint8) * 255
    
    share2_img[:, 0::2] = s2_left.astype(np.uint8) * 255
    share2_img[:, 1::2] = s2_right.astype(np.uint8) * 255
    
    return [Image.fromarray(share1_img).convert("RGB"), 
            Image.fromarray(share2_img).convert("RGB")]


# --- MÉTODO 2 (ANTIGUO 4) ---
def generate_simple_6color(secret_mask, cover_arrs, *, seed=None):
    """
    Construcción 2: Color Black White - VCS (CBW).
    Basado en Naor-Shamir (2,2) con paleta RGBCMY.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    
    if len(cover_arrs) != 2:
        raise ValueError("CBW requiere exactamente 2 participantes.")
    
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(2)]
    
    palette = [
        [255, 0, 0], [0, 255, 0], [0, 0, 255],     
        [0, 255, 255], [255, 0, 255], [255, 255, 0]
    ]
    comp_map = {0: 3, 1: 4, 2: 5, 3: 0, 4: 1, 5: 2}
    palette_arr = np.array(palette, dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            idx_1a = rng.integers(0, 6)
            idx_1b = rng.integers(0, 6)
            
            shares[0][r, c*2]     = palette_arr[idx_1a]
            shares[0][r, c*2 + 1] = palette_arr[idx_1b]
            
            if secret_mask[r, c]:  # Blanco -> Idéntico
                idx_2a, idx_2b = idx_1a, idx_1b
            else:  # Negro -> Complementario
                idx_2a, idx_2b = comp_map[idx_1a], comp_map[idx_1b]
            
            shares[1][r, c*2]     = palette_arr[idx_2a]
            shares[1][r, c*2 + 1] = palette_arr[idx_2b]

    return [Image.fromarray(s) for s in shares]


# --- MÉTODO 3 (EVCS REAL) ---
def generate_evcs_colored(secret_mask, cover_arrs, *, seed=None):
    """
    Construcción 3: CBW-EVCS (Esquema Extendido).
    Implementación rigurosa basada en Yang et al. (Construcción 2 del paper).
    
    Utiliza 4 casos matemáticos para determinar los subpíxeles basándose en:
    1. Bit del Secreto (Blanco/Negro)
    2. Bit de la Cobertura 1 (Fondo/Forma)
    3. Bit de la Cobertura 2 (Fondo/Forma)
    
    Garantiza que cada sombra muestre su imagen de cobertura y que
    la superposición revele el secreto.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape

    if len(cover_arrs) < 2:
        raise ValueError("Este esquema requiere al menos 2 imágenes de cobertura.")

    # Binarizar las coberturas para tomar decisiones lógicas (Blanco=Fondo, Negro=Tinta)
    # Usamos umbral 128 sobre la media RGB
    c1_bw = np.mean(cover_arrs[0], axis=2) > 128
    c2_bw = np.mean(cover_arrs[1], axis=2) > 128

    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    
    # Paleta RGBCMY (6 colores) y Negro
    palette = np.array([
        [255, 0, 0], [0, 255, 0], [0, 0, 255],       # R, G, B
        [0, 255, 255], [255, 0, 255], [255, 255, 0]  # C, M, Y
    ], dtype=np.uint8)
    black_pixel = np.array([0, 0, 0], dtype=np.uint8)
    
    # Mapa de complementarios
    comp_idx = np.array([3, 4, 5, 0, 1, 2])

    # Generamos índices aleatorios para todo el array de una vez (optimización)
    # X e Y son colores aleatorios independientes
    rand_X = rng.integers(0, 6, size=(h, w))
    rand_Y = rng.integers(0, 6, size=(h, w))
    
    # Precalculamos complementarios
    comp_X = comp_idx[rand_X]
    comp_Y = comp_idx[rand_Y]

    # --- LÓGICA POR PÍXEL (Vectorizada) ---
    # Subpíxel 1 (Izquierdo): Controlado principalmente por Cobertura 1 y Secreto
    # Subpíxel 2 (Derecho): Controlado por Cobertura 2 y Cobertura 1
    
    # ITERAMOS POR FILAS PARA ASIGNACIÓN (Más claro que vectorización total compleja)
    for r in range(h):
        for c in range(w):
            # Obtener estados
            sec_w = secret_mask[r, c] # True si Secreto es Blanco
            cov1_w = c1_bw[r, c]      # True si Cover 1 es Fondo (Blanco)
            cov2_w = c2_bw[r, c]      # True si Cover 2 es Fondo (Blanco)
            
            # Colores base para este píxel
            x_idx = rand_X[r, c]
            y_idx = rand_Y[r, c]
            
            # --- ASIGNACIÓN SUBPÍXEL 1 (Indice par) ---
            # Share 1 siempre recibe color aleatorio X en subpíxel 1
            # Esto es consistente con la Construcción 2 del paper
            color_s1_p1 = palette[x_idx]
            
            # Share 2 depende del secreto
            if sec_w:
                # Secreto Blanco: S2 copia a S1
                color_s2_p1 = palette[x_idx]
            else:
                # Secreto Negro: S2 es complementario de S1
                color_s2_p1 = palette[comp_X[r, c]]

            # --- ASIGNACIÓN SUBPÍXEL 2 (Indice impar) ---
            
            # SHARE 1: Depende de SU cobertura (Cov1)
            if cov1_w:
                # Si Cov1 es fondo, ponemos color (ruido)
                color_s1_p2 = palette[y_idx]
            else:
                # Si Cov1 es figura (negro), ponemos NEGRO para oscurecer la sombra
                color_s1_p2 = black_pixel

            # SHARE 2: Depende de SU cobertura (Cov2) y relación con Cov1/Secreto
            if not cov2_w:
                # Si Cov2 es figura (negro), debe ser negro
                color_s2_p2 = black_pixel
            else:
                # Si Cov2 es fondo (quiere color):
                if cov1_w:
                    # Caso: Ambas coberturas son Blancas
                    if sec_w:
                        color_s2_p2 = palette[y_idx] # Igual a S1 (Color)
                    else:
                        color_s2_p2 = palette[comp_Y[r, c]] # Comp a S1 (Negro)
                else:
                    # Caso: Cov1 es Negro pero Cov2 es Blanco
                    # S1 tiene Negro. S2 necesita Color para ver su propia imagen.
                    # Ponemos un color aleatorio (Y). 
                    # El contraste se mantendrá porque [Negro] vs [Color] es oscuro.
                    color_s2_p2 = palette[y_idx]

            # Asignar a matrices
            s1[r, c*2]   = color_s1_p1
            s1[r, c*2+1] = color_s1_p2
            
            s2[r, c*2]   = color_s2_p1
            s2[r, c*2+1] = color_s2_p2

    return [Image.fromarray(s1), Image.fromarray(s2)]


# --- MÉTODO 4 (ANTIGUO 1) ---
def generate_basic_evcs_augmented(secret_mask, cover_arrs, *, seed=None):
    """
    Construcción 4: CBW-EVCS aumentado.
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
                # Caso BLANCO
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    block_color = np.stack([color, white])
                    block_white = np.stack([white, color])
                    
                    if i % 2 == 0:
                        pattern = block_color if flip else block_white
                    else:
                        pattern = block_white if flip else block_color
                    shares[i][r, c*2 : c*2+2] = pattern
            
            else:  
                # Caso NEGRO (Clash)
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    clash = np.roll(color, 1) 
                    block_clash = np.stack([clash, white])
                    pattern = block_clash if flip else block_clash[::-1]
                    shares[i][r, c*2 : c*2+2] = pattern

    return [Image.fromarray(s) for s in shares]


# --- MÉTODO 5 (PLACEHOLDER) ---
def generate_perfect_black_placeholder(secret_mask, cover_arrs):
    """ Placeholder para Perfect Black Aumentado """
    h, w = secret_mask.shape
    dummy = Image.new("RGB", (w*2, h*2), (50, 50, 50)) 
    return [dummy, dummy]