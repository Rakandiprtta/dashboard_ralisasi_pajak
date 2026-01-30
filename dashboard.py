import pandas as pd
import streamlit as st
import plotly.express as px
import time
from streamlit_autorefresh import st_autorefresh
from streamlit_echarts import st_echarts
from datetime import datetime
import io


if 'show_toast' not in st.session_state:
    st.session_state.show_toast = False

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Dashboard Realisasi Anggaran", layout="wide")

# 2. LOAD DATA
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("Data_Pembukuan_SAKTI_Dummy.xlsx")
       
        # Tambahkan .dt.normalize() agar jam 00:00:00 tidak mengganggu filter
        df["Tanggal Transaksi"] = pd.to_datetime(df["Tanggal Transaksi"]).dt.normalize()
        
        df["Akun Belanja"] = df["Akun Belanja"].astype(str)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")

    return pd.DataFrame()

df = load_data()

with st.status("Menghubungkan ke database...", expanded=True) as status:
    st.write("Membaca file Excel...")
    df = load_data()
    st.write("Menghitung total realisasi...")
    # (Opsional) kasih jeda dikit biar loadingnya kelihatan
    import time
    time.sleep(1) 
    status.update(label="Data Berhasil Dimuat!", state="complete", expanded=False)

if not df.empty:

    with st.container():
        st.title("Dashboard Realisasi Anggaran Pajak")
        st.caption(f"Update Terakhir: {datetime.now().strftime('%H:%M:%S')}")

if st.sidebar.button("Ambil Data Terbaru"):
    st.cache_data.clear() # Menghapus cache agar dia membaca ulang Excel
    st.rerun()

if st.sidebar.button("Reset Filter"):
    st.session_state.show_toast = True  # Tandai bahwa toast boleh muncul
    st.rerun()

st.sidebar.markdown("---")

min_date = df["Tanggal Transaksi"].min().date()
max_date = df["Tanggal Transaksi"].max().date()
date_range = st.sidebar.date_input("Rentang Waktu:", value=(min_date, max_date))

    # Filter Jenis
jenis_list = df["Jenis Belanja"].unique()
jenis_filter = st.sidebar.multiselect("Jenis Belanja:", jenis_list, default=jenis_list)

df_filtered = df.copy()

    # 2. Saring berdasarkan Akun & Jenis (Selalu jalan)
df_filtered = df_filtered[
        (df_filtered["Jenis Belanja"].isin(jenis_filter))
    ]

    # 3. Saring berdasarkan Tanggal (HANYA jika rentang sudah lengkap 2 klik)
if isinstance(date_range, tuple) and len(date_range) == 2:
        start_dt, end_dt = date_range
        mask = (df_filtered["Tanggal Transaksi"].dt.date >= start_dt) & \
               (df_filtered["Tanggal Transaksi"].dt.date <= end_dt)
        df_filtered = df_filtered.loc[mask]

if not df_filtered.empty:
    st.toast(f"Berhasil memuat {len(df_filtered)} transaksi!", icon="💰")
else:
    st.toast("Data tidak ditemukan untuk filter ini.", icon="⚠️")

    # 4. HEADER & KPI DENGAN ANIMASI
    
if 'prev_total' not in st.session_state: st.session_state.prev_total = 0
    
total_now = df_filtered["Nilai Transaksi"].sum()
delta = total_now - st.session_state.prev_total
    
kpi_spot = st.empty()
for i in range(11): # Animasi counting
     with kpi_spot.container():
            c1, c2, c3 = st.columns(3)
            curr_v = st.session_state.prev_total + (delta * i / 10)
            c1.metric("Total Realisasi", f"Rp {curr_v:,.0f}", delta=f"{delta:,.0f}")
            c2.metric("Jumlah Transaksi", f"{len(df_filtered)}")
            c3.metric("Rata-rata", f"Rp {df_filtered['Nilai Transaksi'].mean():,.0f}" if len(df_filtered)>0 else "0")
            time.sleep(0.01)
st.session_state.prev_total = total_now

st.markdown("---")

    # 5. GRAFIK SEJAJAR (BAR & PIE)
col1, col2 = st.columns([2, 1])
    
with col1:
    st.subheader("Realisasi per Akun")
    summary = df_filtered.groupby("Akun Belanja")["Nilai Transaksi"].sum().reset_index().sort_values("Nilai Transaksi")
    fig_bar = px.bar(summary, x="Nilai Transaksi", y="Akun Belanja", orientation='h', 
                         color="Nilai Transaksi", color_continuous_scale="Blues")
    fig_bar.update_layout(yaxis={'type':'category'}, height=350)
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.subheader("Komposisi Belanja")
    fig_pie = px.pie(df_filtered, values="Nilai Transaksi", names="Jenis Belanja", hole=0.4)
    fig_pie.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig_pie, use_container_width=True)

    # 6. LINE CHART (TREN)
st.subheader("Tren Realisasi Harian")
tren = df_filtered.groupby("Tanggal Transaksi")["Nilai Transaksi"].sum().reset_index()
fig_line = px.area(tren, x="Tanggal Transaksi", y="Nilai Transaksi", line_shape="spline")
st.plotly_chart(fig_line, use_container_width=True)

    # 7. TABEL & DOWNLOAD
st.subheader("Detail Transaksi")
df_tampilan = df_filtered.copy()
df_tampilan["Nilai Transaksi"] = df_tampilan["Nilai Transaksi"].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
st.dataframe(df_tampilan, use_container_width=True, hide_index=True)
    
    # Tombol Download
buffer = io.BytesIO()
df_filtered.to_excel(buffer, index=False, engine='xlsxwriter')
st.download_button("📥 Download Excel", data=buffer.getvalue(), file_name="realisasi.xlsx")

if df.empty:
    st.error("File Excel tidak ditemukan atau data kosong!")