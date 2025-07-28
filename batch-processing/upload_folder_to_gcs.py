import os
from google.cloud import storage
import argparse
from dotenv import load_dotenv
load_dotenv()


def get_bucket_name():
    bucket = os.getenv("GCP_BUCKET_NAME")
    if not bucket:
        raise ValueError("Bucket name not found in environment variable GCP_BUCKET_NAME.")
    return bucket

def normalize_gcs_path(path):
    # Always use forward slashes for GCS object names
    return str(path).replace("\\", "/")

def upload_file_to_gcs(bucket, local_file, gcs_folder="", replace=True):
    client = storage.Client()
    bucket = client.bucket(bucket)
    filename = os.path.basename(local_file)
    gcs_folder = normalize_gcs_path(gcs_folder)
    blob_path = normalize_gcs_path(os.path.join(gcs_folder, filename)) if gcs_folder else filename
    blob = bucket.blob(blob_path)
    if replace or not blob.exists():
        print(f"Uploading {local_file} to gs://{bucket.name}/{blob_path}")
        blob.upload_from_filename(local_file)
        print("Upload complete.")
    else:
        print(f"File {blob_path} already exists in bucket and --no-replace set. Skipping upload.")


def upload_folder_to_gcs(bucket, local_folder, gcs_folder="", replace=True):
    client = storage.Client()
    bucket = client.bucket(bucket)
    gcs_folder = normalize_gcs_path(gcs_folder)
    for root, _, files in os.walk(local_folder):
        for file in files:
            local_path = os.path.join(root, file)
            # Compute the GCS path (preserve subfolders)
            relative_path = os.path.relpath(local_path, local_folder)
            blob_path = normalize_gcs_path(os.path.join(gcs_folder, relative_path)) if gcs_folder else normalize_gcs_path(relative_path)
            blob = bucket.blob(blob_path)
            if replace or not blob.exists():
                print(f"Uploading {local_path} to gs://{bucket.name}/{blob_path}")
                blob.upload_from_filename(local_path)
            else:
                print(f"File {blob_path} already exists in bucket and --no-replace set. Skipping upload.")
    print("Folder upload complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload a file or folder to a GCP bucket, preserving folder structure.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a single file to upload")
    group.add_argument("--folder", help="Path to a local folder to upload recursively")
    parser.add_argument("--gcs-folder", default="", help="(Optional) Folder path in the bucket to upload into")
    parser.add_argument("--no-replace", action="store_true", help="Do NOT replace file(s) in the bucket if they exist (default: always replace/overwrite)")
    args = parser.parse_args()

    bucket_name = get_bucket_name()
    replace = not args.no_replace
    if args.file:
        upload_file_to_gcs(bucket_name, args.file, args.gcs_folder, replace=replace)
    elif args.folder:
        upload_folder_to_gcs(bucket_name, args.folder, args.gcs_folder, replace=replace) 