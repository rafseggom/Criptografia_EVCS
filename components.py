import streamlit.components.v1 as components
import base64
from io import BytesIO

def image_to_base64(img):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def render_drag_drop_demo(b64_img1, b64_img2):
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
      /* FONDO BLANCO PARA SIMULAR MESA DE LUZ / PAPEL */
      body {{ margin: 0; padding: 0; background-color: #ffffff; }}
      
      .container {{
        position: relative;
        width: 100%;
        height: 600px;
        border: 2px solid #ccc;
        border-radius: 8px;
        display: flex;
        justify_content: center;
        align-items: center;
        overflow: hidden;
        background-color: white;
      }}
      
      .draggable {{
        position: absolute;
        cursor: grab;
        max-width: 90%;
        max-height: 90%;
        /* MULTIPLY: Simula tintas sumándose sobre papel blanco */
        mix-blend-mode: multiply; 
      }}
      
      .draggable:active {{ cursor: grabbing; }}
      
      /* Borde rojo y azul para diferenciar */
      #img1 {{ left: 5%; top: 5%; border: 2px solid #3b82f6; z-index: 1; }}
      #img2 {{ right: 5%; bottom: 5%; border: 2px solid #ef4444; z-index: 2; }}
      
      .badge {{
        position: absolute;
        padding: 5px 10px;
        color: white;
        font-family: sans-serif;
        font-size: 14px;
        font-weight: bold;
        border-radius: 4px;
        z-index: 100;
      }}
    </style>
    </head>
    <body>
    <div class="container">
      <div class="badge" style="background:#3b82f6; left:5%; top:1%;">Participante 1</div>
      <div class="badge" style="background:#ef4444; right:5%; bottom:1%;">Participante 2 (Arrástrame)</div>

      <img id="img1" src="data:image/png;base64,{b64_img1}" class="draggable">
      <img id="img2" src="data:image/png;base64,{b64_img2}" class="draggable">
    </div>

    <script>
      var container = document.querySelector(".container");
      var activeItem = null;
      var active = false;
      var initialX, initialY, currentX, currentY;
      var xOffset = 0, yOffset = 0;

      var draggables = document.querySelectorAll(".draggable");

      draggables.forEach(item => {{
        item.addEventListener("mousedown", dragStart, false);
        item.addEventListener("touchstart", dragStart, false);
      }});

      document.addEventListener("mouseup", dragEnd, false);
      document.addEventListener("touchend", dragEnd, false);
      document.addEventListener("mousemove", drag, false);
      document.addEventListener("touchmove", drag, false);

      function dragStart(e) {{
        if (e.target.classList.contains('draggable')) {{
          activeItem = e.target;
          active = true;
          var style = window.getComputedStyle(activeItem);
          var matrix = new WebKitCSSMatrix(style.transform);
          xOffset = matrix.m41;
          yOffset = matrix.m42;

          if (e.type === "touchstart") {{
            initialX = e.touches[0].clientX - xOffset;
            initialY = e.touches[0].clientY - yOffset;
          }} else {{
            initialX = e.clientX - xOffset;
            initialY = e.clientY - yOffset;
          }}
        }}
      }}

      function dragEnd(e) {{
        initialX = currentX;
        initialY = currentY;
        active = false;
        activeItem = null;
      }}

      function drag(e) {{
        if (active && activeItem) {{
          e.preventDefault();
          if (e.type === "touchmove") {{
            currentX = e.touches[0].clientX - initialX;
            currentY = e.touches[0].clientY - initialY;
          }} else {{
            currentX = e.clientX - initialX;
            currentY = e.clientY - initialY;
          }}
          setTranslate(currentX, currentY, activeItem);
        }}
      }}

      function setTranslate(xPos, yPos, el) {{
        el.style.transform = "translate3d(" + xPos + "px, " + yPos + "px, 0)";
      }}
    </script>
    </body>
    </html>
    """
    components.html(html_code, height=620)