import os
import shutil
import json
import boto3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
STORAGE_MODE = os.getenv("STORAGE_MODE", "LOCAL").upper()
DATASET_ROOT = "server_data/ai_dataset"
BUCKET_NAME = os.getenv("CLOUD_BUCKET_NAME")

# S3 Client Initialization (Cloud Mode only)
s3_client = None
if STORAGE_MODE == "CLOUD":
    try:
        s3_client = boto3.client('s3',
            endpoint_url=os.getenv("CLOUD_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("CLOUD_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("CLOUD_SECRET_KEY")
        )
    except Exception as e:
        print(f"[INIT ERROR] Cloud config missing. Fallback to LOCAL. Error: {e}")
        STORAGE_MODE = "LOCAL"

# Ensure Local Directories Exist
os.makedirs(f"{DATASET_ROOT}/corrupt", exist_ok=True)
os.makedirs(f"{DATASET_ROOT}/fixed", exist_ok=True)
os.makedirs(f"{DATASET_ROOT}/metadata", exist_ok=True)

def archive_session(task_id: str, source_corrupt: str, source_fixed: str, repair_details: dict, status: str = "SUCCESS", error_log: str = None):
    """
    This function decides whether to move files to Local Archive or Upload to Cloud.
    It is synchronous (def, not async def) to run safely in FastAPI BackgroundTasks threadpool.
    """
    
    # Metadata Payload Generation
    meta_payload = {
        "task_id": task_id,
        "timestamp": datetime.utcnow().isoformat(),
        "storage_mode": STORAGE_MODE,
        "status": status,
        "error_log": error_log,
        "details": repair_details
    }

    print(f"[ARCHIVE] Starting archive for {task_id} in {STORAGE_MODE} mode...")

    # ==============================
    # SCENARIO A: CLOUD STORAGE
    # ==============================
    if STORAGE_MODE == "CLOUD" and s3_client:
        try:
            # 1. Upload Corrupt File
            if os.path.exists(source_corrupt):
                s3_client.upload_file(source_corrupt, BUCKET_NAME, f"corrupt/{task_id}.bin")
            
            # 2. Upload Fixed File (If exists)
            if source_fixed and os.path.exists(source_fixed):
                s3_client.upload_file(source_fixed, BUCKET_NAME, f"fixed/{task_id}.bin")
            
            # 3. Upload Metadata (JSON)
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=f"metadata/{task_id}.json",
                Body=json.dumps(meta_payload, indent=2),
                ContentType='application/json'
            )
            
            print(f"[SUCCESS] Task {task_id} uploaded to Cloud.")
            
            # 4. CLEANUP: Delete local temp files
            if os.path.exists(source_corrupt): os.remove(source_corrupt)
            if source_fixed and os.path.exists(source_fixed): os.remove(source_fixed)
            
            return True

        except Exception as e:
            print(f"[ERROR] Cloud Upload Failed: {e}. Falling back to Local...")
            # Fallback to local on failure

    # ==============================
    # SCENARIO B: LOCAL ARCHIVE (Default/Fallback)
    # ==============================
    try:
        # Target Paths
        dest_corrupt = f"{DATASET_ROOT}/corrupt/{task_id}.bin"
        dest_fixed = f"{DATASET_ROOT}/fixed/{task_id}.bin"
        dest_meta = f"{DATASET_ROOT}/metadata/{task_id}.json"

        # 1. Move/Copy Files
        if os.path.exists(source_corrupt):
            shutil.copy2(source_corrupt, dest_corrupt)
        if source_fixed and os.path.exists(source_fixed):
            shutil.copy2(source_fixed, dest_fixed)

        # 2. Save JSON Log
        with open(dest_meta, 'w', encoding='utf-8') as f:
            json.dump(meta_payload, f, indent=4)

        print(f"[SUCCESS] Task {task_id} saved to Local Archive.")
        
        # 3. Cleanup Original Temp Files
        if os.path.exists(source_corrupt): os.remove(source_corrupt) 
        if source_fixed and os.path.exists(source_fixed): os.remove(source_fixed)
        
        return True

    except Exception as e:
        print(f"[CRITICAL] Failed to archive locally: {e}")
        return False
