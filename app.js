// ══════════════════════════════════════════════════════════
// ESTADO
// ══════════════════════════════════════════════════════════
const rows = { estac:[], movil:[], proceso:[], fugit:[], elec:[], calor:[], viajes:[] };

// ══════════════════════════════════════════════════════════
// NAVEGACIÓN
// ══════════════════════════════════════════════════════════
let currentStep = 0;

function goTo(step) {
  document.querySelectorAll('.section').forEach((s,i) => {
    s.classList.toggle('active', i === step);
  });
  document.querySelectorAll('.step-pill').forEach((p,i) => {
    p.classList.remove('active','done');
    if (i === step) p.classList.add('active');
    else if (i < step) p.classList.add('done');
  });
  currentStep = step;
  if (step === 4) buildSummary();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ══════════════════════════════════════════════════════════
// FACTORES DE EMISIÓN
// ══════════════════════════════════════════════════════════
const FE = {
  'Gas natural':  { 'm3': 0.00200, 'GJ': 0.05610, 'MMBtu': 0.05900 },
  'GLP':          { 'litros': 0.00153, 'kg': 0.00214, 'tn': 2.140 },
  'Gasoil':       { 'litros': 0.00268, 'kg': 0.00318, 'tn': 3.180 },
  'Fuel oil':     { 'litros': 0.00273, 'kg': 0.00320, 'tn': 3.200 },
  'Carbón':       { 'kg': 0.00229, 'tn': 2.290 },
  'Biomasa':      { 'kg': 0.00000, 'tn': 0.00000 },
  'Nafta':        { 'litros': 0.00233, 'km': 0.00021 },
  'GNC':          { 'm3': 0.00200, 'km': 0.00012 },
  'Eléctrico':    { 'kWh': 0.00042, 'km': 0.00008 },
  'kWh':  0.00042,
  'MWh':  0.42000,
  'GJ':   0.11667,
};

const TRAVEL_FE = {
  'Avión corto (<700km)':  0.000255,
  'Avión largo (>700km)':  0.000195,
  'Tren':                  0.000041,
  'Ómnibus':               0.000089,
  'Auto alquiler':         0.000210,
};

const COMMUTE_FE = {
  'Auto particular':    0.000210,
  'Transporte público': 0.000041,
  'Remis / taxi':       0.000250,
  'Mixto':              0.000125,
};

function calcTCO2(combustible, unidad, cantidad) {
  const q = parseFloat(cantidad);
  if (!combustible || !unidad || isNaN(q) || q <= 0) return null;
  const table = FE[combustible];
  if (table === undefined) return null;
  const fe = typeof table === 'number' ? table : table[unidad];
  if (fe === undefined) return null;
  return q * fe;
}

// ══════════════════════════════════════════════════════════
// CONFIGURACIÓN DE FILAS REPETIBLES
// ══════════════════════════════════════════════════════════
const rowConfig = {
  estac: [
    { ph: 'Fuente / equipo', key: 'fuente' },
    { ph: 'Combustible', key: 'combustible', type: 'select',
      opts: ['Gas natural','GLP','Gasoil','Fuel oil','Carbón','Biomasa','Otro'] },
    { ph: 'Unidad', key: 'unidad', type: 'select',
      opts: ['m³','litros','kg','tn','MMBtu','GJ'] },
    { ph: 'Cantidad', key: 'cantidad', type: 'number' }
  ],
  movil: [
    { ph: 'Vehículo / flota', key: 'veh' },
    { ph: 'Combustible', key: 'combustible', type: 'select',
      opts: ['Nafta','Gasoil','GNC','GLP','Eléctrico','Otro'] },
    { ph: 'Unidad', key: 'unidad', type: 'select',
      opts: ['litros','m³','km','kWh'] },
    { ph: 'Cantidad', key: 'cantidad', type: 'number' }
  ],
  proceso: [
    { ph: 'Proceso / actividad', key: 'proc' },
    { ph: 'Gas emitido', key: 'gas', type: 'select',
      opts: ['CO₂','CH₄','N₂O','HFCs','PFCs','SF₆'] },
    { ph: 'Unidad', key: 'unidad', type: 'select',
      opts: ['kg','tn','tCO2eq'] },
    { ph: 'Cantidad', key: 'cantidad', type: 'number' }
  ],
  fugit: [
    { ph: 'Refrigerante / gas', key: 'gas' },
    { ph: 'Tipo de equipo', key: 'equipo' },
    { ph: 'Unidad', key: 'unidad', type: 'select',
      opts: ['kg','tCO2eq'] },
    { ph: 'Cantidad recargada', key: 'cantidad', type: 'number' }
  ],
  elec: [
    { ph: 'Instalación / sede', key: 'sede' },
    { ph: 'Distribuidora / CAMMESA', key: 'dist' },
    { ph: 'Unidad', key: 'unidad', type: 'select',
      opts: ['kWh','MWh'] },
    { ph: 'Consumo', key: 'cantidad', type: 'number' }
  ],
  calor: [
    { ph: 'Tipo (vapor, calor, frío)', key: 'tipo' },
    { ph: 'Proveedor', key: 'proveedor' },
    { ph: 'Unidad', key: 'unidad', type: 'select',
      opts: ['GJ','MWh','toneladas vapor'] },
    { ph: 'Cantidad', key: 'cantidad', type: 'number' }
  ],
  viajes: [
    { ph: 'Destino / ruta', key: 'ruta' },
    { ph: 'Medio', key: 'medio', type: 'select',
      opts: ['Avión corto (<700km)','Avión largo (>700km)','Tren','Ómnibus','Auto alquiler'] },
    { ph: 'N° viajes / personas', key: 'n', type: 'number' },
    { ph: 'Km aprox.', key: 'km', type: 'number' }
  ]
};

function addRow(type) {
  const cfg = rowConfig[type];
  const id = Date.now();
  const div = document.createElement('div');
  div.className = 'repeat-row';
  div.id = `row-${type}-${id}`;
  div.style.gridTemplateColumns = `repeat(${cfg.length}, 1fr) 36px`;

  cfg.forEach(f => {
    const wrap = document.createElement('div');
    wrap.className = 'field';
    let el;
    if (f.type === 'select') {
      el = document.createElement('select');
      el.innerHTML = `<option value="">— ${f.ph} —</option>` +
                     f.opts.map(o => `<option>${o}</option>`).join('');
    } else {
      el = document.createElement('input');
      el.type = f.type || 'text';
      el.placeholder = f.ph;
    }
    el.dataset.key = f.key;
    el.dataset.rowid = id;
    el.dataset.rowtype = type;
    wrap.appendChild(el);
    div.appendChild(wrap);
  });

  const rm = document.createElement('button');
  rm.className = 'btn-remove';
  rm.innerHTML = '×';
  rm.title = 'Eliminar fila';
  rm.onclick = () => {
    div.remove();
    rows[type] = rows[type].filter(r => r.id !== id);
  };
  div.appendChild(rm);

  document.getElementById(`${type}-rows`).appendChild(div);
  rows[type].push({ id });
}

// ══════════════════════════════════════════════════════════
// LEER TODAS LAS FILAS DE UN TIPO
// ══════════════════════════════════════════════════════════
function leerFilas(type) {
  const container = document.getElementById(`${type}-rows`);
  if (!container) return [];
  const result = [];
  container.querySelectorAll('.repeat-row').forEach(rowEl => {
    const obj = {};
    rowEl.querySelectorAll('[data-key]').forEach(el => {
      obj[el.dataset.key] = el.value.trim();
    });
    if (Object.values(obj).some(v => v)) result.push(obj);
  });
  return result;
}

// ══════════════════════════════════════════════════════════
// CALCULAR TOTALES
// ══════════════════════════════════════════════════════════
function calcularTotales() {
  let tot1 = 0, tot2 = 0, tot3 = 0;

  // Scope 1
  leerFilas('estac').forEach(r => {
    const v = calcTCO2(r.combustible, r.unidad, r.cantidad);
    if (v) tot1 += v;
  });
  leerFilas('movil').forEach(r => {
    const v = calcTCO2(r.combustible, r.unidad, r.cantidad);
    if (v) tot1 += v;
  });
  leerFilas('proceso').forEach(r => {
    if (r.unidad === 'tCO2eq') {
      const q = parseFloat(r.cantidad);
      if (!isNaN(q)) tot1 += q;
    }
  });
  leerFilas('fugit').forEach(r => {
    if (r.unidad === 'tCO2eq') {
      const q = parseFloat(r.cantidad);
      if (!isNaN(q)) tot1 += q;
    }
  });

  // Scope 2
  leerFilas('elec').forEach(r => {
    const fe = FE[r.unidad];
    const q = parseFloat(r.cantidad);
    if (typeof fe === 'number' && !isNaN(q)) tot2 += q * fe;
  });
  leerFilas('calor').forEach(r => {
    const fe = FE[r.unidad];
    const q = parseFloat(r.cantidad);
    if (typeof fe === 'number' && !isNaN(q)) tot2 += q * fe;
  });

  // Scope 3 - simple categories
  ['c1','c2','c3','c4','c5','c9','c10','c11','c12'].forEach(cat => {
    const el = document.getElementById(`${cat}_val`);
    if (el) {
      const q = parseFloat(el.value);
      if (!isNaN(q) && q > 0) tot3 += q;
    }
  });

  // Cat 6 - business travel
  leerFilas('viajes').forEach(r => {
    const fe = TRAVEL_FE[r.medio];
    const n = parseFloat(r.n);
    const km = parseFloat(r.km);
    if (fe && !isNaN(n) && !isNaN(km)) tot3 += n * km * fe;
  });

  // Cat 7 - employee commute
  const emp = parseFloat(document.getElementById('c7_emp')?.value || 0);
  const kmD = parseFloat(document.getElementById('c7_km')?.value || 0);
  const med = document.getElementById('c7_medio')?.value || '';
  const fe7 = COMMUTE_FE[med];
  if (fe7 && emp > 0 && kmD > 0) tot3 += emp * kmD * 220 * fe7;

  return { tot1, tot2, tot3, total: tot1 + tot2 + tot3 };
}

// ══════════════════════════════════════════════════════════
// CONSTRUIR RESUMEN
// ══════════════════════════════════════════════════════════
function buildSummary() {
  const { tot1, tot2, tot3, total } = calcularTotales();

  // Cards
  document.getElementById('summary-cards').innerHTML = `
    <div class="summary-card s1">
      <div class="scope-label">Alcance 1</div>
      <div class="scope-val">${tot1.toFixed(2)}</div>
      <div class="scope-unit">tCO₂eq</div>
    </div>
    <div class="summary-card s2">
      <div class="scope-label">Alcance 2</div>
      <div class="scope-val">${tot2.toFixed(2)}</div>
      <div class="scope-unit">tCO₂eq</div>
    </div>
    <div class="summary-card s3">
      <div class="scope-label">Alcance 3</div>
      <div class="scope-val">${tot3.toFixed(2)}</div>
      <div class="scope-unit">tCO₂eq</div>
    </div>
  `;

  // Table
  let tbody = '';

  // A1 rows
  tbody += `<tr class="sec-hdr a1"><td colspan="5">⬛ Alcance 1 — Emisiones directas</td></tr>`;
  let hasA1 = false;
  leerFilas('estac').forEach(r => {
    const v = calcTCO2(r.combustible, r.unidad, r.cantidad);
    if (r.fuente || r.combustible) {
      hasA1 = true;
      tbody += `<tr><td>${r.fuente||'Combustión estacionaria'}</td><td style="text-align:right">${r.cantidad||'—'}</td><td>${r.unidad||'—'}</td><td>${r.combustible||'—'}</td><td>${v!==null?v.toFixed(3):'FE requerido'}</td></tr>`;
    }
  });
  leerFilas('movil').forEach(r => {
    const v = calcTCO2(r.combustible, r.unidad, r.cantidad);
    if (r.veh || r.combustible) {
      hasA1 = true;
      tbody += `<tr><td>${r.veh||'Combustión móvil'}</td><td style="text-align:right">${r.cantidad||'—'}</td><td>${r.unidad||'—'}</td><td>${r.combustible||'—'}</td><td>${v!==null?v.toFixed(3):'FE requerido'}</td></tr>`;
    }
  });
  if (!hasA1) tbody += `<tr><td colspan="5" style="color:var(--muted);font-style:italic">Sin fuentes cargadas</td></tr>`;
  tbody += `<tr class="subtot a1"><td colspan="4">Subtotal Alcance 1</td><td>${tot1.toFixed(3)} tCO₂eq</td></tr>`;

  // A2 rows
  tbody += `<tr class="sec-hdr a2"><td colspan="5">🟢 Alcance 2 — Indirectas energía</td></tr>`;
  let hasA2 = false;
  leerFilas('elec').forEach(r => {
    const fe = FE[r.unidad];
    const q = parseFloat(r.cantidad);
    const v = (typeof fe === 'number' && !isNaN(q)) ? (q * fe) : null;
    if (r.sede || r.cantidad) {
      hasA2 = true;
      tbody += `<tr><td>${r.sede||'Electricidad'}</td><td style="text-align:right">${r.cantidad||'—'}</td><td>${r.unidad||'—'}</td><td>${r.dist||'—'}</td><td>${v!==null?v.toFixed(3):'FE requerido'}</td></tr>`;
    }
  });
  if (!hasA2) tbody += `<tr><td colspan="5" style="color:var(--muted);font-style:italic">Sin fuentes cargadas</td></tr>`;
  tbody += `<tr class="subtot a2"><td colspan="4">Subtotal Alcance 2</td><td>${tot2.toFixed(3)} tCO₂eq</td></tr>`;

  // A3 rows
  tbody += `<tr class="sec-hdr a3"><td colspan="5">🟣 Alcance 3 — Cadena de valor</td></tr>`;
  const catLabels = {
    c1:'Cat.1 Bienes y servicios',c2:'Cat.2 Bienes de capital',c3:'Cat.3 Energía',
    c4:'Cat.4 Transporte ↑',c5:'Cat.5 Residuos',c9:'Cat.9 Transporte ↓',
    c10:'Cat.10 Procesamiento',c11:'Cat.11 Uso productos',c12:'Cat.12 Fin de vida',
  };
  let hasA3 = false;
  Object.entries(catLabels).forEach(([cat,label]) => {
    const el = document.getElementById(`${cat}_val`);
    const q = parseFloat(el?.value || 0);
    if (!isNaN(q) && q > 0) {
      hasA3 = true;
      tbody += `<tr><td>${label}</td><td colspan="3">${document.getElementById(`${cat}_metodo`)?.value||'—'}</td><td>${q.toFixed(3)}</td></tr>`;
    }
  });
  leerFilas('viajes').forEach(r => {
    const fe = TRAVEL_FE[r.medio];
    const n = parseFloat(r.n);
    const km = parseFloat(r.km);
    if (r.ruta) {
      hasA3 = true;
      const v = (fe && !isNaN(n) && !isNaN(km)) ? (n*km*fe) : null;
      tbody += `<tr><td>Cat.6 ${r.ruta}</td><td style="text-align:right">${n||'—'} viajes</td><td>${km||'—'} km</td><td>${r.medio||'—'}</td><td>${v?v.toFixed(3):'FE requerido'}</td></tr>`;
    }
  });
  const emp = parseFloat(document.getElementById('c7_emp')?.value||0);
  const kmD = parseFloat(document.getElementById('c7_km')?.value||0);
  const med7 = document.getElementById('c7_medio')?.value||'';
  const fe7 = COMMUTE_FE[med7];
  if (fe7 && emp > 0 && kmD > 0) {
    hasA3 = true;
    const v7 = emp * kmD * 220 * fe7;
    tbody += `<tr><td>Cat.7 Desplazamiento empleados</td><td style="text-align:right">${emp}</td><td>empleados</td><td>${med7}</td><td>${v7.toFixed(3)}</td></tr>`;
  }
  if (!hasA3) tbody += `<tr><td colspan="5" style="color:var(--muted);font-style:italic">Sin fuentes cargadas</td></tr>`;
  tbody += `<tr class="subtot a3"><td colspan="4">Subtotal Alcance 3</td><td>${tot3.toFixed(3)} tCO₂eq</td></tr>`;

  // Total row
  tbody += `<tr style="background:var(--forest);color:white;font-weight:700;font-size:0.95rem">
    <td colspan="4" style="padding:10px 12px">TOTAL GENERAL</td>
    <td style="text-align:right;padding:10px 12px">${total.toFixed(3)} tCO₂eq</td>
  </tr>`;

  document.getElementById('summary-table-wrap').innerHTML = `
    <div class="sum-table-wrap">
      <table class="sum-table">
        <thead>
          <tr>
            <th>Fuente / descripción</th>
            <th style="text-align:right">Cantidad</th>
            <th>Unidad</th>
            <th>Combustible / tipo</th>
            <th style="text-align:right">tCO₂eq</th>
          </tr>
        </thead>
        <tbody>${tbody}</tbody>
      </table>
    </div>
  `;
}

// ══════════════════════════════════════════════════════════
// RECOLECTAR TODOS LOS DATOS DEL FORMULARIO
// ══════════════════════════════════════════════════════════
function recolectarDatos() {
  const g = id => document.getElementById(id)?.value?.trim() || '';

  // Scope 3 simple categories
  const s3cats = {};
  ['c1','c2','c3','c4','c5','c9','c10','c11','c12'].forEach(cat => {
    s3cats[`${cat}_val`]    = g(`${cat}_val`);
    s3cats[`${cat}_metodo`] = g(`${cat}_metodo`);
    s3cats[`${cat}_nota`]   = g(`${cat}_nota`);
  });

  return {
    empresa:   g('empresa'),
    cuit:      g('cuit'),
    sector:    g('sector'),
    pais:      g('pais'),
    provincia: g('provincia'),
    anio:      g('anio'),
    fecha_ini: g('fecha_ini'),
    fecha_fin: g('fecha_fin'),
    estandar:  g('estandar'),
    enfoque:   g('enfoque'),
    responsable: g('responsable'),
    ppa:       g('ppa'),
    pct_renovable: g('pct_renovable'),
    certificado: g('certificado'),
    c7_emp: g('c7_emp'),
    c7_km:  g('c7_km'),
    c7_medio: g('c7_medio'),
    obs_a3: g('obs_a3'),
    ...s3cats,
    estac:   leerFilas('estac'),
    movil:   leerFilas('movil'),
    proceso: leerFilas('proceso'),
    fugit:   leerFilas('fugit'),
    elec:    leerFilas('elec'),
    calor:   leerFilas('calor'),
    viajes:  leerFilas('viajes'),
    declarante: {
      nombre: g('decl_nombre'),
      cargo:  g('decl_cargo'),
      notas:  g('decl_notas'),
    },
  };
}

// ══════════════════════════════════════════════════════════
// GENERAR PDF vía Flask
// ══════════════════════════════════════════════════════════
async function generarPDF() {
  const btn = document.getElementById('btn-pdf');
  const txt = document.getElementById('btn-pdf-text');

  const data = recolectarDatos();

  if (!data.empresa) {
    showToast('Por favor ingresá la razón social de la organización.', true);
    goTo(0);
    return;
  }

  btn.classList.add('loading');
  btn.disabled = true;
  txt.textContent = '⏳ Generando informe...';

  try {
    const resp = await fetch('/generar-pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `Informe_GRI305_${(data.empresa||'empresa').replace(/\s+/g,'_')}_${data.anio||2025}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast('✅ Informe PDF generado correctamente.');
  } catch (err) {
    console.error(err);
    showToast('❌ Error al generar el PDF. Intentá de nuevo.', true);
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
    txt.textContent = '⬇ Generar informe PDF';
  }
}

// ══════════════════════════════════════════════════════════
// TOAST
// ══════════════════════════════════════════════════════════
function showToast(msg, isError = false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast' + (isError ? ' error' : '');
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 4000);
}

// ══════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════
addRow('estac');
addRow('movil');
addRow('elec');
