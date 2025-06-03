# === IMPORT DAN SETUP ===
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import os
import io 
from io import BytesIO
import pickle
from datetime import datetime
import openpyxl

if "jurnal" not in st.session_state:
    st.session_state.jurnal = []

if "keterangan" not in st.session_state:
    st.session_state.keterangan = []

st.set_page_config(page_title="Zaki Telor", layout="wide")

# === FUNGSI SIMPAN & HAPUS SESSION STATE ===
FILE_SESSION = "session_jurnal.pkl"
FILE_KETERANGAN = "session_keterangan.pkl"

def simpan_session_state():
    if "jurnal" in st.session_state:
        with open(FILE_SESSION, "wb") as f:
            pickle.dump(st.session_state.jurnal, f)
    
    if "keterangan" in st.session_state:
        with open(FILE_KETERANGAN, "wb") as f:
            pickle.dump(st.session_state.keterangan, f)

def hapus_session_state_file():
    if os.path.exists(FILE_SESSION):
        os.remove(FILE_SESSION)
    if os.path.exists(FILE_KETERANGAN):
        os.remove(FILE_KETERANGAN)

if os.path.exists(FILE_SESSION):
    with open(FILE_SESSION, "rb") as f:
        st.session_state.jurnal = pickle.load(f)

if os.path.exists(FILE_KETERANGAN):
    with open(FILE_KETERANGAN, "rb") as f:
        st.session_state.keterangan = pickle.load(f) 

# === FUNGSI KATEGORI AKUN ===
def kategori_akun(nama_akun):
    nama = nama_akun.lower()
    if any(k in nama for k in ["penjualan"]):
        return "Pendapatan"
    elif any(k in nama for k in ["beban listrik", "beban air", "beban perawatan"]):
        return "Beban"
    elif any(k in nama for k in ["kas", "bangunan", "peralatan", "persediaan", "perlengkapan"]):
        return "Aktiva"
    elif "utang" in nama:
        return "Kewajiban"
    elif "modal" in nama:
        return "Modal"
    elif "prive" in nama or "pribadi" in nama:
        return "Prive"
    else:
        return "Lainnya"

# === FUNGSI EKSPOR EXCEL ===
def simpan_semua_ke_excel():
    if not st.session_state.get("jurnal"):
        return None, None
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_jurnal = pd.DataFrame(st.session_state.jurnal)
        df_jurnal.to_excel(writer, sheet_name="Jurnal Umum", index=False)

        # Buku Besar
        akun_list = df_jurnal["Akun"].unique()
        buku_besar_all = []
        for akun in akun_list:
            df_akun = df_jurnal[df_jurnal["Akun"] == akun].copy()
            df_akun["Saldo"] = df_akun["Debit"] - df_akun["Kredit"]
            df_akun["Saldo Akumulatif"] = df_akun["Saldo"].cumsum()
            df_akun.insert(0, "Nama Akun", akun)
            buku_besar_all.append(df_akun)
        df_buku_besar = pd.concat(buku_besar_all, ignore_index=True)
        df_buku_besar.to_excel(writer, sheet_name="Buku Besar", index=False)

        # Neraca Saldo
        ref_dict = df_jurnal.groupby("Akun")["Ref"].first().to_dict()
        neraca_saldo = df_jurnal.groupby("Akun")[["Debit", "Kredit"]].sum().reset_index()
        neraca_saldo["Saldo"] = neraca_saldo["Debit"] - neraca_saldo["Kredit"]
        neraca_saldo["Ref"] = neraca_saldo["Akun"].map(ref_dict)
        neraca_saldo = neraca_saldo.sort_values(by="Ref")
        cols = ["Ref", "Akun", "Debit", "Kredit", "Saldo"]
        neraca_saldo = neraca_saldo[cols]
        neraca_saldo.to_excel(writer, sheet_name="Neraca Saldo", index=False)

        # Laba Rugi
        df = df_jurnal
        pendapatan = df[df["Kategori"] == "Pendapatan"]["Kredit"].sum()
        beban = df[df["Kategori"] == "Beban"]["Debit"].sum()
        laba_bersih = pendapatan - beban
        df_laba_rugi = pd.DataFrame([
            {"Kategori": "Pendapatan", "Nominal": pendapatan},
            {"Kategori": "Beban", "Nominal": beban},
            {"Kategori": "Laba Bersih", "Nominal": laba_bersih},
        ])
        df_laba_rugi.to_excel(writer, sheet_name="Laba Rugi", index=False)

        # Perubahan Ekuitas
        modal_awal = df[df["Kategori"] == "Modal"]["Kredit"].sum()
        prive = df[df["Kategori"] == "Prive"]["Debit"].sum()
        modal_akhir = modal_awal + laba_bersih - prive
        df_ekuitas = pd.DataFrame([{
            "Modal Awal": modal_awal,
            "Laba Bersih": laba_bersih,
            "Prive": prive,
            "Modal Akhir": modal_akhir
        }])
        df_ekuitas.to_excel(writer, sheet_name="Perubahan Ekuitas", index=False)

        # Neraca
        aktiva = df[df["Kategori"] == "Aktiva"]
        kewajiban = df[df["Kategori"] == "Kewajiban"]
        total_aktiva = aktiva["Debit"].sum() - aktiva["Kredit"].sum()
        total_kewajiban = kewajiban["Kredit"].sum() - kewajiban["Debit"].sum()
        total_passiva = total_kewajiban + modal_akhir
        df_neraca = pd.DataFrame([
            {"Pos": "Aktiva", "Nominal": total_aktiva},
            {"Pos": "Kewajiban + Modal", "Nominal": total_passiva},
        ])
        df_neraca.to_excel(writer, sheet_name="Neraca", index=False)

    buffer.seek(0)
    filename = "laporan_keuangan.xlsx"
    return buffer, filename

# Reset login hanya sekali saat aplikasi mulai (belum ada flag reset_done)
if "reset_done" not in st.session_state:
    for key in ["login_success", "show_login_success", "username"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.reset_done = True

# Fungsi login page
def login_page():
    if "login_success" not in st.session_state:
        st.session_state.login_success = False
    if "show_login_success" not in st.session_state:
        st.session_state.show_login_success = False

    if not st.session_state.login_success:
        st.title("🔐 Login - Zaki Telor")

        with st.form("login_form"):
            username = st.text_input("Nama Akun")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                if username == "admin" and password == "zakitelor":
                    st.session_state.login_success = True
                    st.session_state.username = username
                    st.session_state.show_login_success = True
                    st.rerun()
                else:
                    st.error("Nama akun atau password salah!")

    elif st.session_state.show_login_success:
        st.success(f"Login berhasil! Selamat datang, {st.session_state.username} 👋")
        st.session_state.show_login_success = False

    return st.session_state.login_success

if not login_page():
    st.stop()

# Sidebar dengan Option Menu
with st.sidebar:
    st.title("LAPORAN KEUANGAN ZAKI TELOR 🐔🪺")
    st.write(f"👤 {st.session_state.username}")
    if st.button("Logout"):
        # Hapus semua key login
        for key in ["login_success", "show_login_success", "username", "reset_done"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
        
# === MENU ===
menu = ["📍 Beranda", "📝 Transaksi", "📅 Jurnal Umum", "📓 Buku Besar", "⚖️ Neraca Saldo", "📈 Laba Rugi", "📊 Perubahan Ekuitas", "📋 Posisi Keuangan"]
selected = st.sidebar.selectbox("Pilih Menu:", menu)

if selected == "📍 Beranda":
    st.title("💰LAPORAN KEUANGAN ZAKI TELOR 🐔")
    st.markdown("""
        ### Tentang Aplikasi
        Aplikasi ini dirancang untuk membantu dalam mencatat dan menyusun laporan keuangan secara praktis dan efisien.
        Fitur yang dapat dikelola antara lain:
        - Transaksi
        - Jurnal Umum
        - Buku Besar
        - Neraca Saldo
        - Laporan Laba Rugi
        - Perubahan Ekuitas
        - Laporan Posisi Keuangan (Neraca)

        ### Panduan Penggunaan
        1. Masukkan transaksi pada menu *Jurnal Umum*.
        2. Data akan otomatis terintegrasi ke *Buku Besar* dan *Neraca Saldo*.
        3. Untuk menyusun laporan laba rugi, perubahan ekuitas dan neraca, gunakan fitur input manual.
        4. Tekan tombol reset di tiap halaman untuk memulai pengisian data baru.

        ### Catatan
        - Pastikan setiap entri jurnal *seimbang* (total debit = total kredit).
        - Pastikan menginput dengan teliti dan cek secara berkala.
    """)

    st.info("Gunakan menu di sidebar untuk mulai mencatat dan melihat laporan keuangan Anda.")
    
# === HALAMAN KETERANGAN TRANSAKSI ===
if selected == "📝 Transaksi":
    st.title("📝 Keterangan Transaksi")
    if "keterangan" not in st.session_state:
        st.session_state.keterangan = []

    with st.form("form_keterangan"):
        tanggal = st.date_input("Tanggal Transaksi")
        deskripsi = st.text_area("Deskripsi Transaksi")
        submitted = st.form_submit_button("Simpan Keterangan")
        if submitted:
            st.session_state.keterangan.append({
                "Tanggal": tanggal.strftime("%Y-%m-%d"),
                "Deskripsi": deskripsi
            })
            simpan_session_state()
            st.success("Keterangan transaksi berhasil disimpan.")

    if st.session_state.keterangan:
        st.subheader("Daftar Keterangan Transaksi")
        st.dataframe(pd.DataFrame(st.session_state.keterangan))
        
    if st.button("🔁 Reset Keterangan Transaksi"):
        st.session_state.keterangan = []
        simpan_session_state()
        st.success("Semua keterangan transaksi telah direset.")

        
# === JURNAL UMUM ===
if selected == "📅 Jurnal Umum":
    st.header("📅 Jurnal Umum")
    if "jurnal" not in st.session_state:
        st.session_state.jurnal = []

    with st.form("form_jurnal"):
        st.subheader("Input Transaksi Jurnal")
        tanggal = st.date_input("Tanggal", value=datetime.today())
        keterangan = st.text_input("Akun")
        akun = st.text_input("Ref")
        col1, col2 = st.columns(2)
        with col1:
            debit = st.number_input("Debit (Rp)", min_value=0.0, format="%.2f")
        with col2:
            kredit = st.number_input("Kredit (Rp)", min_value=0.0, format="%.2f")
        submitted = st.form_submit_button("Tambah")

        if submitted:
            if akun:
                kategori = kategori_akun(keterangan)
                st.session_state.jurnal.append({
                    "Tanggal": tanggal.strftime("%Y-%m-%d"),
                    "Akun": keterangan,
                    "Ref": akun,
                    "Kategori": kategori,
                    "Debit": debit,
                    "Kredit": kredit
                })
                simpan_session_state()
            else:
                st.warning("Nama akun tidak boleh kosong!")

    if st.session_state.jurnal:
        df_jurnal = pd.DataFrame(st.session_state.jurnal)
        st.dataframe(df_jurnal, use_container_width=True)
        st.subheader("Edit Jurnal Jika Perlu:")
        df_edit = st.data_editor(df_jurnal, num_rows="dynamic", use_container_width=True, key="edit_jurnal")
        if st.button("Simpan Perubahan Jurnal"):
            st.session_state.jurnal = df_edit.to_dict(orient="records")
            simpan_session_state()
            st.success("Perubahan jurnal berhasil disimpan.")
        total_debit = df_jurnal["Debit"].sum()
        total_kredit = df_jurnal["Kredit"].sum()
        col1, col2 = st.columns(2)
        col1.metric("Total Debit", f"Rp {total_debit:,.2f}")
        col2.metric("Total Kredit", f"Rp {total_kredit:,.2f}")
        if total_debit == total_kredit:
            st.success("✅ Jurnal seimbang!")
        else:
            st.error("❌ Jurnal tidak seimbang!")

    if st.button("Reset Semua Data"):
        st.session_state.jurnal = []
        hapus_session_state_file()
        st.success("Data jurnal berhasil direset.")
        st.rerun()

# === BUKU BESAR ===
elif selected == "📓 Buku Besar":
    st.header("📓 Buku Besar")
    if "jurnal" in st.session_state and st.session_state.jurnal:
        df_jurnal = pd.DataFrame(st.session_state.jurnal)
        akun_list = df_jurnal["Akun"].unique()

        for akun in akun_list:
            st.subheader(f"Akun: {akun}")
            df_akun = df_jurnal[df_jurnal["Akun"] == akun].copy()
            df_akun["Saldo"] = df_akun["Debit"] - df_akun["Kredit"]
            df_akun["Saldo Akumulatif"] = df_akun["Saldo"].cumsum()

            st.dataframe(df_akun[["Tanggal", "Akun", "Debit", "Kredit", "Saldo Akumulatif"]], use_container_width=True)
            saldo_akhir = df_akun["Saldo Akumulatif"].iloc[-1]
            st.info(f"Saldo akhir akun {akun}: {saldo_akhir:,.2f}")
    else:
        st.info("Tidak ada data jurnal untuk ditampilkan di buku besar.")

# === NERACA SALDO ===
elif selected == "⚖️ Neraca Saldo":
    st.header("⚖️ Neraca Saldo")
    if "jurnal" in st.session_state and st.session_state.jurnal:
        df_jurnal = pd.DataFrame(st.session_state.jurnal)
        akun_list = df_jurnal["Akun"].unique()
        saldo_akhir_list = []

        for akun in akun_list:
            df_akun = df_jurnal[df_jurnal["Akun"] == akun].copy()
            df_akun["Saldo"] = df_akun["Debit"] - df_akun["Kredit"]
            df_akun["Saldo Akumulatif"] = df_akun["Saldo"].cumsum()
            saldo_akhir = df_akun["Saldo Akumulatif"].iloc[-1]
            ref = df_akun["Ref"].iloc[0]
            kategori = df_akun["Kategori"].iloc[0]

            debit = saldo_akhir if saldo_akhir >= 0 else 0
            kredit = -saldo_akhir if saldo_akhir < 0 else 0
            saldo_akhir_list.append({
                "Ref": ref,
                "Akun": akun,
                "Kategori": kategori,
                "Debit": debit,
                "Kredit": kredit
            })

        df_saldo = pd.DataFrame(saldo_akhir_list).sort_values(by="Ref")
        total_debit = df_saldo["Debit"].sum()
        total_kredit = df_saldo["Kredit"].sum()
        total_row = pd.DataFrame({
            "Ref": ["TOTAL"],
            "Akun": [""],
            "Kategori": [""],
            "Debit": [total_debit],
            "Kredit": [total_kredit]
        })

        df_saldo_tampil = pd.concat([df_saldo, total_row], ignore_index=True)
        st.dataframe(df_saldo_tampil[["Ref", "Akun", "Debit", "Kredit"]], use_container_width=True)

        if total_debit == total_kredit:
            st.success("✅ Neraca Saldo Seimbang")
        else:
            st.error(f"❌ Neraca Saldo Tidak Seimbang — Selisih: Rp {abs(total_debit - total_kredit):,.2f}")
    else:
        st.info("Belum ada data jurnal untuk dihitung.")

# === LABA RUGI ===
elif selected == "📈 Laba Rugi":
    st.header("📈 Laporan Laba Rugi")
    if "jurnal" in st.session_state and st.session_state.jurnal:
        df = pd.DataFrame(st.session_state.jurnal)
        pendapatan = df[df["Kategori"] == "Pendapatan"]["Kredit"].sum()
        beban = df[df["Kategori"] == "Beban"]["Debit"].sum()
        laba_bersih = pendapatan - beban

        st.metric("Total Pendapatan", f"Rp {pendapatan:,.2f}")
        st.metric("Total Beban", f"Rp {beban:,.2f}")
        st.metric("Laba Bersih", f"Rp {laba_bersih:,.2f}")
    else:
        st.info("Belum ada data untuk laporan laba rugi.")

# === PERUBAHAN EKUITAS ===
elif selected == "📊 Perubahan Ekuitas":
    st.header("📊 Laporan Perubahan Ekuitas")
    if "jurnal" in st.session_state and st.session_state.jurnal:
        df = pd.DataFrame(st.session_state.jurnal)
        modal_awal = df[df["Kategori"] == "Modal"]["Kredit"].sum()
        prive = df[df["Kategori"] == "Prive"]["Debit"].sum()
        pendapatan = df[df["Kategori"] == "Pendapatan"]["Kredit"].sum()
        beban = df[df["Kategori"] == "Beban"]["Debit"].sum()
        laba_bersih = pendapatan - beban
        modal_akhir = modal_awal + laba_bersih - prive

        st.metric("Modal Awal", f"Rp {modal_awal:,.2f}")
        st.metric("Laba Bersih", f"Rp {laba_bersih:,.2f}")
        st.metric("Prive", f"Rp {prive:,.2f}")
        st.metric("Modal Akhir", f"Rp {modal_akhir:,.2f}")
    else:
        st.info("Belum ada data untuk laporan perubahan ekuitas.")

# === POSISI KEUANGAN ===
elif selected == "📋 Posisi Keuangan":
    st.header("📋 Laporan Posisi Keuangan (Neraca)")
    if "jurnal" in st.session_state and st.session_state.jurnal:
        df = pd.DataFrame(st.session_state.jurnal)
        aktiva = df[df["Kategori"] == "Aktiva"]
        kewajiban = df[df["Kategori"] == "Kewajiban"]
        modal_awal = df[df["Kategori"] == "Modal"]["Kredit"].sum()
        prive = df[df["Kategori"] == "Prive"]["Debit"].sum()
        pendapatan = df[df["Kategori"] == "Pendapatan"]["Kredit"].sum()
        beban = df[df["Kategori"] == "Beban"]["Debit"].sum()
        laba_bersih = pendapatan - beban
        modal_akhir = modal_awal + laba_bersih - prive

        total_aktiva = aktiva["Debit"].sum() - aktiva["Kredit"].sum()
        total_kewajiban = kewajiban["Kredit"].sum() - kewajiban["Debit"].sum()
        total_passiva = total_kewajiban + modal_akhir

        col1, col2 = st.columns(2)
        col1.metric("Total Aktiva", f"Rp {total_aktiva:,.2f}")
        col2.metric("Total Kewajiban + Modal", f"Rp {total_passiva:,.2f}")

        if abs(total_aktiva - total_passiva) < 1e-2:
            st.success("✅ Neraca Seimbang")
        else:
            st.error("❌ Neraca Tidak Seimbang")
    else:
        st.info("Belum ada data untuk laporan posisi keuangan.")

# === TOMBOL EKSPOR ===
st.sidebar.markdown("---")
if st.sidebar.button("📥 Ekspor ke Excel"):
    buffer, filename = simpan_semua_ke_excel()
    if buffer:
        st.sidebar.download_button(
            label="Download Laporan Excel",
            data=buffer,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
