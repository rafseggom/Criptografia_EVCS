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
    [cite_start]Implementación clásica de Naor & Shamir (2,2) monocromática[cite: 7].
    
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
    # Generamos aleatoriamente el primer subpíxel (Izquierdo)
    # 0 = Negro, 1 = Blanco
    s1_left = rng.integers(0, 2, size=(h, w), dtype=np.bool_)
    
    # El subpíxel derecho siempre es el opuesto del izquierdo para mantener densidad 50%
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

    # 3. Construir las imágenes finales expandidas (Interleaving)
    # Dimensiones finales: (h, w*2)
    share1_img = np.zeros((h, w * 2), dtype=np.uint8)
    share2_img = np.zeros((h, w * 2), dtype=np.uint8)
    
    # Asignamos valores: False(0) -> 0 (Negro), True(1) -> 255 (Blanco)
    # Sombra 1
    share1_img[:, 0::2] = s1_left.astype(np.uint8) * 255
    share1_img[:, 1::2] = s1_right.astype(np.uint8) * 255
    
    # Sombra 2
    share2_img[:, 0::2] = s2_left.astype(np.uint8) * 255
    share2_img[:, 1::2] = s2_right.astype(np.uint8) * 255
    
    # Retornamos en RGB para compatibilidad con el resto de la app
    return [Image.fromarray(share1_img).convert("RGB"), 
            Image.fromarray(share2_img).convert("RGB")]


# --- MÉTODO 2 (ANTIGUO 4) - CORREGIDO (Naor-Shamir) ---
def generate_simple_6color(secret_mask, cover_arrs, *, seed=None):
    """
    Construcción 2: Color Black White - VCS (CBW).
    Basado en Naor-Shamir (2,2).
    
    Matemática:
    - Secreto BLANCO: S1 = S2 (Idénticos -> Color)
    - Secreto NEGRO: S1 = Complemento(S2) (Opuestos -> Negro)
    Ignora las imágenes de cobertura (solo ruido de color).
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    
    if len(cover_arrs) != 2:
        raise ValueError("CBW requiere exactamente 2 participantes.")
    
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(2)]
    
    # Paleta y mapa de complementarios
    palette = [
        [255, 0, 0], [0, 255, 0], [0, 0, 255],     # R, G, B
        [0, 255, 255], [255, 0, 255], [255, 255, 0] # C, M, Y
    ]
    comp_map = {0: 3, 1: 4, 2: 5, 3: 0, 4: 1, 5: 2}
    palette_arr = np.array(palette, dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            # S1: Aleatorio puro
            idx_1a = rng.integers(0, 6)
            idx_1b = rng.integers(0, 6)
            
            shares[0][r, c*2]     = palette_arr[idx_1a]
            shares[0][r, c*2 + 1] = palette_arr[idx_1b]
            
            # S2: Depende del secreto
            if secret_mask[r, c]:  # Blanco -> Idéntico
                idx_2a, idx_2b = idx_1a, idx_1b
            else:  # Negro -> Complementario
                idx_2a, idx_2b = comp_map[idx_1a], comp_map[idx_1b]
            
            shares[1][r, c*2]     = palette_arr[idx_2a]
            shares[1][r, c*2 + 1] = palette_arr[idx_2b]

    return [Image.fromarray(s) for s in shares]


# --- MÉTODO 3 (ANTIGUO 5) ---
def generate_evcs_colored(secret_mask, cover_arrs, *, seed=None):
    """
    Construcción 3: CBW-EVCS (Esquema extendido).
    Anti-Ghosting y gestión de preferencias de color.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape

    if len(cover_arrs) < 2:
        raise ValueError("Este esquema requiere al menos 2 coberturas.")

    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)

    palette = np.array([
        [255, 0, 0], [0, 255, 0], [0, 0, 255],
        [0, 255, 255], [255, 0, 255], [255, 255, 0]
    ], dtype=np.uint8)
    comp = {0:3, 1:4, 2:5, 3:0, 4:1, 5:2}
    DARKS, LIGHTS = [0,1,2], [3,4,5]

    wants_light = []
    # Tomamos solo las 2 primeras covers para la lógica base
    for carr in cover_arrs[:2]:
        gray = np.mean(carr, axis=2)
        wants_light.append(gray > 128)

    for r in range(h):
        for c in range(w):
            secret_white = secret_mask[r, c]
            pool1 = LIGHTS if wants_light[0][r, c] else DARKS
            pool2 = LIGHTS if wants_light[1][r, c] else DARKS

            for sub in range(2):
                if secret_white:
                    # Secreto blanco: Buscar NO complementarios
                    c1_idx = int(rng.choice(pool1)) if pool1 else int(rng.integers(0, 6))
                    noncomp2 = [i for i in pool2 if i != comp[c1_idx]]
                    # Fallback si no hay coincidencia limpia
                    if not noncomp2:
                        noncomp2 = [i for i in range(6) if i != comp[c1_idx]]
                    c2_idx = int(rng.choice(noncomp2))
                else:
                    # Secreto negro: Complementarios obligatorios
                    # Aleatorizar quién cede su preferencia para evitar fantasmas
                    if rng.random() > 0.5:
                        c1_idx = int(rng.choice(pool1)) if pool1 else int(rng.integers(0, 6))
                        c2_idx = comp[c1_idx]
                    else:
                        c2_idx = int(rng.choice(pool2)) if pool2 else int(rng.integers(0, 6))
                        c1_idx = comp[c2_idx]

                s1[r, c*2 + sub] = palette[c1_idx]
                s2[r, c*2 + sub] = palette[c2_idx]

    return [Image.fromarray(s1), Image.fromarray(s2)]


# --- MÉTODO 4 (ANTIGUO 1) ---
def generate_basic_evcs_augmented(secret_mask, cover_arrs, *, seed=None):
    """
    Construcción 4: CBW-EVCS aumentado (Antes Básico RGB).
    Usa el concepto de Color vs Clash (Color rotado).
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
                # Caso BLANCO: Distribución complementaria par/impar
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    # Aquí usamos simple Color vs Blanco, no Clash
                    block_color = np.stack([color, white])
                    block_white = np.stack([white, color])
                    
                    if i % 2 == 0:
                        pattern = block_color if flip else block_white
                    else:
                        pattern = block_white if flip else block_color
                    shares[i][r, c*2 : c*2+2] = pattern
            
            else:  
                # Caso NEGRO: Acumulación (Todos iguales o Clash)
                # Para la versión "Aumentada", usamos Clash (color rotado) en vez de blanco
                # para asegurar oscuridad.
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    # Clash: rotar canales RGB -> GBR
                    clash = np.roll(color, 1) 
                    
                    # El patrón incluye el clash para oscurecer más
                    block_clash = np.stack([clash, white])
                    
                    # Todos reciben el mismo patrón espacial
                    pattern = block_clash if flip else block_clash[::-1]
                    shares[i][r, c*2 : c*2+2] = pattern

    return [Image.fromarray(s) for s in shares]


# --- MÉTODO 5 (PLACEHOLDER) ---
def generate_perfect_black_placeholder(secret_mask, cover_arrs):
    """ Placeholder para Perfect Black Aumentado """
    h, w = secret_mask.shape
    dummy = Image.new("RGB", (w*2, h*2), (50, 50, 50)) # Gris oscuro indicativo
    return [dummy, dummy]