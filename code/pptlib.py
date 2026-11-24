"""Small helpers for the slide decks."""
from pptx import Presentation
from pptx.util import Inches as I, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.chart.data import XyChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_MARKER_STYLE
from pptx.enum.dml import MSO_LINE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from lxml import etree
from PIL import Image
def C(h): return RGBColor.from_string(h)
DK, TEAL, INK, TINT, WHITE, AC, MUTE = "0F2F38", "0E7C86", "222B30", "E6F1F2", "FFFFFF", "B8480A", "5E6B73"
FIG = "../results/figures/"
BLUE, ORG, GRN = "1F6FB4", "C2540A", "2A8C45"
LIGHT = {BLUE: "A9CBEA", ORG: "F2C29C", GRN: "AEDDB9"}
NC = {1.33: BLUE, 1.354: ORG, 1.366: GRN}
MK = {1.33: XL_MARKER_STYLE.SQUARE, 1.354: XL_MARKER_STYLE.TRIANGLE, 1.366: XL_MARKER_STYLE.CIRCLE}

class Deck:
    def __init__(self, title):
        self.P = Presentation(); self.P.slide_width, self.P.slide_height = I(13.333), I(7.5)
        self.P.core_properties.title = title; self.P.core_properties.author = "Rishit Bajaj"
        self.lay = self.P.slide_layouts[5]
        for ph in list(self.lay.placeholders):
            if ph.placeholder_format.type == 1 or ph.placeholder_format.idx == 0:
                ph.left, ph.top, ph.width, ph.height = I(.6), I(.4), I(12.13), I(.95)
        self.n = 0
    def slide(self, title, notes="", size=30):
        s = self.P.slides.add_slide(self.lay); t = s.shapes.title; tf = t.text_frame; tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE; tf.margin_left = tf.margin_right = 0
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT; self.run(p, title, size, DK, True)
        self.n += 1; self.text(s, 12.0, 7.0, .75, .3, str(self.n + 1), 10, MUTE, align=PP_ALIGN.RIGHT)
        if notes: s.notes_slide.notes_text_frame.text = notes
        return s
    def dark(self, title, sub, notes="", size=40):
        s = self.P.slides.add_slide(self.lay); s.background.fill.solid(); s.background.fill.fore_color.rgb = C(DK)
        t = s.shapes.title; t.left, t.top, t.width, t.height = I(.9), I(1.5), I(11.5), I(2.3); t.text_frame.word_wrap = True
        t.text_frame.vertical_anchor = MSO_ANCHOR.BOTTOM; t.text_frame.margin_left = 0
        p = t.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.LEFT; self.run(p, title, size, WHITE, True)
        self.text(s, .9, 4.1, 11.5, 2.8, sub, 20, "CFE6E8", gap=10)
        if notes: s.notes_slide.notes_text_frame.text = notes
        return s
    @staticmethod
    def run(p, t, size, color, bold=False):
        for j, part in enumerate(t.split("**")):
            if not part: continue
            r = p.add_run(); r.text = part; f = r.font; f.size, f.name, f.bold, f.color.rgb = Pt(size), "Arial", bold or j % 2 == 1, C(color)
    def text(self, s, x, y, w, h, items, size=16, color=INK, bold=False, gap=7, align=None, bullet=False):
        b = s.shapes.add_textbox(I(x), I(y), I(w), I(h)); tf = b.text_frame; tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        for i, t in enumerate(items if isinstance(items, list) else [items]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.space_after = Pt(gap)
            if align is not None: p.alignment = align
            if bullet:
                pr = p._p.get_or_add_pPr(); pr.set("marL", "228600"); pr.set("indent", "-228600")
                e = etree.SubElement(pr, qn("a:buChar")); e.set("char", "•")
            self.run(p, t, size, color, bold)
        return b
    def card(self, s, x, y, w, h, head, body, hs=22, bs=14, fill=TINT, hc=TEAL, bc=INK):
        b = s.shapes.add_shape(5, I(x), I(y), I(w), I(h)); b.fill.solid(); b.fill.fore_color.rgb = C(fill); b.line.fill.background(); b.adjustments[0] = .05; b.shadow.inherit = False
        tf = b.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.TOP
        tf.margin_left = tf.margin_right = I(.18); tf.margin_top = tf.margin_bottom = I(.13)
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT; p.space_after = Pt(5); self.run(p, head, hs, hc, True)
        for t in (body if isinstance(body, list) else [body]):
            if not t: continue
            p = tf.add_paragraph(); p.alignment = PP_ALIGN.LEFT; p.space_after = Pt(4); self.run(p, t, bs, bc)
    def pic(self, s, f, x, y, w, h, alt=""):
        iw, ih = Image.open(FIG + f).size; k = min(w/iw, h/ih)
        p = s.shapes.add_picture(FIG + f, I(x + (w-iw*k)/2), I(y + (h-ih*k)/2), I(iw*k), I(ih*k))
        p._element.nvPicPr.cNvPr.set("descr", alt or f)
    def table(self, s, rows, x, y, widths, size=14, rh=.42):
        g = s.shapes.add_table(len(rows), len(rows[0]), I(x), I(y), I(sum(widths)), I(rh*len(rows))); t = g.table
        for j, v in enumerate(widths): t.columns[j].width = I(v)
        for i, r in enumerate(rows):
            t.rows[i].height = I(rh)
            for j, v in enumerate(r):
                c = t.cell(i, j); c.fill.solid(); c.fill.fore_color.rgb = C(DK if i == 0 else (TINT if i % 2 else WHITE)); c.vertical_anchor = MSO_ANCHOR.MIDDLE
                c.margin_top = c.margin_bottom = I(.04)
                self.run(c.text_frame.paragraphs[0], str(v), size, WHITE if i == 0 else INK, i == 0)
    def chart(self, s, x, y, w, h, series, xt, yt, xr, yr, log=False, xu=None, yu=None, fmt="General", legend=True, xfmt="0.0"):
        """series: (name, xs, ys, color, dashed, marker or None)."""
        cd = XyChartData()
        for nm, xs, ys, *_ in series:
            q = cd.add_series(nm)
            for a, b in zip(xs, ys): q.add_data_point(float(a), float(b))
        ch = s.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_LINES_NO_MARKERS, I(x), I(y), I(w), I(h), cd).chart
        ch.has_title = False; ch.font.size = Pt(12); ch.font.name = "Arial"; ch.font.color.rgb = C(INK)
        for q, (nm, xs, ys, col, dash, mk) in zip(ch.plots[0].series, series):
            q.smooth = False
            if mk is None:
                q.format.line.color.rgb = C(col); q.format.line.width = Pt(2.25); q.marker.style = XL_MARKER_STYLE.NONE
                if dash: q.format.line.dash_style = MSO_LINE.DASH
            else:
                q.format.line.fill.background(); q.marker.style = mk; q.marker.size = 8
                q.marker.format.fill.solid(); q.marker.format.fill.fore_color.rgb = C(LIGHT[col] if dash else col); q.marker.format.line.color.rgb = C(col)
        for ax, t, (lo, hi), u, f in ((ch.category_axis, xt, xr, xu, xfmt), (ch.value_axis, yt, yr, yu, fmt)):
            ax.has_title = True; p = ax.axis_title.text_frame.paragraphs[0]; self.run(p, t, 12, INK, False)
            ax.minimum_scale, ax.maximum_scale = lo, hi
            if u: ax.major_unit = u
            ax.has_major_gridlines = ax is ch.value_axis
            ax.tick_labels.number_format = f; ax.tick_labels.number_format_is_linked = False; ax.tick_labels.font.size = Pt(12)
            ax.format.line.color.rgb = C("9AA5B1")
        ch.value_axis.major_gridlines.format.line.color.rgb = C("E1E6EA")
        if log:
            sc = ch.value_axis._element.find(qn("c:scaling")); e = etree.Element(qn("c:logBase")); e.set("val", "10"); sc.insert(0, e)
            from pptx.enum.chart import XL_TICK_LABEL_POSITION
            ch.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW
            cr = ch.category_axis._element.find(qn("c:crosses"))
            va = ch.category_axis._element
            for el in va.findall(qn("c:crosses")): va.remove(el)
            e = etree.Element(qn("c:crossesAt")); e.set("val", repr(lo))
            va.find(qn("c:crossAx")).addnext(e)
        ch.has_legend = legend
        if legend:
            ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False; ch.legend.font.size = Pt(12)
            pos = ch.legend._element.find(qn("c:legendPos"))
            for i in reversed([i for i, q in enumerate(series) if q[5] is not None]):
                e = etree.Element(qn("c:legendEntry")); a = etree.SubElement(e, qn("c:idx")); a.set("val", str(i)); b = etree.SubElement(e, qn("c:delete")); b.set("val", "1"); pos.addnext(e)
        return ch
    def save(self, f): self.P.save(f)
