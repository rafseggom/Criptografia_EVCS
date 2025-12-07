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
      body {{ margin: 0; padding: 0; background-color: #f0f2f6; }}
      .container {{
        position: relative;
        width: 100%;
        height: 550px;
        border: 2px dashed #bbb;
        border-radius: 8px;
        display: flex;
        justify_content: center;
        align-items: center;
        overflow: hidden;
      }}
      .draggable {{
        position: absolute;
        cursor: grab;
        max-width: 90%;
        max-height: 90%;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        mix-blend-mode: multiply; 
      }}
      .draggable:active {{ cursor: grabbing; }}
      #img1 {{ left: 5%; top: 5%; border: 4px solid #3b82f6; }} /* Azul - Participante 1 */
      #img2 {{ right: 5%; bottom: 5%; border: 4px solid #ef4444; }} /* Rojo - Participante 2 */
      
      .label {{
        position: absolute;
        background: white;
        padding: 2px 5px;
        font-family: monospace;
        font-weight: bold;
        border-radius: 3px;
        z-index: 10;
      }}
    </style>
    </head>
    <body>
    <div class="container">
      <div style="position:absolute; top:10px; left:10px; color:#555; font-family:sans-serif;">
        Arrastra una imagen sobre la otra para "sumar" las transparencias.
      </div>
      
      <img id="img1" src="data:image/png;base64,{b64_img1}" class="draggable" style="z-index: 1;">
      <img id="img2" src="data:image/png;base64,{b64_img2}" class="draggable" style="z-index: 2;">
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
    components.html(html_code, height=560)