import base64
from io import BytesIO
from string import Template
import streamlit.components.v1 as components


def image_to_base64(img):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def render_multi_drag_demo(b64_images, *, height=820):
    items_html = "\n".join([
        f'<img id="img{i}" src="data:image/png;base64,{b64}" class="draggable" draggable="false">'
        for i, b64 in enumerate(b64_images)
    ])
    template = Template(
        """
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { margin: 0; padding: 0; background: #f8fafc; font-family: 'Segoe UI', sans-serif; }
        .wrap { display: flex; flex-direction: column; gap: 10px; width: min(96vw, 1650px); margin: 0 auto; }
        .controls { display: flex; gap: 12px; align-items: center; justify-content: flex-end; padding: 6px 8px; }
        .btn { background: #0f172a; color: white; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        .btn:active { transform: translateY(1px); }
        .hint { color: #475569; font-size: 13px; margin-right: auto; }
        .canvas { position: relative; width: 100%; height: ${height}px; border: 1px solid #d9e2ec; border-radius: 12px; overflow: hidden; background: #ffffff; }
        .draggable { position: absolute; left: 10%; top: 10%; width: 80%; height: 80%; cursor: grab; mix-blend-mode: multiply; transition: box-shadow 0.15s ease; image-rendering: pixelated; image-rendering: crisp-edges; }
        .draggable:active { cursor: grabbing; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.18); }
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="controls">
          <div class="hint">Arrastra libremente. Usa botones para alinear todas o todas menos una.</div>
          <button class="btn" id="auto_n">Ajustar n</button>
          <button class="btn" id="auto_n1">Ajustar n-1</button>
        </div>
        <div class="canvas" id="canvas">
          ${items}
        </div>
      </div>

      <script>
        const imgs = Array.from(document.querySelectorAll('.draggable'));
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

        const snapAll = () => imgs.forEach(img => applyTranslate(img, 0, 0));
        const snapN1 = () => imgs.forEach((img, idx) => applyTranslate(img, idx === imgs.length - 1 ? 40 : 0, idx === imgs.length - 1 ? 40 : 0));

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

        const end = () => { active = null; };

        window.addEventListener('load', () => {
          imgs.forEach((img, idx) => applyTranslate(img, idx * 24, idx * 24));
        });

        document.getElementById('canvas').addEventListener('mousedown', start, false);
        document.getElementById('canvas').addEventListener('touchstart', start, false);
        window.addEventListener('mousemove', move, false);
        window.addEventListener('touchmove', move, false);
        window.addEventListener('mouseup', end, false);
        window.addEventListener('touchend', end, false);
        document.getElementById('auto_n').addEventListener('click', snapAll);
        document.getElementById('auto_n1').addEventListener('click', snapN1);
      </script>
    </body>
    </html>
    """
    )
    html_code = template.substitute(items=items_html, height=height)
    components.html(html_code, height=height + 100)


def render_drag_drop_demo(b64_img1, b64_img2, *, width=None, height=None):
    cw = int(width or 900)
    ch = int(height or 600)
    cw_view = int(cw * 1.35)
    ch_view = int(ch * 1.35)
    template = Template(
        """
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { margin: 0; padding: 0; background: #f8fafc; font-family: 'Segoe UI', sans-serif; }
        .wrap { display: flex; flex-direction: column; gap: 10px; width: min(95vw, 1600px); margin: 0 auto; }
        .controls { display: flex; gap: 12px; align-items: center; justify-content: flex-end; padding: 6px 8px; }
        .btn { background: #0f172a; color: white; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        .btn:active { transform: translateY(1px); }
        .hint { color: #475569; font-size: 13px; margin-left: auto; }
        .canvas { position: relative; width: 100%; height: clamp(60vh, ${ch_view}px, 90vh); border: 1px solid #d9e2ec; border-radius: 12px; overflow: hidden; background: #ffffff; }
        .draggable { position: absolute; left: 6%; top: 6%; width: 88%; height: 88%; cursor: grab; mix-blend-mode: multiply; transition: box-shadow 0.15s ease; image-rendering: pixelated; image-rendering: crisp-edges; }
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
          <div class="hint">Arrastra y suelta. Usa el botón para alinear perfecto.</div>
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

        const end = () => { active = null; };

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
    html_code = template.substitute(img1=b64_img1, img2=b64_img2, cw=cw, ch=ch, cw_view=cw_view, ch_view=ch_view)
    components.html(html_code, height=720)