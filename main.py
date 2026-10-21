from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import pdfplumber
import pytesseract
from PIL import Image
import io
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def limpiar_precio(val):
    if pd.isna(val):
        return 0.0
    val_str = str(val)
    match = re.search(r'[\d.,]+', val_str)
    if not match:
        return 0.0
    num_str = match.group(0).replace(',', '.')
    try:
        return float(num_str)
    except ValueError:
        return 0.0

@app.post("/procesar-lista")
async def procesar_lista(archivo: UploadFile = File(...)):
    try:
        contents = await archivo.read()
        filename = archivo.filename.lower()
        productos_extraidos = []

        if filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(contents))
            for _, row in df.iterrows():
                cols = row.dropna().tolist()
                if len(cols) >= 2:
                    productos_extraidos.append({
                        "nombre_original": str(cols[0]).strip(),
                        "precio": limpiar_precio(cols[1]),
                        "catalogo_id": None,
                        "nombre_estandarizado_sugerido": str(cols[0]).strip()
                    })

        elif filename.endswith('.pdf'):
            with pdfplumber.open(io.BytesIO(contents)) as pdf:
                for page in pdf.pages:
                    tablas = page.extract_tables()
                    for tabla in tablas:
                        for fila in tabla:
                            fila_limpia = [c for c in fila if c is not None and str(c).strip() != '']
                            if len(fila_limpia) >= 2:
                                productos_extraidos.append({
                                    "nombre_original": str(fila_limpia[0]).strip(),
                                    "precio": limpiar_precio(fila_limpia[1]),
                                    "catalogo_id": None,
                                    "nombre_estandarizado_sugerido": str(fila_limpia[0]).strip()
                                })

        elif filename.endswith(('.png', '.jpg', '.jpeg')):
            imagen = Image.open(io.BytesIO(contents))
            texto_ocr = pytesseract.image_to_string(imagen)
            for linea in texto_ocr.split('\n'):
                linea = linea.strip()
                if linea:
                    partes = re.split(r'\s+(\$?\d+[\.,]?\d*)', linea)
                    if len(partes) >= 2:
                        productos_extraidos.append({
                            "nombre_original": partes[0].strip(),
                            "precio": limpiar_precio(partes[1]),
                            "catalogo_id": None,
                            "nombre_estandarizado_sugerido": partes[0].strip()
                        })

        return {"productos": productos_extraidos}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
