import os
import pandas as pd
import json
from io import StringIO
from pathlib import Path

class StorageClient:
    def __init__(self):
        self.backend = os.getenv('STORAGE_BACKEND', 'local')
        self.bucket_name = os.getenv('GCP_BUCKET_NAME')
        
        if self.backend == 'gcp':
            if not self.bucket_name:
                raise ValueError("GCP_BUCKET_NAME environment variable is required when STORAGE_BACKEND=gcp")
            
            from google.cloud import storage as gcs
            self.gcs_client = gcs.Client()
            self.bucket = self.gcs_client.bucket(self.bucket_name)

    def _local_path(self, path):
        return Path(path)

    def _gcs_path(self, path):
        # Always use forward slashes for GCS object names
        return str(path).replace('\\', '/')

    def exists(self, path):
        if self.backend == 'local':
            return self._local_path(path).exists()
        else:
            return self.bucket.blob(self._gcs_path(path)).exists()

    def read_csv(self, path, **kwargs):
        if self.backend == 'local':
            return pd.read_csv(self._local_path(path), **kwargs)
        else:
            blob = self.bucket.blob(self._gcs_path(path))
            data = blob.download_as_text()
            return pd.read_csv(StringIO(data), **kwargs)

    def write_csv(self, path, df, **kwargs):
        if self.backend == 'local':
            df.to_csv(self._local_path(path), **kwargs)
        else:
            blob = self.bucket.blob(self._gcs_path(path))
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, **kwargs)
            blob.upload_from_string(csv_buffer.getvalue(), content_type='text/csv')

    def read_json(self, path):
        if self.backend == 'local':
            with open(self._local_path(path), 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            blob = self.bucket.blob(self._gcs_path(path))
            data = blob.download_as_text()
            return json.loads(data)

    def write_json(self, path, obj):
        if self.backend == 'local':
            with open(self._local_path(path), 'w', encoding='utf-8') as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
        else:
            blob = self.bucket.blob(self._gcs_path(path))
            blob.upload_from_string(json.dumps(obj, ensure_ascii=False, indent=2), content_type='application/json')

    def read_text(self, path):
        if self.backend == 'local':
            with open(self._local_path(path), 'r', encoding='utf-8') as f:
                return f.read()
        else:
            blob = self.bucket.blob(self._gcs_path(path))
            return blob.download_as_text()

    def read_bytes(self, path):
        if self.backend == 'local':
            with open(self._local_path(path), 'rb') as f:
                return f.read()
        else:
            blob = self.bucket.blob(self._gcs_path(path))
            return blob.download_as_bytes()

    def write_bytes(self, path, data, content_type=None):
        if self.backend == 'local':
            with open(self._local_path(path), 'wb') as f:
                f.write(data)
            return True
        else:
            blob = self.bucket.blob(self._gcs_path(path))
            blob.upload_from_string(data, content_type=content_type)
            return True

    def list_files(self, prefix):
        if self.backend == 'local':
            p = self._local_path(prefix)
            if p.is_dir():
                return [str(f) for f in p.iterdir() if f.is_file()]
            else:
                return []
        else:
            return [b.name for b in self.bucket.list_blobs(prefix=self._gcs_path(prefix))]
    
    def ensure_directory(self, path):
        """Ensure directory exists (for local storage only)"""
        if self.backend == 'local':
            Path(path).mkdir(parents=True, exist_ok=True)
        # For GCS, directories are created automatically when files are uploaded
    
    def delete(self, path):
        """Delete a file from storage"""
        if self.backend == 'local':
            try:
                file_path = self._local_path(path)
                if file_path.exists():
                    file_path.unlink()
                    return True
                else:
                    return False
            except (FileNotFoundError, PermissionError, OSError) as e:
                print(f"Error deleting local file {path}: {e}")
                return False
        else:
            try:
                blob = self.bucket.blob(self._gcs_path(path))
                if blob.exists():
                    blob.delete()
                    return True
                else:
                    return False
            except Exception as e:
                print(f"Error deleting GCS file {path}: {e}")
                return False
    
    def get_backend_info(self):
        """Get information about the current storage backend configuration"""
        info = {
            'backend': self.backend,
            'bucket_name': self.bucket_name if self.backend == 'gcp' else None
        }
        return info
