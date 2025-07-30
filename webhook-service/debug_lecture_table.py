#!/usr/bin/env python3
"""
Debug script to generate HTML with lecture table
This helps inspect the table formatting before PDF conversion
"""

import os
from typing import Dict, Any

def generate_debug_html():
    """Generate HTML file with lecture table for debugging"""
    
    # Sample lecture results data
    lecture_results = {
        "Ser vio": {
            "total_questions": 1,
            "correct_answers": 1,
            "percentage": 100.0,
            "status": "Aprobado"
        },
        "Ser estar": {
            "total_questions": 2,
            "correct_answers": 1,
            "percentage": 50.0,
            "status": "Reprobado"
        },
        "Presente simple": {
            "total_questions": 3,
            "correct_answers": 2,
            "percentage": 66.7,
            "status": "Reprobado"
        },
        "Presente continuo": {
            "total_questions": 1,
            "correct_answers": 1,
            "percentage": 100.0,
            "status": "Aprobado"
        },
        "Pasado simple": {
            "total_questions": 2,
            "correct_answers": 0,
            "percentage": 0.0,
            "status": "Reprobado"
        },
        "Futuro simple": {
            "total_questions": 1,
            "correct_answers": 1,
            "percentage": 100.0,
            "status": "Aprobado"
        }
    }
    
    # Load the original template
    template_path = "templates/plantilla_test_diagnostico.html"
    if not os.path.exists(template_path):
        print(f"❌ Template not found: {template_path}")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    print(f"✅ Loaded template, size: {len(html_content)} characters")
    
    # Replace variables with sample data
    variables = {
        '<<ALUMNO>>': 'Sebastián San Martín',
        '<<Nombre>>': 'Sebastián San Martín',
        '<<MATERIA>>': 'Test de diagnóstico Parte 1 M30M',
        '<<Prueba>>': 'Test de diagnóstico Parte 1 M30M',
        '<<PD%>>': '75.0%',
        '<<Nivel>>': '2',
    }
    
    for var_name, var_value in variables.items():
        html_content = html_content.replace(var_name, var_value)
    
    print("✅ Variables replaced in HTML template")
    
    # Add lecture table (same logic as report_generator.py)
    table_rows = []
    for lecture_name, result_details in lecture_results.items():
        status_string = result_details.get("status", "Reprobado")
        status_class = "status-aprobada" if status_string == "Aprobado" else "status-reprobada"
        
        row = f"""
        <tr>
          <td>{lecture_name}</td>
          <td class="status-cell {status_class}">{status_string}</td>
        </tr>"""
        table_rows.append(row)
    
    table_html = f"""
<section class="page">
  <div class="content">
    <p class="TituloAlumno Negrita">Resultados por Lección</p>
    <table class="results-table">
      <thead>
        <tr>
          <th>Lección</th>
          <th style="text-align:center;">Estado</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
  </div>
</section>"""
    
    # Insert table before closing body tag
    html_content = html_content.replace('</body>', f'{table_html}\n</body>')
    
    # Save debug HTML file
    debug_filename = "debug_lecture_table.html"
    with open(debug_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Debug HTML saved: {debug_filename}")
    print(f"📊 Added table with {len(lecture_results)} lectures")
    print(f"📏 Final HTML size: {len(html_content)} characters")
    print(f"🔗 Open {debug_filename} in your browser to inspect the table")
    
    return True

if __name__ == "__main__":
    print("🔍 Generating debug HTML with lecture table...")
    generate_debug_html() 