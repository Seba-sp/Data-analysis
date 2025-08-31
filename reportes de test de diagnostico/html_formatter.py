#!/usr/bin/env python3
"""
HTML formatting and template handling for the Segment Schedule Report Generator.
"""

import os
import logging
from typing import Any

import pandas as pd

from utils import find_col_case_insensitive

logger = logging.getLogger(__name__)


class HTMLFormatter:
    """Handles HTML template loading and formatting."""
    
    def __init__(self, html_template_path: str = "templates/plantilla_plan_de_estudio.html"):
        self.html_template_path = html_template_path

    def load_html_template(self) -> str:
        """Load the HTML template file."""
        if not os.path.exists(self.html_template_path):
            raise FileNotFoundError(f"HTML template not found: {self.html_template_path}")
        with open(self.html_template_path, "r", encoding="utf-8") as f:
            return f.read()

    def format_preparar_value(self, value: Any) -> str:
        """Format preparar column value to Sí/No."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return "No"
        s = str(value).strip()
        if s == "1":
            return "Sí"
        return "No"

    def format_nivel_value(self, value: Any, test_type: str, is_cuarto_medio: bool = False) -> str:
        """Format nivel column value based on test type and student type."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return "N/A"
        
        s = str(value).strip()
        
        # For "Cuarto medio" students, apply special formatting
        if is_cuarto_medio:
            if test_type == "M1":
                # M1: Nivel 1 -> "General", Nivel 2 -> "Intermedio", Nivel 3 -> "Avanzado"
                if s.lower() in ["nivel 1", "1"]:
                    return "General"
                elif s.lower() in ["nivel 2", "2"]:
                    return "Intermedio"
                elif s.lower() in ["nivel 3", "3"]:
                    return "Avanzado"
                return s
            elif test_type == "CL":
                # CL: Nivel 1 -> "General", Nivel 2/3 -> "Avanzado"
                if s.lower() in ["nivel 1", "1"]:
                    return "General"
                elif s.lower() in ["nivel 2", "nivel 3", "2", "3"]:
                    return "Avanzado"
                return s
            elif test_type in ["CIEN", "HYST"]:
                # CIEN/HYST: Nivel 1 -> "General", Nivel 2 -> "Avanzado"
                if s.lower() in ["nivel 1", "1", "general"]:
                    return "General"
                elif s.lower() in ["nivel 2", "2", "avanzado"]:
                    return "Avanzado"
                return s
        
        # For regular students (Egresado), use original logic
        # For M1 and CL, return the level number
        if test_type in ["M1", "CL", "CIEN"]:
            # Extract number from "Nivel 1", "1", etc.
            for n in (1, 2, 3):
                if s.lower() in [f"nivel {n}", str(n)]:
                    return str(n)
            return s
        
        # For CIEN and HYST, return General/Avanzado
        elif test_type in ["HYST"]:
            if s.lower() in ["avanzado", "nivel 2", "2"]:
                return "Avanzado"
            elif s.lower() in ["general", "nivel 1", "1"]:
                return "General"
            return s
        
        return s

    def format_dominio_value(self, value: Any) -> str:
        """Format dominio column value from decimal to percentage."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return "N/A"
        
        s = str(value).strip()
        
        # If it's "Diagnóstico no rendido", return as is
        if s.lower() == "diagnóstico no rendido":
            return s
        
        try:
            # Handle string format like "0,53"
            if isinstance(value, str):
                # Replace comma with dot for decimal parsing
                value = value.replace(",", ".")
            
            # Convert to float and format as percentage
            float_val = float(value)
            percentage = int(round(float_val * 100))
            return f"{percentage}%"
        except (ValueError, TypeError):
            # If conversion fails, return the original value
            return str(value)

    def populate_results_table_placeholders(self, html_content: str, reporte_row: pd.Series, is_cuarto_medio: bool = False) -> str:
        """Populate the results table placeholders with actual data from the Reporte sheet."""
        
        # Find the relevant columns in the Reporte sheet
        preparar_m1_col = find_col_case_insensitive(reporte_row.to_frame().T, ["preparar_matemática_m1", "preparar_matematica_m1"])
        preparar_m2_col = find_col_case_insensitive(reporte_row.to_frame().T, ["preparar_matemática_m2", "preparar_matematica_m2"])
        preparar_cl_col = find_col_case_insensitive(reporte_row.to_frame().T, ["preparar_competencia_lectora"])
        preparar_cien_col = find_col_case_insensitive(reporte_row.to_frame().T, ["preparar_ciencias"])
        preparar_hyst_col = find_col_case_insensitive(reporte_row.to_frame().T, ["preparar_historia"])
        
        nivel_m1_col = find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel M1"])
        nivel_cl_col = find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel CL"])
        nivel_cien_col = find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel CIEN"])
        nivel_hyst_col = find_col_case_insensitive(reporte_row.to_frame().T, ["Nivel HYST"])
        
        dominio_m1_col = find_col_case_insensitive(reporte_row.to_frame().T, ["Dominio M1"])
        dominio_cl_col = find_col_case_insensitive(reporte_row.to_frame().T, ["Dominio CL"])
        dominio_cien_col = find_col_case_insensitive(reporte_row.to_frame().T, ["Dominio CIEN"])
        dominio_hyst_col = find_col_case_insensitive(reporte_row.to_frame().T, ["Dominio HYST"])
        
        # Get values and format them
        replacements = {}
        
        # Preparar values
        if preparar_m1_col:
            replacements["<<PREPARAR_M1>>"] = self.format_preparar_value(reporte_row.get(preparar_m1_col))
        else:
            replacements["<<PREPARAR_M1>>"] = "N/A"
            
        if preparar_m2_col:
            replacements["<<PREPARAR_M2>>"] = self.format_preparar_value(reporte_row.get(preparar_m2_col))
        else:
            replacements["<<PREPARAR_M2>>"] = "N/A"
            
        if preparar_cl_col:
            replacements["<<PREPARAR_CL>>"] = self.format_preparar_value(reporte_row.get(preparar_cl_col))
        else:
            replacements["<<PREPARAR_CL>>"] = "N/A"
            
        if preparar_cien_col:
            replacements["<<PREPARAR_CIEN>>"] = self.format_preparar_value(reporte_row.get(preparar_cien_col))
        else:
            replacements["<<PREPARAR_CIEN>>"] = "N/A"
            
        if preparar_hyst_col:
            replacements["<<PREPARAR_HYST>>"] = self.format_preparar_value(reporte_row.get(preparar_hyst_col))
        else:
            replacements["<<PREPARAR_HYST>>"] = "N/A"
        
        # Nivel values
        if nivel_m1_col:
            replacements["<<NIVEL_M1>>"] = self.format_nivel_value(reporte_row.get(nivel_m1_col), "M1", is_cuarto_medio)
        else:
            replacements["<<NIVEL_M1>>"] = "N/A"
            
        # For M2, check if student prepares M2 first
        if preparar_m2_col and self.format_preparar_value(reporte_row.get(preparar_m2_col)) == "Sí":
            replacements["<<NIVEL_M2>>"] = "Revisar anexo M2"
        else:
            replacements["<<NIVEL_M2>>"] = ""
            
        if nivel_cl_col:
            replacements["<<NIVEL_CL>>"] = self.format_nivel_value(reporte_row.get(nivel_cl_col), "CL", is_cuarto_medio)
        else:
            replacements["<<NIVEL_CL>>"] = "N/A"
            
        if nivel_cien_col:
            replacements["<<NIVEL_CIEN>>"] = self.format_nivel_value(reporte_row.get(nivel_cien_col), "CIEN", is_cuarto_medio)
        else:
            replacements["<<NIVEL_CIEN>>"] = "N/A"
            
        if nivel_hyst_col:
            replacements["<<NIVEL_HYST>>"] = self.format_nivel_value(reporte_row.get(nivel_hyst_col), "HYST", is_cuarto_medio)
        else:
            replacements["<<NIVEL_HYST>>"] = "N/A"
        
        # Dominio values
        if dominio_m1_col:
            replacements["<<DOMINIO_M1>>"] = self.format_dominio_value(reporte_row.get(dominio_m1_col))
        else:
            replacements["<<DOMINIO_M1>>"] = "N/A"
            
        # For M2, check if student prepares M2 first
        if preparar_m2_col and self.format_preparar_value(reporte_row.get(preparar_m2_col)) == "Sí":
            replacements["<<DOMINIO_M2>>"] = "Revisar anexo M2"
        else:
            replacements["<<DOMINIO_M2>>"] = ""
            
        if dominio_cl_col:
            replacements["<<DOMINIO_CL>>"] = self.format_dominio_value(reporte_row.get(dominio_cl_col))
        else:
            replacements["<<DOMINIO_CL>>"] = "N/A"
            
        if dominio_cien_col:
            replacements["<<DOMINIO_CIEN>>"] = self.format_dominio_value(reporte_row.get(dominio_cien_col))
        else:
            replacements["<<DOMINIO_CIEN>>"] = "N/A"
            
        if dominio_hyst_col:
            replacements["<<DOMINIO_HYST>>"] = self.format_dominio_value(reporte_row.get(dominio_hyst_col))
        else:
            replacements["<<DOMINIO_HYST>>"] = "N/A"
        
        # Apply all replacements
        for placeholder, value in replacements.items():
            html_content = html_content.replace(placeholder, value)
        
        return html_content

    def populate_calendario_general_section(self, html_content: str, reporte_row: pd.Series) -> str:
        """Populate the Calendario General section conditionally based on user type."""
        
        # Find the student type column
        col_tipo_estudiante = find_col_case_insensitive(
            reporte_row.to_frame().T, 
            ["qué_tipo_de_estudiante_eres", "que_tipo_de_estudiante_eres"]
        ) or "qué_tipo_de_estudiante_eres"
        
        # Check if user is "Egresado"
        is_egresado = False
        if col_tipo_estudiante in reporte_row.index:
            tipo_estudiante = str(reporte_row.get(col_tipo_estudiante, "")).strip().lower()
            is_egresado = tipo_estudiante == "egresado"
        
        # Define the Calendario General section HTML
        calendario_general_html = """<!-- =========== PÁGINA 4 - CALENDARIO GENERAL ========== -->
<section class="page">
  <div class="content">
    <h2>2. Calendario General</h2>
    
    <p>El calendario que verás ahora es el calendario general para egresados, sin embargo el Calendario Personalizado es aquel que te recomendaremos a ti en función de tu diagnóstico y tus respuestas en las encuestas.</p>
    
    <table style="width: 60%; border-collapse: collapse; margin: 10px 0; margin-right: 40px; border: 1px solid #000; font-family: 'Times New Roman', Times, serif; font-size: 12px;">
        <thead>
            <tr>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;"></th>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;">Lunes</th>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;">Martes</th>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;">Miércoles</th>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;">Jueves</th>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;">Viernes</th>
                <th style="border: 1px solid #000; padding: 10px; text-align: center; background-color: #f0f0f0;">Sábado</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">(9:00-13:00)</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">Matemática M1</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">Competencia Lectora</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">Matemática M1</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">Competencia Lectora</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">Matemática M1</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;" rowspan="5">Matemática M2</td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">(13:00-14:00)</td>
                <td colspan="5" style="border: 1px solid #000; padding: 10px; text-align: center; font-style: italic;">Almuerzo</td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">(14:00-16:00)</td>
                <td style="border: 1px solid #000; padding: 10px;">Matemática M1</td>
                <td style="border: 1px solid #000; padding: 10px;">Libre</td>
                <td style="border: 1px solid #000; padding: 10px;">Matemática M1</td>
                <td style="border: 1px solid #000; padding: 10px;">Libre</td>
                <td style="border: 1px solid #000; padding: 10px;">Matemática M1</td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">(16:00-18:00)</td>
                <td colspan="4" style="border: 1px solid #000; padding: 10px; text-align: center; font-style: italic;">Ayudantías M30M</td>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">Ayudantía Electivo</td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; padding: 10px; text-align: center;">(18:00-21:00)</td>
                <td style="border: 1px solid #000; padding: 10px;">Libre</td>
                <td style="border: 1px solid #000; padding: 10px;">Electivo</td>
                <td style="border: 1px solid #000; padding: 10px;">Libre</td>
                <td style="border: 1px solid #000; padding: 10px;">Electivo</td>
                <td style="border: 1px solid #000; padding: 10px;"><strong>Viernes M30M</strong></td>
            </tr>
        </tbody>
    </table>
    
    <div style="margin-top: 20px;">
        <p><strong>Puntos importantes:</strong></p>
        <ol style="margin-left: 20px;">
            <li>Recuerda que Electivo puede ser Ciencias o Historia.</li>
            <li>Las Ayudantías M30M son opcionales, sin embargo las ayudantías de electivo son obligatorias, en caso de que no puedas asistir, <strong>siempre quedarán grabadas</strong>.</li>
            <li>Los Viernes M30M son actividades programadas donde haremos concursos, competencias y eventos.</li>
            <li>Si preparas electivo los fines de semana se te enviarán tareas a completar.</li>
            <li>Este horario es un horario general, tu horario personalizado lo encontrarás en las siguientes páginas.</li>
        </ol>
    </div>
  </div>
</section>"""
        
        # Replace the placeholder with the section HTML if user is "Egresado", otherwise remove it
        if is_egresado:
            html_content = html_content.replace("<<CALENDARIO_GENERAL_SECTION>>", calendario_general_html)
        else:
            html_content = html_content.replace("<<CALENDARIO_GENERAL_SECTION>>", "")
        
        return html_content
