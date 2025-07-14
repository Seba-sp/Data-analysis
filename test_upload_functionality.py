#!/usr/bin/env python3
"""
Test script for Google Drive and Slack integration functionality
"""

import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from analisis import upload_file_to_drive, send_slack_notification, get_drive_service, get_slack_client

# Load environment variables from .env file
load_dotenv()

def test_google_drive_connection():
    """Test Google Drive service connection"""
    print("🧪 Probando conexión a Google Drive...")
    
    try:
        drive_service = get_drive_service()
        print("✅ Servicio de Google Drive inicializado exitosamente")
        return True
    except Exception as e:
        print(f"❌ Conexión a Google Drive falló: {e}")
        return False

def test_slack_connection():
    """Test Slack client connection"""
    print("🧪 Probando conexión a Slack...")
    
    try:
        slack_client = get_slack_client()
        print("✅ Cliente de Slack inicializado exitosamente")
        return True
    except Exception as e:
        print(f"❌ Conexión a Slack falló: {e}")
        return False

def test_file_upload():
    """Test file upload to Google Drive"""
    print("🧪 Probando subida de archivo a Google Drive...")
    
    try:
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Este es un archivo de prueba para la funcionalidad de subida a Google Drive.")
            temp_file_path = f.name
        
        # Upload the file
        drive_link = upload_file_to_drive(temp_file_path, "test_upload.txt")
        
        if drive_link:
            print(f"✅ Archivo subido exitosamente: {drive_link}")
            # Clean up
            os.unlink(temp_file_path)
            return True
        else:
            print("❌ Subida de archivo falló")
            os.unlink(temp_file_path)
            return False
            
    except Exception as e:
        print(f"❌ Prueba de subida de archivo falló: {e}")
        return False

def test_slack_notification():
    """Test Slack notification"""
    print("🧪 Probando notificación de Slack...")
    
    try:
        test_links = ["https://example.com/test-file-1.pdf", "https://example.com/test-file-2.xlsx"]
        send_slack_notification("test-course", "Curso de Prueba", test_links)
        print("✅ Notificación de Slack enviada exitosamente")
        return True
    except Exception as e:
        print(f"❌ Prueba de notificación de Slack falló: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Probando Integración de Google Drive y Slack")
    print("=" * 50)
    
    # Check environment variables
    required_vars = [
        'GOOGLE_DRIVE_FOLDER_ID',
        'GOOGLE_SERVICE_ACCOUNT_KEY',
        'SLACK_BOT_TOKEN',
        'SLACK_CHANNEL'
    ]
    
    print("📋 Verificando variables de entorno...")
    missing_vars = []
    for var in required_vars:
        if os.getenv(var):
            print(f"  ✅ {var}: Configurada")
        else:
            print(f"  ❌ {var}: No configurada")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Variables de entorno faltantes: {', '.join(missing_vars)}")
        print("   Configura estas variables para probar la funcionalidad")
        return
    
    print("\n🧪 Ejecutando pruebas de funcionalidad...")
    
    # Test Google Drive
    drive_ok = test_google_drive_connection()
    
    # Test Slack
    slack_ok = test_slack_connection()
    
    # Test file upload (only if Drive is working)
    upload_ok = False
    if drive_ok:
        upload_ok = test_file_upload()
    
    # Test Slack notification (only if Slack is working)
    notification_ok = False
    if slack_ok:
        notification_ok = test_slack_notification()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Resumen de Pruebas:")
    print(f"  Conexión a Google Drive: {'✅ PASÓ' if drive_ok else '❌ FALLÓ'}")
    print(f"  Conexión a Slack: {'✅ PASÓ' if slack_ok else '❌ FALLÓ'}")
    print(f"  Subida de Archivos: {'✅ PASÓ' if upload_ok else '❌ FALLÓ'}")
    print(f"  Notificación de Slack: {'✅ PASÓ' if notification_ok else '❌ FALLÓ'}")
    
    if drive_ok and slack_ok and upload_ok and notification_ok:
        print("\n🎉 ¡Todas las pruebas pasaron! La integración está funcionando correctamente.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa los mensajes de error arriba.")

if __name__ == "__main__":
    main() 