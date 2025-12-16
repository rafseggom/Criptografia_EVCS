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

    if cover_file is None:
        cover = Image.new("RGB", (size, size), (0, 0, 0))
    else:
        cover = Image.open(cover_file).convert("RGB").resize((size, size))
    
    secret_mask = np.array(secret_bw, dtype=bool) 
    cover_arr = np.array(cover, dtype=np.uint8)
    
    return secret_bw.convert("L"), cover, secret_mask, cover_arr


def overlay(share1, share2):
    """ Simulación de superposición (Multiply). """
    return ImageChops.multiply(share1.convert("RGB"), share2.convert("RGB"))


# --- MÉTODO 1 (REAL 2-out-of-N) ---
def generate_bw_vcs(secret_mask, cover_arrs, *, seed=None):
    """
    Construcción 1: VCS - Black and White (Esquema Real 2-out-of-N).
    
    Implementación genuina con expansión m=N.
    - Secreto Blanco: Todas las sombras comparten la MISMA posición para el píxel negro.
      (Apilar 2 o más = 1 Negro).
    - Secreto Negro: Cada sombra tiene su píxel negro en una posición ÚNICA.
      (Apilar 2 = 2 Negros, más oscuro).
      
    Garantiza que S1 y S3 sean distintas (especialmente en zonas negras).
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs) 
    
    if n < 2:
        raise ValueError("VCS requiere al menos 2 participantes.")

    # 1. Creamos N matrices vacías (Blanco = 255) de tamaño H x (W*N)
    # Inicializamos a 255 (BLANCO)
    shares_arr = [np.ones((h, w * n), dtype=np.uint8) * 255 for _ in range(n)]
    
    # 2. Generamos permutaciones aleatorias para cada píxel
    # Esto decide las 'ranuras' de 0 a N-1 disponibles en cada bloque
    perms = np.argsort(rng.random((h, w, n)), axis=2)

    for r in range(h):
        for c in range(w):
            p_indices = perms[r, c] # Array de índices [0, 2, 1...] desordenados
            
            if secret_mask[r, c]: 
                # CASO BLANCO (Fondo/Transparente):
                # Regla (2,N): Todos comparten la misma 'columna negra'.
                # Elegimos la primera ranura de la permutación p_indices[0].
                k = p_indices[0]
                for i in range(n):
                    shares_arr[i][r, c*n + k] = 0 # Pintamos NEGRO
                    # El resto de ranuras se quedan en BLANCO (255)
            else:
                # CASO NEGRO (Secreto):
                # Regla (2,N): Cada participante 'i' pone negro en una ranura DISTINTA.
                # Usamos p_indices[i] para asegurar unicidad.
                for i in range(n):
                    k = p_indices[i]
                    shares_arr[i][r, c*n + k] = 0 # Pintamos NEGRO

    return [Image.fromarray(s).convert("RGB") for s in shares_arr]


# --- MÉTODO 2 (COLOR 2-out-of-N) ---
def generate_simple_6color(secret_mask, cover_arrs, *, seed=None):
    """
    Construcción 2: CBW (Color Black White) - Real 2-out-of-N.
    
    Solución al problema "S1 es igual a S3":
    Utilizamos un esquema híbrido de Densidad + Ruido de Color.
    - Expansión m=N.
    - Marca de contraste: NEGRO (para asegurar la decodificación visual).
    - Relleno: COLORES ALEATORIOS (RGBCMY).
    
    Al usar relleno aleatorio, incluso si dos sombras coinciden en la posición
    de la marca negra (caso blanco), sus píxeles de relleno serán de colores
    distintos. S1 y S3 serán visualmente únicas.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs)
    
    if n < 2:
        raise ValueError("CBW requiere al menos 2 participantes.")
    
    shares_arr = [np.zeros((h, w * n, 3), dtype=np.uint8) for _ in range(n)]
    
    palette = np.array([
        [255, 0, 0], [0, 255, 0], [0, 0, 255],     
        [0, 255, 255], [255, 0, 255], [255, 255, 0]
    ], dtype=np.uint8)
    
    black_pixel = np.array([0, 0, 0], dtype=np.uint8)

    # Permutaciones para posiciones
    perms = np.argsort(rng.random((h, w, n)), axis=2)
    
    # Colores aleatorios para relleno (Noise)
    # Generamos una matriz gigante de índices de color aleatorios
    rand_colors = rng.integers(0, 6, size=(n, h, w * n))

    for r in range(h):
        for c in range(w):
            p_indices = perms[r, c]
            
            # 1. Rellenar TODO el bloque con colores aleatorios (Ruido base)
            # Esto garantiza que S1 y S3 sean distintas siempre.
            for i in range(n):
                for k in range(n): # Llenamos los N subpíxeles
                    col_idx = rand_colors[i, r, c*n + k]
                    shares_arr[i][r, c*n + k] = palette[col_idx]
            
            # 2. Aplicar la Lógica de Secreto (Sobrescribir con MARCA NEGRA)
            if secret_mask[r, c]: 
                # CASO BLANCO (Secreto Transparente)
                # Todos coinciden en la marca negra en la posición k.
                k_pos = p_indices[0]
                for i in range(n):
                    shares_arr[i][r, c*n + k_pos] = black_pixel
            else:
                # CASO NEGRO (Secreto Opaco)
                # Cada uno pone marca negra en posición distinta k_i.
                # Al superponer S1+S2 -> 2 marcas negras (Más oscuro).
                for i in range(n):
                    k_pos = p_indices[i]
                    shares_arr[i][r, c*n + k_pos] = black_pixel

    return [Image.fromarray(s) for s in shares_arr]


# --- MÉTODO 3 (EVCS) ---
def generate_evcs_colored(secret_mask, cover_arrs, *, seed=None, darken_factor=0.2):
    """
    Construcción 3: CBW-EVCS.
    Nota: Este método es inherentemente (2,2) por la matemática de matrices de Yang.
    Si N > 2, usamos distribución cíclica de pares (S1, S2, S1...)
    porque generalizar EVCS a (2,N) requiere resolver sistemas lineales complejos
    fuera del alcance de esta demo.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs)

    if n < 2:
        raise ValueError("Este esquema requiere al menos 2 imágenes de cobertura.")

    # Procesamos solo las 2 primeras covers para generar el par base
    c1_gray = np.array(Image.fromarray(cover_arrs[0]).convert("L"))
    c2_gray = np.array(Image.fromarray(cover_arrs[1]).convert("L"))
    
    c1_dark = c1_gray * darken_factor
    c2_dark = c2_gray * darken_factor
    
    noise_matrix = rng.integers(0, 256, size=(h, w))
    
    c1_bg = c1_dark > noise_matrix 
    c2_bg = c2_dark > noise_matrix

    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    
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
            
            if c1_white and c2_white:
                if sec_white:
                    row1 = [idx_a, idx_b]; row2 = [idx_a, idx_b]
                else:
                    row1 = [idx_a, idx_b]; row2 = [comp_map[idx_a], comp_map[idx_b]]
            elif c1_white and not c2_white:
                if sec_white:
                    row1 = [idx_a, idx_b]; row2 = [idx_a, -1] 
                else:
                    row1 = [idx_a, idx_b]; row2 = [comp_map[idx_a], -1]
            elif not c1_white and c2_white:
                if sec_white:
                    row1 = [idx_a, -1]; row2 = [idx_a, idx_b]
                else:
                    row1 = [idx_a, -1]; row2 = [comp_map[idx_a], idx_b]
            else:
                if sec_white:
                    row1 = [idx_a, -1]; row2 = [idx_a, -1]
                else:
                    row1 = [idx_a, -1]; row2 = [comp_map[idx_a], -1]

            if perms[r, c] == 1:
                row1 = [row1[1], row1[0]]
                row2 = [row2[1], row2[0]]

            def get_rgb(code):
                return black_pixel if code == -1 else palette[code]

            s1[r, c*2]   = get_rgb(row1[0])
            s1[r, c*2+1] = get_rgb(row1[1])
            s2[r, c*2]   = get_rgb(row2[0])
            s2[r, c*2+1] = get_rgb(row2[1])

    # Para EVCS, si N > 2, repetimos el par base (limitación matemática)
    base_imgs = [Image.fromarray(s1), Image.fromarray(s2)]
    final_shares = []
    for i in range(n):
        final_shares.append(base_imgs[i % 2])

    return final_shares

# --- MÉTODO 4 ---
def generate_basic_evcs_augmented(secret_mask, cover_arrs, *, seed=None):
    """ Construcción 4: CBW-EVCS aumentado. """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs)
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(n)]
    white = np.array([255, 255, 255], dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            flip = rng.random() > 0.5
            if secret_mask[r, c]:  
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
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    clash = np.roll(color, 1) 
                    block_clash = np.stack([clash, white])
                    pattern = block_clash if flip else block_clash[::-1]
                    shares[i][r, c*2 : c*2+2] = pattern

    return [Image.fromarray(s) for s in shares]


# --- MÉTODO 5 (PLACEHOLDER) ---
def generate_perfect_black_placeholder(secret_mask, cover_arrs):
    h, w = secret_mask.shape
    dummy = Image.new("RGB", (w*2, h*2), (50, 50, 50)) 
    return [dummy, dummy]