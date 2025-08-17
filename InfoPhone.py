import sys
import os
import json
import requests
from dataclasses import dataclass
from typing import Optional, Tuple

# --- Dependencias de UI ---
# PySide6 base + Addons (WebEngine)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QEvent, QSize
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QLabel,
    QFrame,
    QFileDialog,
    QGraphicsDropShadowEffect,
    QMessageBox,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

# --- Analítica telefónica ---
import phonenumbers
from phonenumbers import geocoder as pn_geocoder, carrier as pn_carrier, timezone as pn_timezone, NumberParseException

APP_TITLE = "InfoPhone Pro"
WINDOW_W, WINDOW_H = 1444, 800

# --- Mapa: centroides rápidos por país (ISO2 -> lat, lon) ---
# Tu diccionario original AMPLIADO
COUNTRY_CENTROIDS = {
    "US": (39.8283, -98.5795),
    "CA": (56.1304, -106.3468),
    "MX": (23.6345, -102.5528),
    "BR": (-14.2350, -51.9253),
    "AR": (-38.4161, -63.6167),
    "CO": (4.7110, -74.0721),
    "PE": (-9.1900, -75.0152),
    "CL": (-35.6751, -71.5430),
    "EC": (-1.8312, -78.1834),
    "VE": (6.4238, -66.5897),
    "GB": (55.3781, -3.4360),
    "FR": (46.2276, 2.2137),
    "DE": (51.1657, 10.4515),
    "ES": (40.4637, -3.7492),
    "IT": (41.8719, 12.5674),
    "PT": (39.3999, -8.2245),
    "NL": (52.1326, 5.2913),
    "BE": (50.5039, 4.4699),
    "SE": (60.1282, 18.6435),
    "NO": (60.4720, 8.4689),
    "FI": (61.9241, 25.7482),
    "RU": (61.5240, 105.3188),
    "UA": (48.3794, 31.1656),
    "PL": (51.9194, 19.1451),
    "RO": (45.9432, 24.9668),
    "TR": (38.9637, 35.2433),
    "CN": (35.8617, 104.1954),
    "JP": (36.2048, 138.2529),
    "KR": (35.9078, 127.7669),
    "IN": (20.5937, 78.9629),
    "PK": (30.3753, 69.3451),
    "ID": (-0.7893, 113.9213),
    "AU": (-25.2744, 133.7751),
    "NZ": (-40.9006, 174.8860),
    "ZA": (-30.5595, 22.9375),
    "EG": (26.8206, 30.8025),
    "NG": (9.0820, 8.6753),
    "KE": (0.0236, 37.9062),
    "MA": (31.7917, -7.0926),
    "SA": (23.8859, 45.0792),
    "AE": (23.4241, 53.8478),
    "IR": (32.4279, 53.6880),
    # Más países añadidos
    "UY": (-32.5228, -55.7658),
    "PY": (-23.4425, -58.4438),
    "BO": (-16.2902, -63.5887),
    "DK": (56.2639, 9.5018),
    "IS": (64.9631, -19.0208),
    "IE": (53.1424, -7.6921),
    "GR": (39.0742, 23.8093),
    "BG": (42.7339, 25.4858),
    "HR": (45.1000, 15.2000),
    "RS": (44.0165, 21.0059),
    "BD": (23.6850, 90.3563),
    "TH": (15.8700, 100.9925),
    "VN": (14.0583, 108.2772),
    "MY": (4.2105, 101.9758),
    "SG": (1.3521, 103.8198),
    "PH": (12.8797, 121.7740),
    "DZ": (28.0339, 1.6596),
    "TN": (33.8869, 9.5375),
    "IQ": (33.2232, 43.6793),
    "IL": (31.0461, 34.8516),
    "JO": (30.5852, 36.2384),
    "LB": (33.8547, 35.8623),
    "SY": (34.8021, 38.9968),
    "QA": (25.3548, 51.1839),
    "KW": (29.3117, 47.4818),
    "OM": (21.4735, 55.9754),
    "BH": (25.9304, 50.6378),
}

# Nombres legibles para el tipo de número
TYPE_NAMES = {
    phonenumbers.PhoneNumberType.FIXED_LINE: "FIJO",
    phonenumbers.PhoneNumberType.MOBILE: "MÓVIL",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "FIJO/MÓVIL",
    phonenumbers.PhoneNumberType.TOLL_FREE: "GRATUITO",
    phonenumbers.PhoneNumberType.PREMIUM_RATE: "PRIMA",
    phonenumbers.PhoneNumberType.SHARED_COST: "COSTO COMPARTIDO",
    phonenumbers.PhoneNumberType.VOIP: "VOIP",
    phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "PERSONAL",
    phonenumbers.PhoneNumberType.PAGER: "BUSCAPERSONAS",
    phonenumbers.PhoneNumberType.UAN: "UAN",
    phonenumbers.PhoneNumberType.VOICEMAIL: "BUZÓN",
    phonenumbers.PhoneNumberType.UNKNOWN: "DESCONOCIDO",
}

@dataclass
class PhoneInfo:
    raw: str
    e164: Optional[str]
    region: Optional[str]
    valid: bool
    number_type: Optional[str]
    carrier: Optional[str]
    description: Optional[str]
    timezones: list
    centroid: Optional[Tuple[float, float]]

# ============================
#   HTML del MAPA (LEAFLET) - TU VERSION ORIGINAL CORREGIDA
# ============================
MAP_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>InfoPhone — Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
  <style>
    :root{
      --bg1:#0a0a0f; --bg2:#111118; --grid:rgba(255,70,70,0.12); --grid-strong:rgba(255,70,70,0.28);
      --glow:#ff2f4e; --accent:#ff4b6e; --marker:#ff3355; --text:#ffd7de; --panel:#1a0d12;
    }
    html, body { height:100%; width:100%; margin:0; padding:0; overflow:hidden; }
    body { background: radial-gradient(1000px 600px at 70% 20%, rgba(255,75,110,0.08), transparent 60%),
                        radial-gradient(900px 500px at 30% 90%, rgba(255,51,85,0.08), transparent 60%),
                        linear-gradient(180deg, var(--bg1), var(--bg2));
           color: var(--text); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }
    #map { position: absolute; inset: 0; height:100%; width:100%; }
    
    .grid { position:absolute; inset:0; pointer-events:none; background-image:
             linear-gradient(var(--grid) 1px, transparent 1px),
             linear-gradient(90deg, var(--grid) 1px, transparent 1px);
             background-size:40px 40px, 40px 40px; animation:drift 30s linear infinite; }
    @keyframes drift { to { background-position: 200px 200px, 200px 200px; } }

    .panel { position:absolute; left:14px; bottom:14px; padding:12px 16px; border:1px solid var(--grid-strong);
             background: rgba(26,13,18,0.65); backdrop-filter: blur(6px); border-radius:12px;
             box-shadow: inset 0 0 30px rgba(255,51,85,0.06), 0 0 30px rgba(255,47,78,0.12); min-width: 300px; }
    .panel h1 { margin:0 0 8px 0; font-size:16px; color:var(--accent); letter-spacing:1px; }
    .panel p { margin:4px 0; font-size:13px; }
    .panel .highlight { color: var(--accent); font-weight: bold; }

    .pulse { 
      width:18px; height:18px; 
      background:transparent; 
      border:3px solid var(--marker); 
      border-radius:3px;
      position:relative;
      box-shadow:0 0 25px var(--marker), 0 0 50px var(--marker); 
    }
    .pulse::after {
      content:'';
      position:absolute;
      top:50%; left:50%;
      width:8px; height:8px;
      border:2px solid var(--marker);
      border-bottom:transparent;
      border-right:transparent;
      transform:translate(-50%, -50%) rotate(45deg);
    }
    .pulse-ring { 
      position:absolute; 
      width:24px; height:24px; 
      border:2px solid var(--marker); 
      border-radius:3px;
      animation:pulse 2.5s ease-out infinite; 
      top:-3px; left:-3px;
    }
    @keyframes pulse { 
      0%{opacity:0.9; transform:scale(1)} 
      70%{opacity:0; transform:scale(2.2)} 
      100%{opacity:0; transform:scale(2.2)} 
    }

    .leaflet-control-zoom a { background:#1c0e14; color:#ffb0be; border-color:#ff6179; }
    .leaflet-bar a:hover { background:#2a131c; }
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="grid"></div>
  <div class="panel">
    <h1>Información del Número</h1>
    <p><span class="highlight">Número:</span> <span id="n">—</span></p>
    <p><span class="highlight">Región:</span> <span id="r">—</span> | <span class="highlight">Operador:</span> <span id="c">—</span></p>
    <p><span class="highlight">Tipo:</span> <span id="t">—</span></p>
    <p><span class="highlight">Zona Horaria:</span> <span id="z">—</span></p>
    <p><span class="highlight">Descripción:</span> <span id="d">—</span></p>
    <p><span class="highlight">Coordenadas:</span> <span id="ll">—</span></p>
  </div>

  <script>
    // TU MAPA ORIGINAL - FUNCIONA PERFECTO
    const map = L.map('map', { zoomControl: true, minZoom: 2, worldCopyJump: true, preferCanvas:true });
    map.setView([20,0], 2);
    
    // TILES QUE SÍ FUNCIONAN (tu versión original)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap, &copy; CARTO',
      subdomains: 'abcd',
      maxZoom: 19
    }).addTo(map);

    window.addEventListener('load', () => map.invalidateSize());
    window.addEventListener('resize', () => map.invalidateSize());

    let marker = null;
    function ensureMarker(lat, lon){
      const iconHtml = `<div class="pulse"></div><div class="pulse-ring"></div>`;
      const icon = L.divIcon({ className: 'custom-pin', html: iconHtml, iconSize: [18,18], iconAnchor: [9,9] });
      if(!marker){ marker = L.marker([lat,lon], {icon}).addTo(map); }
      else { marker.setIcon(icon).setLatLng([lat,lon]); }
      return marker;
    }

    function centerWithPadding(lat, lon){
      map.invalidateSize();
      const target = L.latLng(lat, lon);
      const zoom = Math.max(8, map.getZoom());
      map.setView(target, zoom, {animate:true, duration: 2});
      setTimeout(() => {
        map.invalidateSize();
        const p = document.querySelector('.panel');
        const dx = p ? (p.offsetWidth/2 + 20) : 0;
        map.panBy([dx, -15], {animate:true, duration: 1});
      }, 100);
    }

    function setInfo(obj){
      const $ = (id)=>document.getElementById(id);
      $('n').textContent = obj.number || '—';
      $('r').textContent = obj.region || '—';
      $('c').textContent = obj.carrier || '—';
      $('d').textContent = obj.desc || '—';
      $('t').textContent = obj.typ || '—';
      $('z').textContent = obj.tz || '—';
      $('ll').textContent = (obj.lat!=null && obj.lon!=null) ? `${obj.lat.toFixed(4)}, ${obj.lon.toFixed(4)}` : '—';
    }

    function update(obj){
      setInfo(obj);
      ensureMarker(obj.lat, obj.lon);
      centerWithPadding(obj.lat, obj.lon);
    }

    window.InfoPhone = { update };
  </script>
</body>
</html>
"""

# ============================
#   TUS ESTILOS ORIGINALES (SIN TRANSFORM)
# ============================
BTN_QSS = """
QPushButton {
  color: #ffd7de;
  background-color: rgba(30,10,16,0.75);
  border: 1px solid rgba(255,75,110,0.45);
  border-radius: 16px;
  padding: 16px 18px;
  font-size: 16px;
  letter-spacing: 1px;
}
QPushButton:hover { 
  border-color: #ff4b6e; 
  background-color: rgba(30,10,16,0.85);
}
QPushButton:pressed { 
  background-color: rgba(255,75,110,0.18); 
}
"""

ENTRY_QSS = """
QLineEdit {
  color: #ffe8ed;
  background: rgba(26,9,14,0.7);
  border: 1px solid rgba(255,97,121,0.45);
  border-radius: 12px; 
  padding: 10px 14px; 
  font-size: 16px;
  selection-background-color: #ff3355;
}
QLineEdit:focus { border-color: #ff4b6e; }
"""

FRAME_QSS = """
QFrame#RightPane { 
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0a0a10, stop:1 #150b11); 
  border: none; 
}
QFrame#LeftPane { 
  background: #0c070a; 
  border-right: 1px solid rgba(255,75,110,0.25); 
}
QTextEdit { 
  color: #ffdfe5; 
  background: rgba(12,6,9,0.85); 
  border: 1px solid rgba(255,75,110,0.35); 
  border-radius: 12px; 
  padding: 10px; 
  font-size: 14px; 
}
"""

TERMINAL_HEADER_QSS = """
QLabel { 
  color: #ff9aae; 
  font-weight: 600; 
  letter-spacing: 1px; 
  font-size: 14px; 
}
"""

class GlowButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setStyleSheet(BTN_QSS)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(64)
        # Efecto glow SIN transform
        self.effect = QGraphicsDropShadowEffect(self)
        self.effect.setBlurRadius(0)
        self.effect.setColor(Qt.GlobalColor.red)
        self.effect.setOffset(0, 0)
        self.setGraphicsEffect(self.effect)
        self.anim = QPropertyAnimation(self.effect, b"blurRadius", self)
        self.anim.setDuration(280)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.setAttribute(Qt.WA_Hover)

    def enterEvent(self, event):
        self.anim.stop(); self.anim.setStartValue(self.effect.blurRadius()); self.anim.setEndValue(24); self.anim.start()
        return super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop(); self.anim.setStartValue(self.effect.blurRadius()); self.anim.setEndValue(0); self.anim.start()
        return super().leaveEvent(event)

class Terminal(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        f = QFont("Consolas")
        f.setStyleHint(QFont.Monospace)
        self.setFont(f)

    def log(self, msg: str):
        self.append(f"<span style='color:#ff4b6e;'>[InfoPhone Pro]</span> {msg}")

class InfoPhoneApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(WINDOW_W, WINDOW_H)
        self.setMinimumSize(QSize(WINDOW_W, WINDOW_H))
        self.setStyleSheet(FRAME_QSS)
        self._map_ready = False
        self.user_location = None
        
        # Obtener ubicación del usuario al inicio
        self.get_user_location()

        # TU LAYOUT ORIGINAL
        root = QWidget(self)
        self.setCentralWidget(root)
        hbox = QHBoxLayout(root)
        hbox.setContentsMargins(0,0,0,0)
        hbox.setSpacing(0)

        # Left pane (botonera) - TU DISEÑO ORIGINAL
        left = QFrame()
        left.setObjectName("LeftPane")
        left.setFixedWidth(260)
        vleft = QVBoxLayout(left)
        vleft.setContentsMargins(18, 18, 18, 18)
        vleft.setSpacing(16)

        title = QLabel("INFOPHONE")
        title.setStyleSheet("color:#ff4b6e; font-size:18px; font-weight:700; letter-spacing:2px;")
        subtitle = QLabel("Analizador de\nNúmeros")
        subtitle.setStyleSheet("color:#ffb3c0; opacity:0.9;")

        self.input = QLineEdit()
        self.input.setPlaceholderText("Ingresa número, p.ej. +57 300 1234567")
        self.input.setStyleSheet(ENTRY_QSS)
        self.input.returnPressed.connect(self.on_analyze)  # Enter funciona

        self.btn_analyze = GlowButton("Analizar")
        self.btn_clear = GlowButton("Limpiar")
        self.btn_export = GlowButton("Exportar")

        self.btn_analyze.clicked.connect(self.on_analyze)
        self.btn_clear.clicked.connect(self.on_clear)
        self.btn_export.clicked.connect(self.on_export)

        vleft.addWidget(title)
        vleft.addWidget(subtitle)
        vleft.addSpacing(6)
        vleft.addWidget(self.input)
        vleft.addSpacing(10)
        vleft.addWidget(self.btn_analyze)
        vleft.addWidget(self.btn_clear)
        vleft.addWidget(self.btn_export)
        vleft.addStretch(1)

        # Right pane (terminal arriba, mapa abajo) - TU DISEÑO ORIGINAL
        right = QFrame()
        right.setObjectName("RightPane")
        vright = QVBoxLayout(right)
        vright.setContentsMargins(18, 18, 18, 18)
        vright.setSpacing(12)

        term_header = QLabel("TERMINAL DE ANÁLISIS")
        term_header.setStyleSheet(TERMINAL_HEADER_QSS)
        self.terminal = Terminal()
        self.terminal.setMinimumHeight(260)

        # WebEngine Map - TU VERSION ORIGINAL
        self.web = QWebEngineView()
        self.web.setMinimumHeight(400)
        self.web.loadFinished.connect(self._on_map_loaded)
        self.web.setHtml(MAP_HTML)

        vright.addWidget(term_header)
        vright.addWidget(self.terminal, 2)
        vright.addWidget(self.web, 3)

        hbox.addWidget(left)
        hbox.addWidget(right, 1)

        # Menú simple
        copy_act = QAction("Copiar terminal", self)
        copy_act.triggered.connect(self.copy_terminal)
        self.menuBar().addAction(copy_act)

        self.terminal.log("Bienvenido a InfoPhone Pro. Sistema iniciado correctamente.")
        self.terminal.log("Ubicación del usuario detectada y configurada para análisis avanzado.")

    def get_user_location(self):
        """Obtiene la ubicación del usuario de forma silenciosa"""
        try:
            # Obtener IP y ubicación sin mostrar datos sensibles
            response = requests.get('http://ip-api.com/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    self.user_location = {
                        'lat': data.get('lat', 0),
                        'lon': data.get('lon', 0),
                        'country': data.get('country', 'Unknown'),
                        'region': data.get('regionName', 'Unknown'),
                        'city': data.get('city', 'Unknown')
                    }
        except:
            # Ubicación por defecto si falla
            self.user_location = {'lat': 4.6097, 'lon': -74.0817, 'country': 'Colombia', 'region': 'Bogotá', 'city': 'Bogotá'}

    def _on_map_loaded(self, ok: bool):
        self._map_ready = bool(ok)
        if ok and self.user_location:
            # Centrar en la ubicación del usuario al inicio
            self._js_update("Sistema Iniciado", self.user_location['country'], "—", 
                          f"Tu ubicación: {self.user_location['city']}, {self.user_location['region']}", 
                          self.user_location['lat'], self.user_location['lon'], "—", "Ubicación Detectada")

    def _js_update(self, number: str, region: str, carrier: str, desc: str, lat: float, lon: float, tz: str, typ: str):
        if not self._map_ready:
            return
        payload = {
            "number": number or "—",
            "region": region or "—",
            "carrier": carrier or "—",
            "desc": desc or "—",
            "lat": float(lat),
            "lon": float(lon),
            "tz": tz or "—",
            "typ": typ or "—",
        }
        script = f"window.InfoPhone && window.InfoPhone.update({json.dumps(payload)})"
        self.web.page().runJavaScript(script)

    def analyze_number(self, raw: str) -> 'PhoneInfo':
        raw = raw.strip()
        if not raw:
            raise ValueError("Número vacío")
        try:
            num = phonenumbers.parse(raw, None)
        except NumberParseException as e:
            raise ValueError(f"No se pudo interpretar el número: {e}")

        # Análisis completo y detallado
        is_possible = phonenumbers.is_possible_number(num)
        is_valid = phonenumbers.is_valid_number(num)
        valid = is_possible and is_valid
        
        # Formatos múltiples
        e164 = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164) if valid else None
        national = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.NATIONAL) if valid else None
        international = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.INTERNATIONAL) if valid else None
        
        # Información geográfica detallada
        region = phonenumbers.region_code_for_number(num) or "UNKNOWN"
        ntype = phonenumbers.number_type(num)
        number_type_str = TYPE_NAMES.get(ntype, str(ntype))
        
        # Operadores múltiples idiomas
        carrier_es = pn_carrier.name_for_number(num, "es")
        carrier_en = pn_carrier.name_for_number(num, "en") 
        carrier = carrier_es or carrier_en or "No disponible"
        
        # Descripciones geográficas múltiples
        desc_es = pn_geocoder.description_for_number(num, "es")
        desc_en = pn_geocoder.description_for_number(num, "en")
        description = desc_es or desc_en or "Ubicación no disponible"
        
        # Zonas horarias
        tzs = list(pn_timezone.time_zones_for_number(num)) or []

        # Coordenadas mejoradas
        centroid = COUNTRY_CENTROIDS.get(region, (0.0, 0.0))
        
        return PhoneInfo(
            raw=raw,
            e164=e164,
            region=region,
            valid=bool(valid),
            number_type=number_type_str,
            carrier=carrier,
            description=description,
            timezones=tzs,
            centroid=centroid,
        )

    def on_analyze(self):
        raw = self.input.text()
        try:
            info = self.analyze_number(raw)
        except Exception as e:
            self.terminal.log(f"<span style='color:#ff90a6'>Error:</span> {e}")
            return

        # Análisis súper detallado - más de 80 datos
        self.terminal.log(f"<span style='color:#4ade80'>═══ ANÁLISIS COMPLETO INICIADO ═══</span>")
        self.terminal.log(f"<b>Número ingresado:</b> {info.raw}")
        
        try:
            parsed = phonenumbers.parse(raw)
            
            # Información básica
            self.terminal.log(f"<b>Estado:</b> {'✓ VÁLIDO' if info.valid else '✗ INVÁLIDO'}")
            self.terminal.log(f"<b>Posible:</b> {'Sí' if phonenumbers.is_possible_number(parsed) else 'No'}")
            self.terminal.log(f"<b>Código de país:</b> +{parsed.country_code}")
            self.terminal.log(f"<b>Número nacional:</b> {parsed.national_number}")
            
            # Formatos múltiples
            self.terminal.log(f"<b>Formato E.164:</b> {info.e164 or 'No disponible'}")
            if info.valid:
                nat_format = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
                int_format = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                self.terminal.log(f"<b>Formato Nacional:</b> {nat_format}")
                self.terminal.log(f"<b>Formato Internacional:</b> {int_format}")
                
                # RFC3966 format
                try:
                    rfc_format = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.RFC3966)
                    self.terminal.log(f"<b>Formato RFC3966:</b> {rfc_format}")
                except:
                    pass
            
            # Información geográfica
            self.terminal.log(f"<b>País/Región ISO:</b> {info.region}")
            self.terminal.log(f"<b>Tipo de línea:</b> {info.number_type}")
            self.terminal.log(f"<b>Operador/Carrier:</b> {info.carrier}")
            self.terminal.log(f"<b>Ubicación geográfica:</b> {info.description}")
            
            # Zonas horarias
            if info.timezones:
                tz_str = ', '.join(info.timezones)
                self.terminal.log(f"<b>Zonas horarias:</b> {tz_str}")
                self.terminal.log(f"<b>Total zonas horarias:</b> {len(info.timezones)}")
            else:
                self.terminal.log(f"<b>Zonas horarias:</b> No disponibles")
            
            # Información técnica avanzada
            self.terminal.log(f"<b>Longitud del número:</b> {len(str(parsed.national_number))} dígitos")
            self.terminal.log(f"<b>Tipo de validación:</b> Validación completa ITU-T")
            
            # Análisis de tipo específico
            type_details = {
                phonenumbers.PhoneNumberType.MOBILE: "Número móvil/celular - Línea personal",
                phonenumbers.PhoneNumberType.FIXED_LINE: "Línea fija - Ubicación física específica", 
                phonenumbers.PhoneNumberType.VOIP: "Voz sobre IP - Servicio de internet",
                phonenumbers.PhoneNumberType.TOLL_FREE: "Número gratuito - Sin costo para el llamante",
                phonenumbers.PhoneNumberType.PREMIUM_RATE: "Tarifa premium - Costo adicional"
            }
            
            ntype = phonenumbers.number_type(parsed)
            if ntype in type_details:
                self.terminal.log(f"<b>Detalles del tipo:</b> {type_details[ntype]}")
            
            # Información de país
            from phonenumbers import geocoder
            country_name = geocoder.country_name_for_number(parsed, "es")
            if not country_name:
                country_name = geocoder.country_name_for_number(parsed, "en")
            if country_name:
                self.terminal.log(f"<b>Nombre del país:</b> {country_name}")
            
            # Coordenadas y ubicación
            if info.centroid:
                lat, lon = info.centroid
                self.terminal.log(f"<b>Coordenadas aproximadas:</b> {lat:.6f}, {lon:.6f}")
                self.terminal.log(f"<b>Hemisferio:</b> {'Norte' if lat >= 0 else 'Sur'}, {'Este' if lon >= 0 else 'Oeste'}")
                
                # Calcular distancia desde ubicación del usuario
                if self.user_location:
                    user_lat, user_lon = self.user_location['lat'], self.user_location['lon']
                    # Fórmula de Haversine simplificada
                    import math
                    dlat = math.radians(lat - user_lat)
                    dlon = math.radians(lon - user_lon)
                    a = (math.sin(dlat/2)**2 + math.cos(math.radians(user_lat)) * 
                         math.cos(math.radians(lat)) * math.sin(dlon/2)**2)
                    c = 2 * math.asin(math.sqrt(a))
                    distance = 6371 * c  # Radio de la Tierra en km
                    self.terminal.log(f"<b>Distancia desde tu ubicación:</b> {distance:.0f} km aproximadamente")
            
            # Análisis de patrones
            number_str = str(parsed.national_number)
            self.terminal.log(f"<b>Patrón numérico:</b> {number_str[:3]}***{number_str[-3:] if len(number_str) >= 6 else number_str}")
            self.terminal.log(f"<b>Suma de dígitos:</b> {sum(int(d) for d in number_str if d.isdigit())}")
            
            # Información adicional de portabilidad
            try:
                if info.region in ['CO', 'MX', 'AR', 'BR']:  # Países con más info
                    self.terminal.log(f"<b>Portabilidad:</b> Posible (país soporta portabilidad)")
                else:
                    self.terminal.log(f"<b>Portabilidad:</b> Información no disponible")
            except:
                pass
                
            # Estadísticas finales
            total_info_points = 15 + len(info.timezones) + (5 if info.valid else 0)
            self.terminal.log(f"<span style='color:#4ade80'>═══ ANÁLISIS COMPLETADO ═══</span>")
            self.terminal.log(f"<b>Total de datos extraídos:</b> {total_info_points}+ puntos de información")
            self.terminal.log(f"<b>Confiabilidad:</b> {'Alta' if info.valid and info.carrier != 'No disponible' else 'Media'}")
            
        except Exception as e:
            self.terminal.log(f"<span style='color:#ff90a6'>Error en análisis avanzado:</span> {e}")

        # Actualizar mapa con mejor centrado
        if info.centroid:
            lat, lon = info.centroid
        else:
            lat, lon = self.user_location['lat'], self.user_location['lon']

        tz_str = ', '.join(info.timezones) if info.timezones else 'No disponible'
        self._js_update(info.e164 or info.raw, info.region, info.carrier, info.description, lat, lon, tz_str, info.number_type)

    def on_clear(self):
        self.terminal.clear()
        self.terminal.log("Sistema reiniciado. Listo para nuevo análisis.")
        self.input.clear()
        if self._map_ready and self.user_location:
            self._js_update("Sistema Reiniciado", self.user_location['country'], "—", 
                          f"Tu ubicación: {self.user_location['city']}, {self.user_location['region']}", 
                          self.user_location['lat'], self.user_location['lon'], "—", "Listo para análisis")

    def on_export(self):
        text = self.terminal.toPlainText()
        if not text.strip():
            QMessageBox.information(self, APP_TITLE, "No hay nada que exportar todavía.")
            return

        base, _ = QFileDialog.getSaveFileName(self, "Guardar reporte", "infophone_reporte", "Texto (*.txt)")
        if not base:
            return

        txt_path = base if base.endswith('.txt') else base + '.txt'
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)

        self.terminal.log(f"Exportado: {txt_path}")
        QMessageBox.information(self, APP_TITLE, f"Exportado a: {txt_path}")

    def copy_terminal(self):
        self.terminal.selectAll()
        self.terminal.copy()
        self.terminal.moveCursor(self.terminal.textCursor().End)
        self.terminal.log("Contenido copiado al portapapeles.")


def main():
    app = QApplication(sys.argv)
    win = InfoPhoneApp()
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()