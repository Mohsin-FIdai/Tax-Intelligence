from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import shutil
from pathlib import Path
import asyncio
from run_pipeline import run_full_pipeline
from backend.services.data_service import DataService

router = APIRouter(prefix="/api/v1/system", tags=["System"])

RAW_DIR = Path("data/raw_uploads")

@router.post("/upload")
async def upload_datasets(files: list[UploadFile] = File(...)):
    """Upload raw organization CSV/XLSX files to raw_uploads directory."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    saved_files = []
    
    for file in files:
        if not file.filename.endswith(('.csv', '.xlsx')):
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")
        
        # Normalize target filename if needed or keep original
        file_path = RAW_DIR / file.filename
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(file.filename)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save {file.filename}: {str(e)}")
            
    return {
        "status": "success", 
        "message": f"Successfully uploaded {len(saved_files)} files.", 
        "files": saved_files
    }

pipeline_state = {
    "status": "idle",
    "message": "Ready"
}

@router.post("/run-pipeline")
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """Execute the ML data pipeline and reload the DataService memory."""
    if pipeline_state["status"] == "running":
        return {"status": "error", "message": "Pipeline is already running!"}
        
    pipeline_state["status"] = "running"
    pipeline_state["message"] = "Processing data (ETL, Graph, ML)... This can take up to 10 minutes on a fresh run."
    
    def run_and_reload():
        try:
            run_full_pipeline()
            svc = DataService()
            svc.reload()
            
            # Re-initialize embeddings index if the service is imported
            try:
                from backend.services.embedding_service import EmbeddingService
                emb = EmbeddingService()
                emb.initialize_index()
            except ImportError:
                pass
                
            pipeline_state["status"] = "completed"
            pipeline_state["message"] = f"Pipeline complete! {len(svc.citizens_df) if svc.citizens_df is not None else 0} citizen profiles successfully compiled and loaded."
        except Exception as e:
            pipeline_state["status"] = "error"
            pipeline_state["message"] = f"Pipeline failed: {str(e)}"
            print(f"Pipeline background task failed: {e}")

    # Run pipeline in a background thread to prevent browser timeouts
    background_tasks.add_task(run_and_reload)
    
    return {
        "status": "success", 
        "message": "Pipeline started in background."
    }

@router.get("/pipeline-status")
async def get_pipeline_status():
    """Return the current status of the background pipeline."""
    return pipeline_state

@router.get("/datasets")
async def list_datasets():
    """List all CSV/XLSX files currently inside raw_uploads directory."""
    if not RAW_DIR.exists():
        return {"datasets": []}
        
    datasets = []
    for file_path in RAW_DIR.glob("*"):
        if file_path.suffix.lower() in ('.csv', '.xlsx'):
            domain = "Unknown"
            name_lower = file_path.name.lower()
            if "tax" in name_lower or "fbr" in name_lower:
                domain = "TAX RECORDS"
            elif "property" in name_lower or "revenue" in name_lower:
                domain = "PROPERTY"
            elif "vehicle" in name_lower or "excise" in name_lower:
                domain = "VEHICLE"
            elif "business" in name_lower or "secp" in name_lower:
                domain = "BUSINESS"
            elif "utility" in name_lower or "wapda" in name_lower or "iesco" in name_lower or "bill" in name_lower:
                domain = "UTILITY"
            elif "travel" in name_lower or "fia" in name_lower:
                domain = "TRAVEL"
            elif "mobile" in name_lower or "pta" in name_lower or "telecom" in name_lower:
                domain = "TELECOM"
            elif "bank" in name_lower or "sbp" in name_lower:
                domain = "BANKING"
            elif "nadra" in name_lower or "citizen" in name_lower:
                domain = "CITIZEN REGISTRY"
                
            datasets.append({
                "name": file_path.name,
                "domain": domain,
                "size_kb": round(file_path.stat().st_size / 1024, 1),
                "status": "Loaded"
            })
            
    return {"datasets": datasets}
