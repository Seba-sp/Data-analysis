#!/usr/bin/env python3
"""
Setup script for webhook service
Creates necessary directories and sample files
"""

import os
import pandas as pd
from pathlib import Path

def create_directories():
    """Create necessary directories"""
    directories = [
        "data/webhook_reports",
        "data/responses/questions",
        "templates"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def create_sample_question_banks():
    """Create sample question bank files for testing"""
    sample_data = {
        "Test de diagnóstico Parte 1": [
            {"question_number": 1, "correct_alternative": "A", "lecture": "Introducción a la Programación"},
            {"question_number": 2, "correct_alternative": "B", "lecture": "Introducción a la Programación"},
            {"question_number": 3, "correct_alternative": "C", "lecture": "Variables y Tipos de Datos"},
            {"question_number": 4, "correct_alternative": "A", "lecture": "Variables y Tipos de Datos"},
            {"question_number": 5, "correct_alternative": "B", "lecture": "Control de Flujo"},
            {"question_number": 6, "correct_alternative": "C", "lecture": "Control de Flujo"},
            {"question_number": 7, "correct_alternative": "A", "lecture": "Funciones"},
            {"question_number": 8, "correct_alternative": "B", "lecture": "Funciones"},
            {"question_number": 9, "correct_alternative": "C", "lecture": "Funciones"},
            {"question_number": 10, "correct_alternative": "A", "lecture": "Arrays y Listas"}
        ],
        "Test de diagnóstico Parte 2": [
            {"question_number": 1, "correct_alternative": "A", "lecture": "Programación Orientada a Objetos"},
            {"question_number": 2, "correct_alternative": "B", "lecture": "Programación Orientada a Objetos"},
            {"question_number": 3, "correct_alternative": "C", "lecture": "Herencia y Polimorfismo"},
            {"question_number": 4, "correct_alternative": "A", "lecture": "Herencia y Polimorfismo"},
            {"question_number": 5, "correct_alternative": "B", "lecture": "Interfaces"},
            {"question_number": 6, "correct_alternative": "C", "lecture": "Interfaces"},
            {"question_number": 7, "correct_alternative": "A", "lecture": "Excepciones"},
            {"question_number": 8, "correct_alternative": "B", "lecture": "Excepciones"},
            {"question_number": 9, "correct_alternative": "C", "lecture": "Colecciones"},
            {"question_number": 10, "correct_alternative": "A", "lecture": "Colecciones"}
        ],
        "Test de diagnóstico Parte 3": [
            {"question_number": 1, "correct_alternative": "A", "lecture": "Bases de Datos"},
            {"question_number": 2, "correct_alternative": "B", "lecture": "Bases de Datos"},
            {"question_number": 3, "correct_alternative": "C", "lecture": "SQL Básico"},
            {"question_number": 4, "correct_alternative": "A", "lecture": "SQL Básico"},
            {"question_number": 5, "correct_alternative": "B", "lecture": "Conexiones JDBC"},
            {"question_number": 6, "correct_alternative": "C", "lecture": "Conexiones JDBC"},
            {"question_number": 7, "correct_alternative": "A", "lecture": "Consultas Avanzadas"},
            {"question_number": 8, "correct_alternative": "B", "lecture": "Consultas Avanzadas"},
            {"question_number": 9, "correct_alternative": "C", "lecture": "Transacciones"},
            {"question_number": 10, "correct_alternative": "A", "lecture": "Transacciones"}
        ],
        "Test de diagnóstico Parte 4": [
            {"question_number": 1, "correct_alternative": "A", "lecture": "Desarrollo Web"},
            {"question_number": 2, "correct_alternative": "B", "lecture": "Desarrollo Web"},
            {"question_number": 3, "correct_alternative": "C", "lecture": "Servlets"},
            {"question_number": 4, "correct_alternative": "A", "lecture": "Servlets"},
            {"question_number": 5, "correct_alternative": "B", "lecture": "JSP"},
            {"question_number": 6, "correct_alternative": "C", "lecture": "JSP"},
            {"question_number": 7, "correct_alternative": "A", "lecture": "Spring Framework"},
            {"question_number": 8, "correct_alternative": "B", "lecture": "Spring Framework"},
            {"question_number": 9, "correct_alternative": "C", "lecture": "REST APIs"},
            {"question_number": 10, "correct_alternative": "A", "lecture": "REST APIs"}
        ]
    }
    
    for assessment_title, questions in sample_data.items():
        df = pd.DataFrame(questions)
        file_path = f"data/responses/questions/{assessment_title}.csv"
        df.to_csv(file_path, index=False)
        print(f"✅ Created question bank: {file_path}")

def create_env_template():
    """Create environment template file"""
    env_template = """# LearnWorlds API Configuration
CLIENT_ID=your_client_id_here
SCHOOL_DOMAIN=your_school_domain.learnworlds.com
ACCESS_TOKEN=your_access_token_here

# Webhook Security
LEARNWORLDS_WEBHOOK_SECRET=your_webhook_secret_here

# Email Configuration
EMAIL_FROM=your_email@gmail.com
EMAIL_PASS=your_app_password_here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Optional: Admin notifications
ADMIN_EMAIL=admin@yourdomain.com

# GCP Configuration (for production)
STORAGE_BACKEND=local  # Change to 'gcp' for production
GCP_PROJECT_ID=your_project_id
GCP_BUCKET_NAME=your_bucket_name
GOOGLE_SERVICE_ACCOUNT_KEY=your_base64_encoded_key

# Webhook URL (for testing)
WEBHOOK_URL=http://localhost:8080/webhook
"""
    
    with open("env.template", "w") as f:
        f.write(env_template)
    print("✅ Created env.template file")

def main():
    """Main setup function"""
    print("🚀 Setting up webhook service...")
    
    # Create directories
    create_directories()
    
    # Create sample question banks
    create_sample_question_banks()
    
    # Create environment template
    create_env_template()
    
    print("\n✅ Setup completed!")
    print("\n📋 Next steps:")
    print("1. Copy env.template to .env and fill in your credentials")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Test locally: python webhook_main.py")
    print("4. Test webhook: python test_webhook_local.py")

if __name__ == "__main__":
    main() 