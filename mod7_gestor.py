import hashlib
import io
import time
import unicodedata
from typing import Dict, Optional

import folium
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from streamlit_folium import st_folium
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ==============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS ADAPTATIVOS
# ==============================================================================
st.set_page_config(
    page_title="Padrón Unificado Tacna EMR 2026",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    }
    .app-header {
        background: linear-gradient(135deg, #1B3B6F 0%, #0F172A 100%);
        color: white;
        padding: 20px;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(27, 59, 111, 0.15);
    }
    .app-header h1 {
        font-size: 24px;
        font-weight: 700;
        margin: 0;
    }
    .app-header p {
        font-size: 13px;
        margin-top: 4px;
        opacity: 0.9;
    }
    .elector-card {
        background-color: #FFFFFF;
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 14px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    .dni-badge {
        background-color: #E0F2FE;
        color: #0369A1;
        font-weight: 700;
        font-size: 13px;
        padding: 3px 8px;
        border-radius: 8px;
        display: inline-block;
    }
    .dis-badge {
        background-color: #DCFCE7;
        color: #15803D;
        font-size: 12px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 8px;
        display: inline-block;
        margin-left: 6px;
    }
    .pro-badge {
        background-color: #FEF3C7;
        color: #B45309;
        font-size: 12px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 8px;
        display: inline-block;
        margin-left: 6px;
    }
    .elector-name {
        font-size: 16px;
        font-weight: 700;
        color: #1E293B;
        margin: 8px 0;
        text-transform: uppercase;
    }
    .elector-detail {
        font-size: 12px;
        color: #475569;
        margin-top: 4px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""",
    unsafe_allow_html=True,
)


# ==============================================================================
# 2. AUTENTICACIÓN Y GESTOR DE PERFILES / PERMISOS GRANULARES
# ==============================================================================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Catálogo general de permisos del sistema
PERMISOS_SISTEMA = {
    "consultar_padron": "🪪 Búsqueda & Fichas",
    "ver_dashboard": "📊 Dashboard Estadístico",
    "ver_mapas": "🗺️ Geolocalización / Mapas",
    "exportar_reportes": "📥 Exportar Reportes",
    "gestionar_usuarios": "⚙️ Gestor de Perfiles & Permisos",
}

if "db_usuarios" not in st.session_state:
    st.session_state.db_usuarios = {
        "admin": {
            "password_hash": hash_password("admin123"),
            "nombre": "Administrador General",
            "rol": "Administrador",
            "permisos": list(PERMISOS_SISTEMA.keys()),
        },
        "analista": {
            "password_hash": hash_password("analista123"),
            "nombre": "Analista de Datos",
            "rol": "Analista",
            "permisos": ["consultar_padron", "ver_dashboard", "ver_mapas", "exportar_reportes"],
        },
        "operador": {
            "password_hash": hash_password("campo123"),
            "nombre": "Operador de Campo",
            "rol": "Operador",
            "permisos": ["consultar_padron"],
        },
    }

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None


def login_form():
    st.markdown(
        """
        <div class="app-header">
            <h1>🔒 CONTROL DE ACCESO REGIONAL EMR TACNA 2026</h1>
            <p>Sistema Unificado: Tacna, Tarata, Candarave y Jorge Basadre</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            st.subheader("Iniciar Sesión")
            usuario_input = st.text_input("Usuario")
            password_input = st.text_input("Contraseña", type="password")
            btn_ingresar = st.form_submit_button("Ingresar al Sistema", use_container_width=True)

            if btn_ingresar:
                usr = usuario_input.strip().lower()
                if usr in st.session_state.db_usuarios:
                    pass_hash = hash_password(password_input)
                    if st.session_state.db_usuarios[usr]["password_hash"] == pass_hash:
                        st.session_state.logged_in = True
                        st.session_state.user_info = {
                            "username": usr,
                            "nombre": st.session_state.db_usuarios[usr]["nombre"],
                            "rol": st.session_state.db_usuarios[usr]["rol"],
                            "permisos": st.session_state.db_usuarios[usr].get("permisos", []),
                        }
                        st.success(f"Bienvenido {st.session_state.user_info['nombre']}!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Contraseña incorrecta.")
                else:
                    st.error("El usuario ingresado no existe.")

        st.info(
            """
            **Credenciales de Demostración:**
            * **Admin:** `admin` / `admin123` *(Acceso Total + GestPara implementar un **Módulo Gestor de Perfiles y Permisos** basado en el modelo RBAC (*Role-Based Access Control*), se requiere estructurar la base de datos, definir la lógica del backend y proteger las rutas en el frontend.

### 1. Modelo de Base de Datos (Relacional)

Necesitas 4 tablas principales para gestionar la relación muchos a muchos entre usuarios, roles y permisos: