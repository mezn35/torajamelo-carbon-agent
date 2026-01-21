import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# --- 1. Konfigurasi Halaman ---
st.set_page_config(page_title="Torajamelo Carbon Agent", page_icon="🌱")
st.title("🌱 Torajamelo AI Sustainability Assistant")
st.caption("Powered by Groq (Llama3) & LangChain - 100% Free Architecture")

# --- 2. Cek API Key ---
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    st.error("🚨 API Key belum disetting! Masukkan di Settings > Secrets Streamlit.")
    st.stop()

# --- 3. Definisi ALAT (Tools) ---
# Ini adalah "Skill" yang kita ajarkan ke AI. 
# Dia akan otomatis memilih alat ini jika user bertanya topik terkait.

@tool
def hitung_emisi_logistik(berat_kg: float, jarak_km: float, mode: str):
    """
    Gunakan alat ini untuk menghitung emisi pengiriman barang.
    Parameters:
    - berat_kg: Berat barang dalam Kilogram.
    - jarak_km: Jarak tempuh dalam KM (Estimasikan jarak antar kota jika user tidak memberi angka).
    - mode: Pilih salah satu: 'darat' (truk/mobil), 'udara' (pesawat), atau 'laut' (kapal).
    """
    # Faktor Emisi (kgCO2e per kg-km) - Estimasi Data Standar Logistik
    factors = {
        "darat": 0.0001,  # ~Truck Diesel
        "udara": 0.002,   # ~Air Freight (Sangat tinggi!)
        "laut": 0.00001   # ~Sea Freight (Paling rendah)
    }
    
    # Ambil faktor emisi berdasarkan mode, default ke 'darat' jika typo
    selected_factor = factors.get(mode.lower(), 0.0001)
    
    # Rumus: Berat x Jarak x Faktor
    total_emisi = berat_kg * jarak_km * selected_factor
    
    return {
        "detail": f"Logistik {mode} seberat {berat_kg}kg sejauh {jarak_km}km",
        "total_emisi_kgCO2e": round(total_emisi, 2),
        "pesan": "Perhitungan logistik selesai."
    }

@tool
def hitung_emisi_listrik(kwh: float, lokasi: str = "indonesia"):
    """
    Gunakan alat ini untuk menghitung emisi dari penggunaan listrik (kantor/toko).
    Parameters:
    - kwh: Jumlah konsumsi listrik dalam kWh.
    - lokasi: Lokasi penggunaan (default: indonesia).
    """
    # Grid Emission Factor Indonesia (Rata-rata ~0.79 kgCO2/kWh)
    factor = 0.79 
    total_emisi = kwh * factor
    return f"Penggunaan {kwh} kWh listrik di {lokasi} menghasilkan estimasi {round(total_emisi, 2)} kgCO2e."

# Daftarkan alat ke dalam list
tools = [hitung_emisi_logistik, hitung_emisi_listrik]

# --- 4. Otak AI (LLM Setup) ---
# Menggunakan model Llama3-8b yang sangat
