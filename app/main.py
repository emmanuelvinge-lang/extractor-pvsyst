from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List
import shutil
import os
import uuid
from .extractor import process_pdf, process_pdf_data

app = FastAPI()

# Directorios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(TEMP_DIR, exist_ok=True)

# Montar archivos estáticos (Frontend)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Endpoint que acepta uno o múltiples archivos PDF"""
    
    if not files:
        raise HTTPException(status_code=400, detail="No se recibieron archivos")
    
    # Validar que todos sean PDFs
    for file in files:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"El archivo {file.filename} no es un PDF")

    # Generar ID único para este lote
    batch_id = str(uuid.uuid4())
    excel_filename = f"{batch_id}.xlsx"
    excel_path = os.path.join(TEMP_DIR, excel_filename)
    
    all_data = []
    
    try:
        # Procesar cada PDF
        for file in files:
            file_id = str(uuid.uuid4())
            pdf_filename = f"{file_id}.pdf"
            pdf_path = os.path.join(TEMP_DIR, pdf_filename)
            
            # Guardar PDF temporalmente
            with open(pdf_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Procesar PDF
            data, error = process_pdf_data(pdf_path)
            
            if error:
                # Si hay error, agregar fila con error
                data = {"Nombre del Archivo": file.filename, "Error": error}
            else:
                # Agregar nombre del archivo al inicio
                data = {"Nombre del Archivo": file.filename, **data}
            
            all_data.append(data)
            
            # Limpiar PDF temporal
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        
        # Crear DataFrame consolidado y guardar Excel
        import pandas as pd
        df = pd.DataFrame(all_data)
        df.to_excel(excel_path, index=False)
        
        return JSONResponse(content={
            "message": f"Extracción exitosa de {len(files)} archivo(s)",
            "data": all_data,
            "download_url": f"/download/{excel_filename}"
        })

    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(TEMP_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename="Reporte_Procesado.xlsx")
    raise HTTPException(status_code=404, detail="Archivo no encontrado")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
