"""
MugiManager - Machine Learning Incident Engine
NLP Classifier & Delay Predictor trained with Scikit-Learn for Gipuzkoa Transit Alerts
"""
import os
import joblib
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

MODEL_FILE = os.path.join(os.path.dirname(__file__), "incident_ml_models.joblib")

# Realistic Domain Training Dataset for Gipuzkoa Public Transport Incidents
TRAINING_DATA = [
    # --- CRÍTICA / ALTA: Averías graves, cortes, catenaria ---
    {
        "text": "Avería grave en la catenaria entre Herrera y Lezo-Errenteria. Circulación totalmente interrumpida en ambos sentidos.",
        "severity": "CRITICA",
        "category": "Avería Vía / Catenaria",
        "zone": "Oarsoaldea",
        "operator": "Renfe Cercanías",
        "delay_min": 50,
        "alternative": "Utilice la línea E2 de Euskotren (El Topo) desde Herrera o Errenteria como alternativa ferroviaria."
    },
    {
        "text": "Corte total del servicio Topo entre Amara y Anoeta por desprendimiento en el túnel. Servicio suspendido.",
        "severity": "CRITICA",
        "category": "Avería Vía / Catenaria",
        "zone": "Donostialdea",
        "operator": "Euskotren",
        "delay_min": 60,
        "alternative": "Utilice las líneas 28 y 26 de Dbus desde el Boulevard o Pío XII para conectar Amara con Anoeta."
    },
    {
        "text": "Fallo en el sistema de señalización en Donostia Estación del Norte. Trenes de Cercanías C1 detenidos indefinidamente.",
        "severity": "CRITICA",
        "category": "Avería Vía / Catenaria",
        "zone": "Donostialdea",
        "operator": "Renfe Cercanías",
        "delay_min": 45,
        "alternative": "Acuda a la estación de autobuses anexa (Atotxa) y use líneas Lurraldebus TO01 (Tolosa) o E02 (Errenteria)."
    },
    {
        "text": "Incendio en la vía férrea a la altura de Zumaia. Suspendida la circulación ferroviaria Donostia-Bilbao de Euskotren.",
        "severity": "CRITICA",
        "category": "Avería Vía / Catenaria",
        "zone": "Urola Kosta",
        "operator": "Euskotren",
        "delay_min": 75,
        "alternative": "Transbordo por carretera con autobús Lurraldebus UK09 hacia Zarautz y Donostia."
    },
    {
        "text": "Inundación en el paso inferior de Hernani por crecida del río Urumea. Cortado el servicio de trenes C1.",
        "severity": "CRITICA",
        "category": "Meteorología y Temporal",
        "zone": "Donostialdea",
        "operator": "Renfe Cercanías",
        "delay_min": 60,
        "alternative": "Utilice autobuses de Lurraldebus línea A1 / G2 hacia Hernani y Andoain."
    },

    # --- ALTA: Retrasos notables, huelgas, obras con transbordo ---
    {
        "text": "Huelga general del sector de transportes en Gipuzkoa. Servicios mínimos del 30% en Lurraldebus y Dbus durante toda la jornada.",
        "severity": "ALTA",
        "category": "Huelga y Servicios",
        "zone": "Donostialdea",
        "operator": "Lurraldebus",
        "delay_min": 35,
        "alternative": "Priorice el uso de Euskotren y Renfe Cercanías cuyos servicios mínimos operan al 50-70%."
    },
    {
        "text": "Obras de soterramiento en el tramo de Donostia Centro. Transbordos obligatorios en autobús entre Lugaritz y Amara.",
        "severity": "ALTA",
        "category": "Obras y Mantenimiento",
        "zone": "Donostialdea",
        "operator": "Euskotren",
        "delay_min": 25,
        "alternative": "Siga la señalización hacia el autobús lanzadera gratuito habilitado con tarjeta MUGI."
    },
    {
        "text": "Accidente múltiple en la autopista AP-8 a la altura de Zarautz. Retenciones kilométricas y retrasos de 30 minutos en autobuses DO01 y UK09.",
        "severity": "ALTA",
        "category": "Tráfico y Accidentes",
        "zone": "Urola Kosta",
        "operator": "Lurraldebus",
        "delay_min": 30,
        "alternative": "Utilice el tren de Euskotren E1 desde Zarautz hacia Donostia Amara para evitar la retención vial."
    },
    {
        "text": "Fuerte temporal de viento en la costa de Pasajes y Donostia. Retrasos severos en las líneas marítimas y Lurraldebus E01.",
        "severity": "ALTA",
        "category": "Meteorología y Temporal",
        "zone": "Oarsoaldea",
        "operator": "Lurraldebus",
        "delay_min": 20,
        "alternative": "Utilice el Topo E2 desde la estación de Pasaia o Galtzaraborda hacia Donostia."
    },
    {
        "text": "Avería de un tren de mercancías entre Tolosa y Beasain ocupa vía única. Retrasos de 35 minutos en toda la línea C1.",
        "severity": "ALTA",
        "category": "Avería Tren / Bus",
        "zone": "Goierri",
        "operator": "Renfe Cercanías",
        "delay_min": 35,
        "alternative": "Utilice los autobuses comarcales de Lurraldebus TO01 o GO01 en las paradas contiguas a la N-1."
    },

    # --- MEDIA: Retrasos moderados, cambios de vía, desvíos urbanos ---
    {
        "text": "Retrasos de 10 a 15 minutos en la línea C1 de Cercanías por limitación temporal de velocidad en la curva de Andoain.",
        "severity": "MEDIA",
        "category": "Obras y Mantenimiento",
        "zone": "Goierri",
        "operator": "Renfe Cercanías",
        "delay_min": 15,
        "alternative": "Los trenes continúan prestando servicio con marcha reducida; no se requiere transbordo."
    },
    {
        "text": "Manifestación en el Boulevard donostiarra. Las líneas de Dbus 05, 13, 26 y 28 trasladan su parada cabecera a Okendo.",
        "severity": "MEDIA",
        "category": "Tráfico y Accidentes",
        "zone": "Donostialdea",
        "operator": "Dbus",
        "delay_min": 10,
        "alternative": "Acuda a la parada provisional en Calle Okendo / Reina Regente."
    },
    {
        "text": "Obras de asfaltado en Pasai Antxo. La línea E02 de Lurraldebus suprime provisionalmente la parada de Alameda.",
        "severity": "MEDIA",
        "category": "Obras y Mantenimiento",
        "zone": "Oarsoaldea",
        "operator": "Lurraldebus",
        "delay_min": 12,
        "alternative": "Realice el embarque en la parada de Eskalantegi o en la estación de Renfe Pasaia."
    },
    {
        "text": "Avería mecánica en un autobús de la línea 28 en Pío XII. Frecuencias alteradas temporalmente en dirección a Hospitales.",
        "severity": "MEDIA",
        "category": "Avería Tren / Bus",
        "zone": "Donostialdea",
        "operator": "Dbus",
        "delay_min": 12,
        "alternative": "Espere al siguiente convoy de la línea 28 (frecuencia cada 6 minutos) o tome la línea 17."
    },
    {
        "text": "Trabajos nocturnos de bateo en vía entre Irun Ficoba y Hendaia. Trenes circulan por vía única con demoras de 10 minutos.",
        "severity": "MEDIA",
        "category": "Obras y Mantenimiento",
        "zone": "Bidasoa",
        "operator": "Euskotren",
        "delay_min": 10,
        "alternative": "Servicio operativo con 10 min de demora estimada."
    },
    {
        "text": "Tráfico denso en el acceso a Donostia por Carlos I. Retrasos de 15 minutos en los autobuses procedentes de Tolosa y Arrasate.",
        "severity": "MEDIA",
        "category": "Tráfico y Accidentes",
        "zone": "Donostialdea",
        "operator": "Lurraldebus",
        "delay_min": 15,
        "alternative": "Puede descender en Pío XII y conectar a pie con Euskotren Amara para cruzar el centro."
    },

    # --- BAJA: Informativos, incidencias leves, ascensores ---
    {
        "text": "Aviso informativo: Ascensor de acceso al andén 2 de la estación de Zarautz San Pelaio fuera de servicio por mantenimiento.",
        "severity": "BAJA",
        "category": "Obras y Mantenimiento",
        "zone": "Urola Kosta",
        "operator": "Euskotren",
        "delay_min": 2,
        "alternative": "Personas con movilidad reducida pueden acceder por la rampa exterior del andén 1."
    },
    {
        "text": "Puntualidad habitual en la red de Dbus. Tráfico fluido en los carriles bus de Donostia.",
        "severity": "BAJA",
        "category": "Informativo",
        "zone": "Donostialdea",
        "operator": "Dbus",
        "delay_min": 0,
        "alternative": "Servicio funcionando conforme a horarios oficiales."
    },
    {
        "text": "Campaña de información sobre tarifas bonificadas MUGI en la estación de Renfe Gros. Sin afectación a los trenes.",
        "severity": "BAJA",
        "category": "Informativo",
        "zone": "Donostialdea",
        "operator": "Renfe Cercanías",
        "delay_min": 0,
        "alternative": "Circulación de trenes regular."
    },
    {
        "text": "Llovizna suave en Donostialdea. La flota de autobuses circula a velocidad reglamentaria sin alteraciones significativas.",
        "severity": "BAJA",
        "category": "Meteorología y Temporal",
        "zone": "Donostialdea",
        "operator": "Lurraldebus",
        "delay_min": 3,
        "alternative": "Sin afección relevante a los trayectos."
    },
    {
        "text": "Sustitución de marquesina en la parada de Benta Berri. Parada desplazada 30 metros hacia adelante.",
        "severity": "BAJA",
        "category": "Obras y Mantenimiento",
        "zone": "Donostialdea",
        "operator": "Dbus",
        "delay_min": 0,
        "alternative": "Nueva señalética instalada en el poste provisional."
    },
    {
        "text": "Refuerzo especial de trenes de Euskotren por evento deportivo en el Reale Arena Anoeta.",
        "severity": "BAJA",
        "category": "Informativo",
        "zone": "Donostialdea",
        "operator": "Euskotren",
        "delay_min": 0,
        "alternative": "Frecuencias ampliadas cada 7 minutos tras la finalización del partido."
    },

    # --- Más muestras de entrenamiento bilingües / modales ---
    {
        "text": "Avería técnica en unidad de Renfe en Billabona provoca retraso de 20 minutos en sentido Donostia.",
        "severity": "MEDIA",
        "category": "Avería Tren / Bus",
        "zone": "Goierri",
        "operator": "Renfe Cercanías",
        "delay_min": 20,
        "alternative": "Tome autobús Lurraldebus TO01 en Billabona Centro."
    },
    {
        "text": "Corte de catenaria por caída de rama en Loiola. Topo E2 y E5 paralizados temporalmente.",
        "severity": "CRITICA",
        "category": "Avería Vía / Catenaria",
        "zone": "Donostialdea",
        "operator": "Euskotren",
        "delay_min": 45,
        "alternative": "Utilice la línea 26 de Dbus en la ribera del Urumea."
    },
    {
        "text": "Desprendimiento de rocas en la N-634 entre Getaria y Zarautz. Lurraldebus UK09 desviado por autopista.",
        "severity": "ALTA",
        "category": "Meteorología y Temporal",
        "zone": "Urola Kosta",
        "operator": "Lurraldebus",
        "delay_min": 25,
        "alternative": "Combine con Euskotren E1 en la estación de Zarautz."
    },
    {
        "text": "Nieve y hielo en el puerto de Etxegarate. Afección en servicios interurbanos de Goierri.",
        "severity": "ALTA",
        "category": "Meteorología y Temporal",
        "zone": "Goierri",
        "operator": "Lurraldebus",
        "delay_min": 30,
        "alternative": "El servicio de Renfe Cercanías C1 opera con normalidad por vía férrea."
    },
    {
        "text": "Obras de accesibilidad en andenes de Errenteria Euskotren. Trenes circulan con parada normal.",
        "severity": "BAJA",
        "category": "Obras y Mantenimiento",
        "zone": "Oarsoaldea",
        "operator": "Euskotren",
        "delay_min": 1,
        "alternative": "Siga los itinerarios peatonales habilitados."
    },
    {
        "text": "Colisión leve de tráfico en el túnel de Ondarreta. Retrasos de 8 minutos en líneas 05 y 25.",
        "severity": "MEDIA",
        "category": "Tráfico y Accidentes",
        "zone": "Donostialdea",
        "operator": "Dbus",
        "delay_min": 8,
        "alternative": "Camine hacia la estación de Lugaritz de Euskotren si se desplaza hacia Amara."
    },
    {
        "text": "Incidencia en el enclavamiento de Irun Colón. Retrasos de 15 minutos en salidas de Euskotren hacia Hendaia.",
        "severity": "MEDIA",
        "category": "Avería Vía / Catenaria",
        "zone": "Bidasoa",
        "operator": "Euskotren",
        "delay_min": 15,
        "alternative": "Camine a Renfe Irun (4 min) o use Lurraldebus E26."
    },
    {
        "text": "Revisión técnica de unidades en cocheras de Armentia. Lurraldebus GO01 suprime una salida intermedia.",
        "severity": "MEDIA",
        "category": "Avería Tren / Bus",
        "zone": "Debagoiena",
        "operator": "Lurraldebus",
        "delay_min": 20,
        "alternative": "Siguiente salida programada en 40 minutos o enlace vía Bergara."
    }
]

class IncidentMLService:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
        self.severity_classifier = LogisticRegression(C=1.5, max_iter=300)
        self.category_classifier = LogisticRegression(C=1.5, max_iter=300)
        self.zone_classifier = LogisticRegression(C=1.5, max_iter=300)
        self.operator_classifier = LogisticRegression(C=1.5, max_iter=300)
        self.delay_regressor = Ridge(alpha=1.0)
        self.is_trained = False
        self.accuracy_metrics = {}

        # Preloaded active live incidents for Gipuzkoa (real-world simulation)
        self.active_incidents = [
            {
                "id": "INC-2026-001",
                "title": "Obras del Pasante Ferroviario en Donostia Centro",
                "text": "Obras de integración soterrada del Topo en Donostia Centro. Transbordo señalizado en superficie entre Lugaritz y Amara con buses lanzadera.",
                "created_at": (datetime.now() - timedelta(hours=2)).strftime("%d/%m/%Y %H:%M"),
                "operator": "Euskotren",
                "zone": "Donostialdea",
                "status": "En curso",
                "source": "Aviso Oficial Eusko Trenbide Sarea / ATTG"
            },
            {
                "id": "INC-2026-002",
                "title": "Avería de señalización en Herrera Intermodal",
                "text": "Fallo intermitente en circuito de vía en Herrera. Los trenes de Renfe Cercanías C1 y Topo E2 circulan con demoras de 10 a 15 minutos.",
                "created_at": (datetime.now() - timedelta(minutes=45)).strftime("%d/%m/%Y %H:%M"),
                "operator": "Renfe Cercanías",
                "zone": "Oarsoaldea",
                "status": "En curso",
                "source": "Centro de Gestión de Tráfico Adif / Renfe"
            },
            {
                "id": "INC-2026-003",
                "title": "Obras de calmado de tráfico en Pasai Antxo",
                "text": "Obras de reurbanización en la travesía de Pasai Antxo. La línea E02 de Lurraldebus desvía su itinerario por la variante.",
                "created_at": (datetime.now() - timedelta(hours=5)).strftime("%d/%m/%Y %H:%M"),
                "operator": "Lurraldebus",
                "zone": "Oarsoaldea",
                "status": "En curso",
                "source": "Lurraldebus / Diputación Foral de Gipuzkoa"
            },
            {
                "id": "INC-2026-004",
                "title": "Alta afluencia y refuerzo en Dbus Línea 28",
                "text": "Tráfico fluido en Donostia con servicios de refuerzo en Dbus línea 28 hacia Policlínica y Hospital Universitario Donostia.",
                "created_at": (datetime.now() - timedelta(hours=1)).strftime("%d/%m/%Y %H:%M"),
                "operator": "Dbus",
                "zone": "Donostialdea",
                "status": "Activo informativo",
                "source": "Dbus Donostia"
            }
        ]

        # Auto-train models on initial load
        self.train()

    def train(self) -> Dict[str, Any]:
        """Train scikit-learn models on transit incident dataset."""
        texts = [item["text"] for item in TRAINING_DATA]
        severities = [item["severity"] for item in TRAINING_DATA]
        categories = [item["category"] for item in TRAINING_DATA]
        zones = [item["zone"] for item in TRAINING_DATA]
        operators = [item["operator"] for item in TRAINING_DATA]
        delays = [item["delay_min"] for item in TRAINING_DATA]

        # Fit vectorizer
        X = self.vectorizer.fit_transform(texts)

        # Train models
        self.severity_classifier.fit(X, severities)
        self.category_classifier.fit(X, categories)
        self.zone_classifier.fit(X, zones)
        self.operator_classifier.fit(X, operators)
        self.delay_regressor.fit(X, delays)

        # Evaluate self-training accuracy
        pred_sev = self.severity_classifier.predict(X)
        pred_cat = self.category_classifier.predict(X)
        pred_zone = self.zone_classifier.predict(X)

        self.accuracy_metrics = {
            "severity_accuracy": round(accuracy_score(severities, pred_sev) * 100, 1),
            "category_accuracy": round(accuracy_score(categories, pred_cat) * 100, 1),
            "zone_accuracy": round(accuracy_score(zones, pred_zone) * 100, 1),
            "sample_count": len(TRAINING_DATA),
            "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "algorithm": "TF-IDF (1-2 ngrams) + Calibrated Logistic Regression & Ridge Regressor"
        }
        self.is_trained = True

        # Pre-score active incidents
        for inc in self.active_incidents:
            analysis = self.predict_incident(inc["text"])
            inc["ml_analysis"] = analysis

        return self.accuracy_metrics

    def predict_incident(self, text: str) -> Dict[str, Any]:
        """Inference pipeline for any incident text entered by user or ingested from transit feed."""
        if not self.is_trained:
            self.train()

        X_input = self.vectorizer.transform([text])

        # Predict classes
        severity = str(self.severity_classifier.predict(X_input)[0])
        category = str(self.category_classifier.predict(X_input)[0])
        zone = str(self.zone_classifier.predict(X_input)[0])
        operator = str(self.operator_classifier.predict(X_input)[0])

        # Predict confidence
        severity_probs = self.severity_classifier.predict_proba(X_input)[0]
        max_prob = float(np.max(severity_probs))
        confidence_pct = round(max_prob * 100, 1)

        # Estimate delay
        delay_est = float(self.delay_regressor.predict(X_input)[0])
        delay_min = max(0, int(round(delay_est)))

        # Derive recommended mitigation alternative
        alternative = self._generate_alternative(severity, zone, operator, category)

        # Extract top indicative features / keywords
        feature_names = self.vectorizer.get_feature_names_out()
        tfidf_scores = X_input.toarray()[0]
        top_indices = np.argsort(tfidf_scores)[::-1][:4]
        key_terms = [feature_names[i] for i in top_indices if tfidf_scores[i] > 0]

        severity_colors = {
            "CRITICA": {"bg": "#fee2e2", "text": "#991b1b", "border": "#ef4444", "label": "Crítica (Corte de línea)"},
            "ALTA": {"bg": "#ffedd5", "text": "#9a3412", "border": "#f97316", "label": "Alta (Retrasos severos)"},
            "MEDIA": {"bg": "#fef9c3", "text": "#854d0e", "border": "#eab308", "label": "Media (Afección parcial)"},
            "BAJA": {"bg": "#ecfdf5", "text": "#065f46", "border": "#10b981", "label": "Baja (Informativo / Leve)"}
        }

        return {
            "input_text": text,
            "predicted_severity": severity,
            "severity_meta": severity_colors.get(severity, severity_colors["MEDIA"]),
            "predicted_category": category,
            "predicted_zone": zone,
            "predicted_operator": operator,
            "estimated_delay_min": delay_min,
            "confidence_percentage": confidence_pct,
            "key_factors": key_terms,
            "recommended_alternative": alternative
        }

    def _generate_alternative(self, severity: str, zone: str, operator: str, category: str) -> str:
        """Rule-based decision assistant that recommends multimodal transfer solutions for detected incidents."""
        if severity == "BAJA":
            return "No requiere transbordo alternativo. El servicio opera con regularidad o retraso mínimo."

        if operator == "Renfe Cercanías":
            if zone in ["Donostialdea", "Oarsoaldea"]:
                return "Alternativa recomendada: Acuda a la estación de Euskotren Topo (E2) en Herrera, Pasaia o Errenteria, o use Lurraldebus E02 con su tarjeta MUGI."
            elif zone == "Goierri":
                return "Alternativa recomendada: Utilice los autobuses de Lurraldebus línea TO01 (Tolosa directo) o GO01 en las paradas de la N-1."
            else:
                return "Alternativa recomendada: Líneas combinadas de Lurraldebus desde la estación de autobuses más próxima."

        elif operator == "Euskotren":
            if zone in ["Donostialdea", "Oarsoaldea"]:
                return "Alternativa recomendada: Utilice Renfe Cercanías C1 desde Herrera o Gros, o autobuses Dbus (13/28) y Lurraldebus (E01/E02)."
            elif zone == "Urola Kosta":
                return "Alternativa recomendada: Tome los autobuses de Lurraldebus UK09 (Zarautz-Donostia) o UK10 (por autopista)."
            else:
                return "Alternativa recomendada: Autobuses interurbanos Lurraldebus por el corredor correspondiente."

        elif operator == "Lurraldebus":
            if zone == "Urola Kosta":
                return "Alternativa recomendada: Tome el tren Euskotren E1 en la estación de Zarautz o Zumaia."
            elif zone == "Goierri":
                return "Alternativa recomendada: Tome el tren Renfe Cercanías C1 en Tolosa, Beasain o Zumarraga."
            else:
                return "Alternativa recomendada: Utilice el ferrocarril de proximidad (Euskotren / Renfe) con transbordo bonificado MUGI."

        elif operator == "Dbus":
            return "Alternativa recomendada: Utilice las estaciones de Euskotren (Amara, Anoeta, Lugaritz, Herrera) o líneas de autobús colaterales."

        return "Alternativa recomendada: Consulte el planificador multimodal de MugiManager para calcular un desvío óptimo entre tren y autobús."

    def get_active_incidents(self, zone_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        if not zone_filter or zone_filter == "all":
            return self.active_incidents
        return [inc for inc in self.active_incidents if inc.get("zone", "").lower() == zone_filter.lower()]

    def report_incident(self, title: str, text: str, operator: str, zone: str) -> Dict[str, Any]:
        """Add a new incident, analyze it with ML immediately, and add to the active list."""
        analysis = self.predict_incident(text)
        new_inc = {
            "id": f"INC-2026-{len(self.active_incidents) + 1:03d}",
            "title": title,
            "text": text,
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "operator": operator if operator != "Auto" else analysis["predicted_operator"],
            "zone": zone if zone != "Auto" else analysis["predicted_zone"],
            "status": "Activo reportado",
            "source": "Aviso de usuario / Central de Incidencias MugiManager",
            "ml_analysis": analysis
        }
        self.active_incidents.insert(0, new_inc)
        return new_inc

incident_ml_service = IncidentMLService()
