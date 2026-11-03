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
    .category-header {
        background-color: #f1f3f5;
        padding: 8px 12px;
        border-radius: 5px;
        font-weight: bold;
        color: #1e3a8a;
        margin-top: 10px;
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

# Başlık
st.title("🧭 Saffet Çam OO - Yaşam Pencerem Risk Analiz Sistemi")
st.caption("Rehberlik Servisi ve Okul Yönetimi Tematik Risk ve Öğrenci Takip Modülü")

# 4 Ana Başlık ve Kapsadığı Maddeler
KATEGORILER = {
    "1. Kritik Risk, Güvenlik ve İstismar": [
        "7. Arkadaşlarımdan bazıları bağımlılık yapıcı madde kullanıyor.",
        "13. Fiziksel güce ihtiyacım olduğunda beni destekleyecek bir grubun üyesiyim.",
        "15. Çevremdeki insanlar tarafından istemediğim söz ve hareketlere maruz kalıyorum.",
        "16. Hoşlanmadığım davranışlara zorlanıyorum.",
        "18. Hayatı yaşamaya değer bulmuyorum.",
        "25. Yaşamım üzerinde hiç kontrolüm yok.",
        "36. Okulda kendimi güvende hissetmiyorum."
    ],
    "2. Aile İçi Dinamikler ve Sosyo-Ekonomik Durum": [
        "2. Ailem benim bir üst öğrenime devam etmemi istemiyor.",
        "10. Ailemin benden beklentisi çok yüksek.",
        "11. Aile ortamımızda sık sık tartışma olur.",
        "14. Temel ihtiyaçlarımızı karşılayacak maddi olanaklardan yoksunum.",
        "17. Ailemin geçimini sağlamak için bir işte çalışıyorum.",
        "19. Ailemi bana ve ihtiyaçlarıma (maddi, manevi) karşı ilgisiz buluyorum.",
        "21. Ailemiz içerisinde belli kurallar yoktur.",
        "22. Ailemde zararlı alışkanlıkları olan birey/bireyler var.",
        "24. Ailemden ayrı yaşıyorum.",
        "29. Annem/babam okuma yazma bilmiyor.",
        "38. Ailem teknoloji ile (cep telefonu, tablet, internet vs.) çok vakit geçiriyor.",
        "47. Ailemden biri/birileri şehit/gazi oldu."
    ],
    "3. Bireysel, Psikolojik ve Duygusal Boyut": [
        "1. Sürekli devam eden bir hastalığım var.",
        "3. Deprem/yangın/sel/savaş/trafik kazası vb. durumlardan en az birini yaşadım.",
        "4. Değerlerimi/inançlarımı yaşayabileceğim ortam sağlanmıyor.",
        "5. Daha önce yaşamadığım bazı korkularım var.",
        "6. Öfkemi kontrol edemiyorum.",
        "8. Teknoloji ile (cep telefonu, tablet, internet vs.) çok vakit geçiriyorum.",
        "9. Çoğu zaman kimseyle konuşmak görüşmek istemiyorum.",
        "12. Arkadaşlık kurmakta zorlanıyorum.",
        "20. Fiziksel görünüşümden rahatsızım.",
        "23. Kendime hiç güvenim yok.",
        "26. Kendimi belirli bir alanda çok yetenekli buluyorum.",
        "30. Başkaları ile kıyaslanıyorum.",
        "34. Fazla heyecanlanıyorum.",
        "37. Kendimi herhangi bir alanda yetenekli bulmuyorum.",
        "39. Farklı tercihlerimden dolayı çevrem tarafından dışlanıyorum.",
        "42. Sevdiğim bir yakınımı kaybettiğim için çok üzgünüm."
    ],
    "4. Okul İklimi, Dersler ve Eğitsel Alan": [
        "27. Okul dışında kaliteli vakit geçireceğim aktiviteler yapacak fırsatım yok.",
        "28. İstesem de derslerimde başarılı olamıyorum.",
        "31. Dersler ilgi çekici hale getirilmiyor.",
        "32. Okulu bitirdikten sonra ne yapmak istediğimi bilmiyorum.",
        "33. Okulu sevmiyorum.",
        "35. Okulda problemlerimizle fazla ilgilenilmiyor.",
        "40. Okuldaki disiplin anlayışından rahatsızım.",
        "41. Okulda yeteri kadar sosyal etkinlik düzenlenmiyor.",
        "43. Okulda alınan kararlarda öğrencilerin görüşü alınmıyor.",
        "44. Öğrenci sorunları öğrencilerle çözülmek yerine önce ailelere aktarılıyor.",
        "45. Öğrenciler arasında ayrım yapılıyor.",
        "46. Okula uyum sağlayamadım.",
        "48. Okul yeterince temiz değil."
    ]
}

# Açıklama sütunları eşleştirmesi
ACIKLAMA_MAP = {
    "1. Sürekli devam eden bir hastalığım var.": "1. Madde için devam eden hastalığınız varsa lütfen yazınız:",
    "3. Deprem/yangın/sel/savaş/trafik kazası vb. durumlardan en az birini yaşadım.": "3. Madde için yaşadıysanız hangisi olduğunu belirtiniz:",
    "24. Ailemden ayrı yaşıyorum.": "24. Madde için aileden ayrı yaşıyorsanız nedenini belirtiniz:",
    "42. Sevdiğim bir yakınımı kaybettiğim için çok üzgünüm.": "42. Madde için kaybettiğiniz yakınınızı lütfen belirtiniz:"
}

# Kenar Çubuğu
st.sidebar.header("📁 Veri Yükleme ve Başlatma")
uploaded_file = st.sidebar.file_uploader("Form Yanıtları Dosyasını Seçin (CSV / Excel)", type=["csv", "xlsx"])

if uploaded_file is not None:
    if "current_file_name" not in st.session_state or st.session_state.current_file_name != uploaded_file.name:
        st.session_state.current_file_name = uploaded_file.name
        st.session_state.analiz_yapildi = False

def process_dataset(file):
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    class_cols = [c for c in df.columns if any(k in c.lower() for k in ['sınıf', 'sube', 'şube'])]
    class_col = class_cols[0] if class_cols else "Sınıfınız ve Şubeniz"

    # Öğrenci ad/no birleştirme
    name_cols = [c for c in df.columns if 'adınız' in c.lower() or 'soyadınız' in c.lower()]
    def extract_student_info(row):
        for col in name_cols:
            val = row[col]
            if pd.notna(val) and str(val).strip() != '':
                return str(val).strip()
        return "Bilinmiyor"

    df['Ogrenci_Ham'] = df.apply(extract_student_info, axis=1)

    def split_no_name(val):
        match = re.match(r'^(\d+)\s*[-/]?\s*(.*)$', str(val))
        if match:
            return match.group(1), match.group(2).strip()
        return "-", str(val).strip()

    df['Okul_No'] = df['Ogrenci_Ham'].apply(lambda x: split_no_name(x)[0])
    df['Ad_Soyad'] = df['Ogrenci_Ham'].apply(lambda x: split_no_name(x)[1])

    main_questions = [c for c in df.columns if re.match(r'^\d+\.', c) and 'lütfen' not in c.lower() and 'belirtiniz' not in c.lower()]
    risk_questions = [q for q in main_questions if not q.startswith('26.')]

    df['Genel_Risk_Puani'] = df[risk_questions].apply(lambda row: (row == 'Bana Uygun').sum(), axis=1)
    df['Kritik_Risk_Puani'] = df[KATEGORILER["1. Kritik Risk, Güvenlik ve İstismar"]].apply(lambda row: (row == 'Bana Uygun').sum(), axis=1)

    return df, class_col, main_questions, risk_questions

# RUN BUTONU
if uploaded_file is not None:
    run_button = st.sidebar.button("🚀 Analizi Başlat / Çalıştır (Run)")
    if run_button:
        with st.spinner("Veriler işleniyor..."):
            df_proc, class_col, main_questions, risk_questions = process_dataset(uploaded_file)
            st.session_state.df_processed = df_proc
            st.session_state.meta = {
                "class_col": class_col,
                "main_questions": main_questions,
                "risk_questions": risk_questions
            }
            st.session_state.analiz_yapildi = True
        st.sidebar.success("Analiz tamamlandı!")

# Analiz Sonuç Paneli
if st.session_state.analiz_yapildi and st.session_state.df_processed is not None:
    df = st.session_state.df_processed
    class_col = st.session_state.meta["class_col"]
    main_questions = st.session_state.meta["main_questions"]
    risk_questions = st.session_state.meta["risk_questions"]

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Kapsam Seçimi")
    all_classes = ["Tüm Okul"] + sorted(df[class_col].dropna().unique().tolist())
    selected_class = st.sidebar.selectbox("Sınıf / Şube:", all_classes)

    filtered_df = df if selected_class == "Tüm Okul" else df[df[class_col] == selected_class]

    # Üst Özet Kartları
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Öğrenci Sayısı", len(filtered_df))
    c2.metric("Ortalama Risk Skoru", f"{filtered_df['Genel_Risk_Puani'].mean():.1f}")
    c3.metric("Maksimum Risk", f"{filtered_df['Genel_Risk_Puani'].max():.0f}")
    c4.metric("Kritik Riskli Öğrenci", len(filtered_df[filtered_df['Kritik_Risk_Puani'] > 0]))

    st.markdown("---")

    # Sekmeler
    tab_cat, tab_risk, tab_custom, tab_student = st.tabs([
        "📊 Tematik Başlık Analiz Raporu",
        "🚨 En Yüksek Riskli Öğrenciler",
        "📌 Özel Çoklu Madde Filtresi",
        "👤 Bireysel Öğrenci Profili"
    ])

    # SEKME 1: TEMATİK BAŞLIK BAZLI ANALİZ VE SEÇENLERİ GÖSTERME
    with tab_cat:
        st.subheader(f"Başlıklara Göre Madde Dağılımı ve Seçen Öğrenciler ({selected_class})")
        st.write("İncelemek istediğiniz tematik başlığı seçiniz. Ardından herhangi bir maddenin yanındaki **'Öğrencileri Göster'** kutusunu açarak o maddeyi işaretleyen öğrencilerin tam listesine ve açıklamalarına ulaşabilirsiniz.")

        selected_cat = st.selectbox("📂 Tematik Başlık Seçiniz:", list(KATEGORILER.keys()))
        cat_items = KATEGORILER[selected_cat]

        # Başlığa ait maddelerin özet tablosunu oluştur
        summary_rows = []
        for item in cat_items:
            count = (filtered_df[item] == "Bana Uygun").sum()
            ratio = (count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
            summary_rows.append({
                "Madde": item,
                "İşaretleyen Öğrenci": count,
                "Oran (%)": f"%{ratio:.1f}"
            })

        summary_table = pd.DataFrame(summary_rows)
        st.dataframe(summary_table, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("👥 Maddeyi Seçen Öğrencilerin Detay Listesi")

        # Maddeleri expander içinde açıp öğrencileri listeleme
        for item in cat_items:
            chosen_students = filtered_df[filtered_df[item] == "Bana Uygun"].copy()
            st_count = len(chosen_students)
            
            exp_title = f"{'🔴' if 'Kritik' in selected_cat else '🔹'} {item} — ({st_count} Öğrenci)"
            with st.expander(exp_title, expanded=(st_count > 0 and 'Kritik' in selected_cat)):
                if st_count == 0:
                    st.caption("Bu maddeyi işaretleyen öğrenci bulunmamaktadır.")
                else:
                    show_cols = [class_col, 'Okul_No', 'Ad_Soyad', 'Genel_Risk_Puani']
                    
                    # Eğer maddenin özel açık uçlu açıklaması varsa tabloya ekle
                    expl_col = ACIKLAMA_MAP.get(item)
                    if expl_col and expl_col in filtered_df.columns:
                        show_cols.append(expl_col)

                    display_subset = chosen_students[show_cols].rename(columns={
                        class_col: 'Sınıf/Şube',
                        'Okul_No': 'No',
                        'Ad_Soyad': 'Öğrenci Adı Soyadı',
                        'Genel_Risk_Puani': 'Genel Risk Skoru'
                    })
                    if expl_col and expl_col in filtered_df.columns:
                        display_subset = display_subset.rename(columns={expl_col: 'Öğrencinin Açıklaması / Detay'})

                    st.dataframe(display_subset, use_container_width=True, hide_index=True)

                    # Bu maddeye özel Excel indirme butonu
                    b_io = io.BytesIO()
                    with pd.ExcelWriter(b_io, engine='xlsxwriter') as wr:
                        display_subset.to_excel(wr, sheet_name='Ogrenci_Listesi', index=False)
                    st.download_button(
                        label=f"📥 Bu Maddenin Öğrenci Listesini İndir (Excel)",
                        data=b_io.getvalue(),
                        file_name=f"Madde_Raporu_{item[:15].strip()}_{selected_class}.xlsx",
                        mime="application/vnd.ms-excel",
                        key=f"dl_{item}"
                    )

    # SEKME 2: EN YÜKSEK RİSKLİ ÖĞRENCİLER
    with tab_risk:
        st.subheader(f"En Yüksek Risk Sıralaması ({selected_class})")
        col_c1, col_c2 = st.columns([2, 1])
        with col_c1:
            min_risk = st.slider("Minimum Risk Eşiği:", min_value=0, max_value=int(df['Genel_Risk_Puani'].max()), value=15)
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

    # SEKME 3: ÖZEL ÇOKLU MADDE FİLTRESİ
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

            # Başlık bazında işaretlediği maddeler
            st.markdown("##### 📋 Başlıklara Göre İşaretlediği Maddeler:")
            for cat_name, cat_items_list in KATEGORILER.items():
                marked_in_cat = [q for q in cat_items_list if s_data[q] == "Bana Uygun"]
                if marked_in_cat:
                    st.markdown(f"**{cat_name} ({len(marked_in_cat)} Madde):**")
                    for q in marked_in_cat:
                        crit_flag = "🔴 " if "Kritik" in cat_name else "🔹 "
                        st.write(f"{crit_flag}{q}")

            # Açık uçlu metinler
            st.markdown("##### 📝 Öğrencinin Yazılı Notları:")
            note_cols = [c for c in df.columns if any(k in c.lower() for k in ['yazınız', 'belirtiniz', 'eklemek'])]
            found_any = False
            for nc in note_cols:
                if pd.notna(s_data[nc]) and str(s_data[nc]).strip() != "":
                    found_any = True
                    st.info(f"**{nc}:** {s_data[nc]}")
            if not found_any:
                st.caption("Öğrencinin ek bir açıklaması bulunmamaktadır.")

elif uploaded_file is not None and not st.session_state.analiz_yapildi:
    st.info("👈 Dosya hazır. Analizi çalıştırmak için sol paneldeki **'🚀 Analizi Başlat / Çalıştır (Run)'** butonuna tıklayınız.")
else:
    st.info("👈 Başlamak için sol menüden CSV veya Excel formatındaki anket dosyasını yükleyin.")