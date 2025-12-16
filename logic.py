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
    Construcción 3: CBW-EVCS (Esquema Extendido) - Factor 30% Luz (70% Oscuridad).
    
    Ajuste de Usuario (Fine-Tuning):
    El usuario detectó que con el 50%, a alta resolución, el ojo humano sigue
    percibiendo patrones de densidad (ghosting).
    
    Corrección:
    Bajamos la luminosidad del fondo al 30% (Factor 0.3).
    Esto implica una densidad de tinta simulada del 70%.
    Al saturar el fondo de ruido oscuro, la diferencia visual entre las zonas
    con texto (tinta sólida) y el fondo (tinta aleatoria) se vuelve indetectable
    para el ojo humano, incluso en monitores RGB brillantes.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape

    if len(cover_arrs) < 2:
        raise ValueError("Este esquema requiere al menos 2 imágenes de cobertura.")

    # 1. Convertir Covers a Escala de Grises
    c1_gray = np.array(Image.fromarray(cover_arrs[0]).convert("L"))
    c2_gray = np.array(Image.fromarray(cover_arrs[1]).convert("L"))
    
    # 2. OSCURECIMIENTO AL 80% (Factor de Luz 0.2)
    # Matemáticamente: Pixel * 0.2.
    # El blanco (255) pasa a ser ~51 (Gris muy oscuro).
    # Esto inunda el fondo de píxeles negros tras el dithering, ocultando el secreto.
    DARKEN_FACTOR = 0.2
    c1_dark = c1_gray * DARKEN_FACTOR
    c2_dark = c2_gray * DARKEN_FACTOR
    
    # 3. Dithering Probabilístico
    noise_matrix = rng.integers(0, 256, size=(h, w))
    
    # Al ser la imagen tan oscura, la mayoría de veces (c_dark < noise),
    # el resultado será False (Negro). El fondo será muy denso.
    c1_bg = c1_dark > noise_matrix 
    c2_bg = c2_dark > noise_matrix

    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    
    # Paleta RGBCMY
    palette = np.array([
        [255, 0, 0], [0, 255, 0], [0, 0, 255],     
        [0, 255, 255], [255, 0, 255], [255, 255, 0]
    ], dtype=np.uint8)
    
    black_pixel = np.array([0, 0, 0], dtype=np.uint8)
    comp_map = np.array([3, 4, 5, 0, 1, 2])

    rand_cols = rng.integers(0, 6, size=(h, w, 2))
    perms = rng.integers(0, 2, size=(h, w))

    for r in range(h):
        for c in range(w):
            sec_white = secret_mask[r, c]
            c1_white = c1_bg[r, c] 
            c2_white = c2_bg[r, c] 
            
            idx_a = rand_cols[r, c, 0]
            idx_b = rand_cols[r, c, 1]
            
            # --- CONSTRUCCIÓN 2 ESTRICTA ---
            # Secreto Perfect Black (-1)
            
            # CASO 1: Ambas Fondo
            if c1_white and c2_white:
                if sec_white:
                    row1 = [idx_a, idx_b]
                    row2 = [idx_a, idx_b]
                else:
                    row1 = [idx_a, idx_b]
                    row2 = [comp_map[idx_a], comp_map[idx_b]]

            # CASO 2: C1 Fondo, C2 Tinta
            elif c1_white and not c2_white:
                if sec_white:
                    row1 = [idx_a, idx_b]
                    row2 = [idx_a, -1] 
                else:
                    row1 = [idx_a, idx_b]
                    row2 = [comp_map[idx_a], -1]

            # CASO 3: C1 Tinta, C2 Fondo
            elif not c1_white and c2_white:
                if sec_white:
                    row1 = [idx_a, -1]
                    row2 = [idx_a, idx_b]
                else:
                    row1 = [idx_a, -1]
                    row2 = [comp_map[idx_a], idx_b]

            # CASO 4: Ambas Tinta
            else:
                if sec_white:
                    row1 = [idx_a, -1]
                    row2 = [idx_a, -1]
                else:
                    row1 = [idx_a, -1]
                    row2 = [comp_map[idx_a], -1]

            # --- PERMUTACIÓN ---
            if perms[r, c] == 1:
                row1 = [row1[1], row1[0]]
                row2 = [row2[1], row2[0]]

            # --- PINTADO ---
            def get_rgb(code):
                return black_pixel if code == -1 else palette[code]

            s1[r, c*2]   = get_rgb(row1[0])
            s1[r, c*2+1] = get_rgb(row1[1])
            
            s2[r, c*2]   = get_rgb(row2[0])
            s2[r, c*2+1] = get_rgb(row2[1])

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