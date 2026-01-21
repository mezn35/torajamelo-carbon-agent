import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage

# --- 1. SETUP ---
st.set_page_config(page_title="Torajamelo Carbon Auditor", page_icon="🚫", layout="wide")
st.title("🚫 Torajamelo Strict Auditor")
st.caption("Zero Tolerance for Assumptions. Data must be explicit.")

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    st.error("🚨 API Key belum disetting!")
    st.stop()

# --- 2. DATABASE EMISI (STANDAR DEFRA 2023) ---
FAKTOR_EMISI = {
    # Key harus spesifik agar AI tidak asal pilih
    "truk_diesel": 0.00028,
    "mobil_box": 0.00032,
    "kereta_api_barang": 0.00003, # Khusus barang
    "pesawat_jarak_pendek": 0.00254, # < 400km (Boros)
    "pesawat_jarak_jauh": 0.00190,   # > 3000km (Efisien)
    "kapal_laut_kargo": 0.00001
}

# --- 3. ALAT DENGAN VALIDASI LAPIS BAJA ---
@tool
def validasi_dan_hitung(berat_kg: float = 0, jarak_km: float = 0, jenis_kendaraan: str = ""):
    """
    Alat tunggal untuk menghitung emisi.
    
    ATURAN KERAS (HARD RULES):
    1. Parameter 'berat_kg' TIDAK BOLEH 0. Jika user tidak sebut angka, isi 0.
    2. Parameter 'jarak_km' TIDAK BOLEH 0.
    3. Parameter 'jenis_kendaraan' harus persis salah satu dari:
       ['truk_diesel', 'mobil_box', 'kereta_api_barang', 'pesawat_jarak_pendek', 'pesawat_jarak_jauh', 'kapal_laut_kargo']
    
    JANGAN MENCOBA MENEBAK. KIRIM APA ADANYA DARI USER.
    """
    
    errors = []
    
    # Validasi 1: Berat
    if berat_kg <= 0:
        errors.append("❌ Berat barang (kg) belum diisi.")
        
    # Validasi 2: Jarak
    if jarak_km <= 0:
        errors.append("❌ Jarak tempuh (km) belum diketahui.")
        
    # Validasi 3: Jenis Kendaraan & Pencocokan Ketat
    kunci_ditemukan = None
    input_clean = jenis_kendaraan.lower().replace(" ", "_")
    
    # Cek apakah input user cocok dengan database
    if input_clean in FAKTOR_EMISI:
        kunci_ditemukan = input_clean
    else:
        # Jika tidak cocok persis, cek apakah mengandung kata kunci ambigu
        if "pesawat" in input_clean:
            errors.append("❌ Jenis Pesawat ambigu. Pilih: 'pesawat_jarak_pendek' atau 'pesawat_jarak_jauh'?")
        elif "kereta" in input_clean and "barang" not in input_clean:
             # Paksa user confirm kereta barang, bukan kereta penumpang
            errors.append("❌ Jenis Kereta ambigu. Apakah maksud Anda 'kereta_api_barang'?")
        elif "truk" in input_clean and "diesel" not in input_clean:
            errors.append("❌ Jenis Truk ambigu. Apakah maksud Anda 'truk_diesel'?")
        else:
            errors.append(f"❌ Kendaraan '{jenis_kendaraan}' tidak dikenal di database DEFRA.")

    # KEPUTUSAN FINAL
    if errors:
        return "\n".join(errors) + "\n\nMohon lengkapi data di atas agar saya bisa menghitung."
    
    # Jika lolos semua validasi, baru hitung
    faktor = FAKTOR_EMISI[kunci_ditemukan]
    total = berat_kg * jarak_km * faktor
    
    return {
        "status": "APPROVED",
        "detail": f"{berat_kg}kg x {jarak_km}km x {kunci_ditemukan}",
        "faktor": faktor,
        "total_emisi_kgCO2e": round(total, 4)
    }

tools = [validasi_dan_hitung]

# --- 4. OTAK AI (Strict Mode) ---
llm = ChatGroq(
    temperature=0, 
    model="llama-3.3-70b-versatile", 
    api_key=api_key
).bind_tools(tools)

# --- 5. UI ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Sistem Auditor Siap. Saya tidak akan menghitung jika data Berat, Jarak, dan Jenis Kendaraan tidak lengkap."}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Contoh: Kirim kain ke Jakarta"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        # System Prompt: DILARANG MENGHITUNG MANUAL
        messages_for_ai = [
            SystemMessage(content="""
            Kamu adalah Auditor Galak.
            1. JANGAN PERNAH menghitung manual pakai otakmu. WAJIB pakai tool `validasi_dan_hitung`.
            2. Jangan pernah menebak berat atau jarak. Jika user tidak sebut angka, kirim 0 ke tool.
            3. Jika Tool mengembalikan error (tanda ❌), bacakan error tersebut ke user dan minta kelengkapan data.
            """)
        ]
        
        for i, m in enumerate(st.session_state.messages):
            if i == 0: continue 
            role_class = HumanMessage if m["role"] == "user" else AIMessage
            messages_for_ai.append(role_class(content=m["content"]))
        
        try:
            response = llm.invoke(messages_for_ai)
            
            if response.tool_calls:
                status_container = st.status("🕵️ Memeriksa Kelengkapan Data...", expanded=True)
                tool_messages = []
                
                for tool_call in response.tool_calls:
                    # Tampilkan apa yang dikirim AI ke Tool (untuk debugging user)
                    args = tool_call["args"]
                    status_container.write(f"**Data Diterima:** Berat={args.get('berat_kg',0)}, Jarak={args.get('jarak_km',0)}, Jenis='{args.get('jenis_kendaraan','')}'")
                    
                    selected_tool = {t.name: t for t in tools}[tool_call["name"]]
                    tool_output = selected_tool.invoke(args)
                    
                    if isinstance(tool_output, str) and "❌" in tool_output:
                        status_container.error("Data Tidak Lengkap / Ambigu!")
                    else:
                        status_container.success("Data Valid! Menghitung...")
                    
                    tool_messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(tool_output)))
                
                status_container.update(label="Validasi Selesai", state="complete", expanded=False)

                messages_for_ai.append(response) 
                messages_for_ai.extend(tool_messages)
                
                final_response = llm.invoke(messages_for_ai)
                st.write(final_response.content)
                st.session_state.messages.append({"role": "assistant", "content": final_response.content})
            
            else:
                st.write(response.content)
                st.session_state.messages.append({"role": "assistant", "content": response.content})

        except Exception as e:
            st.error(f"Error: {str(e)}")
