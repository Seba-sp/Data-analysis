import os
from batch_process import run_batch_pipeline
from storage import StorageClient

if __name__ == "__main__":
    # Read options from environment variables or set defaults
    category = os.getenv("CATEGORY") or None
    course = os.getenv("COURSE") or None
    download_only = os.getenv("DOWNLOAD_ONLY", "False").lower() == "true"
    analysis_only = os.getenv("ANALYSIS_ONLY", "False").lower() == "true"
    no_upload = os.getenv("NO_UPLOAD", "False").lower() == "true"

    print(f"[Cloud Run Job] Starting batch process with options:")
    if category:
        print(f"  category: {category}")
    if course:
        print(f"  course: {course}")
    print(f"  download_only: {download_only}")
    print(f"  analysis_only: {analysis_only}")
    print(f"  no_upload: {no_upload}")

    # Validate storage configuration
    print(f"[Cloud Run Job] Validating storage configuration...")
    try:
        storage = StorageClient()
        backend_info = storage.get_backend_info()
        print(f"  Storage backend: {backend_info['backend']}")
        if backend_info['backend'] == 'gcp':
            print(f"  GCS bucket: {backend_info['bucket_name']}")
    except Exception as e:
        print(f"[Cloud Run Job] Storage configuration error: {e}")
        print("[Cloud Run Job] Please ensure GCP_BUCKET_NAME is set when using STORAGE_BACKEND=gcp")
        raise

    try:
        run_batch_pipeline(
            config_path="cursos.yml",
            category=category,
            course_id=course,
            download_only=download_only,
            analysis_only=analysis_only,
            no_upload=no_upload
        )
        print("[Cloud Run Job] Batch process completed successfully.")
    except Exception as e:
        print(f"[Cloud Run Job] ERROR: {e}")
        raise