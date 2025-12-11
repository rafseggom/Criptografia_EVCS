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
    Yang et al. (2015): Construcción VCS extendida para n participantes.
    
    Principio matemático:
    - Píxel BLANCO (fondo/máscara=True): Patrones ALTERNOS que se cancelan
    - Píxel NEGRO (secreto/máscara=False): TODAS las sombras generan el MISMO patrón
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
                # Patrones alternos que se cancelan
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    block_color = np.stack([color, white])
                    block_white = np.stack([white, color])
                    
                    if i % 2 == 0:
                        pattern = block_color if flip else block_white
                    else:
                        pattern = block_white if flip else block_color
                    
                    shares[i][r, c*2 : c*2+2] = pattern
            
            else:  # NEGRO (secreto)
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
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs)
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(n)]

    for r in range(h):
        for c in range(w):
            flip = rng.random() > 0.5
            
            if secret_mask[r, c]:  # BLANCO
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
            
            else:  # NEGRO
                # TODAS las sombras: MISMO patrón
                for i in range(n):
                    color = cover_arrs[i][r, c]
                    inv_color = 255 - color
                    pair_a = np.stack([color, inv_color])
                    pair_b = np.stack([inv_color, color])
                    
                    pattern = pair_a if flip else pair_b
                    shares[i][r, c*2 : c*2+2] = pattern

    return [Image.fromarray(s) for s in shares]


def generate_simple_6color(secret_mask, cover_arrs, *, seed=None):
    """
    Construcción 4: Simple 6-Color según Yang et al. (2015)
    
    Esquema puro con 6 colores primarios aleatorios.
    
    Usa los 6 colores primarios del modelo RGB + CMY:
    - Colores: Red, Green, Blue, Cyan, Magenta, Yellow
    - Complementarios: R↔C, G↔M, B↔Y
    
    Principio CORRECTO:
    - Píxel NEGRO del SECRETO: Complementarios en MISMAS posiciones
      → S1[pos0]=R y S2[pos0]=C → R×C = Negro
      → S1[pos1]=G y S2[pos1]=M → G×M = Negro
      → Resultado: TODO NEGRO
      
    - Píxel BLANCO del SECRETO: NO complementarios en MISMAS posiciones
      → S1[pos0]=R y S2[pos0]=G → R×G = Color oscuro pero NO negro
      → Resultado: COLORES (no negro)
    """
    rng = np.random.default_rng(seed)
    h, w = secret_mask.shape
    n = len(cover_arrs)
    
    if n != 2:
        raise ValueError("Simple 6-Color requiere exactamente 2 participantes")
    
    shares = [np.zeros((h, w * 2, 3), dtype=np.uint8) for _ in range(2)]
    
    # 6 colores primarios RGB + CMY (valores puros para máximo contraste)
    colors = {
        0: np.array([255, 0, 0], dtype=np.uint8),      # Red
        1: np.array([0, 255, 0], dtype=np.uint8),      # Green
        2: np.array([0, 0, 255], dtype=np.uint8),      # Blue
        3: np.array([0, 255, 255], dtype=np.uint8),    # Cyan
        4: np.array([255, 0, 255], dtype=np.uint8),    # Magenta
        5: np.array([255, 255, 0], dtype=np.uint8),    # Yellow
    }
    
    # Pares complementarios: R↔C(0↔3), G↔M(1↔4), B↔Y(2↔5)
    complementary = {0: 3, 3: 0, 1: 4, 4: 1, 2: 5, 5: 2}

    for r in range(h):
        for c in range(w):
            
            if secret_mask[r, c]:  # BLANCO del SECRETO (fondo)
                # Elegir 2 colores aleatorios para cada posición del píxel expandido
                # IMPORTANTE: NO deben ser complementarios entre sombras en la MISMA posición
                
                # Posición 0 del píxel expandido
                c1_pos0 = rng.integers(0, 6)
                c2_pos0 = rng.integers(0, 6)
                # Asegurar que NO sean complementarios
                while c2_pos0 == complementary[c1_pos0]:
                    c2_pos0 = rng.integers(0, 6)
                
                # Posición 1 del píxel expandido
                c1_pos1 = rng.integers(0, 6)
                c2_pos1 = rng.integers(0, 6)
                # Asegurar que NO sean complementarios
                while c2_pos1 == complementary[c1_pos1]:
                    c2_pos1 = rng.integers(0, 6)
                
                shares[0][r, c*2] = colors[c1_pos0]
                shares[0][r, c*2+1] = colors[c1_pos1]
                
                shares[1][r, c*2] = colors[c2_pos0]
                shares[1][r, c*2+1] = colors[c2_pos1]
            
            else:  # NEGRO del SECRETO
                # Elegir colores complementarios para CADA posición
                # S1 y S2 deben tener complementarios en las MISMAS posiciones
                
                # Posición 0: elegir un color base y su complementario
                base0 = rng.integers(0, 6)
                comp0 = complementary[base0]
                
                # Posición 1: elegir otro par (puede ser el mismo o diferente)
                base1 = rng.integers(0, 6)
                comp1 = complementary[base1]
                
                # S1 tiene los colores base, S2 tiene los complementarios
                shares[0][r, c*2] = colors[base0]
                shares[0][r, c*2+1] = colors[base1]
                
                shares[1][r, c*2] = colors[comp0]
                shares[1][r, c*2+1] = colors[comp1]

    return [Image.fromarray(s) for s in shares]
