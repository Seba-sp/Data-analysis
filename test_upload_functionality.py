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

def debug_list_shared_drives_and_folders():
    print("\n[DEBUG] Listando Shared Drives accesibles y carpetas visibles:")
    try:
        drive_service = get_drive_service()
        # List all accessible Shared Drives
        drives = drive_service.drives().list().execute().get('drives', [])
        if not drives:
            print("[DEBUG] No se encontraron Shared Drives accesibles para la service account.")
        for d in drives:
            print(f"  Shared Drive: {d['name']} (ID: {d['id']})")
            # List folders in this Shared Drive
            folder_results = drive_service.files().list(
                q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora='drive',
                driveId=d['id']
            ).execute()
            for f in folder_results.get('files', []):
                print(f"    Carpeta: {f['name']} (ID: {f['id']})")
    except Exception as e:
        import traceback
        print(f"[DEBUG] Error al listar Shared Drives o carpetas: {e}")
        traceback.print_exc()


def create_folder_in_shared_drive(shared_drive_id, folder_name):
    print(f"\n[DEBUG] Intentando crear carpeta '{folder_name}' en Shared Drive ID: {shared_drive_id}")
    try:
        drive_service = get_drive_service()
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'driveId': shared_drive_id
        }
        folder = drive_service.files().create(
            body=folder_metadata,
            fields='id, name',
            supportsAllDrives=True
        ).execute()
        print(f"[DEBUG] Carpeta creada: {folder['name']} (ID: {folder['id']})")
        return folder['id']
    except Exception as e:
        import traceback
        print(f"[DEBUG] Error al crear carpeta: {e}")
        traceback.print_exc()
        return None

def test_google_drive_connection():
    """Test Google Drive service connection"""
    print("🧪 Probando conexión a Google Drive...")
    
    try:
        print("[DEBUG] Inicializando servicio de Google Drive...")
        drive_service = get_drive_service()
        print("✅ Servicio de Google Drive inicializado exitosamente")
        return True
    except Exception as e:
        import traceback
        print(f"❌ Conexión a Google Drive falló: {e}")
        traceback.print_exc()
        return False

def test_slack_connection():
    """Test Slack client connection"""
    print("🧪 Probando conexión a Slack...")
    
    try:
        print("[DEBUG] Inicializando cliente de Slack...")
        slack_client = get_slack_client()
        print("✅ Cliente de Slack inicializado exitosamente")
        return True
    except Exception as e:
        import traceback
        print(f"❌ Conexión a Slack falló: {e}")
        traceback.print_exc()
        return False

def test_file_upload():
    """Test file upload to Google Drive (with replace logic and per-course folder)"""
    print("🧪 Probando subida de archivo a Google Drive...")
    from datetime import datetime
    try:
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Este es un archivo de prueba para la funcionalidad de subida a Google Drive.")
            temp_file_path = f.name
        file_size = os.path.getsize(temp_file_path)
        today = datetime.now().date()
        mtime = datetime.fromtimestamp(os.path.getmtime(temp_file_path)).date()
        ctime = datetime.fromtimestamp(os.path.getctime(temp_file_path)).date()
        if mtime != today and ctime != today:
            print(f"[DEBUG] Archivo de prueba no es de hoy, omitiendo subida.")
            os.unlink(temp_file_path)
            return False
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        print(f"[DEBUG] Archivo temporal creado: {temp_file_path} (tamaño: {file_size} bytes)")
        print(f"[DEBUG] Subiendo a carpeta de Drive con ID: {folder_id}")
        # Use a per-course folder for the test
        from analisis import get_drive_service, find_or_create_folder, upload_file_to_drive
        drive_service = get_drive_service()
        test_folder_id = find_or_create_folder(drive_service, folder_id, 'test-upload')
        # Upload the file (should replace if exists)
        drive_link = upload_file_to_drive(temp_file_path, "test_upload.txt", test_folder_id)
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
        import traceback
        print(f"❌ Prueba de subida de archivo falló: {e}")
        traceback.print_exc()
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
    
    # Debug: List accessible Shared Drives and folders
    debug_list_shared_drives_and_folders()
    
    # Optionally: Try to create a folder in a Shared Drive (uncomment and set ID)
    # shared_drive_id = 'TU_SHARED_DRIVE_ID_AQUI'
    # create_folder_in_shared_drive(shared_drive_id, 'carpeta-creada-por-service-account')
    
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