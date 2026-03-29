from flask import Flask, render_template, request, send_file, jsonify
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import Flowable

app = Flask(__name__)

# ── EMISSION FACTORS (tCO2eq / unit) ─────────────────────────────────────────
FE = {
    'Gas natural':  {'m3': 0.00200, 'GJ': 0.05610, 'MMBtu': 0.05900},
    'GLP':          {'litros': 0.00153, 'kg': 0.00214, 'tn': 2.140},
    'Gasoil':       {'litros': 0.00268, 'kg': 0.00318, 'tn': 3.180},
    'Fuel oil':     {'litros': 0.00273, 'kg': 0.00320, 'tn': 3.200},
    'Carbon':       {'kg': 0.00229, 'tn': 2.290},
    'Biomasa':      {'kg': 0.00000, 'tn': 0.00000},
    'Nafta':        {'litros': 0.00233, 'km': 0.00021},
    'GNC':          {'m3': 0.00200, 'km': 0.00012},
    'Electrico':    {'kWh': 0.00042, 'km': 0.00008},
    'kWh':  0.00042,
    'MWh':  0.42000,
    'GJ':   0.11667,
}

TRAVEL_FE = {
    'Avion corto': 0.000255,
    'Avion largo': 0.000195,
    'Tren':        0.000041,
    'Omnibus':     0.000089,
    'Auto alquiler': 0.000210,
}

COMMUTE_FE = {
    'Auto particular': 0.000210,
    'Transporte publico': 0.000041,
    'Remis / taxi': 0.000250,
    'Mixto': 0.000125,
}

def calc_tco2(combustible, unidad, cantidad):
    try:
        cantidad = float(cantidad)
        if cantidad <= 0:
            return None
    except (TypeError, ValueError):
        return None
    table = FE.get(combustible)
    if table is None:
        return None
    if isinstance(table, float):
        return cantidad * table
    fe = table.get(unidad)
    if fe is None:
        return None
    return cantidad * fe


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generar-pdf', methods=['POST'])
def generar_pdf():
    data = request.get_json()
    pdf_bytes = build_pdf(data)
    empresa = data.get('empresa', 'empresa').replace(' ', '_')
    anio = data.get('anio', '2025')
    filename = f"Informe_GRI305_{empresa}_{anio}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


# ─────────────────────────────────────────────────────────────────────────────
# PDF BUILDER
# ─────────────────────────────────────────────────────────────────────────────
class ColorRect(Flowable):
    """A simple colored rectangle background block."""
    def __init__(self, width, height, color, radius=4):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.color = color
        self.radius = radius

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=0)


def build_pdf(d):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"Inventario GEI · {d.get('empresa','—')}",
        author="Coop Agenda 20.30"
    )

    # ── COLORS ──────────────────────────────────────────────────────────────
    FOREST   = colors.HexColor('#1a3a2a')
    MOSS     = colors.HexColor('#2d5a40')
    SAGE     = colors.HexColor('#4a7c59')
    MINT     = colors.HexColor('#a8d5b5')
    CREAM    = colors.HexColor('#f5f0e8')
    SAND     = colors.HexColor('#e8dfc8')
    MUTED    = colors.HexColor('#6b7c72')
    ACCENT   = colors.HexColor('#c8a96e')
    C_S1     = colors.HexColor('#1a5276')
    C_S1L    = colors.HexColor('#d6eaf8')
    C_S2     = colors.HexColor('#186a3b')
    C_S2L    = colors.HexColor('#d5f5e3')
    C_S3     = colors.HexColor('#7d3c98')
    C_S3L    = colors.HexColor('#e8daef')
    C_GOLD   = colors.HexColor('#9a7d0a')
    C_GOLDB  = colors.HexColor('#fef9e7')
    WHITE    = colors.white
    LGRAY    = colors.HexColor('#f4f6f9')
    BORDER   = colors.HexColor('#dde3ec')

    # ── STYLES ───────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def sty(name, **kw):
        return ParagraphStyle(name, **kw)

    s_cover_title = sty('CoverTitle', fontName='Helvetica-Bold', fontSize=22,
                        textColor=WHITE, leading=28, spaceAfter=6)
    s_cover_sub   = sty('CoverSub', fontName='Helvetica', fontSize=11,
                        textColor=colors.HexColor('#c8e6d4'), leading=16)
    s_section     = sty('SecTitle', fontName='Helvetica-Bold', fontSize=13,
                        textColor=C_S1, leading=18, spaceBefore=14, spaceAfter=6)
    s_body        = sty('Body', fontName='Helvetica', fontSize=9,
                        textColor=colors.HexColor('#333333'), leading=14)
    s_body_bold   = sty('BodyBold', fontName='Helvetica-Bold', fontSize=9,
                        textColor=colors.HexColor('#1e1e1e'), leading=14)
    s_note        = sty('Note', fontName='Helvetica', fontSize=8,
                        textColor=colors.HexColor('#555555'), leading=12)
    s_label       = sty('Label', fontName='Helvetica', fontSize=7,
                        textColor=colors.HexColor('#888888'), leading=10, spaceAfter=1)
    s_val         = sty('Val', fontName='Helvetica-Bold', fontSize=10,
                        textColor=WHITE, leading=14)
    s_th          = sty('TH', fontName='Helvetica-Bold', fontSize=8,
                        textColor=WHITE, leading=10, alignment=TA_LEFT)
    s_td          = sty('TD', fontName='Helvetica', fontSize=8,
                        textColor=colors.HexColor('#333333'), leading=11)
    s_td_r        = sty('TDR', fontName='Helvetica', fontSize=8,
                        textColor=colors.HexColor('#333333'), leading=11, alignment=TA_RIGHT)
    s_gri_tag     = sty('GRITag', fontName='Helvetica-Bold', fontSize=7,
                        textColor=WHITE, leading=9, backColor=C_S1)
    s_sig_name    = sty('SigName', fontName='Helvetica-Bold', fontSize=9,
                        textColor=colors.HexColor('#1e1e1e'), leading=12)
    s_sig_sub     = sty('SigSub', fontName='Helvetica', fontSize=8,
                        textColor=MUTED, leading=11)
    s_footer      = sty('Footer', fontName='Helvetica', fontSize=7,
                        textColor=colors.HexColor('#aaaaaa'), leading=10)
    s_center      = sty('Center', fontName='Helvetica-Bold', fontSize=9,
                        textColor=colors.HexColor('#333333'), leading=12, alignment=TA_CENTER)

    story = []
    W = A4[0] - 4*cm  # usable width

    fecha = datetime.now().strftime('%d/%m/%Y')

    # =========================================================================
    # COVER BLOCK
    # =========================================================================
    def cover_table(d, fecha):
        empresa  = d.get('empresa', '—')
        cuit     = d.get('cuit', '—')
        sector   = d.get('sector', '—')
        anio     = d.get('anio', '2025')
        estandar = d.get('estandar', 'GHG Protocol')
        provincia= d.get('provincia', '—')
        pais     = d.get('pais', 'Argentina')

        title_p  = Paragraph('Inventario de Emisiones de<br/>Gases de Efecto Invernadero', s_cover_title)
        sub_p    = Paragraph('Informe conforme a GRI 305: Emisiones 2016 · GHG Protocol Corporate Standard', s_cover_sub)

        def meta_cell(label, value):
            return [Paragraph(label.upper(), sty('ml', fontName='Helvetica', fontSize=6,
                              textColor=colors.HexColor('#a8d5b5'), leading=9)),
                    Paragraph(str(value), sty('mv', fontName='Helvetica-Bold', fontSize=9,
                              textColor=WHITE, leading=12))]

        meta_data = [
            [Table([[meta_cell('Organización', empresa)]], colWidths=[W/3-0.3*cm]),
             Table([[meta_cell('CUIT', cuit)]], colWidths=[W/3-0.3*cm]),
             Table([[meta_cell('Sector', sector)]], colWidths=[W/3-0.3*cm])],
            [Table([[meta_cell('Período', anio)]], colWidths=[W/3-0.3*cm]),
             Table([[meta_cell('Estándar', estandar)]], colWidths=[W/3-0.3*cm]),
             Table([[meta_cell('Emisión', fecha)]], colWidths=[W/3-0.3*cm])],
        ]
        meta_t = Table(meta_data, colWidths=[W/3]*3)
        meta_t.setStyle(TableStyle([
            ('ALIGN', (0,0),(-1,-1),'LEFT'),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),0),
            ('RIGHTPADDING',(0,0),(-1,-1),0),
            ('TOPPADDING',(0,0),(-1,-1),6),
            ('BOTTOMPADDING',(0,0),(-1,-1),6),
        ]))

        cover_inner = [[title_p], [sub_p], [Spacer(1, 12)], [meta_t]]
        cover_t = Table(cover_inner, colWidths=[W])
        cover_t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1), FOREST),
            ('LEFTPADDING',(0,0),(-1,-1), 20),
            ('RIGHTPADDING',(0,0),(-1,-1), 20),
            ('TOPPADDING',(0,0),(0,0), 28),
            ('TOPPADDING',(0,1),(-1,-1), 6),
            ('BOTTOMPADDING',(0,-1),(-1,-1), 24),
            ('ROUNDEDCORNERS', [6]),
        ]))
        return cover_t

    story.append(cover_table(d, fecha))
    story.append(Spacer(1, 14))

    # =========================================================================
    # TOTALS CARDS
    # =========================================================================
    def calc_totals(d):
        tot1 = tot2 = tot3 = 0.0

        # Scope 1
        for row in d.get('estac', []):
            v = calc_tco2(row.get('combustible',''), row.get('unidad',''), row.get('cantidad',''))
            if v: tot1 += v
        for row in d.get('movil', []):
            v = calc_tco2(row.get('combustible',''), row.get('unidad',''), row.get('cantidad',''))
            if v: tot1 += v
        for row in d.get('proceso', []):
            try:
                v = float(row.get('cantidad', 0))
                if row.get('unidad') == 'tCO2eq': tot1 += v
            except: pass
        for row in d.get('fugit', []):
            try:
                v = float(row.get('cantidad', 0))
                if row.get('unidad') == 'tCO2eq': tot1 += v
            except: pass

        # Scope 2
        for row in d.get('elec', []):
            u = row.get('unidad', '')
            try:
                q = float(row.get('cantidad', 0))
                fe = FE.get(u)
                if isinstance(fe, float): tot2 += q * fe
            except: pass
        for row in d.get('calor', []):
            u = row.get('unidad', '')
            try:
                q = float(row.get('cantidad', 0))
                fe = FE.get(u)
                if isinstance(fe, float): tot2 += q * fe
            except: pass

        # Scope 3 - simple categories
        for cat in ['c1','c2','c3','c4','c5','c9','c10','c11','c12']:
            try:
                v = float(d.get(f'{cat}_val', 0) or 0)
                tot3 += v
            except: pass

        # Cat 6 - business travel
        for row in d.get('viajes', []):
            medio = row.get('medio', '')
            try:
                n = float(row.get('n', 0))
                km = float(row.get('km', 0))
                key = medio.replace('(<700km)','corto').replace('(>700km)','largo').replace('/','').strip()
                fe_key = next((k for k in TRAVEL_FE if k.lower() in key.lower()), None)
                if fe_key:
                    tot3 += n * km * TRAVEL_FE[fe_key]
            except: pass

        # Cat 7 - employee commute
        try:
            emp = float(d.get('c7_emp', 0) or 0)
            km_d = float(d.get('c7_km', 0) or 0)
            medio = d.get('c7_medio', '')
            fe_key = next((k for k in COMMUTE_FE if k.lower() in medio.lower()), None)
            if fe_key and emp > 0 and km_d > 0:
                tot3 += emp * km_d * 220 * COMMUTE_FE[fe_key]
        except: pass

        return tot1, tot2, tot3

    tot1, tot2, tot3 = calc_totals(d)
    tot_total = tot1 + tot2 + tot3

    def scope_card(label, value, bg, fg):
        label_p = Paragraph(label.upper(), sty('cl', fontName='Helvetica', fontSize=7,
                            textColor=fg, leading=10))
        val_p   = Paragraph(f'{value:.1f}', sty('cv', fontName='Helvetica-Bold', fontSize=22,
                             textColor=fg, leading=26))
        unit_p  = Paragraph('tCO<sub rise="2" size="6">2</sub>eq',
                             sty('cu', fontName='Helvetica', fontSize=8, textColor=fg, leading=10))
        t = Table([[label_p],[val_p],[unit_p]], colWidths=[(W/4)-0.4*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1), bg),
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1), 12),
            ('BOTTOMPADDING',(0,-1),(-1,-1), 12),
            ('ROUNDEDCORNERS',[6]),
        ]))
        return t

    cards_row = [[
        scope_card('Alcance 1', tot1,    C_S1L, C_S1),
        scope_card('Alcance 2', tot2,    C_S2L, C_S2),
        scope_card('Alcance 3', tot3,    C_S3L, C_S3),
        scope_card('Total',     tot_total, C_GOLDB, C_GOLD),
    ]]
    cards_t = Table(cards_row, colWidths=[(W/4)]*4, hAlign='LEFT')
    cards_t.setStyle(TableStyle([
        ('LEFTPADDING',(0,0),(-1,-1),4),
        ('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),0),
        ('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(cards_t)
    story.append(Spacer(1, 20))

    # =========================================================================
    # HELPER: section title with GRI tag
    # =========================================================================
    def sec_title(label, tag=None):
        txt = f'<font color="#1a4b8c"><b>{label}</b></font>'
        if tag:
            txt = f'<font color="white" backColor="#1a4b8c"> {tag} </font>  ' + txt
        p = Paragraph(txt, sty('sec', fontName='Helvetica-Bold', fontSize=12,
                     textColor=C_S1, leading=16, spaceBefore=12, spaceAfter=4))
        story.append(p)
        story.append(HRFlowable(width=W, thickness=1.5, color=C_S1, spaceAfter=8))

    def note_box(text):
        t = Table([[Paragraph(text, s_note)]], colWidths=[W - 0.6*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1), LGRAY),
            ('LINEAFTER', (0,0),(0,-1), 0.3*cm, colors.HexColor('#0d7c6e')),
            ('LEFTPADDING',(0,0),(-1,-1),10),
            ('RIGHTPADDING',(0,0),(-1,-1),10),
            ('TOPPADDING',(0,0),(-1,-1),8),
            ('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('ROUNDEDCORNERS',[4]),
        ]))
        story.append(t)
        story.append(Spacer(1,8))

    def data_table(headers, rows, col_widths):
        th_row = [Paragraph(h, s_th) for h in headers]
        data = [th_row]
        for r in rows:
            data.append([Paragraph(str(c), s_td) for c in r])
        if len(data) == 1:
            data.append([Paragraph('—', s_td)] * len(headers))
        t = Table(data, colWidths=col_widths)
        style = [
            ('BACKGROUND',(0,0),(-1,0), C_S1),
            ('TEXTCOLOR',(0,0),(-1,0), WHITE),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
            ('FONTSIZE',(0,0),(-1,0),8),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE, LGRAY]),
            ('LINEBELOW',(0,0),(-1,-1),0.25, BORDER),
            ('TOPPADDING',(0,0),(-1,-1),5),
            ('BOTTOMPADDING',(0,0),(-1,-1),5),
            ('LEFTPADDING',(0,0),(-1,-1),6),
            ('RIGHTPADDING',(0,0),(-1,-1),6),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
        ]
        t.setStyle(TableStyle(style))
        story.append(t)
        story.append(Spacer(1, 8))

    def total_row_table(label, value, color):
        row = [[Paragraph(f'<b>{label}</b>', sty('tr',fontName='Helvetica-Bold',fontSize=9,
                          textColor=color, leading=12)),
                Paragraph(f'<b>{value:.3f} tCO<sub rise="2" size="6">2</sub>eq</b>',
                          sty('trv',fontName='Helvetica-Bold',fontSize=10,
                              textColor=color,leading=12,alignment=TA_RIGHT))]]
        t = Table(row, colWidths=[W*0.7, W*0.3])
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1), colors.HexColor('#eaf2fb')),
            ('LINEABOVE',(0,0),(-1,-1),1.5, color),
            ('TOPPADDING',(0,0),(-1,-1),6),
            ('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('LEFTPADDING',(0,0),(-1,-1),8),
            ('RIGHTPADDING',(0,0),(-1,-1),8),
        ]))
        story.append(t)
        story.append(Spacer(1,14))

    # =========================================================================
    # GRI DECLARATION
    # =========================================================================
    sec_title('Declaración sobre uso de los Estándares GRI')
    story.append(Paragraph(
        f"Este informe fue preparado con referencia a los <b>Estándares GRI</b>, en particular "
        f"<b>GRI 305: Emisiones 2016</b> y el <b>{d.get('estandar','GHG Protocol Corporate Standard')}</b>. "
        f"El período de reporte comprende el año <b>{d.get('anio','2025')}</b>. "
        f"La organización informante es <b>{d.get('empresa','—')}</b>, CUIT <b>{d.get('cuit','—')}</b>, "
        f"con sede en <b>{d.get('provincia','—')}, {d.get('pais','Argentina')}</b>. "
        f"El enfoque de consolidación adoptado es: <b>{d.get('enfoque','—')}</b>.",
        s_body))
    story.append(Spacer(1,6))
    note_box(f"<b>GRI 2-14:</b> El inventario ha sido supervisado por <b>{d.get('responsable','el responsable designado')}</b>.")

    # =========================================================================
    # SCOPE 1
    # =========================================================================
    sec_title('Emisiones directas — Alcance 1', 'GRI 305-1')
    story.append(Paragraph('Emisiones brutas de GEI de fuentes propias o controladas por la organización.', s_body))
    story.append(Spacer(1,6))

    hdrs = ['Categoría / Fuente', 'Combustible', 'Unidad', 'Cantidad', 'tCO\u2082eq']
    cw   = [W*0.3, W*0.2, W*0.12, W*0.15, W*0.13]

    rows_s1 = []
    # Stationary
    for r in d.get('estac', []):
        comb = r.get('combustible','—')
        u    = r.get('unidad','—')
        try: q = float(r.get('cantidad',0)); qs = f'{q:,.1f}'
        except: q=0; qs='—'
        v = calc_tco2(comb, u, q)
        vs = f'{v:.3f}' if v is not None else 'FE requerido'
        rows_s1.append([r.get('fuente', r.get('veh','—')) or 'Combustión estacionaria', comb, u, qs, vs])
    # Mobile
    for r in d.get('movil', []):
        comb = r.get('combustible','—')
        u    = r.get('unidad','—')
        try: q = float(r.get('cantidad',0)); qs = f'{q:,.1f}'
        except: q=0; qs='—'
        v = calc_tco2(comb, u, q)
        vs = f'{v:.3f}' if v is not None else 'FE requerido'
        rows_s1.append([r.get('veh','Combustión móvil'), comb, u, qs, vs])
    # Process
    for r in d.get('proceso', []):
        try: q = float(r.get('cantidad',0)); qs = f'{q:,.1f}'
        except: qs='—'
        rows_s1.append([r.get('proc','Proceso'), r.get('gas','—'), r.get('unidad','—'), qs, qs if r.get('unidad')=='tCO2eq' else 'FE requerido'])
    # Fugitive
    for r in d.get('fugit', []):
        try: q = float(r.get('cantidad',0)); qs = f'{q:,.1f}'
        except: qs='—'
        rows_s1.append([r.get('gas','Fugitivo'), r.get('equipo','—'), r.get('unidad','—'), qs, qs if r.get('unidad')=='tCO2eq' else 'FE requerido'])

    if rows_s1:
        data_table(hdrs, rows_s1, cw)
    total_row_table('Subtotal Alcance 1', tot1, C_S1)
    note_box('<b>Metodología:</b> Factores de emisión del IPCC AR6 (GWP-100) y IPCC Guidelines for National GHG Inventories.')

    # =========================================================================
    # SCOPE 2
    # =========================================================================
    sec_title('Emisiones indirectas por energía — Alcance 2', 'GRI 305-2')
    story.append(Paragraph('Emisiones brutas de GEI asociadas a energía comprada/adquirida a terceros.', s_body))
    story.append(Spacer(1,6))

    rows_s2 = []
    for r in d.get('elec', []):
        u = r.get('unidad','—')
        try: q = float(r.get('cantidad',0)); qs = f'{q:,.1f}'
        except: q=0; qs='—'
        fe = FE.get(u)
        v = (q * fe) if isinstance(fe, float) else None
        vs = f'{v:.3f}' if v is not None else 'FE requerido'
        rows_s2.append([r.get('sede','Electricidad'), r.get('dist','—'), u, qs, vs])
    for r in d.get('calor', []):
        u = r.get('unidad','—')
        try: q = float(r.get('cantidad',0)); qs = f'{q:,.1f}'
        except: q=0; qs='—'
        fe = FE.get(u)
        v = (q * fe) if isinstance(fe, float) else None
        vs = f'{v:.3f}' if v is not None else 'FE requerido'
        rows_s2.append([r.get('tipo','Calor/vapor'), r.get('proveedor','—'), u, qs, vs])

    hdrs2 = ['Tipo', 'Instalación / Proveedor', 'Unidad', 'Consumo', 'tCO\u2082eq']
    cw2   = [W*0.2, W*0.28, W*0.1, W*0.15, W*0.17]
    if rows_s2:
        data_table(hdrs2, rows_s2, cw2)
    total_row_table('Subtotal Alcance 2 (método ubicación)', tot2, C_S2)

    # Market method
    ppa = 'Sí' if d.get('ppa') == 'si' else 'No'
    pct = d.get('pct_renovable','0') or '0'
    cert = d.get('certificado','—') or '—'
    mkt_data = [['Contratos de energía renovable (PPA/PPE)', ppa],
                ['% de energía renovable certificada', f'{pct} %'],
                ['Tipo de certificado / acreditación', cert]]
    data_table(['Parámetro método de mercado', 'Valor'], mkt_data, [W*0.65, W*0.25])
    note_box('<b>GRI 305-2:</b> Factor de emisión red eléctrica Argentina CAMMESA: 0,420 tCO<sub rise="2" size="5">2</sub>eq/MWh (referencia 2023).')

    # =========================================================================
    # SCOPE 3
    # =========================================================================
    sec_title('Otras emisiones indirectas — Alcance 3', 'GRI 305-3')
    story.append(Paragraph('Emisiones brutas de GEI en la cadena de valor — categorías aguas arriba y aguas abajo.', s_body))
    story.append(Spacer(1,6))

    cat_labels = {
        'c1': 'Cat. 1 — Bienes y servicios adquiridos',
        'c2': 'Cat. 2 — Bienes de capital',
        'c3': 'Cat. 3 — Actividades relacionadas con energía',
        'c4': 'Cat. 4 — Transporte y distribución (aguas arriba)',
        'c5': 'Cat. 5 — Residuos generados en operaciones',
        'c9': 'Cat. 9 — Transporte y distribución (aguas abajo)',
        'c10': 'Cat. 10 — Procesamiento de productos vendidos',
        'c11': 'Cat. 11 — Uso de productos vendidos',
        'c12': 'Cat. 12 — Tratamiento fin de vida',
    }
    rows_s3 = []
    for key, label in cat_labels.items():
        val  = d.get(f'{key}_val','') or ''
        met  = d.get(f'{key}_metodo','—') or '—'
        nota = d.get(f'{key}_nota','') or ''
        try:
            v = float(val)
            vs = f'{v:.3f}'
        except:
            v=0; vs='—'
        rows_s3.append([label, met, vs, nota])

    # Cat 6 - travel
    travel_tot = 0.0
    travel_rows = []
    for r in d.get('viajes', []):
        medio = r.get('medio','—')
        try:
            n = float(r.get('n', 0))
            km = float(r.get('km', 0))
            key = medio.lower()
            fe_key = next((k for k in TRAVEL_FE if k.lower() in key), None)
            v = n * km * TRAVEL_FE[fe_key] if fe_key else None
            travel_tot += v if v else 0
            vs = f'{v:.3f}' if v else 'FE requerido'
        except:
            vs = '—'
        travel_rows.append([f'Cat. 6 — Viajes: {r.get("ruta","—")}', medio, vs, ''])

    if travel_rows:
        rows_s3 = travel_rows + rows_s3

    # Cat 7 - commute
    try:
        emp = float(d.get('c7_emp', 0) or 0)
        km_d = float(d.get('c7_km', 0) or 0)
        medio7 = d.get('c7_medio','') or ''
        fe_key7 = next((k for k in COMMUTE_FE if k.lower() in medio7.lower()), None)
        if fe_key7 and emp > 0:
            v7 = emp * km_d * 220 * COMMUTE_FE[fe_key7]
            rows_s3.append([f'Cat. 7 — Desplazamiento empleados ({medio7})',
                            'Basado en distancia', f'{v7:.3f}', f'{int(emp)} emp.'])
    except: pass

    hdrs3 = ['Categoría GHG Protocol / GRI', 'Método', 'tCO\u2082eq', 'Notas']
    cw3   = [W*0.38, W*0.28, W*0.14, W*0.1]
    if rows_s3:
        data_table(hdrs3, rows_s3, cw3)
    total_row_table('Subtotal Alcance 3', tot3, C_S3)

    obs3 = d.get('obs_a3','')
    if obs3:
        note_box(f'<b>Observaciones / fuentes de datos:</b> {obs3}')

    # =========================================================================
    # INTENSITY & REDUCTION
    # =========================================================================
    sec_title('Intensidad y reducción de emisiones', 'GRI 305-4 / 305-5')
    note_box(
        '<b>GRI 305-4 — Intensidad:</b> La organización calculará la intensidad de emisiones '
        '(tCO<sub rise="2" size="5">2</sub>eq / unidad de producción o facturación) en el próximo '
        'ciclo de reporte, utilizando los datos del presente inventario como línea de base.<br/><br/>'
        '<b>GRI 305-5 — Reducción:</b> Este es el inventario de año base. Se establecerán metas de '
        'reducción alineadas con el Acuerdo de París en el proceso de planificación estratégica de sostenibilidad.'
    )

    # =========================================================================
    # DECLARATION
    # =========================================================================
    sec_title('Declaración del responsable del inventario')
    decl = d.get('declarante', {})
    story.append(Paragraph(
        f"Yo, <b>{decl.get('nombre','—')}</b>, en carácter de <b>{decl.get('cargo','—')}</b> de "
        f"<b>{d.get('empresa','—')}</b>, declaro que la información contenida en este inventario de "
        f"emisiones de GEI es, a mi leal saber y entender, completa, precisa y fiel reflejo de las "
        f"actividades de la organización durante el período <b>{d.get('anio','2025')}</b>.",
        s_body))
    story.append(Spacer(1,10))

    notas_decl = decl.get('notas','')
    if notas_decl:
        note_box(f'<b>Notas adicionales:</b> {notas_decl}')

    # Signature block
    story.append(Spacer(1,20))
    sig_data = [
        [Paragraph(f"<b>{decl.get('nombre','—')}</b>", s_sig_name),
         Paragraph('<b>Consultor/a responsable</b>', s_sig_name)],
        [Paragraph(f"{decl.get('cargo','—')} · {d.get('empresa','—')}", s_sig_sub),
         Paragraph('Coop Agenda 20.30 · Consultoría en Huella de Carbono', s_sig_sub)],
        [Paragraph('__________________________', s_sig_sub),
         Paragraph('__________________________', s_sig_sub)],
        [Paragraph('Firma', s_sig_sub),
         Paragraph('Firma / Sello', s_sig_sub)],
    ]
    sig_t = Table(sig_data, colWidths=[W/2]*2)
    sig_t.setStyle(TableStyle([
        ('ALIGN',(0,0),(-1,-1),'LEFT'),
        ('TOPPADDING',(0,0),(-1,-1),4),
        ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(sig_t)

    # =========================================================================
    # FOOTER
    # =========================================================================
    story.append(Spacer(1,20))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER, spaceAfter=6))
    footer_data = [[
        Paragraph(f"Informe GRI 305 · {d.get('empresa','—')} · Período {d.get('anio','2025')}", s_footer),
        Paragraph(f"Preparado por Coop Agenda 20.30 · Consultoría en Huella de Carbono · {fecha}", s_footer),
    ]]
    ft = Table(footer_data, colWidths=[W*0.55, W*0.45])
    ft.setStyle(TableStyle([('ALIGN',(1,0),(1,0),'RIGHT'),
                            ('LEFTPADDING',(0,0),(-1,-1),0),
                            ('RIGHTPADDING',(0,0),(-1,-1),0)]))
    story.append(ft)

    doc.build(story)
    return buf.getvalue()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
