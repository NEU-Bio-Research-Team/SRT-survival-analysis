# -*- coding: utf-8 -*-
"""Build the WITS data-walkthrough deck on top of the user's Slides_template.pptx."""
import copy, os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image

TPL = "deck/assets/Slides_template.pptx"
NAVY   = RGBColor(0x0E, 0x28, 0x41)
TEXT   = RGBColor(0x00, 0x20, 0x60)
TEAL   = RGBColor(0x15, 0x60, 0x82)
ORANGE = RGBColor(0xE9, 0x71, 0x32)
PURPLE = RGBColor(0xA0, 0x2B, 0x93)
MUTED  = RGBColor(0x5A, 0x6B, 0x7A)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT  = RGBColor(0xEE, 0xF2, 0xF6)
BAND   = RGBColor(0xF7, 0xF9, 0xFA)
RULE   = RGBColor(0xC3, 0xCE, 0xD8)
FONT   = "Times New Roman"
SW, SH = 13.3333, 7.5

# ---------------------------------------------------------------- utilities
def clone(prs, idx):
    """Duplicate an existing slide (keeps all its chrome shapes)."""
    src = prs.slides[idx]
    dst = prs.slides.add_slide(src.slide_layout)
    for sh in list(dst.shapes):
        sh._element.getparent().remove(sh._element)
    for sh in src.shapes:
        dst.shapes._spTree.append(copy.deepcopy(sh._element))
    return dst

def reorder(prs, order):
    lst = prs.slides._sldIdLst
    ids = list(lst)
    for i in ids: lst.remove(i)
    for i in order: lst.append(ids[i])

def set_text(shape, text, size=None, bold=None, color=None, align=None):
    tf = shape.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = text
    f = r.font; f.name = FONT
    if size: f.size = Pt(size)
    if bold is not None: f.bold = bold
    f.color.rgb = color or TEXT
    if align: p.alignment = align
    return p

def title_of(slide):
    """The template's title text box is the last shape on the cloned slide."""
    return slide.shapes[4]

def set_title(slide, text):
    sz = 32 if len(text) <= 56 else (27 if len(text) <= 76 else 23)
    sh = title_of(slide)
    if len(text) > 56:                      # allow a second line without clipping
        sh.height = Inches(1.00)
    set_text(sh, text, size=sz, bold=True, color=TEXT, align=PP_ALIGN.CENTER)

def tag(slide, left_tag, author):
    sh = slide.shapes[3]
    sh.width = Inches(3.4)                      # template box fits only a short tag
    set_text(sh, left_tag, size=16, color=WHITE, align=PP_ALIGN.LEFT)
    set_text(slide.shapes[1], author, size=16, color=WHITE, align=PP_ALIGN.LEFT)

def box(slide, l, t, w, h):
    return slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))

def para(tf, text, size=16, bold=False, color=None, align=PP_ALIGN.LEFT,
         space_before=0, space_after=6, first=False, italic=False, bullet=None):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    if bullet:
        r0 = p.add_run(); r0.text = bullet + "  "
        r0.font.name = FONT; r0.font.size = Pt(size); r0.font.bold = True
        r0.font.color.rgb = TEAL
    r = p.add_run(); r.text = text
    f = r.font; f.name = FONT; f.size = Pt(size); f.bold = bold; f.italic = italic
    f.color.rgb = color or TEXT
    p.alignment = align
    p.space_before = Pt(space_before); p.space_after = Pt(space_after)
    return p

def rich(tf, chunks, size=16, align=PP_ALIGN.LEFT, first=False,
         space_before=0, space_after=6):
    """chunks = [(text, bold, color), ...]"""
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    for txt, bold, col in chunks:
        r = p.add_run(); r.text = txt
        f = r.font; f.name = FONT; f.size = Pt(size); f.bold = bold
        f.color.rgb = col or TEXT
    p.alignment = align
    p.space_before = Pt(space_before); p.space_after = Pt(space_after)
    return p

def picture(slide, path, top=1.06, bottom=6.92, max_w=12.5):
    """Center a figure inside the content area, preserving aspect ratio."""
    iw, ih = Image.open(path).size
    avail_h, avail_w = bottom - top, max_w
    w = avail_w; h = w * ih / iw
    if h > avail_h:
        h = avail_h; w = h * iw / ih
    left = (SW - w) / 2
    return slide.shapes.add_picture(path, Inches(left), Inches(top + (avail_h - h) / 2),
                                    Inches(w), Inches(h))

def note(slide, text, top=6.55, size=12.5, color=MUTED, left=0.62, width=12.1,
         align=PP_ALIGN.LEFT, italic=True):
    tb = box(slide, left, top, width, 0.55)
    tf = tb.text_frame; tf.word_wrap = True
    para(tf, text, size=size, color=color, align=align, italic=italic, first=True)
    return tb

def rule(slide, l, t, w, color=RULE, h=0.014):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = color; s.line.fill.background()
    s.shadow.inherit = False
    return s

def chip(slide, l, t, w, h, text, fill, fg=WHITE, size=11.5, bold=False, radius=True):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                 Inches(l), Inches(t), Inches(w), Inches(h))
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    shp.line.fill.background(); shp.shadow.inherit = False
    if radius:
        try: shp.adjustments[0] = 0.16
        except Exception: pass
    tf = shp.text_frame; tf.word_wrap = True
    tf.margin_left = Inches(0.08); tf.margin_right = Inches(0.08)
    tf.margin_top = Inches(0.02); tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(tf, text, size=size, bold=bold, color=fg, align=PP_ALIGN.CENTER, first=True,
         space_after=0)
    return shp

def table(slide, data, l, t, w, col_w=None, size=12.5, head_size=12.5, row_h=0.33,
          head_h=0.38, head_fill=NAVY, zebra=True, aligns=None, bold_col0=False):
    rows, cols = len(data), len(data[0])
    h = head_h + row_h * (rows - 1)
    gf = slide.shapes.add_table(rows, cols, Inches(l), Inches(t), Inches(w), Inches(h))
    tbl = gf.table
    tbl.first_row = True; tbl.horz_banding = False
    if col_w:
        tot = sum(col_w)
        for i, cw in enumerate(col_w):
            tbl.columns[i].width = Emu(int(Inches(w) * cw / tot))
    tbl.rows[0].height = Inches(head_h)
    for r in range(1, rows): tbl.rows[r].height = Inches(row_h)
    for r in range(rows):
        for c in range(cols):
            cell = tbl.cell(r, c)
            cell.margin_left = Inches(0.09); cell.margin_right = Inches(0.07)
            cell.margin_top = Inches(0.035); cell.margin_bottom = Inches(0.035)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if r == 0:
                cell.fill.fore_color.rgb = head_fill
            else:
                cell.fill.fore_color.rgb = BAND if (zebra and r % 2 == 0) else WHITE
            txt = data[r][c]
            tf = cell.text_frame; tf.clear(); tf.word_wrap = True
            al = PP_ALIGN.LEFT
            if aligns and c < len(aligns):
                al = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[aligns[c]]
            if isinstance(txt, tuple):      # (text, colour)
                txt, col = txt
            else:
                col = None
            p = tf.paragraphs[0]
            run = p.add_run(); run.text = str(txt)
            f = run.font; f.name = FONT
            f.size = Pt(head_size if r == 0 else size)
            f.bold = True if (r == 0 or (bold_col0 and c == 0)) else False
            f.color.rgb = WHITE if r == 0 else (col or TEXT)
            p.alignment = al
    return gf

def kpis(slide, items, top=1.25, h=1.18, left=0.62, width=12.1, gap=0.16, size_v=30, size_l=12):
    n = len(items)
    w = (width - gap * (n - 1)) / n
    for i, (val, lab) in enumerate(items):
        x = left + i * (w + gap)
        s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(top), Inches(w), Inches(h))
        s.fill.solid(); s.fill.fore_color.rgb = LIGHT; s.line.fill.background()
        s.shadow.inherit = False
        rule(slide, x, top, w, NAVY, 0.045)
        tf = s.text_frame; tf.word_wrap = True
        tf.margin_top = Inches(0.12); tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        para(tf, val, size=size_v, bold=True, color=NAVY, align=PP_ALIGN.CENTER,
             first=True, space_after=2)
        para(tf, lab, size=size_l, color=MUTED, align=PP_ALIGN.CENTER, space_after=0)

def section(prs, num, title, sub, tagtxt, author):
    s = clone(prs, 2)
    tag(s, tagtxt, author)
    set_text(title_of(s), "", size=32)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(2.55), Inches(SW), Inches(1.9))
    bar.fill.solid(); bar.fill.fore_color.rgb = NAVY; bar.line.fill.background()
    bar.shadow.inherit = False
    tbn = box(s, 1.1, 2.66, 11.2, 0.40)
    tfn = tbn.text_frame; tfn.word_wrap = True
    para(tfn, num, size=17, bold=True, color=RGBColor(0x7F, 0xA8, 0xC4), first=True, space_after=0)
    rule(s, 1.1, 3.06, 0.62, RGBColor(0x7F, 0xA8, 0xC4), 0.028)
    tb = box(s, 1.1, 3.14, 11.2, 0.72)
    tf = tb.text_frame; tf.word_wrap = True
    para(tf, title, size=34, bold=True, color=WHITE, first=True, space_after=0)
    tb2 = box(s, 1.1, 3.92, 11.2, 0.6)
    tf2 = tb2.text_frame; tf2.word_wrap = True
    para(tf2, sub, size=15, color=RGBColor(0xC6, 0xD5, 0xE2), first=True, space_after=0)
    return s

def card(slide, l, t, w, h, head, body, accent=TEAL, head_size=14, body_size=12.5):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = BAND
    s.line.color.rgb = RULE; s.line.width = Pt(0.75); s.shadow.inherit = False
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(0.055), Inches(h))
    bar.fill.solid(); bar.fill.fore_color.rgb = accent; bar.line.fill.background()
    bar.shadow.inherit = False
    tb = box(slide, l + 0.20, t + 0.11, w - 0.34, h - 0.20)
    tf = tb.text_frame; tf.word_wrap = True
    para(tf, head, size=head_size, bold=True, color=accent, first=True, space_after=4)
    for ln in (body if isinstance(body, list) else [body]):
        para(tf, ln, size=body_size, color=TEXT, space_after=3)
    return s
