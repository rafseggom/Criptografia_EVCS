import numpy as np
from PIL import Image, ImageChops, ImageOps


def prepare_inputs(secret_file, cover_file, *, invert=False, size=640, dither=True):
    """Carga, normaliza y binariza entradas para los tres esquemas."""
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
    """Simula superposición física con modo multiply."""
    return ImageChops.multiply(share1.convert("RGB"), share2.convert("RGB"))


def generate_basic(secret_mask, cover_arr, *, seed=None):
    """Construcción 1: RGB básico con expansión m=2 (horizontal)."""
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    white = np.array([255, 255, 255], dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            color = cover_arr[r, c]
            block_color = np.stack([color, white])
            block_white = np.stack([white, color])
            flip = rng.random() > 0.5
            base = block_color if flip else block_white
            if secret_mask[r, c]:
                other = base
            else:
                other = block_white if flip else block_color
            s1[r, c * 2 : c * 2 + 2] = base
            s2[r, c * 2 : c * 2 + 2] = other

    return Image.fromarray(s1), Image.fromarray(s2)


def generate_complementary(secret_mask, cover_arr, *, seed=None):
    """Construcción 2: Complementarios CMY/RGB, expansión m=2."""
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            color = cover_arr[r, c]
            inv_color = 255 - color
            pair_a = np.stack([color, inv_color])
            pair_b = np.stack([inv_color, color])
            flip = rng.random() > 0.5
            base = pair_a if flip else pair_b
            if secret_mask[r, c]:
                other = base
            else:
                other = pair_b if flip else pair_a
            s1[r, c * 2 : c * 2 + 2] = base
            s2[r, c * 2 : c * 2 + 2] = other

    return Image.fromarray(s1), Image.fromarray(s2)


def generate_perfect_black(secret_mask, cover_arr, *, seed=None):
    """Construcción 3: Perfect Black m=4 (bloques 2x2)."""
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    s1 = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
    white = np.array([255, 255, 255], dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            color = cover_arr[r, c]
            pat_diag = np.stack(
                [np.stack([color, white]), np.stack([white, color])]
            )
            pat_anti = np.stack(
                [np.stack([white, color]), np.stack([color, white])]
            )
            flip = rng.random() > 0.5
            base = pat_diag if flip else pat_anti
            if secret_mask[r, c]:
                other = base
            else:
                other = pat_anti if flip else pat_diag
            s1[r * 2 : r * 2 + 2, c * 2 : c * 2 + 2] = base
            s2[r * 2 : r * 2 + 2, c * 2 : c * 2 + 2] = other

    return Image.fromarray(s1), Image.fromarray(s2)


def generate_basic_multi(secret_mask, cover_arrs, *, seed=None):
    """Yang et al. (2015): Construcción EVCS con n participantes y imágenes de cobertura personalizadas.
    
    Principio:
    - Píxel NEGRO (secreto): TODAS las sombras tienen el MISMO bloque (al multiplicar = negro)
    - Píxel BLANCO (fondo): Las sombras tienen bloques DIFERENTES que se cancelan (al multiplicar = blanco)
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs)
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(n)]
    white = np.array([255, 255, 255], dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            if secret_mask[r, c]:  # PIXEL NEGRO (secreto)
                # Todas las sombras obtienen el MISMO patrón [color, blanco]
                flip = rng.random() > 0.5
                for participant_idx in range(n):
                    color = cover_arrs[participant_idx][r, c]
                    block_color = np.stack([color, white])
                    block_white = np.stack([white, color])
                    pattern = block_color if flip else block_white
                    shares[participant_idx][r, c * 2 : c * 2 + 2] = pattern
            else:  # PIXEL BLANCO (fondo)
                # Cada participante obtiene un patrón DIFERENTE
                # Distribución: los índices pares y impares reciben patrones invertidos
                flip = rng.random() > 0.5
                for participant_idx in range(n):
                    color = cover_arrs[participant_idx][r, c]
                    block_color = np.stack([color, white])
                    block_white = np.stack([white, color])
                    
                    # Patrón complementario basado en paridad
                    if participant_idx % 2 == 0:
                        pattern = block_white if flip else block_color
                    else:
                        pattern = block_color if flip else block_white
                    
                    shares[participant_idx][r, c * 2 : c * 2 + 2] = pattern

    return [Image.fromarray(s) for s in shares]


def generate_complementary_multi(secret_mask, cover_arrs, *, seed=None):
    """Construcción 2 extendida a n participantes con imágenes de cobertura personalizadas."""
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs)
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(n)]

    for r in range(h):
        for c in range(w):
            flip = rng.random() > 0.5  # MISMO flip para todos los participantes en este píxel
            
            for participant_idx in range(n):
                color = cover_arrs[participant_idx][r, c]
                inv_color = 255 - color
                pair_a = np.stack([color, inv_color])
                pair_b = np.stack([inv_color, color])
                
                if secret_mask[r, c]:  # PIXEL NEGRO
                    # Todos obtienen el MISMO patrón
                    shares[participant_idx][r, c * 2 : c * 2 + 2] = pair_a if flip else pair_b
                else:  # PIXEL BLANCO
                    # Patrones DIFERENTES según paridad
                    if participant_idx % 2 == 0:
                        pattern = pair_b if flip else pair_a
                    else:
                        pattern = pair_a if flip else pair_b
                    shares[participant_idx][r, c * 2 : c * 2 + 2] = pattern

    return [Image.fromarray(s) for s in shares]