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
# Menggunakan model Llama3-8b yang sangat cepat di Groq
llm = ChatGroq(
    temperature=0, 
    model="llama3-8b-8192", 
    api_key=api_key
).bind_tools(tools)

# --- 5. Interface Chat & Memory ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Halo! Saya Assistant Emisi Torajamelo. Saya bisa bantu hitung jejak karbon pengiriman kain atau listrik kantor. Mau hitung apa hari ini?"}
    ]

# Tampilkan history chat
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Input User
if prompt := st.chat_input("Contoh: Hitung emisi kirim 10kg kain dari Jakarta ke Bali naik pesawat"):
    # 1. Tampilkan pesan user
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # 2. Proses di Backend
    with st.chat_message("assistant"):
        # Siapkan history pesan untuk dikirim ke AI
        messages_for_ai = [
            HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"])
            for m in st.session_state.messages
        ]
        
        # --- PHASE 1: AI BERPIKIR ---
        response = llm.invoke(messages_for_ai)
        
        # Cek apakah AI memutuskan untuk menggunakan ALAT?
        if response.tool_calls:
            status_container = st.status("🤖 Sedang menghitung...", expanded=True)
            
            # Eksekusi alat yang diminta AI
            tool_messages = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                status_container.write(f"Menggunakan alat: `{tool_name}`")
                status_container.write(f"Data: {tool_args}")
                
                # Cari fungsi yang sesuai dan jalankan
                selected_tool = {t.name: t for t in tools}[tool_name]
                tool_output = selected_tool.invoke(tool_args)
                
                # Simpan hasil alat
                tool_messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(tool_output)))
                status_container.write("✅ Perhitungan selesai.")
            
            status_container.update(label="Selesai!", state="complete", expanded=False)

            # --- PHASE 2: AI MERANGKUM HASIL ---
            # Masukkan hasil alat kembali ke memori AI agar dia bisa menjelaskannya ke user
            messages_for_ai.append(response) 
            messages_for_ai.extend(tool_messages)
            
            final_response = llm.invoke(messages_for_ai)
            response_content = final_response.content
            
        else:
            # Jika tidak pakai alat (chat biasa)
            response_content = response.content

        st.write(response_content)
        st.session_state.messages.append({"role": "assistant", "content": response_content})
