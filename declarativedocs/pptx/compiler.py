#!/usr/bin/env python3
"""
DDF Presentation Compiler — YAML to PPTX
https://ddf.dev · https://github.com/declarativedocs/compiler-py

Part of the Declarative Document Format (DDF) project.
SPDX-License-Identifier: Apache-2.0
"""

import re, copy
import yaml
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.chart.data import CategoryChartData
from pptx.oxml.ns import qn
from lxml import etree


# ═══════════════════ CONSTANTS ═══════════════════

NSMAP_A = "http://schemas.openxmlformats.org/drawingml/2006/main"

SHADOW_PRESETS = {
    "default": dict(blur=6, offset=2, angle=135, color="000000", opacity=0.15),
    "soft":    dict(blur=8, offset=2, angle=135, color="000000", opacity=0.10),
    "hard":    dict(blur=3, offset=3, angle=135, color="000000", opacity=0.25),
    "glow":    dict(blur=10, offset=0, angle=0,  color="000000", opacity=0.10),
    "up":      dict(blur=6, offset=2, angle=270, color="000000", opacity=0.12),
}

ALIGN = {
    "left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER,
    "right": PP_ALIGN.RIGHT, "justify": PP_ALIGN.JUSTIFY,
}
VANCHOR = {"top": "t", "middle": "ctr", "bottom": "b"}

SHAPES = {
    "rectangle": MSO_SHAPE.RECTANGLE, "rect": MSO_SHAPE.RECTANGLE,
    "rounded_rectangle": MSO_SHAPE.ROUNDED_RECTANGLE, "rounded": MSO_SHAPE.ROUNDED_RECTANGLE,
    "oval": MSO_SHAPE.OVAL, "circle": MSO_SHAPE.OVAL,
}

CHARTS = {
    "bar": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "bar_horizontal": XL_CHART_TYPE.BAR_CLUSTERED,
    "line": XL_CHART_TYPE.LINE,
    "pie": XL_CHART_TYPE.PIE,
    "doughnut": XL_CHART_TYPE.DOUGHNUT,
    "scatter": XL_CHART_TYPE.XY_SCATTER,
    "radar": XL_CHART_TYPE.RADAR,
}

LAYOUT_SIZES = {
    "16x9": (10, 5.625), "16x10": (10, 6.25),
    "4x3": (10, 7.5), "wide": (13.3, 7.5),
}

LEGEND_POS = {
    "b": XL_LEGEND_POSITION.BOTTOM, "t": XL_LEGEND_POSITION.TOP,
    "l": XL_LEGEND_POSITION.LEFT, "r": XL_LEGEND_POSITION.RIGHT,
}

ICON_GLYPHS = {
    "dollar": "$", "percent": "%", "hash": "#", "at": "@",
    "plus": "+", "check": "✓", "star": "★", "arrow_up": "↑",
    "arrow_right": "→", "heart": "♥", "x": "✕", "bell": "♦",
    "chart": "◆", "users": "●", "gear": "⚙", "target": "◎",
    "mail": "✉", "flag": "⚑", "lightning": "⚡", "trophy": "◆",
    "shield": "■", "rocket": "▲", "globe": "◉", "lock": "▣",
    "book": "▪", "tools": "⚒", "briefcase": "■", "search": "◎",
}


# ═══════════════════ HELPERS ═══════════════════

def color(val):
    return RGBColor.from_string(str(val).lstrip("#"))


def set_body_anchor(txBox, anchor):
    """Set vertical alignment on a text box (top/middle/bottom)."""
    bp = txBox._element.txBody.find(qn("a:bodyPr"))
    if bp is not None:
        bp.set("anchor", VANCHOR.get(anchor, "t"))


def apply_font(run, opts):
    f = run.font
    if opts.get("size"):   f.size = Pt(opts["size"])
    if opts.get("font"):   f.name = opts["font"]
    if opts.get("color"):  f.color.rgb = color(opts["color"])
    if opts.get("bold") is not None:  f.bold = opts["bold"]
    if opts.get("italic") is not None: f.italic = opts["italic"]
    if opts.get("underline") is not None: f.underline = opts["underline"]


def apply_shadow(shape, shadow):
    if not shadow:
        return
    opts = dict(SHADOW_PRESETS[shadow]) if isinstance(shadow, str) and shadow in SHADOW_PRESETS else (
        dict(shadow) if isinstance(shadow, dict) else None
    )
    if not opts:
        return
    spPr = shape._element.spPr
    for el in spPr.findall(qn("a:effectLst")):
        spPr.remove(el)
    xml = (
        f'<a:effectLst xmlns:a="{NSMAP_A}">'
        f'<a:outerShdw blurRad="{int(opts.get("blur",6)*12700)}" '
        f'dist="{int(opts.get("offset",2)*12700)}" '
        f'dir="{int(opts.get("angle",135)*60000)}" algn="bl" rotWithShape="0">'
        f'<a:srgbClr val="{opts.get("color","000000")}">'
        f'<a:alpha val="{int(opts.get("opacity",0.15)*100000)}"/>'
        f'</a:srgbClr></a:outerShdw></a:effectLst>'
    )
    spPr.append(etree.fromstring(xml))


def set_corner_radius(shape, radius, w, h):
    if not radius or min(w, h) <= 0:
        return
    try:
        shape.adjustments[0] = (radius / min(w, h)) * 0.5
    except Exception:
        pass


def set_bullet(paragraph):
    """Enable bullet character on a paragraph via XML."""
    pPr = paragraph._element.get_or_add_pPr()
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
        for old in pPr.findall(qn(tag)):
            pPr.remove(old)
    # Indent: marL = left margin, indent = hanging indent (negative)
    pPr.set("marL", str(int(Inches(0.3))))      # left margin
    pPr.set("indent", str(int(-Inches(0.15))))   # hanging indent
    bu = etree.SubElement(pPr, qn("a:buChar"))
    bu.set("char", "\u2022")


# ═══════════════════ THEME ═══════════════════

def build_theme_map(theme):
    if not theme:
        return {}
    flat = {}
    for entries in theme.values():
        if isinstance(entries, dict):
            flat.update(entries)
    for _ in range(5):
        changed = False
        for k, v in list(flat.items()):
            if isinstance(v, str) and re.match(r"^\$[a-zA-Z_]\w*$", v):
                ref = flat.get(v[1:])
                if ref and not (isinstance(ref, str) and ref.startswith("$")):
                    flat[k] = ref; changed = True
        if not changed:
            break
    return flat


def resolve(val, tmap):
    if isinstance(val, str):
        return tmap.get(val[1:], val) if re.match(r"^\$[a-zA-Z_]\w*$", val) else val
    if isinstance(val, list):
        return [resolve(v, tmap) for v in val]
    if isinstance(val, dict):
        return {k: resolve(v, tmap) for k, v in val.items()}
    return val


# ═══════════════════ LAYOUT CALC ═══════════════════

def calc_positions(layout, x, y, w, h, count, columns=3, gap=0.25):
    if count == 0:
        return []
    if layout == "grid":
        cols = columns
        rows = -(-count // cols)
        iw = (w - gap * (cols - 1)) / cols
        ih = (h - gap * (rows - 1)) / rows
        return [dict(x=x + (i % cols) * (iw + gap),
                     y=y + (i // cols) * (ih + gap), w=iw, h=ih)
                for i in range(count)]
    # row
    iw = (w - gap * (count - 1)) / count
    return [dict(x=x + i * (iw + gap), y=y, w=iw, h=h) for i in range(count)]


# ═══════════════════ ELEMENT RENDERERS ═══════════════════

def render_text(slide, el):
    x, y, w, h = el.get("x", 0), el.get("y", 0), el.get("w", 5), el.get("h", 1)
    txBox = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = txBox.text_frame
    tf.word_wrap = True
    set_body_anchor(txBox, el.get("valign", "top"))

    # Margin
    m = el.get("margin")
    if m is not None:
        m_emu = Pt(m) if isinstance(m, (int, float)) else 0
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = m_emu

    base_align = ALIGN.get(el.get("align"), None)

    if el.get("runs"):
        for i, rd in enumerate(el["runs"]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            if base_align: p.alignment = base_align
            p.space_after = Pt(rd.get("spaceAfter", 0))
            p.space_before = Pt(0)
            r = p.add_run()
            r.text = str(rd.get("text", ""))
            # Inherit element-level font, then override with run-level
            merged = {k: el[k] for k in ("size", "font", "color", "bold", "italic") if k in el}
            merged.update({k: rd[k] for k in ("size", "font", "color", "bold", "italic") if k in rd})
            apply_font(r, merged)

    elif el.get("bullets"):
        space = el.get("spaceAfter", 4)
        for i, b in enumerate(el["bullets"]):
            is_str = isinstance(b, str)
            text = b if is_str else b.get("text", "")
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            if base_align: p.alignment = base_align
            p.space_after = Pt(b.get("spaceAfter", space) if not is_str else space)
            p.space_before = Pt(0)
            set_bullet(p)
            r = p.add_run()
            r.text = str(text)
            # Inherit from element, override from bullet item
            merged = {k: el[k] for k in ("size", "font", "color", "bold") if k in el}
            if not is_str:
                merged.update({k: b[k] for k in ("size", "font", "color", "bold") if k in b})
            apply_font(r, merged)

    else:
        p = tf.paragraphs[0]
        if base_align: p.alignment = base_align
        r = p.add_run()
        r.text = str(el.get("text", ""))
        apply_font(r, {k: el[k] for k in ("size", "font", "color", "bold", "italic", "underline") if k in el})


def render_shape(slide, el):
    x, y, w, h = el.get("x", 0), el.get("y", 0), el.get("w", 1), el.get("h", 1)
    name = el.get("shape", "rectangle")

    # Lines → thin filled rectangle
    if name in ("line", "LINE"):
        lo = el.get("line", {})
        lw = lo.get("width", 2)
        lc = lo.get("color", "000000")
        sh = Pt(lw) if h < 0.001 else Inches(h)
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), sh)
        shape.fill.solid(); shape.fill.fore_color.rgb = color(lc)
        shape.line.fill.background()
        return shape

    mso = SHAPES.get(name, MSO_SHAPE.RECTANGLE)
    shape = slide.shapes.add_shape(mso, Inches(x), Inches(y), Inches(w), Inches(h))

    if el.get("fill"):
        shape.fill.solid(); shape.fill.fore_color.rgb = color(el["fill"])
    else:
        shape.fill.background()

    lo = el.get("line")
    if lo:
        shape.line.color.rgb = color(lo.get("color", "000000"))
        shape.line.width = Pt(lo.get("width", 1))
    else:
        shape.line.fill.background()

    if el.get("radius") and name in ("rounded_rectangle", "rounded"):
        set_corner_radius(shape, el["radius"], w, h)

    apply_shadow(shape, el.get("shadow"))
    return shape


def render_image(slide, el):
    x, y, w, h = el.get("x", 0), el.get("y", 0), el.get("w", 3), el.get("h", 2)
    path = el.get("path")
    if path:
        return slide.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))


def render_chart(slide, el):
    x, y, w, h = el.get("x", 0), el.get("y", 0), el.get("w", 6), el.get("h", 4)
    chart_name = el.get("chart", "bar")

    if chart_name == "bar" and el.get("direction") == "bar":
        ct = XL_CHART_TYPE.BAR_CLUSTERED
    else:
        ct = CHARTS.get(chart_name, XL_CHART_TYPE.COLUMN_CLUSTERED)

    series_list = el.get("series", [])
    cd = CategoryChartData()
    if series_list:
        cd.categories = series_list[0].get("labels", [])
        for s in series_list:
            cd.add_series(s.get("name", ""), s.get("values", []))

    frame = slide.shapes.add_chart(ct, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    chart = frame.chart
    style = el.get("style", {})

    # Title
    if el.get("chartTitle"):
        chart.has_title = True
        chart.chart_title.text_frame.paragraphs[0].text = el["chartTitle"]
        chart.chart_title.text_frame.paragraphs[0].font.size = Pt(14)
    else:
        chart.has_title = False

    # Colors
    colors_list = el.get("colors", [])
    if colors_list:
        plot = chart.plots[0]
        if chart_name in ("pie", "doughnut"):
            ser = plot.series[0]
            vals = series_list[0].get("values", [])
            for i in range(min(len(colors_list), len(vals))):
                try:
                    pt = ser.points[i]
                    pt.format.fill.solid()
                    pt.format.fill.fore_color.rgb = color(colors_list[i])
                except Exception:
                    pass
        else:
            for i, ser in enumerate(plot.series):
                if i < len(colors_list):
                    ser.format.fill.solid()
                    ser.format.fill.fore_color.rgb = color(colors_list[i])

    # Legend
    if style.get("legend") is not None:
        chart.has_legend = bool(style["legend"])
        if chart.has_legend:
            chart.legend.include_in_layout = False
            lp = style.get("legendPos")
            if lp in LEGEND_POS:
                chart.legend.position = LEGEND_POS[lp]
            if style.get("legendSize"):
                chart.legend.font.size = Pt(style["legendSize"])

    # Data labels
    if style.get("dataLabels") or style.get("showPercent"):
        plot = chart.plots[0]
        plot.has_data_labels = True
        dl = plot.data_labels
        if style.get("showPercent"):
            dl.show_percentage = True; dl.show_value = False
        else:
            dl.show_value = True
        dl.font.size = Pt(10)

    return frame


def render_table(slide, el):
    x, y, w, h = el.get("x", 0), el.get("y", 0), el.get("w", 8), el.get("h", 3)
    rows_data = el.get("rows", [])
    if not rows_data:
        return
    nr = len(rows_data)
    nc = max(len(r) for r in rows_data)

    tshape = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(h))
    tbl = tshape.table

    cw = el.get("colWidths")
    if cw:
        for i, v in enumerate(cw):
            if i < nc: tbl.columns[i].width = Inches(v)

    for r, row in enumerate(rows_data):
        for c, cd_item in enumerate(row):
            if c >= nc: break
            cell = tbl.cell(r, c)
            if isinstance(cd_item, (str, int, float)):
                cell.text = str(cd_item)
                p = cell.text_frame.paragraphs[0]
                if el.get("size"): p.font.size = Pt(el["size"])
                if el.get("font"): p.font.name = el["font"]
            elif isinstance(cd_item, dict):
                cell.text = str(cd_item.get("text", ""))
                p = cell.text_frame.paragraphs[0]
                if cd_item.get("bold"):  p.font.bold = True
                if cd_item.get("color"): p.font.color.rgb = color(cd_item["color"])
                sz = cd_item.get("size") or el.get("size")
                if sz: p.font.size = Pt(sz)
                fn = cd_item.get("font") or el.get("font")
                if fn: p.font.name = fn
                if cd_item.get("fill"):
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = color(cd_item["fill"])
                if cd_item.get("align"):
                    p.alignment = ALIGN.get(cd_item["align"])


def render_icon(slide, el):
    """Render a colored circle with a centered glyph/letter."""
    x, y = el.get("x", 0), el.get("y", 0)
    size = el.get("size", 0.5)
    bg_color = el.get("bg", "1E2761")
    fg_color = el.get("color", "FFFFFF")
    name = str(el.get("icon", "?"))
    glyph = ICON_GLYPHS.get(name, name)  # lookup or use raw char/text
    if len(glyph) > 2:
        glyph = glyph[0]

    # Circle background
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(size), Inches(size))
    shape.fill.solid(); shape.fill.fore_color.rgb = color(bg_color)
    shape.line.fill.background()

    # Centered glyph
    txBox = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(size), Inches(size))
    tf = txBox.text_frame; tf.word_wrap = False
    set_body_anchor(txBox, "middle")
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = glyph
    r.font.size = Pt(max(8, int(size * 26)))
    r.font.color.rgb = color(fg_color)
    r.font.bold = True


def render_group(slide, el):
    x, y, w, h = el.get("x", 0), el.get("y", 0), el.get("w", 9), el.get("h", 3)
    gap = el.get("gap", 0.25)
    items = el.get("items", [])
    card = el.get("card", {})
    positions = calc_positions(el.get("layout", "row"), x, y, w, h,
                               len(items), el.get("columns", 3), gap)

    for i, item in enumerate(items):
        p = positions[i]
        px, py, pw, ph = p["x"], p["y"], p["w"], p["h"]

        # Card background shape
        if card.get("fill") or card.get("shadow") or card.get("border"):
            mso = MSO_SHAPE.ROUNDED_RECTANGLE if card.get("radius") else MSO_SHAPE.RECTANGLE
            sh = slide.shapes.add_shape(mso, Inches(px), Inches(py), Inches(pw), Inches(ph))
            if card.get("fill"):
                sh.fill.solid(); sh.fill.fore_color.rgb = color(card["fill"])
            else:
                sh.fill.background()
            if card.get("border"):
                sh.line.color.rgb = color(card["border"]); sh.line.width = Pt(1)
            else:
                sh.line.fill.background()
            if card.get("radius"):
                set_corner_radius(sh, card["radius"], pw, ph)
            apply_shadow(sh, card.get("shadow"))

        # Content
        icon_cfg = item.get("icon") if isinstance(item, dict) else None
        icon_offset = 0  # vertical offset for text when icon present

        if icon_cfg:
            ic = icon_cfg if isinstance(icon_cfg, dict) else {"icon": icon_cfg}
            ic_size = ic.get("size", min(0.45, ph * 0.28))
            ic_x = px + (pw - ic_size) / 2
            ic_y = py + ph * 0.1
            render_icon(slide, {
                "type": "icon", "x": ic_x, "y": ic_y, "size": ic_size,
                "icon": ic.get("icon", ic.get("name", ic.get("text", "?"))),
                "bg": ic.get("bg", "1E2761"), "color": ic.get("color", "FFFFFF"),
            })
            icon_offset = ic_size + ph * 0.05

        if item.get("runs"):
            ty = py + icon_offset
            th = ph - icon_offset
            txBox = slide.shapes.add_textbox(Inches(px), Inches(ty), Inches(pw), Inches(th))
            tf = txBox.text_frame; tf.word_wrap = True
            tf.margin_left = tf.margin_right = Pt(4)
            tf.margin_top = tf.margin_bottom = Pt(0)
            va = "top" if icon_cfg else item.get("valign", "middle")
            set_body_anchor(txBox, va)
            al = ALIGN.get(item.get("align", "center"), PP_ALIGN.CENTER)
            for j, rd in enumerate(item["runs"]):
                p_obj = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                p_obj.alignment = al
                p_obj.space_after = Pt(rd.get("spaceAfter", 2))
                p_obj.space_before = Pt(0)
                r = p_obj.add_run()
                r.text = str(rd.get("text", ""))
                apply_font(r, rd)

        elif item.get("elements"):
            for sub in item["elements"]:
                ae = dict(sub)
                ae["x"] = px + sub.get("x", 0)
                ae["y"] = py + sub.get("y", 0)
                if "w" not in ae: ae["w"] = pw - sub.get("x", 0) * 2
                if "h" not in ae: ae["h"] = ph - sub.get("y", 0) * 2
                render_element(slide, ae)

        elif item.get("text") or isinstance(item, str):
            txt = item if isinstance(item, str) else item.get("text", "")
            txBox = slide.shapes.add_textbox(Inches(px), Inches(py), Inches(pw), Inches(ph))
            tf = txBox.text_frame; tf.word_wrap = True
            set_body_anchor(txBox, "middle")
            p_obj = tf.paragraphs[0]
            p_obj.alignment = PP_ALIGN.CENTER
            r = p_obj.add_run(); r.text = str(txt)
            if isinstance(item, dict):
                apply_font(r, item)


def render_element(slide, el):
    t = el.get("type")
    renderers = {
        "text": render_text, "shape": render_shape, "image": render_image,
        "chart": render_chart, "table": render_table, "group": render_group,
        "icon": render_icon,
    }
    fn = renderers.get(t)
    if fn:
        fn(slide, el)
    else:
        print(f"Warning: unknown element type '{t}'")


# ═══════════════════ MASTERS ═══════════════════

def instantiate_master(master_def, data):
    elements = copy.deepcopy(master_def.get("elements", []))
    data = data or {}
    def repl(obj):
        if isinstance(obj, str):
            return re.sub(r"\{\{(\w+)\}\}", lambda m: str(data.get(m.group(1), m.group(0))), obj)
        if isinstance(obj, list):  return [repl(v) for v in obj]
        if isinstance(obj, dict):  return {k: repl(v) for k, v in obj.items()}
        return obj
    return repl(elements)


# ═══════════════════ COMPILER ═══════════════════

def compile_yaml(yaml_path, output_path):
    with open(yaml_path) as f:
        raw = yaml.safe_load(f)

    p = raw.get("presentation")
    if not p:
        raise ValueError('YAML must have a top-level "presentation" key')

    tmap = build_theme_map(p.get("theme"))
    spec = resolve(p, tmap)

    prs = Presentation()
    sw, sh = LAYOUT_SIZES.get(str(spec.get("layout", "16x9")), (10, 5.625))
    prs.slide_width = Inches(sw); prs.slide_height = Inches(sh)

    blank = prs.slide_layouts[6]
    masters = spec.get("masters", {})

    for sd in spec.get("slides", []):
        slide = prs.slides.add_slide(blank)

        # Background
        bg = sd.get("background")
        if not bg and sd.get("master") and sd["master"] in masters:
            bg = masters[sd["master"]].get("background")
        if bg:
            c = bg if isinstance(bg, str) else bg.get("color")
            if c:
                slide.background.fill.solid()
                slide.background.fill.fore_color.rgb = color(c)

        # Elements: master + slide-level
        elements = []
        if sd.get("master") and sd["master"] in masters:
            elements = instantiate_master(masters[sd["master"]], sd.get("data"))
        if sd.get("elements"):
            elements += sd["elements"]

        for el in elements:
            render_element(slide, el)

    prs.save(output_path)
    return output_path
