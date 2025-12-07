import base64
from io import BytesIO
from string import Template
import streamlit.components.v1 as components


def image_to_base64(img):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def render_drag_drop_demo(b64_img1, b64_img2, *, width=None, height=None, snap=18):
    cw = int(width or 900)
    ch = int(height or 600)
    aspect = f"{cw}/{ch}"
    template = Template(
        """
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { margin: 0; padding: 0; background: #f8fafc; font-family: 'Segoe UI', sans-serif; }
        .wrap { display: flex; flex-direction: column; gap: 10px; }
        .controls { display: flex; gap: 12px; align-items: center; justify-content: flex-end; padding: 6px 8px; }
        .btn { background: #0f172a; color: white; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        .btn:active { transform: translateY(1px); }
        .hint { color: #475569; font-size: 13px; margin-left: auto; }
        .canvas { position: relative; width: 100%; max-width: 1100px; aspect-ratio: ${aspect}; max-height: 78vh; border: 1px solid #d9e2ec; border-radius: 12px; overflow: hidden; background: #ffffff; margin: 0 auto; }
        .draggable { position: absolute; inset: 0; cursor: grab; width: 100%; height: 100%; mix-blend-mode: multiply; transition: box-shadow 0.15s ease; image-rendering: pixelated; image-rendering: crisp-edges; }
        .draggable:active { cursor: grabbing; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.18); }
        #img1 { border: 2px solid #2563eb; border-radius: 6px; z-index: 1; }
        #img2 { border: 2px solid #ef4444; border-radius: 6px; z-index: 2; }
        .badge { position: absolute; padding: 6px 10px; color: white; font-size: 13px; font-weight: 700; border-radius: 6px; z-index: 100; letter-spacing: 0.3px; }
        .badge.blue { background: #2563eb; left: 10px; top: 10px; }
        .badge.red { background: #ef4444; right: 10px; bottom: 10px; }
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="controls">
          <div class="hint">Arrastra y suelta. Si se alinean a menos de ${snap}px se acoplan.</div>
          <button class="btn" id="auto">Ajustar automáticamente</button>
        </div>
        <div class="canvas" id="canvas">
          <div class="badge blue">Participante 1</div>
          <div class="badge red">Participante 2</div>
          <img id="img1" src="data:image/png;base64,${img1}" class="draggable" draggable="false">
          <img id="img2" src="data:image/png;base64,${img2}" class="draggable" draggable="false">
        </div>
      </div>

      <script>
        const canvas = document.getElementById('canvas');
        const imgs = Array.from(document.querySelectorAll('.draggable'));
        const snapRange = ${snap};
        let active = null;
        let startX = 0, startY = 0, baseX = 0, baseY = 0;

        const applyTranslate = (el, x, y) => {
          const nx = Math.round(x);
          const ny = Math.round(y);
          el.style.transform = "translate3d(" + nx + "px, " + ny + "px, 0)";
        };

        const getTranslate = (el) => {
          const t = window.getComputedStyle(el).transform;
          if (t === 'none') return { x: 0, y: 0 };
          const m = new DOMMatrix(t);
          return { x: m.m41, y: m.m42 };
        };

        const snapTogether = () => {
          imgs.forEach(img => applyTranslate(img, 0, 0));
        };

        const maybeSnap = (el) => {
          const other = imgs.find(i => i !== el);
          const pos = getTranslate(el);
          const posOther = getTranslate(other);
          const dx = pos.x - posOther.x;
          const dy = pos.y - posOther.y;
          const dist = Math.hypot(dx, dy);
          if (dist <= snapRange) {
            snapTogether();
          }
        };

        const start = (e) => {
          if (!e.target.classList.contains('draggable')) return;
          active = e.target;
          const pos = getTranslate(active);
          baseX = pos.x;
          baseY = pos.y;
          startX = e.type === 'touchstart' ? e.touches[0].clientX : e.clientX;
          startY = e.type === 'touchstart' ? e.touches[0].clientY : e.clientY;
        };

        const move = (e) => {
          if (!active) return;
          e.preventDefault();
          const x = e.type === 'touchmove' ? e.touches[0].clientX : e.clientX;
          const y = e.type === 'touchmove' ? e.touches[0].clientY : e.clientY;
          const dx = x - startX;
          const dy = y - startY;
          applyTranslate(active, baseX + dx, baseY + dy);
        };

        const end = () => {
          if (active) maybeSnap(active);
          active = null;
        };

        const centerOffset = 30;
        window.addEventListener('load', () => {
          applyTranslate(imgs[0], -centerOffset, -centerOffset);
          applyTranslate(imgs[1], centerOffset, centerOffset);
        });

        canvas.addEventListener('mousedown', start, false);
        canvas.addEventListener('touchstart', start, false);
        window.addEventListener('mousemove', move, false);
        window.addEventListener('touchmove', move, false);
        window.addEventListener('mouseup', end, false);
        window.addEventListener('touchend', end, false);
        document.getElementById('auto').addEventListener('click', snapTogether);
      </script>
    </body>
    </html>
    """
    )
    html_code = template.substitute(aspect=aspect, img1=b64_img1, img2=b64_img2, snap=snap)
    components.html(html_code, height=720)