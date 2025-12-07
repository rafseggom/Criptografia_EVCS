import numpy as np
from PIL import Image, ImageChops, ImageOps

def process_images(secret_path, cover_path, invert_secret=False):
    """
    Procesa las imágenes.
    Añadido: invert_secret para arreglar si el negro/blanco sale al revés.
    """
    target_size = (400, 400) # Un poco más grande para el proyector
    
    # Procesar Secreto
    secret = Image.open(secret_path).convert('L').resize(target_size) # Escala de grises primero
    # Binarizar con umbral (Threshold) para limpiar ruido jpg
    secret = secret.point(lambda x: 0 if x < 128 else 255, '1')
    
    if invert_secret:
        secret = ImageOps.invert(secret.convert('L')).convert('1')
        
    # Procesar Cover
    cover = Image.open(cover_path).convert('RGB').resize(target_size)
    
    return secret, cover

def superimpose_images(img1, img2):
    """Simula la superposición de transparencias (Multiply)."""
    img1 = img1.convert("RGBA")
    img2 = img2.convert("RGBA")
    return ImageChops.multiply(img1, img2)

def generate_rgb_basic(secret_img, cover_img):
    """Construcción 1: Básica (m=2)"""
    secret_arr = np.array(secret_img)
    cover_arr = np.array(cover_img)
    h, w = secret_arr.shape
    
    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    
    for r in range(h):
        for c in range(w):
            color = list(cover_arr[r, c])
            white = [255, 255, 255]
            
            # Bloques base
            # [Color, Blanco]
            b_color = [color, white]
            # [Blanco, Color]
            b_white = [white, color]
            
            # Aleatorizar S1
            flip = np.random.rand() > 0.5
            p1 = b_color if flip else b_white
            
            # Lógica:
            # Secreto Blanco (Fondo) -> Sombras IGUALES (Color+Color=Color, Blanco+Blanco=Blanco) -> Se ve la imagen cover clara
            # Secreto Negro (Tinta)  -> Sombras OPUESTAS (Color+Blanco=Color, Blanco+Color=Color) -> Se ve TODO color (Más denso/oscuro visualmente)
            
            if secret_arr[r, c] > 0: # Blanco (255)
                p2 = p1 
            else: # Negro (0)
                p2 = b_white if flip else b_color
            
            s1[r, c*2:c*2+2] = p1
            s2[r, c*2:c*2+2] = p2
            
    return Image.fromarray(s1), Image.fromarray(s2)

def generate_cmy_complementary(secret_img, cover_img):
    """Construcción 2: Complementarios (Alto Contraste)"""
    secret_arr = np.array(secret_img)
    cover_arr = np.array(cover_img)
    h, w = secret_arr.shape
    
    s1 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h, w * 2, 3), dtype=np.uint8)
    
    for r in range(h):
        for c in range(w):
            col = cover_arr[r, c]
            color = list(col)
            # Inverso matemático
            inv_color = [255 - x for x in col]
            
            flip = np.random.rand() > 0.5
            pair_A = [color, inv_color]
            pair_B = [inv_color, color]
            
            p1 = pair_A if flip else pair_B
            
            if secret_arr[r, c] > 0: # Blanco -> Iguales
                p2 = p1
            else: # Negro -> Opuestos
                p2 = pair_B if flip else pair_A

            s1[r, c*2:c*2+2] = p1
            s2[r, c*2:c*2+2] = p2
            
    return Image.fromarray(s1), Image.fromarray(s2)

def generate_perfect_black(secret_img, cover_img):
    """Construcción 3 (Paper Cons.5): Perfect Black (m=4)"""
    secret_arr = np.array(secret_img)
    cover_arr = np.array(cover_img)
    h, w = secret_arr.shape
    
    s1 = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
    s2 = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
    
    for r in range(h):
        for c in range(w):
            color = list(cover_arr[r, c])
            white = [255, 255, 255]
            
            # Bloques 2x2
            # Diagonal: [C, W]
            #           [W, C]
            pat_D = np.array([[color, white], [white, color]], dtype=np.uint8)
            
            # Anti-Diagonal: [W, C]
            #                [C, W]
            pat_A = np.array([[white, color], [color, white]], dtype=np.uint8)
            
            flip = np.random.rand() > 0.5
            base_p1 = pat_D if flip else pat_A
            
            if secret_arr[r, c] > 0: # Blanco
                base_p2 = base_p1 # Iguales -> Dejan huecos blancos
            else: # Negro
                base_p2 = pat_A if flip else pat_D # Opuestos -> Llenan todo de color (Oscuro)
            
            s1[r*2:r*2+2, c*2:c*2+2] = base_p1
            s2[r*2:r*2+2, c*2:c*2+2] = base_p2
            
    return Image.fromarray(s1), Image.fromarray(s2)