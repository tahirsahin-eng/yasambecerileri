import streamlit as st
import pandas as pd
import re
import io

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Yaşam Pencerem - Risk Analiz Portalı",
    page_icon="🧭",
    layout="wide"
)

# Arayüz Stili
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #d9534f;
    }
    div.stButton > button:first-child {
        background-color: #0d6efd;
        color: white;
        font-weight: bold;
        border-radius: 6px;
        width: 100%;
        padding: 10px;
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

st.title("🧭 Saffet Çam OO - Yaşam Pencerem Risk Analiz Sistemi")
st.caption("Rehberlik Servisi ve Okul Yönetimi Tematik Risk ve Öğrenci Takip Modülü")

# 4 Ana Başlık - Numaralara Göre Eşleştirme (Böylece sütun adındaki küçük harf/noktalama farkları hata vermez)
KATEGORI_NUMARALARI = {
    "1. Kritik Risk, Güvenlik ve İstismar": [7, 13, 15, 16, 18, 25, 36],
    "2. Aile İçi Dinamikler ve Sosyo-Ekonomik Durum": [2, 10, 11, 14, 17, 19, 21, 22, 24, 29, 38, 47],
    "3. Bireysel, Psikolojik ve Duygusal Boyut": [1, 3, 4, 5, 6, 8, 9, 12, 20, 23, 26, 30, 34, 37, 39, 42],
    "4. Okul İklimi, Dersler ve Eğitsel Alan": [27, 28, 31, 32, 33, 35, 40, 41, 43, 44, 45, 46, 48]
}

# Kenar Çubuğu
st.sidebar.header("📁 Veri Yükleme ve Başlatma")
uploaded_file = st.sidebar.file_uploader("Form Yanıtları Dosyasını Seçin (CSV / Excel)", type=["csv", "xlsx"])

if uploaded_file is not None:
    if "current_file_name" not in st.session_state or st.session_state.current_file_name != uploaded_file.name:
        st.session_state.current_file_name = uploaded_file.name
        st.session_state.analiz_yapildi = False

def process_dataset(file):
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
    except Exception:
        file.seek(0)
        df = pd.read_excel(file, engine='openpyxl')

    # Sınıf sütununu dinamik bul
    class_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['sınıf', 'sube', 'şube'])]
    class_col = class_cols[0] if class_cols else df.columns[1]

    # Öğrenci adı sütunlarını bulup birleştir
    name_cols = [c for c in df.columns if any(k in str(c).lower() for k in ['adınız', 'soyadınız', 'öğrenci', 'ad soyad'])]
    
    def extract_student_info(row):
        if name_cols:
            for col in name_cols:
                val = row[col]
                if pd.notna(val) and str(val).strip() != '':
                    return str(val).strip()
        # Eğer ad soyad sütunu bulunamazsa 2. veya 3. sütunu dene
        for c in df.columns[1:5]:
            if pd.notna(row[c]) and str(row[c]).strip() != '':
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

    # Ana soruları dinamik olarak tespit et (Başında sayı olanlar ve açık uçlu soru olmayanlar)
    main_questions = [
        c for c in df.columns 
        if re.match(r'^\d+\.', str(c).strip()) and not any(k in str(c).lower() for k in ['lütfen', 'belirtiniz', 'yazınız'])
    ]

    # Soru numarasına göre sütun haritası
    q_num_to_col = {}
    for col in main_questions:
        m = re.match(r'^(\d+)\.', str(col).strip())
        if m:
            q_num_to_col[int(m.group(1))] = col

    # Kategorileri mevcut sütunlarla eşleştir
    kategoriler_map = {}
    for cat_name, num_list in KATEGORI_NUMARALARI.items():
        matched_cols = [q_num_to_col[n] for n in num_list if n in q_num_to_col]
        kategoriler_map[cat_name] = matched_cols

    # Risk maddeleri (26. yetenek maddesi hariç)
    risk_questions = [col for col in main_questions if not str(col).strip().startswith('26.')]

    # Risk puanlarını güvenli hesapla
    df['Genel_Risk_Puani'] = df[risk_questions].apply(lambda row: (row == 'Bana Uygun').sum(), axis=1) if risk_questions else 0

    kritik_cols = kategoriler_map.get("1. Kritik Risk, Güvenlik ve İstismar", [])
    if kritik_cols:
        df['Kritik_Risk_Puani'] = df[kritik_cols].apply(lambda row: (row == 'Bana Uygun').sum(), axis=1)
    else:
        df['Kritik_Risk_Puani'] = 0

    return df, class_col, main_questions, risk_questions, kategoriler_map

# RUN BUTONU
if uploaded_file is not None:
    run_button = st.sidebar.button("🚀 Analizi Başlat / Çalıştır (Run)")
    if run_button:
        with st.spinner("Dosya taranıyor, risk skorları hesaplanıyor..."):
            try:
                df_proc, class_col, main_questions, risk_questions, kategoriler_map = process_dataset(uploaded_file)
                st.session_state.df_processed = df_proc
                st.session_state.meta = {
                    "class_col": class_col,
                    "main_questions": main_questions,
                    "risk_questions": risk_questions,
                    "kategoriler_map": kategoriler_map
                }
                st.session_state.analiz_yapildi = True
                st.sidebar.success("Analiz tamamlandı!")
            except Exception as e:
                st.error(f"Dosya işlenirken hata oluştu: {e}")

# Analiz Sonuçları
if st.session_state.analiz_yapildi and st.session_state.df_processed is not None:
    df = st.session_state.df_processed
    class_col = st.session_state.meta["class_col"]
    main_questions = st.session_state.meta["main_questions"]
    risk_questions = st.session_state.meta["risk_questions"]
    kategoriler_map = st.session_state.meta["kategoriler_map"]

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Kapsam Seçimi")
    all_classes = ["Tüm Okul"] + sorted([str(x) for x in df[class_col].dropna().unique()])
    selected_class = st.sidebar.selectbox("Sınıf / Şube:", all_classes)

    filtered_df = df if selected_class == "Tüm Okul" else df[df[class_col] == selected_class]

    # Metrikler
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Öğrenci Sayısı", len(filtered_df))
    c2.metric("Ortalama Risk", f"{filtered_df['Genel_Risk_Puani'].mean():.1f}")
    c3.metric("En Yüksek Risk", f"{filtered_df['Genel_Risk_Puani'].max():.0f}")
    c4.metric("Kritik Riskli Öğrenci", len(filtered_df[filtered_df['Kritik_Risk_Puani'] > 0]))

    st.markdown("---")

    tab_cat, tab_risk, tab_custom, tab_student = st.tabs([
        "📊 Tematik Başlık Analiz Raporu",
        "🚨 En Yüksek Riskli Öğrenciler",
        "📌 Özel Çoklu Madde Filtresi",
        "👤 Bireysel Öğrenci Kartı"
    ])

    # SEKME 1: TEMATİK BAŞLIKLAR
    with tab_cat:
        st.subheader(f"Tematik Başlıklara Göre Maddeler ve Seçenler ({selected_class})")
        selected_cat = st.selectbox("📂 Tematik Başlık Seçiniz:", list(kategoriler_map.keys()))
        cat_items = kategoriler_map[selected_cat]

        if not cat_items:
            st.warning("Bu başlık altında eşleşen madde bulunamadı.")
        else:
            summary_rows = []
            for item in cat_items:
                count = (filtered_df[item] == "Bana Uygun").sum()
                ratio = (count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
                summary_rows.append({
                    "Madde": item,
                    "İşaretleyen Sayısı": count,
                    "Oran (%)": f"%{ratio:.1f}"
                })
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("👥 Maddeyi Seçen Öğrencilerin Detay Listesi")

            for item in cat_items:
                chosen = filtered_df[filtered_df[item] == "Bana Uygun"].copy()
                st_count = len(chosen)
                
                exp_title = f"{'🔴' if 'Kritik' in selected_cat else '🔹'} {item} — ({st_count} Öğrenci)"
                with st.expander(exp_title, expanded=(st_count > 0 and 'Kritik' in selected_cat)):
                    if st_count == 0:
                        st.caption("Bu maddeyi işaretleyen öğrenci bulunmamaktadır.")
                    else:
                        disp = chosen[[class_col, 'Okul_No', 'Ad_Soyad', 'Genel_Risk_Puani']].rename(columns={
                            class_col: 'Sınıf/Şube',
                            'Okul_No': 'No',
                            'Ad_Soyad': 'Öğrenci Adı Soyadı',
                            'Genel_Risk_Puani': 'Genel Risk Skoru'
                        })
                        st.dataframe(disp, use_container_width=True, hide_index=True)

                        # Excel İndir
                        b_io = io.BytesIO()
                        with pd.ExcelWriter(b_io, engine='openpyxl') as wr:
                            disp.to_excel(wr, sheet_name='Ogrenci_Listesi', index=False)
                        st.download_button(
                            label="📥 Bu Maddenin Öğrenci Listesini İndir (Excel)",
                            data=b_io.getvalue(),
                            file_name=f"Madde_{item[:12].strip()}_{selected_class}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_{item}"
                        )

    # SEKME 2: EN YÜKSEK RİSKLİ ÖĞRENCİLER
    with tab_risk:
        st.subheader(f"En Yüksek Risk Sıralaması ({selected_class})")
        col_c1, col_c2 = st.columns([2, 1])
        with col_c1:
            max_p = int(df['Genel_Risk_Puani'].max()) if len(df) > 0 else 30
            min_risk = st.slider("Minimum Risk Eşiği:", min_value=0, max_value=max_p, value=min(15, max_p))
        with col_c2:
            only_critical = st.checkbox("Yalnızca Kritik Maddesi Olanlar", value=False)

        res_df = filtered_df[filtered_df['Genel_Risk_Puani'] >= min_risk]
        if only_critical:
            res_df = res_df[res_df['Kritik_Risk_Puani'] > 0]

        res_df = res_df.sort_values(by=['Kritik_Risk_Puani', 'Genel_Risk_Puani'], ascending=[False, False])
        disp_cols = [class_col, 'Okul_No', 'Ad_Soyad', 'Kritik_Risk_Puani', 'Genel_Risk_Puani']
        
        st.dataframe(
            res_df[disp_cols].rename(columns={
                class_col: 'Sınıf/Şube',
                'Okul_No': 'No',
                'Ad_Soyad': 'Öğrenci Adı Soyadı',
                'Kritik_Risk_Puani': 'Kritik Madde Sayısı',
                'Genel_Risk_Puani': 'Toplam Risk Skoru'
            }),
            use_container_width=True,
            height=320,
            hide_index=True
        )

    # SEKME 3: ÇOKLU MADDE FİLTRESİ
    with tab_custom:
        st.subheader("Özel Çoklu Madde Filtresi")
        selected_custom_items = st.multiselect("Birlikte sorgulanacak maddeleri seçin:", options=main_questions)
        rule = st.radio("Filtre Kuralı:", ["Seçilenlerin EN AZ BİRİNİ işaretleyenler (VEYA)", "Seçilenlerin TÜMÜNÜ işaretleyenler (VE)"], horizontal=True)

        if selected_custom_items:
            mask = (filtered_df[selected_custom_items] == "Bana Uygun").any(axis=1) if "EN AZ BİRİNİ" in rule else (filtered_df[selected_custom_items] == "Bana Uygun").all(axis=1)
            c_res = filtered_df[mask].copy()
            st.info(f"Kriterlere uyan **{len(c_res)}** öğrenci bulundu.")
            st.dataframe(c_res[[class_col, 'Okul_No', 'Ad_Soyad', 'Genel_Risk_Puani'] + selected_custom_items].rename(columns={class_col: 'Sınıf/Şube'}), use_container_width=True, hide_index=True)

    # SEKME 4: BİREYSEL ÖĞRENCİ DOSYASI
    with tab_student:
        st.subheader("Bireysel Öğrenci Kartı")
        s_opts = filtered_df[['Okul_No', 'Ad_Soyad', 'Ogrenci_Ham']].drop_duplicates()
        sel_s = st.selectbox("Öğrenci Seçiniz:", options=s_opts['Ogrenci_Ham'].tolist())

        if sel_s:
            s_data = filtered_df[filtered_df['Ogrenci_Ham'] == sel_s].iloc[0]
            st.markdown(f"#### 👤 {s_data['Ad_Soyad']} ({s_data[class_col]} - No: {s_data['Okul_No']})")
            sc1, sc2 = st.columns(2)
            sc1.warning(f"**Genel Risk Skoru:** {s_data['Genel_Risk_Puani']} / {len(risk_questions)}")
            sc2.error(f"**Kritik Madde Sayısı:** {s_data['Kritik_Risk_Puani']}")

            st.markdown("##### 📋 Başlıklara Göre İşaretlediği Maddeler:")
            for cat_name, cat_items_list in kategoriler_map.items():
                marked_in_cat = [q for q in cat_items_list if s_data[q] == "Bana Uygun"]
                if marked_in_cat:
                    st.markdown(f"**{cat_name} ({len(marked_in_cat)} Madde):**")
                    for q in marked_in_cat:
                        crit_flag = "🔴 " if "Kritik" in cat_name else "🔹 "
                        st.write(f"{crit_flag}{q}")

elif uploaded_file is not None and not st.session_state.analiz_yapildi:
    st.info("👈 Dosya hazır. Analizi çalıştırmak için sol paneldeki **'🚀 Analizi Başlat / Çalıştır (Run)'** butonuna tıklayınız.")
else:
    st.info("👈 Başlamak için sol menüden CSV veya Excel formatındaki anket dosyasını yükleyin.")