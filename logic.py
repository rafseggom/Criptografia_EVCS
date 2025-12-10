import numpy as np
from PIL import Image, ImageChops, ImageOps

def prepare_inputs(secret_file, cover_file, *, invert=False, size=640, dither=True):
    """Carga, normaliza y binariza entradas."""
    secret = Image.open(secret_file).convert("L").resize((size, size))
    if invert:
        secret = ImageOps.invert(secret)

    if dither:
        secret_bw = secret.convert("1")
    else:
        # Umbral simple: <128 es Negro (0), >=128 es Blanco (255)
        secret_bw = secret.point(lambda x: 255 if x >= 128 else 0, mode="1")

    cover = Image.open(cover_file).convert("RGB").resize((size, size))
    
    # En PIL '1': True (1) es Blanco, False (0) es Negro.
    secret_mask = np.array(secret_bw, dtype=bool) 
    cover_arr = np.array(cover, dtype=np.uint8)
    
    return secret_bw.convert("L"), cover, secret_mask, cover_arr


def overlay(share1, share2):
    """Simula superposición física con modo multiply (modelo sustractivo)."""
    return ImageChops.multiply(share1.convert("RGB"), share2.convert("RGB"))


def generate_basic(secret_mask, cover_arr, *, seed=None):
    """
    Construcción 1 (RGB) CORREGIDA: Alineación de colisión.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    white = np.array([255, 255, 255], dtype=np.uint8)

    # El clash es el color rotado (R->G->B)
    cover_clash = np.roll(cover_arr, 1, axis=2)

    for r in range(h):
        for c in range(w):
            color = cover_arr[r, c]
            clash = cover_clash[r, c]
            
            # U1: [Color, Blanco]
            block_u1 = np.stack([color, white])
            
            # U2: Depende del secreto
            if secret_mask[r, c]: # BLANCO (Fondo)
                # Coincidencia: [Color, Blanco]
                # Resultado: [Color, Blanco] (Luz)
                block_u2 = np.stack([color, white])
            else: # NEGRO (Secreto)
                # CORRECCIÓN MATEMÁTICA:
                # El 'clash' debe estar en la posición 0 para chocar con el 'color' de U1.
                # Resultado: [Color*Clash, Blanco*Blanco] = [NEGRO, BLANCO]
                block_u2 = np.stack([clash, white])

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
    Construcción 2 (Complementarios): Correcta, usa inverso.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            color = cover_arr[r, c]
            inv_color = 255 - color # Inverso matemático
            
            pair_a = np.stack([color, inv_color])
            pair_b = np.stack([inv_color, color])
            
            flip = rng.random() > 0.5
            
            if secret_mask[r, c]: # Blanco
                base = pair_a if flip else pair_b
                other = base
            else: # Negro
                base = pair_a if flip else pair_b
                other = pair_b if flip else pair_a # Inverso
            
            s1[r, c * 2 : c * 2 + 2] = base
            s2[r, c * 2 : c * 2 + 2] = other

    return Image.fromarray(s1), Image.fromarray(s2)


def generate_perfect_black(secret_mask, cover_arr, *, seed=None):
    """
    Perfect Black estricto:
    - Para PIXEL BLANCO (fondo): ambas sombras llevan el mismo patrón (diagonal o antidiagonal)
      usando [C, W] / [W, C] (como en tu versión).
    - Para PIXEL NEGRO (tinta): diseñamos los dos bloques de 2x2 de forma que **en cada
      subposición** al menos una de las sombras tenga BLACK = [0,0,0]. Así, al multiplicar,
      el resultado es BLACK puro en toda la celda 2x2.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    s1 = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
    white = np.array([255, 255, 255], dtype=np.uint8)
    black = np.array([0, 0, 0], dtype=np.uint8)
    inv_cover = 255 - cover_arr

    for r in range(h):
        for c in range(w):
            color = cover_arr[r, c]
            inv   = inv_cover[r, c]
            flip = rng.random() > 0.5

            # Matriz Diagonal (opción de fondo)
            mat_diag = np.stack([
                np.stack([color, white]),
                np.stack([white, color])
            ])

            # Matriz Antidiagonal (opción de fondo alternativa)
            mat_anti_spatial = np.stack([
                np.stack([white, color]),
                np.stack([color, white])
            ])

            if secret_mask[r, c]:  # SECRETO BLANCO -> ambas sombras iguales
                base = mat_diag if flip else mat_anti_spatial
                s1[r*2:r*2+2, c*2:c*2+2] = base
                s2[r*2:r*2+2, c*2:c*2+2] = base
            else:  # SECRETO NEGRO -> patrón estricto que garantiza NEGRO al superponer
                # Estrategia: para cada una de las 4 posiciones (2x2) ponemos BLACK en
                # al menos una de las dos sombras.
                # Construimos:
                #   s1_blk = [[C, BLACK],
                #             [BLACK, C]]
                #   s2_blk = [[BLACK, inv],
                #             [inv, BLACK]]
                # Resultado por posición (multiplicación):
                #   (C * BLACK) = BLACK
                #   (BLACK * inv) = BLACK
                #   etc -> Toda la celda 2x2 queda BLACK.
                s1_blk = np.stack([
                    np.stack([color, black]),
                    np.stack([black, color])
                ])
                s2_blk = np.stack([
                    np.stack([black, inv]),
                    np.stack([inv, black])
                ])

                # Si queremos alternar orientación visual para estética, podemos rotar
                # los bloques cuando flip=True (manteniendo la propiedad de bloqueo).
                if flip:
                    # rota 90 grados (equivalente a transpose + flip)
                    s1_blk = np.rot90(s1_blk, k=1, axes=(0,1))
                    s2_blk = np.rot90(s2_blk, k=1, axes=(0,1))

                s1[r*2:r*2+2, c*2:c*2+2] = s1_blk
                s2[r*2:r*2+2, c*2:c*2+2] = s2_blk

    return Image.fromarray(s1), Image.fromarray(s2)


def generate_basic_multi(secret_mask, cover_arrs, *, seed=None):
    """
    Yang et al. (2015): Construcción VCS extendida para n participantes.
    
    Principio matemático:
    - Píxel NEGRO (secreto): TODAS las sombras generan [Color_i, Blanco]
      → Al multiplicar: Color_1 × Color_2 × ... × Color_n × Blanco = NEGRO ✓
    
    - Píxel BLANCO (fondo): Las sombras generan patrones ALTERNOS
      → Índices pares: [Color_i, Blanco]
      → Índices impares: [Blanco, Color_i]
      → Al multiplicar: Se cancelan y producen BLANCO ✓
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs)
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(n)]
    white = np.array([255, 255, 255], dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            flip = rng.random() > 0.5
            
            if secret_mask[r, c]:  # PIXEL BLANCO (Fondo)
                # Patrones alternos que se cancelan
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    block_color = np.stack([color, white])
                    block_white = np.stack([white, color])
                    
                    # Paridad determina patrón
                    if i % 2 == 0:
                        pattern = block_color if flip else block_white
                    else:
                        pattern = block_white if flip else block_color
                    
                    shares[i][r, c*2 : c*2+2] = pattern
            
            else:  # PIXEL NEGRO (Secreto)
                # TODAS las sombras generan el MISMO patrón
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    block_color = np.stack([color, white])
                    block_white = np.stack([white, color])
                    
                    # MISMO patrón para todos
                    pattern = block_color if flip else block_white
                    shares[i][r, c*2 : c*2+2] = pattern

    return [Image.fromarray(s) for s in shares]


def generate_complementary_multi(secret_mask, cover_arrs, *, seed=None):
    """
    Yang et al. (2015) con colores complementarios para mayor contraste.
    Usa inverso cromático en lugar de blanco.
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs)
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(n)]

    for r in range(h):
        for c in range(w):
            flip = rng.random() > 0.5
            
            if secret_mask[r, c]:  # PIXEL BLANCO
                # Patrones alternos con complementarios
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    inv_color = 255 - color
                    pair_a = np.stack([color, inv_color])
                    pair_b = np.stack([inv_color, color])
                    
                    if i % 2 == 0:
                        pattern = pair_a if flip else pair_b
                    else:
                        pattern = pair_b if flip else pair_a
                    
                    shares[i][r, c*2 : c*2+2] = pattern
            
            else:  # PIXEL NEGRO
                # TODAS las sombras: MISMO patrón
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    inv_color = 255 - color
                    pair_a = np.stack([color, inv_color])
                    pair_b = np.stack([inv_color, color])
                    
                    pattern = pair_a if flip else pair_b
                    shares[i][r, c*2 : c*2+2] = pattern

    return [Image.fromarray(s) for s in shares]