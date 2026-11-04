import streamlit as st
import pandas as pd
import re
import io

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Yaşam Pencerem - Risk Analiz Portalı",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mobil & Masaüstü Stil
st.markdown("""
<style>
    @media (max-width: 768px) {
        .block-container { padding: 0.8rem !important; }
        h1 { font-size: 1.4rem !important; }
        h2, h3 { font-size: 1.1rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    }
    div.stButton > button:first-child {
        background-color: #0d6efd;
        color: white;
        font-weight: bold;
        border-radius: 6px;
        width: 100%;
        padding: 12px;
    }
    div.stButton > button:first-child:hover {
        background-color: #0b5ed7;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Oturum Durumu
if "analiz_yapildi" not in st.session_state:
    st.session_state.analiz_yapildi = False
if "df_processed" not in st.session_state:
    st.session_state.df_processed = None
if "meta" not in st.session_state:
    st.session_state.meta = {}

st.title("🧭 Yaşam Pencerem Risk Analiz Sistemi")
st.caption("Rehberlik Servisi ve Okul Yönetimi Çoklu Veri Kaynağı Modülü")

# Kategori Numaraları
KATEGORI_NUMARALARI = {
    "1. Kritik Risk, Güvenlik ve İstismar": [7, 13, 15, 16, 18, 25, 36],
    "2. Aile İçi Dinamikler ve Sosyo-Ekonomik": [2, 10, 11, 14, 17, 19, 21, 22, 24, 29, 38, 47],
    "3. Bireysel, Psikolojik ve Duygusal Boyut": [1, 3, 4, 5, 6, 8, 9, 12, 20, 23, 26, 30, 34, 37, 39, 42],
    "4. Okul İklimi ve Dersler": [27, 28, 31, 32, 33, 35, 40, 41, 43, 44, 45, 46, 48]
}

# Veri Kaynağı
st.sidebar.header("📁 Veri Kaynağı")
kaynak_turu = st.sidebar.radio(
    "Veri Alma Yöntemi:",
    ["Google Drive / E-Tablo Linki", "Dosya Yükle (CSV / Excel)"],
    index=0
)

sheet_url = ""
uploaded_file = None

def convert_google_sheet_url_to_csv(url):
    sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if sheet_id_match:
        sheet_id = sheet_id_match.group(1)
        gid_match = re.search(r'[#&]gid=([0-9]+)', url)
        gid = gid_match.group(1) if gid_match else "0"
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return url

if kaynak_turu == "Google Drive / E-Tablo Linki":
    sheet_url = st.sidebar.text_input(
        "Google Sheets Bağlantısını Yapıştırın:",
        placeholder="https://docs.google.com/spreadsheets/d/...",
        help="Link yapıştırdıktan sonra klavyeden Enter tuşuna basınız."
    )
    if not sheet_url and not st.session_state.analiz_yapildi:
        st.info("💡 **Google Drive'dan Okuma:** Google E-Tablo linkini sol menüye yapıştırıp alttaki **'🚀 Analizi Başlat / Çalıştır (Run)'** butonuna tıklayınız. (Tablonun 'Bağlantıya sahip herkes görüntüleyebilir' ayarında olduğundan emin olunuz).")
else:
    uploaded_file = st.sidebar.file_uploader("CSV veya Excel Dosyası Seçin:", type=["csv", "xlsx"])

# RUN BUTONU HER ZAMAN GÖRÜNÜR OLMALI
run_clicked = st.sidebar.button("🚀 Analizi Başlat / Çalıştır (Run)")

def process_dataset(df):
    class_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['sınıf', 'sube', 'şube'])]
    class_col = class_cols[0] if class_cols else df.columns[1]

    name_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['adınız', 'soyadınız', 'öğrenci', 'ad soyad'])]
    
    def extract_student_info(row):
        for col in name_cols:
            val = row[col]
            if pd.notna(val) and str(val).strip() != '':
                return str(val).strip()
        for c in df.columns:
            if c != class_col and pd.notna(row[c]) and isinstance(row[c], str) and len(str(row[c]).strip()) > 3:
                if not any(k in str(row[c]).lower() for k in ['bana uygun', 'uygun değil', 'evet', 'hayır']):
                    return str(row[c]).strip()
        return "Bilinmiyor"

    df['Ogrenci_Ham'] = df.apply(extract_student_info, axis=1)

    def split_no_name(val):
        match = re.match(r'^(\d+)\s*[-/]?\s*(.*)$', str(val))
        if match:
            return match.group(1), match.group(2).strip()
        return "-", str(val).strip()

    df['Okul_No'] = df['Ogrenci_Ham'].apply(lambda x: split_no_name(x)[0])
    df['Ad_Soyad'] = df['Ogrenci_Ham'].apply(lambda x: split_no_name(x)[1])

    main_questions = []
    q_num_map = {}
    for c in df.columns:
        c_str = str(c).strip()
        m = re.match(r'^(\d+)[\.\s\-]', c_str)
        if m and not any(k in c_str.lower() for k in ['lütfen', 'belirtiniz', 'yazınız', 'nedenini']):
            main_questions.append(c)
            q_num_map[int(m.group(1))] = c

    if not main_questions:
        for c in df.columns:
            vals = df[c].dropna().astype(str).str.strip().tolist()
            if any(v in ['Bana Uygun', 'Evet', '1', 'X', 'x'] for v in vals):
                main_questions.append(c)

    kategoriler_map = {}
    for cat_name, num_list in KATEGORI_NUMARALARI.items():
        matched = [q_num_map[n] for n in num_list if n in q_num_map]
        kategoriler_map[cat_name] = matched

    if not any(len(v) > 0 for v in kategoriler_map.values()) and main_questions:
        kategoriler_map["Genel Anket Maddeleri"] = main_questions

    risk_questions = [c for c in main_questions if not str(c).strip().startswith('26.')]

    def is_positive_mark(val):
        return str(val).strip() in ['Bana Uygun', 'Evet', '1', 'X', 'x', 'True', 'true']

    if risk_questions:
        df['Genel_Risk_Puani'] = df[risk_questions].apply(lambda row: row.map(is_positive_mark).sum(), axis=1)
    else:
        df['Genel_Risk_Puani'] = 0

    kritik_cols = kategoriler_map.get("1. Kritik Risk, Güvenlik ve İstismar", [])
    if kritik_cols:
        df['Kritik_Risk_Puani'] = df[kritik_cols].apply(lambda row: row.map(is_positive_mark).sum(), axis=1)
    else:
        df['Kritik_Risk_Puani'] = 0

    return df, class_col, main_questions, risk_questions, kategoriler_map

# Butona basıldığında veriyi oku ve işle
if run_clicked:
    raw_df = None
    if kaynak_turu == "Google Drive / E-Tablo Linki":
        if not sheet_url.strip():
            st.sidebar.error("Lütfen önce bir Google Sheets bağlantısı yapıştırın!")
        else:
            with st.spinner("Google E-Tablo indiriliyor..."):
                try:
                    csv_export_url = convert_google_sheet_url_to_csv(sheet_url)
                    raw_df = pd.read_csv(csv_export_url)
                    st.sidebar.success("E-Tablo başarıyla indirildi!")
                except Exception as e:
                    st.sidebar.error(f"Tablo okunamadı! Paylaşım ayarının 'Bağlantıya sahip herkes' olduğundan emin olun. Hata: {e}")
    else:
        if uploaded_file is None:
            st.sidebar.error("Lütfen önce bir dosya yükleyin!")
        else:
            try:
                if uploaded_file.name.endswith('.csv'):
                    raw_df = pd.read_csv(uploaded_file)
                else:
                    raw_df = pd.read_excel(uploaded_file)
            except Exception:
                uploaded_file.seek(0)
                raw_df = pd.read_csv(uploaded_file, sep=';')

    if raw_df is not None:
        with st.spinner("Veriler işleniyor, risk analizi yapılıyor..."):
            df_proc, class_col, main_questions, risk_questions, kategoriler_map = process_dataset(raw_df)
            st.session_state.df_processed = df_proc
            st.session_state.meta = {
                "class_col": class_col,
                "main_questions": main_questions,
                "risk_questions": risk_questions,
                "kategoriler_map": kategoriler_map
            }
            st.session_state.analiz_yapildi = True
            st.rerun()

# Analiz Sonuçları
if st.session_state.analiz_yapildi and st.session_state.df_processed is not None:
    df = st.session_state.df_processed
    class_col = st.session_state.meta["class_col"]
    main_questions = st.session_state.meta["main_questions"]
    risk_questions = st.session_state.meta["risk_questions"]
    kategoriler_map = st.session_state.meta["kategoriler_map"]

    all_classes = ["Tüm Okul"] + sorted([str(x) for x in df[class_col].dropna().unique()])
    selected_class = st.selectbox("🎯 Sınıf / Şube Seçiniz:", all_classes)

    filtered_df = df if selected_class == "Tüm Okul" else df[df[class_col] == selected_class]

    c1, c2 = st.columns(2)
    c1.metric("Toplam Öğrenci", len(filtered_df))
    c2.metric("Ortalama Risk Skoru", f"{filtered_df['Genel_Risk_Puani'].mean():.1f}")
    
    c3, c4 = st.columns(2)
    c3.metric("Maksimum Risk", f"{filtered_df['Genel_Risk_Puani'].max():.0f}")
    c4.metric("Kritik Riskli Öğrenci", len(filtered_df[filtered_df['Kritik_Risk_Puani'] > 0]))

    st.markdown("---")

    tab_cat, tab_risk, tab_custom, tab_student = st.tabs([
        "📊 Başlıklar",
        "🚨 Risk Sıralaması",
        "📌 Madde Filtresi",
        "👤 Öğrenci Kartı"
    ])

    with tab_cat:
        available_cats = [k for k in kategoriler_map.keys() if len(kategoriler_map[k]) > 0]
        selected_cat = st.selectbox("Kategori Seçiniz:", available_cats if available_cats else list(kategoriler_map.keys()))
        cat_items = kategoriler_map.get(selected_cat, [])

        if cat_items:
            summary_rows = []
            for item in cat_items:
                cnt = filtered_df[item].astype(str).str.strip().isin(['Bana Uygun', 'Evet', '1', 'X', 'x', 'True']).sum()
                pct = (cnt / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
                summary_rows.append({"Madde": item, "Kişi": cnt, "Oran": f"%{pct:.1f}"})
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

            for item in cat_items:
                chosen_mask = filtered_df[item].astype(str).str.strip().isin(['Bana Uygun', 'Evet', '1', 'X', 'x', 'True'])
                chosen = filtered_df[chosen_mask]
                st_cnt = len(chosen)
                with st.expander(f"{item} ({st_cnt} Öğrenci)"):
                    if st_cnt > 0:
                        disp = chosen[[class_col, 'Okul_No', 'Ad_Soyad', 'Genel_Risk_Puani']].rename(columns={
                            class_col: 'Şube', 'Okul_No': 'No', 'Ad_Soyad': 'Öğrenci', 'Genel_Risk_Puani': 'Risk'
                        })
                        st.dataframe(disp, use_container_width=True, hide_index=True)

    with tab_risk:
        raw_max = int(df['Genel_Risk_Puani'].max()) if len(df) > 0 else 0
        max_p = max(1, raw_max if raw_max > 0 else len(risk_questions))
        min_risk = st.slider("Asgari Risk Puanı:", 0, max_p, min(10, max_p))
        only_crit = st.checkbox("Yalnızca kritik maddesi olanlar", value=False)

        res_df = filtered_df[filtered_df['Genel_Risk_Puani'] >= min_risk]
        if only_crit:
            res_df = res_df[res_df['Kritik_Risk_Puani'] > 0]

        res_df = res_df.sort_values(by=['Kritik_Risk_Puani', 'Genel_Risk_Puani'], ascending=[False, False])
        st.dataframe(
            res_df[[class_col, 'Okul_No', 'Ad_Soyad', 'Kritik_Risk_Puani', 'Genel_Risk_Puani']].rename(columns={
                class_col: 'Şube', 'Okul_No': 'No', 'Ad_Soyad': 'Öğrenci', 'Kritik_Risk_Puani': 'Kritik', 'Genel_Risk_Puani': 'Risk'
            }),
            use_container_width=True,
            hide_index=True
        )

    with tab_custom:
        selected_custom_items = st.multiselect("Maddeleri seçiniz:", options=main_questions)
        if selected_custom_items:
            mask = filtered_df[selected_custom_items].astype(str).isin(['Bana Uygun', 'Evet', '1', 'X', 'x', 'True']).any(axis=1)
            c_res = filtered_df[mask]
            st.info(f"{len(c_res)} öğrenci bulundu.")
            st.dataframe(c_res[[class_col, 'Okul_No', 'Ad_Soyad', 'Genel_Risk_Puani'] + selected_custom_items], use_container_width=True, hide_index=True)

    with tab_student:
        s_opts = filtered_df[['Okul_No', 'Ad_Soyad', 'Ogrenci_Ham']].drop_duplicates()
        sel_s = st.selectbox("Öğrenci:", options=s_opts['Ogrenci_Ham'].tolist())
        if sel_s:
            s_data = filtered_df[filtered_df['Ogrenci_Ham'] == sel_s].iloc[0]
            st.write(f"**{s_data['Ad_Soyad']}** ({s_data[class_col]} - No: {s_data['Okul_No']})")
            st.write(f"Risk Skoru: **{s_data['Genel_Risk_Puani']}** | Kritik Madde: **{s_data['Kritik_Risk_Puani']}**")
            marked = [q for q in risk_questions if str(s_data[q]).strip() in ['Bana Uygun', 'Evet', '1', 'X', 'x', 'True']]
            with st.expander(f"İşaretlediği Maddeler ({len(marked)})"):
                for m in marked:
                    st.write(f"• {m}")