from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
def style(raw, out):
    d = Document(raw)
    for s in d.sections:
        s.page_width, s.page_height = Cm(21), Cm(29.7)
        s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.2)
        s.header_distance = s.footer_distance = Cm(1.2); s.gutter = Cm(0)
        p = s.footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER; r = p.add_run()
        for t, x in (("begin", None), (None, "PAGE"), ("end", None)):
            e = OxmlElement("w:fldChar" if t else "w:instrText")
            if t: e.set(qn("w:fldCharType"), t)
            else: e.text = x
            r._r.append(e)
    sizes = {"normal": 11, "body text": 11, "first paragraph": 11, "compact": 11, "heading 1": 17, "heading 2": 13, "heading 3": 11.5, "title": 22, "subtitle": 13, "author": 12, "image caption": 9.5, "source code": 9}
    for st in d.styles:
        if st.type != 1: continue
        rp = st.element.get_or_add_rPr(); f = rp.find(qn("w:rFonts"))
        if f is not None: rp.remove(f)
        st.font.name = "Consolas" if "ource" in st.name else "Calibri"; rp.rFonts.set(qn("w:eastAsia"), "Calibri")
        if st.name.lower() in sizes: st.font.size = Pt(sizes[st.name.lower()])
        if st.name.lower().startswith(("heading", "title", "subtitle")): st.font.color.rgb = RGBColor(0x0F, 0x2F, 0x38)
        if st.name.lower().startswith("heading"): st.paragraph_format.keep_with_next = True
    for t in d.tables:
        b = OxmlElement("w:tblBorders")
        for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
            x = OxmlElement("w:" + e); x.set(qn("w:val"), "single"); x.set(qn("w:sz"), "4"); x.set(qn("w:space"), "0"); x.set(qn("w:color"), "9AA5B1"); b.append(x)
        pr = t._tbl.tblPr; an = next((pr.find(qn("w:"+k)) for k in ("shd", "tblLayout", "tblCellMar", "tblLook") if pr.find(qn("w:"+k)) is not None), None)
        an.addprevious(b) if an is not None else pr.append(b)
        for i, row in enumerate(t.rows):
            c = row._tr.get_or_add_trPr()
            if c.find(qn("w:cantSplit")) is None: c.insert(0, OxmlElement("w:cantSplit"))
            for cell in row.cells:
                if i == 0:
                    sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), "E6F1F2"); cell._tc.get_or_add_tcPr().append(sh)
                for p in cell.paragraphs:
                    p.paragraph_format.space_after = p.paragraph_format.space_before = Pt(1.5)
                    for r in p.runs:
                        r.font.size = Pt(9.5)
                        if i == 0: r.bold = True
    for p in d.paragraphs:
        if p._p.findall(".//" + qn("w:drawing")): p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next = True
        if p.style.name == "Image Caption": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        tx = p.text
        if p.runs and p.runs[0].bold and tx.split(".")[0].isdigit() and all(r.bold for r in p.runs if r.text.strip()): p.paragraph_format.keep_with_next = True
        if p.style.name.lower() == "heading 1" and tx.startswith(("Part 12", "Part 13", "Part 14", "Part 7.")): p.paragraph_format.page_break_before = True
    d.save(out)
