"""
MugiManager - Integrated Public Transport Service
Unified Data & Routing for Gipuzkoa: Euskotren, Renfe Cercanías, Lurraldebus & Dbus
"""
from typing import Dict, List, Any, Optional
import heapq
import itertools
import math
import re
import urllib.parse

class TransportService:
    def __init__(self):
        self.operators = [
            {
                "id": "euskotren",
                "name": "Euskotren Trena",
                "type": "Trena (Ferrocarril)",
                "color": "#005baa",
                "badge_bg": "#e6f0fa",
                "badge_text": "#005baa",
                "description": "Líneas de ferrocarril metropolitano y regional (Topo y E1)."
            },
            {
                "id": "renfe",
                "name": "Renfe Cercanías",
                "type": "Trena (Ferrocarril)",
                "color": "#990033",
                "badge_bg": "#fae6ec",
                "badge_text": "#990033",
                "description": "Línea C-1 Irun - Donostia San Sebastián - Brinkola."
            },
            {
                "id": "lurraldebus",
                "name": "Lurraldebus",
                "type": "Autobusa (Interurbano)",
                "color": "#007a3d",
                "badge_bg": "#e6f5ed",
                "badge_text": "#007a3d",
                "description": "Red de autobuses interurbanos de la Diputación Foral de Gipuzkoa."
            },
            {
                "id": "dbus",
                "name": "Dbus",
                "type": "Autobusa (Urbano)",
                "color": "#0082c9",
                "badge_bg": "#e6f4fc",
                "badge_text": "#0082c9",
                "description": "Compañía del Tranvía de San Sebastián (Servicio urbano de Donostia)."
            },
            {
                "id": "metrobilbao",
                "name": "Metro Bilbao",
                "type": "Metro",
                "color": "#e2231a",
                "badge_bg": "#fdeceb",
                "badge_text": "#b71c14",
                "description": "Líneas L1 y L2 del metro de Bilbao (interoperable con MUGI)."
            },
            {
                "id": "bizkaibus",
                "name": "Bizkaibus",
                "type": "Autobusa (Interurbano)",
                "color": "#5f8f1f",
                "badge_bg": "#eef5e4",
                "badge_text": "#4a7016",
                "description": "Autobuses interurbanos de Bizkaia (interoperable con MUGI)."
            }
        ]

        # Intermodal Transfer Hubs in Gipuzkoa
        self.transfer_hubs = [
            {
                "id": "hub-donostia-atotxa",
                "name": "Donostia Intermodal (Estación del Norte Atotxa / Bus Geltokia)",
                "municipality": "Donostia / San Sebastián",
                "description": "Enlace subterráneo directo (1 min) entre Renfe Cercanías C-1, Estación Central de Lurraldebus y líneas de Dbus (17, 37, 45).",
                "operators": ["renfe", "lurraldebus", "dbus"],
                "walk_transfer_min": 2,
                "amenities": ["Puntos de recarga MUGI", "Accesibilidad PMR ascensor", "Aseos", "Información turística"]
            },
            {
                "id": "hub-donostia-amara",
                "name": "Donostia Amara (Easo Euskotren / Pío XII / Centelles)",
                "municipality": "Donostia / San Sebastián",
                "description": "Estación término de Euskotren (E1, E2 Topo, E5) con parada inmediata de Dbus (5, 21, 28) y líneas Lurraldebus a Tolosaldea y Goierri.",
                "operators": ["euskotren", "dbus", "lurraldebus"],
                "walk_transfer_min": 3,
                "amenities": ["Puntos de recarga MUGI", "Taquillas Euskotren", "Aseos"]
            },
            {
                "id": "hub-herrera",
                "name": "Herrera Intermodal",
                "municipality": "Donostia / San Sebastián",
                "description": "Nodo multimodal que une andenes de Renfe C-1, Euskotren E2/E5 Topo y paradas de Lurraldebus (E02) y Dbus (13, 27).",
                "operators": ["euskotren", "renfe", "lurraldebus", "dbus"],
                "walk_transfer_min": 2,
                "amenities": ["Pasarela directa adaptada", "Validadoras MUGI en ambos andenes"]
            },
            {
                "id": "hub-irun-colon",
                "name": "Irun Centro (Renfe Colón / Ficoba Euskotren / Paseo Colón Bus)",
                "municipality": "Irun",
                "description": "Conexión entre trenes de Cercanías Renfe, Topo Euskotren y autobuses Lurraldebus (E20, E24, E26).",
                "operators": ["renfe", "euskotren", "lurraldebus"],
                "walk_transfer_min": 4,
                "amenities": ["Venta y recarga MUGI", "Accesible PMR"]
            },
            {
                "id": "hub-tolosa",
                "name": "Tolosa Geltokia (Renfe / Rondilla Lurraldebus)",
                "municipality": "Tolosa",
                "description": "Enlace entre Cercanías Renfe C-1 y los servicios Lurraldebus TO01, TO02 y comarcales de Tolosaldea.",
                "operators": ["renfe", "lurraldebus"],
                "walk_transfer_min": 3,
                "amenities": ["Punto de recarga MUGI"]
            },
            {
                "id": "hub-zarautz",
                "name": "Zarautz San Pelaio (Euskotren / N-634 Lurraldebus)",
                "municipality": "Zarautz",
                "description": "Conexión directa entre trenes E1 Donostia-Bilbo y las líneas UK09 y UK10 de Lurraldebus hacia Donostia y Urola Kosta.",
                "operators": ["euskotren", "lurraldebus"],
                "walk_transfer_min": 2,
                "amenities": ["Validadoras MUGI"]
            }
        ]

        # Lines Catalog (Bus and Train together)
        self.lines = [
            # --- EUSKOTREN ---
            {
                "id": "E2",
                "operator_id": "euskotren",
                "operator_name": "Euskotren Trena",
                "mode": "Tren",
                "code": "E2",
                "name": "E2 Lasarte-Oria - Donostia Amara - Hendaia (El Topo)",
                "origin": "Lasarte-Oria",
                "destination": "Hendaia",
                "frequency": "Cada 15 min (laborables) / 30 min (festivos)",
                "hours": "05:45 - 23:15 (Servicio nocturno fines de semana)",
                "stops": [
                    "Lasarte-Oria", "Errekalde", "Añorga", "Lugaritz", "Amara (Donostia)",
                    "Anoeta", "Loiola", "Herrera", "Pasaia (Euskotren)", "Galtzaraborda",
                    "Errenteria (Euskotren)", "Fanderia", "Oiartzun (Euskotren)",
                    "Irun Belaskoenea", "Irun Colon", "Irun Ficoba", "Hendaia"
                ]
            },
            {
                "id": "E1",
                "operator_id": "euskotren",
                "operator_name": "Euskotren Trena",
                "mode": "Tren",
                "code": "E1",
                "name": "E1 Donostia Amara - Zarautz - Zumaia - Eibar - Matiko (Bilbao)",
                "origin": "Donostia Amara",
                "destination": "Bilbao Matiko",
                "frequency": "Cada 30 min (Donostia-Zumaia) / Cada 60 min (Donostia-Bilbao)",
                "hours": "06:00 - 22:30",
                "stops": [
                    "Amara (Donostia)", "Lugaritz", "Añorga", "Usurbil", "Aia-Orio",
                    "Zarautz San Pelaio", "Zarautz", "Zumaia", "Arroa-Zestoa", "Deba",
                    "Mendaro", "Altzola", "Elgoibar", "Toletxegain", "Eibar", "Ermua",
                    "Zaldibar", "Berriz", "Durango", "Amorebieta", "Lemoa", "Usansolo",
                    "Galdakao", "Kukullaga (Etxebarri)", "Otxarkoaga", "Txurdinaga",
                    "Zurbaranbarri", "Zazpikaleak / Casco Viejo", "Uribarri", "Bilbao Matiko"
                ]
            },
            {
                "id": "E5",
                "operator_id": "euskotren",
                "operator_name": "Euskotren Trena",
                "mode": "Tren",
                "code": "E5",
                "name": "E5 Donostia Amara - Herrera - Altza",
                "origin": "Amara (Donostia)",
                "destination": "Altza",
                "frequency": "Cada 15 min",
                "hours": "06:10 - 22:50",
                "stops": [
                    "Amara (Donostia)", "Anoeta", "Loiola", "Herrera", "Altza"
                ]
            },

            # --- RENFE CERCANÍAS ---
            {
                "id": "C1",
                "operator_id": "renfe",
                "operator_name": "Renfe Cercanías",
                "mode": "Tren",
                "code": "C-1",
                "name": "C-1 Irun - Donostia San Sebastián - Tolosa - Brinkola",
                "origin": "Irun",
                "destination": "Brinkola",
                "frequency": "Cada 15-20 min (Tramo Irun-Tolosa) / Cada 30-60 min (Brinkola)",
                "hours": "05:30 - 23:00",
                "stops": [
                    "Irun (Renfe)", "Ventas de Irun", "Lezo-Errenteria", "Pasaia (Renfe)",
                    "Herrera (Renfe)", "Ategorrieta", "Gros", "Donostia San Sebastián (Atotxa)",
                    "Loiola (Renfe)", "Martutene", "Hernani Centro", "Hernani", "Urnieta",
                    "Andoain Centro", "Andoain", "Billabona-Zizurkil", "Anoeta (Renfe)",
                    "Tolosa Centro", "Tolosa", "Alegia", "Ikaztegieta", "Legorreta",
                    "Itsasondo", "Ordizia", "Beasain", "Ormaiztegi", "Zumarraga", "Legazpi", "Brinkola"
                ]
            },

            # --- LURRALDEBUS ---
            {
                "id": "E01",
                "operator_id": "lurraldebus",
                "operator_name": "Lurraldebus",
                "mode": "Autobús",
                "code": "E01",
                "name": "E01 Pasai Donibane - Lezo - Errenteria - Donostia",
                "origin": "Pasai Donibane",
                "destination": "Donostia (Gipuzkoa Plaza)",
                "frequency": "Cada 20 min",
                "hours": "06:15 - 22:45",
                "stops": [
                    "Pasai Donibane (Bidebieta)", "Lezo Renfe", "Errenteria Centro",
                    "Pasai Antxo", "Trintxerpe", "Donostia Miracruz", "Donostia (Gipuzkoa Plaza)"
                ]
            },
            {
                "id": "E02",
                "operator_id": "lurraldebus",
                "operator_name": "Lurraldebus",
                "mode": "Autobús",
                "code": "E02",
                "name": "E02 Oiartzun - Errenteria - Pasai Antxo - Donostia",
                "origin": "Oiartzun Centro",
                "destination": "Donostia (Gipuzkoa Plaza)",
                "frequency": "Cada 20 min",
                "hours": "06:00 - 23:00",
                "stops": [
                    "Oiartzun Centro", "Fanderia", "Errenteria Centro",
                    "Herrera", "Bidebieta", "Donostia Estación Autobuses (Atotxa)", "Donostia (Gipuzkoa Plaza)"
                ]
            },
            {
                "id": "UK09",
                "operator_id": "lurraldebus",
                "operator_name": "Lurraldebus",
                "mode": "Autobús",
                "code": "UK09",
                "name": "UK09 Zumaia - Getaria - Zarautz - Orio - Usurbil - Donostia",
                "origin": "Zumaia Estación",
                "destination": "Donostia Estación Autobuses",
                "frequency": "Cada 30 min",
                "hours": "06:20 - 22:20",
                "stops": [
                    "Zumaia Estación", "Getaria", "Zarautz San Pelaio", "Orio", "Usurbil",
                    "Donostia Antiguo (Zumalakarregi)", "Donostia Estación Autobuses (Atotxa)"
                ]
            },
            {
                "id": "TO01",
                "operator_id": "lurraldebus",
                "operator_name": "Lurraldebus",
                "mode": "Autobús",
                "code": "TO01",
                "name": "TO01 Tolosa - Andoain - Donostia (Directo N-1)",
                "origin": "Tolosa Geltokia",
                "destination": "Donostia Estación Autobuses",
                "frequency": "Cada 30 min",
                "hours": "06:15 - 22:30",
                "stops": [
                    "Tolosa Geltokia", "Andoain", "Donostia Pio XII", "Donostia Estación Autobuses (Atotxa)"
                ]
            },
            {
                "id": "GO01",
                "operator_id": "lurraldebus",
                "operator_name": "Lurraldebus",
                "mode": "Autobús",
                "code": "GO01",
                "name": "GO01 Arrasate / Mondragón - Oñati - Bergara - Donostia",
                "origin": "Arrasate Garibai",
                "destination": "Donostia Estación Autobuses",
                "frequency": "Cada 60 min",
                "hours": "06:30 - 21:30",
                "stops": [
                    "Arrasate Garibai", "Oñati", "Bergara", "Donostia Pio XII", "Donostia Estación Autobuses (Atotxa)"
                ]
            },
            {
                "id": "DO01",
                "operator_id": "lurraldebus",
                "operator_name": "Lurraldebus",
                "mode": "Autobús",
                "code": "DO01",
                "name": "DO01 Donostia - Bilbao Intermodal (Autopista AP-8 Directo)",
                "origin": "Donostia Estación Autobuses",
                "destination": "Bilbao Intermodal",
                "frequency": "Cada 30-60 min",
                "hours": "06:00 - 22:30",
                "speed_kmh": 75,
                "stops": [
                    "Donostia Estación Autobuses (Atotxa)", "Zarautz Bomberos (enlace)", "Bilbao Intermodal (Gurtubay)"
                ]
            },

            # --- DBUS (DONOSTIA) ---
            {
                "id": "D28",
                "operator_id": "dbus",
                "operator_name": "Dbus",
                "mode": "Autobús",
                "code": "28",
                "name": "28 Amara - Ospitaleak / Miramon",
                "origin": "Boulevard (Donostia)",
                "destination": "Miramon / Hospitales",
                "frequency": "Cada 6 - 8 min (Alta frecuencia)",
                "hours": "06:30 - 23:30",
                "stops": [
                    "Boulevard (Donostia)", "San Martín", "Amara (Pío XII / Euskotren)",
                    "Anoeta (Estadio)", "Hospital Donostia", "Policlínica Gipuzkoa", "Miramon Teknologia Parkea"
                ]
            },
            {
                "id": "D05",
                "operator_id": "dbus",
                "operator_name": "Dbus",
                "mode": "Autobús",
                "code": "05",
                "name": "05 Benta Berri",
                "origin": "Boulevard (Donostia)",
                "destination": "Erregenea / Benta Berri",
                "frequency": "Cada 8 - 10 min",
                "hours": "06:45 - 23:15",
                "stops": [
                    "Boulevard (Donostia)", "Askatasuna", "San Martín", "La Concha",
                    "Antiguo (Zumalakarregi)", "Benta Berri (Resurrección María de Azkue)"
                ]
            },
            {
                "id": "D13",
                "operator_id": "dbus",
                "operator_name": "Dbus",
                "mode": "Autobús",
                "code": "13",
                "name": "13 Altza - Boulevard",
                "origin": "Boulevard (Donostia)",
                "destination": "Altza (Larratxo)",
                "frequency": "Cada 6 - 8 min",
                "hours": "06:15 - 23:45",
                "stops": [
                    "Boulevard (Donostia)", "Gros (Gran Vía)", "Ategorrieta", "Miracruz",
                    "Herrera", "Altza", "Larratxo"
                ]
            },
            {
                "id": "D26",
                "operator_id": "dbus",
                "operator_name": "Dbus",
                "mode": "Autobús",
                "code": "26",
                "name": "26 Amara - Martutene",
                "origin": "Boulevard (Donostia)",
                "destination": "Martutene",
                "frequency": "Cada 15 min",
                "hours": "06:30 - 22:45",
                "stops": [
                    "Boulevard (Donostia)", "Amara (Pío XII / Euskotren)", "Loiola (Ribera)", "Txomin Enea", "Martutene"
                ]
            },

            # --- METRO BILBAO ---
            {
                "id": "ML1",
                "operator_id": "metrobilbao",
                "operator_name": "Metro Bilbao",
                "mode": "Metro",
                "code": "L1",
                "name": "L1 Etxebarri - Bilbao - Getxo - Plentzia",
                "origin": "Etxebarri",
                "destination": "Plentzia",
                "frequency": "Cada 5 min (tramo común) / Cada 15 min (Plentzia)",
                "hours": "06:00 - 23:00 (nocturno fines de semana)",
                "stops": [
                    "Etxebarri", "Bolueta", "Santutxu", "Zazpikaleak / Casco Viejo", "Abando",
                    "Moyua", "Indautxu", "San Mamés", "Deusto", "Sarriko", "San Inazio",
                    "Erandio", "Leioa", "Areeta", "Algorta", "Plentzia"
                ]
            },
            {
                "id": "ML2",
                "operator_id": "metrobilbao",
                "operator_name": "Metro Bilbao",
                "mode": "Metro",
                "code": "L2",
                "name": "L2 Basauri - Bilbao - Barakaldo - Santurtzi - Kabiezes",
                "origin": "Basauri",
                "destination": "Kabiezes",
                "frequency": "Cada 5 min (tramo común) / Cada 10 min",
                "hours": "06:00 - 23:00 (nocturno fines de semana)",
                "stops": [
                    "Basauri", "Ariz", "Etxebarri", "Bolueta", "Santutxu", "Zazpikaleak / Casco Viejo",
                    "Abando", "Moyua", "Indautxu", "San Mamés", "Deusto", "Sarriko", "San Inazio",
                    "Barakaldo", "Sestao", "Portugalete", "Santurtzi", "Kabiezes"
                ]
            },

            # --- BIZKAIBUS ---
            {
                "id": "A3247",
                "operator_id": "bizkaibus",
                "operator_name": "Bizkaibus",
                "mode": "Autobús",
                "code": "A3247",
                "name": "A3247 Bilbao (Termibus) - Aeropuerto",
                "origin": "Bilbao Intermodal (Gurtubay)",
                "destination": "Bilbao Aeropuerto (Loiu)",
                "frequency": "Cada 15-20 min",
                "hours": "05:20 - 00:00",
                "speed_kmh": 40,
                "stops": [
                    "Bilbao Intermodal (Gurtubay)", "Moyua (Bizkaibus)", "Bilbao Aeropuerto (Loiu)"
                ]
            }
        ]

        # Build index of all unique stops and the lines passing through them
        self._build_stop_index()
        self._prepare_routing()

    STOP_METADATA = {
        # Donostia / San Sebastián
        "Amara (Donostia)": {"address": "Plaza Easo s/n", "municipality": "Donostia / San Sebastián", "lat": 43.3138, "lng": -1.9818},
        "Donostia San Sebastián (Atotxa)": {"address": "Paseo de Francia 22 (Estación del Norte)", "municipality": "Donostia / San Sebastián", "lat": 43.3175, "lng": -1.9774},
        "Donostia Estación Autobuses (Atotxa)": {"address": "Paseo Federico García Lorca 1", "municipality": "Donostia / San Sebastián", "lat": 43.3168, "lng": -1.9765},
        "Donostia (Gipuzkoa Plaza)": {"address": "Plaza de Gipuzkoa", "municipality": "Donostia / San Sebastián", "lat": 43.3218, "lng": -1.9830},
        "Boulevard (Donostia)": {"address": "Alameda del Boulevard", "municipality": "Donostia / San Sebastián", "lat": 43.3225, "lng": -1.9825},
        "Amara (Pío XII / Euskotren)": {"address": "Plaza Pío XII 1", "municipality": "Donostia / San Sebastián", "lat": 43.3085, "lng": -1.9805},
        "Donostia Pio XII": {"address": "Plaza Pío XII 1", "municipality": "Donostia / San Sebastián", "lat": 43.3085, "lng": -1.9805},
        "Herrera": {"address": "Plaza de Herrera / Paseo de Herrera", "municipality": "Donostia / San Sebastián", "lat": 43.3179, "lng": -1.9365},
        "Herrera (Renfe)": {"address": "Paseo de Herrera (Andén Renfe)", "municipality": "Donostia / San Sebastián", "lat": 43.3182, "lng": -1.9360},
        "Anoeta": {"address": "Paseo de Anoeta s/n (Junto al Reale Arena)", "municipality": "Donostia / San Sebastián", "lat": 43.3015, "lng": -1.9740},
        "Anoeta (Estadio)": {"address": "Paseo de Anoeta s/n", "municipality": "Donostia / San Sebastián", "lat": 43.3015, "lng": -1.9740},
        "Loiola": {"address": "Sierra de Aralar Kalea", "municipality": "Donostia / San Sebastián", "lat": 43.3056, "lng": -1.9612},
        "Loiola (Renfe)": {"address": "Camino de Uba / Loiola", "municipality": "Donostia / San Sebastián", "lat": 43.3060, "lng": -1.9610},
        "Loiola (Ribera)": {"address": "Travesía de Loiola 14", "municipality": "Donostia / San Sebastián", "lat": 43.3070, "lng": -1.9620},
        "Gros": {"address": "Calle Iparraguirre / Zurriola", "municipality": "Donostia / San Sebastián", "lat": 43.3222, "lng": -1.9735},
        "Ategorrieta": {"address": "Avenida de Navarra / Ategorrieta", "municipality": "Donostia / San Sebastián", "lat": 43.3235, "lng": -1.9615},
        "Lugaritz": {"address": "Lugaritz Pasealekua 21", "municipality": "Donostia / San Sebastián", "lat": 43.3075, "lng": -2.0040},
        "Añorga": {"address": "Añorga Txiki Kalea", "municipality": "Donostia / San Sebastián", "lat": 43.2925, "lng": -2.0055},
        "Errekalde": {"address": "Errekalde Hiribidea", "municipality": "Donostia / San Sebastián", "lat": 43.2785, "lng": -2.0125},
        "Altza": {"address": "Santa Bárbara Pasealekua, Altza", "municipality": "Donostia / San Sebastián", "lat": 43.3195, "lng": -1.9285},
        "Martutene": {"address": "Paseo de Martutene 45", "municipality": "Donostia / San Sebastián", "lat": 43.2965, "lng": -1.9565},
        "Hospital Donostia": {"address": "Paseo Dr. Beguiristain 115", "municipality": "Donostia / San Sebastián", "lat": 43.2935, "lng": -1.9765},
        "Policlínica Gipuzkoa": {"address": "Paseo de Miramon 174", "municipality": "Donostia / San Sebastián", "lat": 43.2915, "lng": -1.9745},
        "Miramon Teknologia Parkea": {"address": "Mikeletegi Pasealekua 53", "municipality": "Donostia / San Sebastián", "lat": 43.2895, "lng": -1.9715},
        "Benta Berri (Resurrección María de Azkue)": {"address": "Calle Resurrección María de Azkue 8", "municipality": "Donostia / San Sebastián", "lat": 43.3115, "lng": -2.0065},
        "Donostia Antiguo (Zumalakarregi)": {"address": "Avenida de Zumalakarregi 15", "municipality": "Donostia / San Sebastián", "lat": 43.3145, "lng": -2.0015},
        "Donostia Miracruz": {"address": "Calle Miracruz 38", "municipality": "Donostia / San Sebastián", "lat": 43.3210, "lng": -1.9710},
        "Bidebieta": {"address": "Juan XXIII Pasealekua, Bidebieta", "municipality": "Donostia / San Sebastián", "lat": 43.3215, "lng": -1.9425},
        "Trintxerpe": {"address": "Euskadi Etorbidea 22, Trintxerpe", "municipality": "Pasaia", "lat": 43.3235, "lng": -1.9295},
        "San Martín": {"address": "Calle San Martín 32", "municipality": "Donostia / San Sebastián", "lat": 43.3175, "lng": -1.9845},
        "Txomin Enea": {"address": "Paseo de Antzieta / Txomin", "municipality": "Donostia / San Sebastián", "lat": 43.3035, "lng": -1.9585},
        # Irun / Hondarribia / Hendaia
        "Irun (Renfe)": {"address": "Estación de Tren, Paseo de Colón", "municipality": "Irun", "lat": 43.3382, "lng": -1.7915},
        "Irun Colon": {"address": "Paseo de Colón 52 (Topo)", "municipality": "Irun", "lat": 43.3395, "lng": -1.7910},
        "Irun Belaskoenea": {"address": "Calle Aduana / Belaskoenea", "municipality": "Irun", "lat": 43.3345, "lng": -1.8025},
        "Irun Ficoba": {"address": "Avenida Iparralde / Ficoba", "municipality": "Irun", "lat": 43.3485, "lng": -1.7825},
        "Ventas de Irun": {"address": "Barrio Ventas de Irun", "municipality": "Irun", "lat": 43.3285, "lng": -1.8155},
        "Hendaia": {"address": "Place de la Gare, Hendaye", "municipality": "Hendaia", "lat": 43.3533, "lng": -1.7744},
        # Oarsoaldea
        "Errenteria (Euskotren)": {"address": "Biteri Kalea s/n", "municipality": "Errenteria", "lat": 43.3115, "lng": -1.8995},
        "Errenteria Centro": {"address": "Avenida de Navarra / Alameda", "municipality": "Errenteria", "lat": 43.3125, "lng": -1.9015},
        "Galtzaraborda": {"address": "Galtzaraborda Hiribidea", "municipality": "Errenteria", "lat": 43.3135, "lng": -1.9125},
        "Fanderia": {"address": "Fanderia Pasealekua", "municipality": "Errenteria", "lat": 43.3085, "lng": -1.8925},
        "Lezo-Errenteria": {"address": "Estación Renfe Lezo-Errenteria", "municipality": "Lezo", "lat": 43.3185, "lng": -1.8995},
        "Lezo Renfe": {"address": "Jauregi Kalea, Lezo", "municipality": "Lezo", "lat": 43.3190, "lng": -1.8990},
        "Pasaia (Euskotren)": {"address": "Eskalantegi Kalea (Andén Topo)", "municipality": "Pasaia", "lat": 43.3175, "lng": -1.9215},
        "Pasaia (Renfe)": {"address": "Geltoki Kalea (Andén Renfe)", "municipality": "Pasaia", "lat": 43.3180, "lng": -1.9220},
        "Pasai Antxo": {"address": "Gure Zumardia, Pasai Antxo", "municipality": "Pasaia", "lat": 43.3170, "lng": -1.9210},
        "Pasai Donibane (Bidebieta)": {"address": "Donibane Kalea, Pasai Donibane", "municipality": "Pasaia", "lat": 43.3275, "lng": -1.9160},
        "Oiartzun (Euskotren)": {"address": "Arragua Auzoa", "municipality": "Oiartzun", "lat": 43.3055, "lng": -1.8795},
        "Oiartzun Centro": {"address": "Rafael Picabea Hiribidea / Altzibar", "municipality": "Oiartzun", "lat": 43.2985, "lng": -1.8615},
        # Urola Kosta
        "Zarautz": {"address": "Lapurdi Kalea 15", "municipality": "Zarautz", "lat": 43.2845, "lng": -2.1685},
        "Zarautz San Pelaio": {"address": "Nafarroa Kalea / San Pelaio", "municipality": "Zarautz", "lat": 43.2865, "lng": -2.1615},
        "Zarautz Bomberos (enlace)": {"address": "Autovía del Cantábrico AP-8 Enlace", "municipality": "Zarautz", "lat": 43.2795, "lng": -2.1680},
        "Zumaia": {"address": "Estazioko Bidea s/n", "municipality": "Zumaia", "lat": 43.2945, "lng": -2.2530},
        "Zumaia Estación": {"address": "Estazioko Bidea s/n (Euskotren & Bus)", "municipality": "Zumaia", "lat": 43.2945, "lng": -2.2530},
        "Getaria": {"address": "Sahatsaga Kalea (Puerto / Centro)", "municipality": "Getaria", "lat": 43.3035, "lng": -2.2045},
        "Aia-Orio": {"address": "Estación de Aia-Orio", "municipality": "Orio", "lat": 43.2765, "lng": -2.1265},
        "Orio": {"address": "Abaromendi Kalea, Orio", "municipality": "Orio", "lat": 43.2790, "lng": -2.1280},
        "Usurbil": {"address": "San Esteban Auzoa / Estación", "municipality": "Usurbil", "lat": 43.2725, "lng": -2.0465},
        "Lasarte-Oria": {"address": "Geltoki Kalea 4", "municipality": "Lasarte-Oria", "lat": 43.2685, "lng": -2.0195},
        # Tolosaldea & Goierri
        "Hernani": {"address": "Elkano Kalea / Geltokia", "municipality": "Hernani", "lat": 43.2675, "lng": -1.9765},
        "Hernani Centro": {"address": "Zinkoenea Plaza, Hernani", "municipality": "Hernani", "lat": 43.2645, "lng": -1.9775},
        "Urnieta": {"address": "Idiazabal Kalea, Urnieta", "municipality": "Urnieta", "lat": 43.2465, "lng": -1.9965},
        "Andoain": {"address": "Ama Kandida Hiribidea", "municipality": "Andoain", "lat": 43.2215, "lng": -2.0185},
        "Andoain Centro": {"address": "Kale Berria 38, Andoain", "municipality": "Andoain", "lat": 43.2185, "lng": -2.0210},
        "Billabona-Zizurkil": {"address": "Geltoki Kalea, Villabona-Zizurkil", "municipality": "Villabona", "lat": 43.1875, "lng": -2.0525},
        "Anoeta (Renfe)": {"address": "Estación de Anoeta (Tolosa)", "municipality": "Anoeta", "lat": 43.1615, "lng": -2.0695},
        "Tolosa": {"address": "Geltoki Plaza s/n", "municipality": "Tolosa", "lat": 43.1365, "lng": -2.0745},
        "Tolosa Centro": {"address": "Rondilla Kalea 34", "municipality": "Tolosa", "lat": 43.1385, "lng": -2.0725},
        "Tolosa Geltokia": {"address": "Plaza de la Estación Renfe", "municipality": "Tolosa", "lat": 43.1365, "lng": -2.0745},
        "Ordizia": {"address": "Geltoki Kalea, Ordizia", "municipality": "Ordizia", "lat": 43.0565, "lng": -2.1785},
        "Beasain": {"address": "Kale Nagusia / Geltokia", "municipality": "Beasain", "lat": 43.0475, "lng": -2.1985},
        "Ormaiztegi": {"address": "Geltoki Bidea, Ormaiztegi", "municipality": "Ormaiztegi", "lat": 43.0425, "lng": -2.2535},
        "Zumarraga": {"address": "Antziola Auzoa / Renfe", "municipality": "Zumarraga", "lat": 43.0885, "lng": -2.3145},
        "Legazpi": {"address": "Geltoki Kalea, Legazpi", "municipality": "Legazpi", "lat": 43.0545, "lng": -2.3365},
        "Brinkola": {"address": "Brinkola Auzoa, Legazpi", "municipality": "Legazpi", "lat": 43.0235, "lng": -2.3485},
        # Debabarrena & Alto Deba
        "Deba": {"address": "Hondartza Pasealekua, Deba", "municipality": "Deba", "lat": 43.2955, "lng": -2.3525},
        "Mendaro": {"address": "Mendarozabal, Mendaro", "municipality": "Mendaro", "lat": 43.2555, "lng": -2.3845},
        "Elgoibar": {"address": "Santa Ana Kalea, Elgoibar", "municipality": "Elgoibar", "lat": 43.2145, "lng": -2.4135},
        "Eibar": {"address": "Estaziño Kalea 1", "municipality": "Eibar", "lat": 43.1845, "lng": -2.4675},
        "Arrasate Garibai": {"address": "Garibai Hiribidea, Arrasate", "municipality": "Arrasate / Mondragón", "lat": 43.0645, "lng": -2.4925},
        "Oñati": {"address": "Posta Kalea, Oñati", "municipality": "Oñati", "lat": 43.0335, "lng": -2.4145},
        "Bergara": {"address": "Ibargarai Hiribidea, Bergara", "municipality": "Bergara", "lat": 43.1175, "lng": -2.4115},
        "Bilbao Intermodal (Gurtubay)": {"address": "Gurtubay Kalea 1 (Termibus)", "municipality": "Bilbao", "lat": 43.2605, "lng": -2.9495},
        "Bilbao Matiko": {"address": "Tiboli Kalea 24 (Matiko)", "municipality": "Bilbao", "lat": 43.2715, "lng": -2.9285},
        "Arroa-Zestoa": {"address": "Estación de Arroa", "municipality": "Zestoa", "lat": 43.2880, "lng": -2.2970},
        "Altzola": {"address": "Apeadero de Altzola", "municipality": "Elgoibar", "lat": 43.2295, "lng": -2.4025},
        "Toletxegain": {"address": "Apeadero de Toletxegain", "municipality": "Elgoibar", "lat": 43.2045, "lng": -2.4335},
        "Alegia": {"address": "Estación de Alegia", "municipality": "Alegia", "lat": 43.1015, "lng": -2.0975},
        "Ikaztegieta": {"address": "Estación de Ikaztegieta", "municipality": "Ikaztegieta", "lat": 43.0935, "lng": -2.1225},
        "Legorreta": {"address": "Estación de Legorreta", "municipality": "Legorreta", "lat": 43.0855, "lng": -2.1475},
        "Itsasondo": {"address": "Estación de Itsasondo", "municipality": "Itsasondo", "lat": 43.0695, "lng": -2.1665},
        "Askatasuna": {"address": "Askatasunaren Hiribidea", "municipality": "Donostia / San Sebastián", "lat": 43.3195, "lng": -1.9850},
        "La Concha": {"address": "Paseo de La Concha", "municipality": "Donostia / San Sebastián", "lat": 43.3165, "lng": -1.9905},
        "Antiguo (Zumalakarregi)": {"address": "Avenida de Zumalakarregi 15", "municipality": "Donostia / San Sebastián", "lat": 43.3145, "lng": -2.0015},
        "Gros (Gran Vía)": {"address": "Gran Vía, Gros", "municipality": "Donostia / San Sebastián", "lat": 43.3240, "lng": -1.9760},
        "Miracruz": {"address": "Calle Miracruz 38", "municipality": "Donostia / San Sebastián", "lat": 43.3210, "lng": -1.9710},
        "Larratxo": {"address": "Larratxo Pasealekua, Altza", "municipality": "Donostia / San Sebastián", "lat": 43.3135, "lng": -1.9285},
        # Durangaldea / Bizkaia (E1)
        "Ermua": {"address": "Estación de Ermua", "municipality": "Ermua", "lat": 43.1855, "lng": -2.4995},
        "Zaldibar": {"address": "Estación de Zaldibar", "municipality": "Zaldibar", "lat": 43.1705, "lng": -2.5455},
        "Berriz": {"address": "Estación de Berriz", "municipality": "Berriz", "lat": 43.1745, "lng": -2.5765},
        "Durango": {"address": "Estación de Durango (Intermodal)", "municipality": "Durango", "lat": 43.1700, "lng": -2.6335},
        "Amorebieta": {"address": "Estación de Amorebieta", "municipality": "Amorebieta-Etxano", "lat": 43.2195, "lng": -2.7335},
        "Lemoa": {"address": "Estación de Lemoa", "municipality": "Lemoa", "lat": 43.2095, "lng": -2.7745},
        "Usansolo": {"address": "Estación de Usansolo", "municipality": "Galdakao", "lat": 43.2185, "lng": -2.8165},
        "Galdakao": {"address": "Estación de Galdakao", "municipality": "Galdakao", "lat": 43.2305, "lng": -2.8435},
        "Kukullaga (Etxebarri)": {"address": "Estación Euskotren Kukullaga", "municipality": "Etxebarri", "lat": 43.2475, "lng": -2.8855},
        "Otxarkoaga": {"address": "Estación Euskotren Otxarkoaga", "municipality": "Bilbao", "lat": 43.2560, "lng": -2.8945},
        "Txurdinaga": {"address": "Estación Euskotren Txurdinaga", "municipality": "Bilbao", "lat": 43.2575, "lng": -2.9035},
        "Zurbaranbarri": {"address": "Estación Euskotren Zurbaranbarri", "municipality": "Bilbao", "lat": 43.2585, "lng": -2.9115},
        "Zazpikaleak / Casco Viejo": {"address": "Plaza Unamuno (Metro + Euskotren)", "municipality": "Bilbao", "lat": 43.2595, "lng": -2.9235},
        "Uribarri": {"address": "Estación Euskotren Uribarri", "municipality": "Bilbao", "lat": 43.2665, "lng": -2.9245},
        # Metro Bilbao
        "Basauri": {"address": "Estación de Metro Basauri", "municipality": "Basauri", "lat": 43.2370, "lng": -2.8860},
        "Ariz": {"address": "Estación de Metro Ariz", "municipality": "Basauri", "lat": 43.2420, "lng": -2.8890},
        "Etxebarri": {"address": "Estación de Metro Etxebarri", "municipality": "Etxebarri", "lat": 43.2470, "lng": -2.8905},
        "Bolueta": {"address": "Estación de Metro Bolueta", "municipality": "Bilbao", "lat": 43.2510, "lng": -2.9040},
        "Santutxu": {"address": "Plaza de Santutxu", "municipality": "Bilbao", "lat": 43.2540, "lng": -2.9180},
        "Abando": {"address": "Plaza Circular (Abando)", "municipality": "Bilbao", "lat": 43.2615, "lng": -2.9275},
        "Moyua": {"address": "Plaza Moyua", "municipality": "Bilbao", "lat": 43.2630, "lng": -2.9350},
        "Moyua (Bizkaibus)": {"address": "Alameda Rekalde / Plaza Moyua", "municipality": "Bilbao", "lat": 43.2628, "lng": -2.9345},
        "Indautxu": {"address": "Plaza Indautxu", "municipality": "Bilbao", "lat": 43.2605, "lng": -2.9420},
        "San Mamés": {"address": "Sabino Arana Etorbidea (San Mamés)", "municipality": "Bilbao", "lat": 43.2620, "lng": -2.9480},
        "Deusto": {"address": "Lehendakari Agirre Etorbidea (Deusto)", "municipality": "Bilbao", "lat": 43.2705, "lng": -2.9465},
        "Sarriko": {"address": "Estación de Metro Sarriko", "municipality": "Bilbao", "lat": 43.2750, "lng": -2.9535},
        "San Inazio": {"address": "Estación de Metro San Inazio", "municipality": "Bilbao", "lat": 43.2780, "lng": -2.9630},
        "Erandio": {"address": "Estación de Metro Erandio", "municipality": "Erandio", "lat": 43.3030, "lng": -2.9730},
        "Leioa": {"address": "Estación de Metro Leioa", "municipality": "Leioa", "lat": 43.3260, "lng": -2.9860},
        "Areeta": {"address": "Estación de Metro Areeta (Las Arenas)", "municipality": "Getxo", "lat": 43.3385, "lng": -3.0105},
        "Algorta": {"address": "Estación de Metro Algorta", "municipality": "Getxo", "lat": 43.3495, "lng": -3.0080},
        "Plentzia": {"address": "Estación de Metro Plentzia", "municipality": "Plentzia", "lat": 43.4040, "lng": -2.9460},
        "Barakaldo": {"address": "Estación de Metro Barakaldo", "municipality": "Barakaldo", "lat": 43.2975, "lng": -2.9890},
        "Sestao": {"address": "Estación de Metro Sestao", "municipality": "Sestao", "lat": 43.3090, "lng": -3.0060},
        "Portugalete": {"address": "Estación de Metro Portugalete", "municipality": "Portugalete", "lat": 43.3190, "lng": -3.0210},
        "Santurtzi": {"address": "Estación de Metro Santurtzi", "municipality": "Santurtzi", "lat": 43.3285, "lng": -3.0330},
        "Kabiezes": {"address": "Estación de Metro Kabiezes", "municipality": "Santurtzi", "lat": 43.3240, "lng": -3.0430},
        "Bilbao Aeropuerto (Loiu)": {"address": "Terminal del Aeropuerto de Bilbao", "municipality": "Loiu", "lat": 43.3010, "lng": -2.9105}
    }

    # Paradas distintas que en la práctica son el mismo punto de enlace (o están a un paseo corto).
    # Minutos a pie entre cualquier par del grupo.
    STATION_GROUPS = [
        (["Zumaia", "Zumaia Estación"], 1),
        (["Amara (Donostia)", "Amara (Pío XII / Euskotren)", "Donostia Pio XII"], 4),
        (["Donostia San Sebastián (Atotxa)", "Donostia Estación Autobuses (Atotxa)"], 2),
        (["Herrera", "Herrera (Renfe)"], 2),
        (["Donostia (Gipuzkoa Plaza)", "Boulevard (Donostia)"], 3),
        (["Loiola", "Loiola (Renfe)", "Loiola (Ribera)"], 3),
        (["Anoeta", "Anoeta (Estadio)"], 2),
        (["Irun (Renfe)", "Irun Colon"], 3),
        (["Tolosa", "Tolosa Geltokia", "Tolosa Centro"], 3),
        (["Lezo-Errenteria", "Lezo Renfe"], 2),
        (["Errenteria (Euskotren)", "Errenteria Centro"], 3),
        (["Pasaia (Euskotren)", "Pasaia (Renfe)", "Pasai Antxo"], 3),
        (["Andoain", "Andoain Centro"], 5),
        (["Hernani", "Hernani Centro"], 5),
        (["Gros", "Gros (Gran Vía)"], 4),
        (["Antiguo (Zumalakarregi)", "Donostia Antiguo (Zumalakarregi)"], 1),
        (["Miracruz", "Donostia Miracruz"], 1),
        (["Aia-Orio", "Orio"], 6),
        (["Bilbao Intermodal (Gurtubay)", "San Mamés"], 3),
        (["Kukullaga (Etxebarri)", "Etxebarri"], 5),
        (["Moyua", "Moyua (Bizkaibus)"], 1),
    ]

    # Velocidad comercial media por operador (km/h) para estimar tiempos de trayecto
    OPERATOR_SPEED_KMH = {
        "euskotren": 42, "renfe": 45, "metrobilbao": 36,
        "lurraldebus": 38, "bizkaibus": 38, "dbus": 14,
    }

    def get_stop_metadata(self, name: str) -> Dict[str, Any]:
        clean = name.strip()
        if clean in self.STOP_METADATA:
            meta = self.STOP_METADATA[clean].copy()
        else:
            meta = {
                "address": f"Parada {clean}",
                "municipality": "Gipuzkoa",
                "lat": 43.3183,
                "lng": -1.9812
            }
        query_str = f"{clean}, {meta['address']}, {meta['municipality']}, Gipuzkoa"
        meta["maps_url"] = f"https://www.google.com/maps/search/?api=1&query={meta['lat']},{meta['lng']}"
        meta["maps_search_url"] = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(query_str)}"
        meta["maps_dir_url"] = f"https://www.google.com/maps/dir/?api=1&destination={meta['lat']},{meta['lng']}"
        return meta

    def _build_stop_index(self):
        self.stops_index: Dict[str, Dict[str, Any]] = {}
        for line in self.lines:
            for s in line["stops"]:
                clean_s = s.strip()
                if clean_s not in self.stops_index:
                    is_hub = False  # se calcula al terminar el índice
                    meta = self.get_stop_metadata(clean_s)
                    self.stops_index[clean_s] = {
                        "name": clean_s,
                        "address": meta["address"],
                        "municipality": meta["municipality"],
                        "lat": meta["lat"],
                        "lng": meta["lng"],
                        "maps_url": meta["maps_url"],
                        "maps_search_url": meta["maps_search_url"],
                        "maps_dir_url": meta["maps_dir_url"],
                        "lines": [],
                        "operators": set(),
                        "is_transfer_hub": is_hub,
                        "modes": set()
                    }
                self.stops_index[clean_s]["lines"].append({
                    "line_id": line["id"],
                    "code": line["code"],
                    "name": line["name"],
                    "mode": line["mode"],
                    "operator_id": line["operator_id"],
                    "operator_name": line["operator_name"]
                })
                self.stops_index[clean_s]["operators"].add(line["operator_id"])
                self.stops_index[clean_s]["modes"].add(line["mode"])

        # Format sets to lists for JSON serialization
        for stop_name, info in self.stops_index.items():
            info["is_transfer_hub"] = len(info["operators"]) >= 2 or len(info["lines"]) >= 3 or any(
                stop_name in members for members, _ in self.STATION_GROUPS)
            info["operators"] = list(info["operators"])
            info["modes"] = list(info["modes"])

    def get_all_lines(self, operator_filter: Optional[str] = None, mode_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for line in self.lines:
            if operator_filter and line["operator_id"].lower() != operator_filter.lower():
                continue
            if mode_filter and line["mode"].lower() != mode_filter.lower():
                continue
            line_copy = dict(line)
            line_copy["maps_route_url"] = f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote_plus(line['origin'] + ' Gipuzkoa')}&destination={urllib.parse.quote_plus(line['destination'] + ' Gipuzkoa')}"
            results.append(line_copy)
        return results

    def get_line_by_id(self, line_id: str) -> Optional[Dict[str, Any]]:
        for line in self.lines:
            if line["id"].lower() == line_id.lower() or line["code"].lower() == line_id.lower():
                line_copy = dict(line)
                stops_detail = []
                for s in line["stops"]:
                    meta = self.get_stop_metadata(s)
                    stop_obj = {
                        "name": s,
                        "address": meta["address"],
                        "municipality": meta["municipality"],
                        "lat": meta["lat"],
                        "lng": meta["lng"],
                        "maps_url": meta["maps_url"],
                        "maps_search_url": meta["maps_search_url"],
                        "maps_dir_url": meta["maps_dir_url"],
                        "connecting_lines": [
                            l["code"] for l in self.stops_index.get(s, {}).get("lines", []) if l["line_id"] != line["id"]
                        ]
                    }
                    stops_detail.append(stop_obj)
                line_copy["stops_detail"] = stops_detail
                line_copy["maps_route_url"] = f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote_plus(line['origin'] + ' Gipuzkoa')}&destination={urllib.parse.quote_plus(line['destination'] + ' Gipuzkoa')}"
                return line_copy
        return None

    def search_stops(self, query: str = "") -> List[Dict[str, Any]]:
        q = query.lower().strip()
        matched = []
        for stop_name, data in self.stops_index.items():
            if not q or q in stop_name.lower():
                matched.append(data)
        # Sort transfer hubs first, then alphabetically
        return sorted(matched, key=lambda x: (not x["is_transfer_hub"], x["name"]))

    # ------------------------------------------------------------------
    # Planificador: camino más corto (Dijkstra) sobre la red completa
    # ------------------------------------------------------------------
    TRANSFER_PENALTY_MIN = 5   # coste "percibido" de cada transbordo al ordenar rutas
    TRANSFER_WALK_MIN = 2      # cambio de andén/parada cuando se transborda en la misma parada
    MAX_BOARDINGS = 3          # hasta 2 transbordos

    def _prepare_routing(self):
        """Precalcula tiempos acumulados por línea, esperas y grupos de paradas."""
        self._group_of: Dict[str, tuple] = {}
        for members, walk in self.STATION_GROUPS:
            for m in members:
                self._group_of[m] = (members, walk)

        self._lines_by_id = {l["id"]: l for l in self.lines}
        self._cum_min: Dict[str, List[float]] = {}
        self._wait_min: Dict[str, float] = {}
        for line in self.lines:
            speed = line.get("speed_kmh") or self.OPERATOR_SPEED_KMH.get(line["operator_id"], 35)
            cum = [0.0]
            for a, b in zip(line["stops"], line["stops"][1:]):
                km = self._distance_km(a, b) * 1.25  # factor de trazado real frente a línea recta
                cum.append(cum[-1] + km / speed * 60 + 0.6)  # + parada en estación
            self._cum_min[line["id"]] = cum
            headway = re.search(r"(\d+)", line.get("frequency", ""))
            self._wait_min[line["id"]] = min(int(headway.group(1)) / 2, 15) if headway else 10

    def _distance_km(self, a: str, b: str) -> float:
        ma, mb = self.get_stop_metadata(a), self.get_stop_metadata(b)
        lat1, lng1, lat2, lng2 = map(math.radians, (ma["lat"], ma["lng"], mb["lat"], mb["lng"]))
        h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
        return 6371 * 2 * math.asin(math.sqrt(h))

    def _shortest_path(self, origin: str, dest: str, max_boardings: int, banned: frozenset = frozenset()):
        """Dijkstra sobre estados (parada, línea|None, nº subidas). Devuelve la lista de pasos o None."""
        start = (origin, None, 0)
        dist = {start: 0.0}
        prev: Dict[tuple, tuple] = {}
        tie = itertools.count()
        heap = [(0.0, next(tie), start)]
        while heap:
            cost, _, state = heapq.heappop(heap)
            if cost > dist.get(state, float("inf")):
                continue
            stop, line_id, boardings = state
            if stop == dest and line_id is None:
                path = [state]
                while path[-1] in prev:
                    path.append(prev[path[-1]][0])
                path.reverse()
                return path, prev

            edges = []
            if line_id is None:
                # Subir a una línea en esta parada
                if boardings < max_boardings:
                    for l in self.stops_index[stop]["lines"]:
                        if l["line_id"] in banned:
                            continue
                        extra = 0.0 if boardings == 0 else self._wait_min[l["line_id"]]
                        penalty = 0.0 if boardings == 0 else self.TRANSFER_PENALTY_MIN
                        edges.append(((stop, l["line_id"], boardings + 1), extra, penalty))
                # Caminar a una parada del mismo nodo
                if stop in self._group_of:
                    members, walk = self._group_of[stop]
                    for m in members:
                        if m != stop and m in self.stops_index:
                            edges.append(((m, None, boardings), walk, 0.0))
            else:
                line = self._lines_by_id[line_id]
                stops = line["stops"]
                idx = stops.index(stop)
                cum = self._cum_min[line_id]
                for nidx in (idx - 1, idx + 1):
                    if 0 <= nidx < len(stops):
                        edges.append(((stops[nidx], line_id, boardings), abs(cum[nidx] - cum[idx]), 0.0))
                # Bajarse (si luego sube a otra línea en la misma parada, cuenta el cambio de andén)
                edges.append(((stop, None, boardings), 0.0, 0.0))

            for nstate, mins, penalty in edges:
                ncost = cost + mins + penalty
                if ncost < dist.get(nstate, float("inf")) - 1e-9:
                    dist[nstate] = ncost
                    prev[nstate] = (state, mins)
                    heapq.heappush(heap, (ncost, next(tie), nstate))
        return None

    def _path_to_route(self, path: list, prev: dict) -> Dict[str, Any]:
        segments: List[Dict[str, Any]] = []
        total = 0.0
        i = 0
        while i < len(path) - 1:
            stop, line_id, _ = path[i]
            nstop, nline, _ = path[i + 1]
            step_min = prev[path[i + 1]][1]
            if line_id is None and nline is None:
                # Tramo a pie entre paradas del mismo nodo
                total += step_min
                segments.append({"type": "walk_transfer", "mode": "A pie", "from_stop": stop, "to_stop": nstop,
                                 "duration_min": round(step_min), "note": f"Camina de {stop} a {nstop}."})
                i += 1
            elif line_id is None and nline is not None:
                # Subida: recorrer hasta que se baja de la línea
                board_stop, wait = stop, step_min
                j = i + 1
                ride = 0.0
                while path[j + 1][1] == nline:
                    ride += prev[path[j + 1]][1]
                    j += 1
                alight_stop = path[j][0]
                line = self._lines_by_id[nline]
                if segments and segments[-1]["type"] == "transit":
                    # Transbordo en la misma parada: cambio de andén
                    segments.append({"type": "walk_transfer", "mode": "A pie", "from_stop": board_stop, "to_stop": board_stop,
                                     "duration_min": self.TRANSFER_WALK_MIN,
                                     "note": "Cambio de andén o parada con bonificación MUGI en los primeros 50 minutos."})
                    total += self.TRANSFER_WALK_MIN
                total += wait + ride
                n_stops = abs(line["stops"].index(alight_stop) - line["stops"].index(board_stop))
                segments.append({
                    "type": "transit", "mode": line["mode"], "operator_id": line["operator_id"],
                    "operator_name": line["operator_name"], "line_code": line["code"], "line_name": line["name"],
                    "line_id": line["id"], "from_stop": board_stop, "to_stop": alight_stop,
                    "stops_count": n_stops, "duration_min": max(1, round(ride)), "frequency": line["frequency"],
                })
                i = j
            else:
                i += 1

        transit = [s for s in segments if s["type"] == "transit"]
        for k, seg in enumerate(segments, start=1):
            seg["segment_order"] = k
        num_transfers = len(transit) - 1
        modes = {s["mode"] for s in transit}
        if num_transfers == 0:
            rtype = "Directo"
        elif "Autobús" in modes and modes & {"Tren", "Metro"}:
            rtype = "Transbordo Intermodal (Bus + Tren)"
        else:
            rtype = "Transbordo"
        return {
            "route_id": "route-" + "-".join(s["line_id"] for s in transit),
            "type": rtype,
            "total_duration_min": max(1, round(total)),
            "num_transfers": num_transfers,
            "mugi_transfer_applied": num_transfers > 0,
            "fare_breakdown": self._calculate_mugi_fares(len(transit), is_transfer=num_transfers > 0),
            "segments": segments,
        }

    def _resolve_stop(self, name: str) -> Optional[str]:
        clean = name.strip()
        if clean in self.stops_index:
            return clean
        matches = [k for k in self.stops_index if clean.lower() in k.lower()]
        return matches[0] if matches else None

    def plan_multimodal_journey(self, origin: str, destination: str) -> Dict[str, Any]:
        """
        Calcula las rutas óptimas entre dos paradas combinando todas las líneas (tren, metro y bus),
        con transbordos a pie entre paradas del mismo nodo. Devuelve la mejor ruta y alternativas
        razonables, descartando las que son más lentas y además tienen más transbordos.
        """
        orig_clean = self._resolve_stop(origin)
        dest_clean = self._resolve_stop(destination)
        if not orig_clean or not dest_clean:
            return {
                "found": False,
                "error": f"No se han encontrado las paradas '{origin}' o '{destination}'. Selecciona una parada de la lista.",
                "origin": origin, "destination": destination, "routes": []
            }

        candidates: Dict[tuple, Dict[str, Any]] = {}

        def collect(max_b: int, banned: frozenset = frozenset()):
            found = self._shortest_path(orig_clean, dest_clean, max_b, banned)
            if not found:
                return None
            route = self._path_to_route(*found)
            key = tuple(s["line_id"] for s in route["segments"] if s["type"] == "transit")
            if key and key not in candidates:
                candidates[key] = route
            return key

        # Mejor ruta con 0, 1 y 2 transbordos, y alternativas prohibiendo cada línea usada
        base_keys = [collect(b) for b in range(1, self.MAX_BOARDINGS + 1)]
        for key in {k for k in base_keys if k}:
            for line_id in key:
                collect(self.MAX_BOARDINGS, frozenset({line_id}))

        routes = list(candidates.values())
        # Descartar rutas dominadas: otra igual o más rápida con igual o menos transbordos
        routes = [r for r in routes if not any(
            o is not r and o["num_transfers"] <= r["num_transfers"]
            and o["total_duration_min"] <= r["total_duration_min"]
            and (o["num_transfers"], o["total_duration_min"]) != (r["num_transfers"], r["total_duration_min"])
            for o in routes)]
        if routes:
            best = min(r["total_duration_min"] for r in routes)
            routes = [r for r in routes if r["total_duration_min"] <= best * 1.6 + 15]
        routes.sort(key=lambda r: r["total_duration_min"] + self.TRANSFER_PENALTY_MIN * r["num_transfers"])

        # Fusionar rutas idénticas por líneas paralelas (p. ej. L1 y L2 en el tramo común)
        merged: Dict[tuple, Dict[str, Any]] = {}
        for r in routes:
            shape = tuple((s["type"], s["from_stop"], s["to_stop"]) for s in r["segments"])
            if shape not in merged:
                merged[shape] = r
                continue
            for kept, other in zip(merged[shape]["segments"], r["segments"]):
                if kept["type"] == "transit" and other["line_code"] not in kept["line_code"].split(" / "):
                    kept["line_code"] += " / " + other["line_code"]
        routes = list(merged.values())[:4]

        return {
            "found": len(routes) > 0,
            "origin": orig_clean,
            "destination": dest_clean,
            "count": len(routes),
            "routes": routes
        }

    def _calculate_mugi_fares(self, stages: int, is_transfer: bool = False) -> Dict[str, Any]:
        """Calculates standard ticket price vs. MUGI discount brackets for 1 or 2 stages."""
        single_ticket_unit = 1.95
        base_cash = single_ticket_unit * stages

        # With MUGI, 2nd stage under 50 min has a major transfer discount (ATTG rule)
        # Stage 1: 1.03€ (tramo 1), 0.84€ (tramo 2), 0.19€ (tramo 3)
        # Stage 2: 0.00€ if urban / 0.25€ if interurban
        t1_unit = 1.03
        t2_unit = 0.84
        t3_unit = 0.19

        # Con transbordo dentro de los 50 min solo se paga la primera etapa;
        # sin transbordo cada etapa se paga a precio de tramo.
        paid_stages = 1 if is_transfer else stages

        mugi_tramo_1 = round(t1_unit * paid_stages, 2)
        mugi_tramo_2 = round(t2_unit * paid_stages, 2)
        mugi_tramo_3 = round(t3_unit * paid_stages, 2)

        return {
            "single_cash_ticket": f"{base_cash:.2f}€",
            "mugi_tramo_1": f"{mugi_tramo_1:.2f}€ (Ahorro {round((1 - mugi_tramo_1/base_cash)*100)}%)",
            "mugi_tramo_2": f"{mugi_tramo_2:.2f}€ (Ahorro {round((1 - mugi_tramo_2/base_cash)*100)}%)",
            "mugi_tramo_3": f"{mugi_tramo_3:.2f}€ (Ahorro {round((1 - mugi_tramo_3/base_cash)*100)}%)",
            "transfer_rule": "Bonificación ATTG activa: Segundo trayecto gratuito o al 0% si se valida dentro de los 50 minutos." if is_transfer else "Tarifa por trayecto único."
        }

transport_service = TransportService()
