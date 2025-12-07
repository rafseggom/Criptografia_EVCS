import numpy as np
from PIL import Image, ImageChops

def process_images(secret_path, cover_path):
    """Prepara las imágenes a 300x300."""
    target_size = (300, 300)
    secret = Image.open(secret_path).convert('1').resize(target_size)
    cover = Image.open(cover_path).convert('RGB').resize(target_size)
    return secret, cover

def superimpose_images(img1, img2):
    """
    Simula la superposición física perfecta (Operación Multiply).
    Esto es lo que hace el botón automático.
    """
    # Convertimos a RGBA para asegurar compatibilidad
    img1 = img1.convert("RGBA")
    img2 = img2.convert("RGBA")
    # ImageChops.multiply simula poner dos transparencias una sobre otra
    return ImageChops.multiply(img1, img2)

def generate_rgb_basic(secret_img, cover_img):
    """Construcción 1: Básica RGB (m=2)"""
    secret_arr = np.array(secret_img)
    cover_arr = np.array(cover_img)
    h, w = secret_arr.shape
    
    s1 = np.zeros((h, w * 2, 4), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 4), dtype=np.uint8)
    
    for r in range(h):
        for c in range(w):
            color = list(cover_arr[r, c]) + [255]
            trans = [0, 0, 0, 0]
            
            # Bloques base
            # Opción A: [Color, Trans]
            opt_A = [color, trans]
            # Opción B: [Trans, Color]
            opt_B = [trans, color]
            
            # Elección aleatoria de la base para S1 (Fundamental para seguridad)
            # Si no hacemos esto, S1 siempre sería igual y S2 llevaría el secreto.
            idx = np.random.randint(0, 2) # 0 o 1
            pattern_base = opt_A if idx == 0 else opt_B
            pattern_inverse = opt_B if idx == 0 else opt_A
            
            if secret_arr[r, c] > 0: # Blanco (Secreto) -> Iguales
                p1 = pattern_base
                p2 = pattern_base
            else: # Negro (Secreto) -> Complementarios
                p1 = pattern_base
                p2 = pattern_inverse
            
            s1[r, c*2:c*2+2] = p1
            s2[r, c*2:c*2+2] = p2
            
    return Image.fromarray(s1), Image.fromarray(s2)

def generate_cmy_complementary(secret_img, cover_img):
    """Construcción 2: Inversión de color"""
    secret_arr = np.array(secret_img)
    cover_arr = np.array(cover_img)
    h, w = secret_arr.shape
    
    s1 = np.zeros((h, w * 2, 4), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 4), dtype=np.uint8)
    
    for r in range(h):
        for c in range(w):
            col = cover_arr[r, c]
            color = list(col) + [255]
            inv_color = [255 - x for x in col] + [255]
            
            # Aleatorización de posición
            if np.random.rand() > 0.5:
                pair_A = [color, inv_color]
                pair_B = [inv_color, color]
            else:
                pair_A = [inv_color, color]
                pair_B = [color, inv_color]
            
            if secret_arr[r, c] > 0: # Blanco -> Iguales
                p1 = pair_A
                p2 = pair_A
            else: # Negro -> Opuestos
                p1 = pair_A
                p2 = pair_B

            s1[r, c*2:c*2+2] = p1
            s2[r, c*2:c*2+2] = p2
            
    return Image.fromarray(s1), Image.fromarray(s2)

def generate_perfect_black(secret_img, cover_img):
    """
    Construcción 5: Perfect Black (m=4, Bloque 2x2).
    CORREGIDO: Aleatorización total para evitar que el secreto se vea en una sombra.
    """
    secret_arr = np.array(secret_img)
    cover_arr = np.array(cover_img)
    h, w = secret_arr.shape
    
    s1 = np.zeros((h * 2, w * 2, 4), dtype=np.uint8)
    s2 = np.zeros((h * 2, w * 2, 4), dtype=np.uint8)
    
    for r in range(h):
        for c in range(w):
            color = list(cover_arr[r, c]) + [255]
            trans = [0, 0, 0, 0]
            
            # Definimos dos patrones base opuestos para el bloque 2x2
            # Patrón Diagonal (D)
            pat_D = np.array([[color, trans], 
                              [trans, color]], dtype=np.uint8)
            # Patrón Anti-Diagonal (A)
            pat_A = np.array([[trans, color], 
                              [color, trans]], dtype=np.uint8)
            
            # --- ALEATORIZACIÓN CRÍTICA ---
            # Tiramos una moneda para decidir qué patrón lleva Sombra 1.
            # Esto asegura que Sombra 1 sea ruido aleatorio puro.
            flip = np.random.rand() > 0.5
            base_p1 = pat_D if flip else pat_A
            
            # Ahora decidimos Sombra 2 basándonos en el Secreto y en Sombra 1
            if secret_arr[r, c] > 0: # Blanco (Luz) -> S2 debe ser IGUAL a S1
                base_p2 = base_p1
            else: # Negro (Oscuridad) -> S2 debe ser OPUESTO a S1
                # Si S1 era D, S2 es A. Si S1 era A, S2 es D.
                base_p2 = pat_A if flip else pat_D
            
            # Asignamos
            s1[r*2:r*2+2, c*2:c*2+2] = base_p1
            s2[r*2:r*2+2, c*2:c*2+2] = base_p2
            
    return Image.fromarray(s1), Image.fromarray(s2)