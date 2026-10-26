from __future__ import annotations
import json, math
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from PIL import Image, ImageOps, ImageDraw

@dataclass(frozen=True)
class TimingProfile:
    point_step_px: float = 2.0
    point_delay_ms: float = 10.0
    before_mouse_down_ms: float = 20.0
    after_mouse_up_ms: float = 20.0
    after_mouse_down_ms: float = 40.0
    before_mouse_up_ms: float = 50.0

@dataclass(frozen=True)
class PlanMetrics:
    stroke_count: int
    point_count: int
    drawing_length_px: float
    pen_up_distance_px: float
    strokes_1_2px: int
    strokes_3_5px: int
    strokes_6_10px: int
    strokes_over_10px: int
    estimated_seconds: float

def load_json(path: str | Path) -> dict[str, Any]:
    try: data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, json.JSONDecodeError) as exc: raise ValueError(f'Не удалось прочитать JSON: {exc}') from exc
    if not isinstance(data, dict): raise ValueError('Корень DrawingPlan JSON должен быть объектом.')
    return data

def _xy(p):
    if isinstance(p, dict) and 'x' in p and 'y' in p: x, y = float(p['x']), float(p['y'])
    elif isinstance(p, (list, tuple)) and len(p) >= 2: x, y = float(p[0]), float(p[1])
    else: raise ValueError(f'Неподдерживаемый формат точки: {p!r}')
    if not math.isfinite(x) or not math.isfinite(y): raise ValueError('Координаты должны быть конечными числами.')
    return x, y

def _dimensions(plan):
    canvas = plan.get('canvas')
    if isinstance(canvas, dict) and 'width' in canvas and 'height' in canvas:
        return int(canvas['width']), int(canvas['height'])
    return int(plan.get('width', 1)), int(plan.get('height', 1))

def get_strokes(plan):
    strokes = plan.get('strokes')
    if not isinstance(strokes, list): raise ValueError("В JSON не найден массив 'strokes'.")
    for i, s in enumerate(strokes):
        if not isinstance(s, dict) or not isinstance(s.get('points'), list): raise ValueError(f'Штрих №{i+1} должен содержать массив points.')
        for p in s['points']: _xy(p)
    return strokes

def _length(stroke):
    pts = [_xy(p) for p in stroke['points']]
    return sum(math.hypot(b[0]-a[0], b[1]-a[1]) for a,b in zip(pts, pts[1:]))

def analyze_plan(plan, profile=TimingProfile()):
    strokes = get_strokes(plan); point_count = 0; draw_len = 0.0; pen_up = 0.0; bins = [0,0,0,0]; prev = None; calls = 0
    for s in strokes:
        pts = [_xy(p) for p in s['points']]; point_count += len(pts); length = _length(s); draw_len += length
        bins[0 if length <= 2 else 1 if length <= 5 else 2 if length <= 10 else 3] += 1
        if pts:
            if prev is not None:
                d = math.hypot(pts[0][0]-prev[0], pts[0][1]-prev[1]); pen_up += d
                calls += math.ceil(d / max(profile.point_step_px, .1))
            for a,b in zip(pts, pts[1:]): calls += max(1, math.ceil(math.hypot(b[0]-a[0], b[1]-a[1]) / max(profile.point_step_px, .1)))
            prev = pts[-1]
    overhead = profile.before_mouse_down_ms + profile.after_mouse_down_ms + profile.before_mouse_up_ms + profile.after_mouse_up_ms
    seconds = (calls*profile.point_delay_ms + len(strokes)*overhead)/1000
    return PlanMetrics(len(strokes), point_count, draw_len, pen_up, *bins, seconds)

def load_mask(path):
    try:
        with Image.open(path) as opened: image = ImageOps.exif_transpose(opened).convert('L')
    except (OSError, ValueError) as exc: raise ValueError(f'Не удалось открыть маску: {exc}') from exc
    if image.width*image.height > 40_000_000: raise ValueError('Маска больше лимита 40 млн пикселей.')
    return image

def build_scanline_plan(mask, row_step_px=1, threshold=127, foreground='dark', max_strokes=250_000):
    if row_step_px < 1: raise ValueError('Шаг строк должен быть не меньше 1.')
    if not 0 <= threshold <= 255: raise ValueError('Порог должен быть в диапазоне 0–255.')
    if foreground not in ('dark','light'): raise ValueError("foreground должен быть 'dark' или 'light'.")
    gray=mask.convert('L'); w,h=gray.size; px=gray.load(); strokes=[]; total=0; scanned=0; runs=0; singles=0
    def fg(x,y): return px[x,y] <= threshold if foreground == 'dark' else px[x,y] >= threshold
    for y in range(h): total += sum(1 for x in range(w) if fg(x,y))
    for y in range(0,h,row_step_px):
        row=[fg(x,y) for x in range(w)]; scanned += sum(row); x=0
        while x<w:
            if not row[x]: x+=1; continue
            start=x
            while x+1<w and row[x+1]: x+=1
            end=x; runs+=1
            if start==end:
                singles+=1
                if end < w-1: points=[{'x':float(start),'y':float(y)},{'x':float(start+1),'y':float(y)}]
                elif start>0: points=[{'x':float(start),'y':float(y)},{'x':float(start-1),'y':float(y)}]
                elif h > 1 and y < h - 1: points=[{'x':float(start),'y':float(y)},{'x':float(start),'y':float(y+1)}]
                elif h > 1 and y > 0: points=[{'x':float(start),'y':float(y)},{'x':float(start),'y':float(y-1)}]
                else: points=[{'x':float(start),'y':float(y)},{'x':float(start),'y':float(y)}]
            else: points=[{'x':float(start),'y':float(y)},{'x':float(end),'y':float(y)}]
            strokes.append({'name':f'scanline_y{y}_x{start}-{end}','points':points,'closed':False,'metadata':{'row_y':str(y),'x_start':str(start),'x_end':str(end)}})
            if len(strokes)>max_strokes: raise ValueError(f'План превысил лимит {max_strokes:,} штрихов. Увеличьте шаг строк или уменьшите изображение.')
            x+=1
    from datetime import datetime, timezone
    name = f'Stage 8 scanline plan (step {row_step_px})'
    plan = {
        'schema_version': 1,
        'name': name,
        'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'coordinate_system': 'local_canvas_pixels',
        'canvas': {'width': w, 'height': h},
        # Retain aliases for Stage 8 preview/metrics; Stage 6 reads canvas.width/height.
        'width': w, 'height': h,
        'strokes': strokes,
        'generation': {'method':'raster_scanline','row_step_px':row_step_px,'threshold':threshold,'foreground':foreground,'foreground_pixels_total':total,'foreground_pixels_scanned':scanned,'raw_runs_found':runs,'strokes_created':len(strokes),'single_pixel_runs':singles,'note':'Raster order preserved; no merging or short-stroke removal.'}
    }
    metrics = analyze_plan(plan)
    plan['summary'] = {'stroke_count': metrics.stroke_count, 'drawing_length_px': round(metrics.drawing_length_px, 2), 'pen_up_distance_px': round(metrics.pen_up_distance_px, 2)}
    return plan

def render_plan_preview(plan, scale_limit=1000):
    width, height = _dimensions(plan)
    w=max(1,width); h=max(1,height); scale=min(1.0,scale_limit/max(w,h)); ow=max(1,round(w*scale)); oh=max(1,round(h*scale))
    image=Image.new('RGB',(ow,oh),'white'); d=ImageDraw.Draw(image)
    for s in get_strokes(plan):
        pts=[(round(x*scale),round(y*scale)) for x,y in map(_xy,s['points'])]
        if len(pts)>=2:
            d.line(pts,fill=(205,30,145),width=1); x,y=pts[0]; d.ellipse((x-1,y-1,x+1,y+1),fill=(30,130,80))
    return image

def save_plan(path, plan):
    # Normalize every saved plan to the schema expected by Stage 6 DrawingPlan.from_dict.
    width, height = _dimensions(plan)
    from datetime import datetime, timezone
    compatible = dict(plan)
    compatible['schema_version'] = int(compatible.get('schema_version', 1))
    compatible['name'] = str(compatible.get('name', 'Stage 8 drawing plan'))
    compatible['created_at'] = str(compatible.get('created_at') or datetime.now(timezone.utc).isoformat(timespec='seconds'))
    compatible['coordinate_system'] = 'local_canvas_pixels'
    compatible['canvas'] = {'width': width, 'height': height}
    compatible['width'], compatible['height'] = width, height
    compatible['strokes'] = get_strokes(compatible)
    metrics = analyze_plan(compatible)
    compatible['summary'] = {'stroke_count': metrics.stroke_count, 'drawing_length_px': round(metrics.drawing_length_px, 2), 'pen_up_distance_px': round(metrics.pen_up_distance_px, 2)}
    Path(path).write_text(json.dumps(compatible,ensure_ascii=False,indent=2),encoding='utf-8')
