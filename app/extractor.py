import pdfplumber
import re
import pandas as pd
import os
def extract_value(text, pattern, group_index=1):
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(group_index)
    return None
def process_pdf_data(pdf_path):
    """Procesa un PDF y retorna solo los datos extraídos sin guardar Excel"""
    print(f"Procesando {pdf_path}...")
    
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
    except Exception as e:
        return None, f"Error al abrir el PDF: {str(e)}"
    # Diccionario para guardar los datos extraídos
    data = {}
    # 1. Potencia DC [kWp]
    data['Potencia DC [kWp]'] = extract_value(full_text, r"System power\s*:\s*([\d\.]+)\s*kWp")
    if not data['Potencia DC [kWp]']:
        data['Potencia DC [kWp]'] = extract_value(full_text, r"Pnom total\s*([\d\.]+)\s*kWp")
    # 2. Potencia AC [kWn]
    data['Potencia AC [kWn]'] = extract_value(full_text, r"Grid power limit\s*([\d\.]+)\s*kWac")
    if not data['Potencia AC [kWn]']:
         data['Potencia AC [kWn]'] = extract_value(full_text, r"Total power\s*([\d\.]+)\s*kVA")
    # 3. Producción específica y Generación neta - DETECCIÓN AUTOMÁTICA DE PERCENTILES
    # Buscar todos los percentiles que aparezcan en el documento (P10, P25, P50, P75, P90, P95, P99, etc.)
    
    # Encontrar todos los percentiles únicos en el texto
    percentiles_found = set()
    
    # Buscar patrones de Specific production (P##)
    specific_matches = re.findall(r"Specific production \((P\d+)\)", full_text, re.IGNORECASE)
    percentiles_found.update(specific_matches)
    
    # Buscar patrones de Produced Energy (P##)
    energy_matches = re.findall(r"Produced Energy \((P\d+)\)", full_text, re.IGNORECASE)
    percentiles_found.update(energy_matches)
    
    # Ordenar percentiles numéricamente (P50, P75, P90, etc.)
    percentiles_sorted = sorted(percentiles_found, key=lambda x: int(x[1:]))
    
    # Extraer valores para cada percentil encontrado
    for percentile in percentiles_sorted:
        # Producción específica (kWh/kWp/year)
        pattern_specific = rf"Specific production \({percentile}\)\s*([\d]+)\s*kWh/kWp/year"
        value = extract_value(full_text, pattern_specific)
        if value:  # Solo agregar si se encontró el valor
            data[f'Producción específica {percentile} [kWh/kWp/año]'] = value
        
        # Generación neta esperada (MWh/year)
        pattern_energy = rf"Produced Energy \({percentile}\)\s*([\d\.]+)\s*MWh/year"
        value = extract_value(full_text, pattern_energy)
        if value:  # Solo agregar si se encontró el valor
            data[f'Generación neta esperada {percentile} [MWh/año]'] = value
    # 5. Performance Ratio (PR)
    data['Performance Ratio (PR) [%]'] = extract_value(full_text, r"Perf\. Ratio PR\s*([\d\.,]+)\s*%")
    # 6. y 7. Módulos e Inversores
    try:
        match_section = re.search(r"PV Array Characteristics\s+PV module", full_text)
        
        if match_section:
            section_start = match_section.start()
            section_text = full_text[section_start:section_start+1000]
            
            man_match = re.search(r"Manufacturer\s+(?P<pv_man>.+?)\s+Manufacturer\s+(?P<inv_man>.+)", section_text)
            pv_man = man_match.group("pv_man").strip() if man_match else "Unknown"
            inv_man = man_match.group("inv_man").strip() if man_match else "Unknown"
            model_match = re.search(r"Model\s+(?P<pv_model>.+?)\s+Model\s+(?P<inv_model>.+)", section_text)
            pv_model = model_match.group("pv_model").strip() if model_match else "Unknown"
            inv_model = model_match.group("inv_model").strip() if model_match else "Unknown"
        else:
            pv_man, inv_man, pv_model, inv_model = "Unknown", "Unknown", "Unknown", "Unknown"
            
    except Exception as e:
        pv_man, inv_man, pv_model, inv_model = "Error", "Error", "Error", "Error"
    pv_power = extract_value(full_text, r"Unit Nom\. Power\s*([\d]+)Wp")
    pv_count = extract_value(full_text, r"Nb\. of modules\s*(\d+)\s*units")
    data['Módulos Fotovoltaicos'] = f"{pv_man} {pv_model} ({pv_power} Wp) - {pv_count} unidades"
    inv_count = extract_value(full_text, r"Nb\. of units\s*(\d+)\s*units")
    data['Inversores'] = f"{inv_man} {inv_model} - {inv_count} unidades"
    # 8. Base de datos meteorológicos (capturar solo dataset y proveedor, max 2 líneas)
    weather_match = re.search(r"Weather data\s*[:]?\s*\n([^\n]+)\n([^\n]+)", full_text, re.IGNORECASE)
    if weather_match:
        dataset = weather_match.group(1).strip()
        provider = weather_match.group(2).strip()
        data['Base de datos meteorológicos'] = f"{dataset} {provider}"
    else:
        # fallback a una sola línea
        alt_match = re.search(r"Weather data\s*[:]?\s*\n([^\n]+)", full_text, re.IGNORECASE)
        data['Base de datos meteorológicos'] = alt_match.group(1).strip() if alt_match else "No detectado"
    # 9. Capacidad del Transformador
    trf_match = extract_value(full_text, r"Transformer from Datasheets.*?Nominal power\s*([\d\.]+)\s*kVA", group_index=1)
    if not trf_match:
         trf_match = extract_value(full_text, r"Nominal power\s*([\d\.]+)\s*kVA")
    data['Capacidad del Transformador [kW]'] = trf_match if trf_match else "No detectado"
    return data, None
def process_pdf(pdf_path, output_path):
    """Procesa un PDF y guarda los datos en Excel (mantiene compatibilidad)"""
    data, error = process_pdf_data(pdf_path)
    if error:
        return None, error
    
    # Crear DataFrame y guardar a Excel
    try:
        df = pd.DataFrame([data])
        df.to_excel(output_path, index=False)
        return data, None
    except Exception as e:
        return None, f"Error al generar Excel: {str(e)}"
