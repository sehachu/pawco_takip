import streamlit as st
import pandas as pd
import sqlite3
import datetime
import plotly.express as px

st.set_page_config(page_title="Pet & Kuafor", layout="centered") # 'wide' yerine 'centered' mobilde daha iyi durur
# --- AYARLAR VE VERİTABANI BAĞLANTISI ---
st.set_page_config(page_title="PAWCO Mağaza Yönetim Paneli", layout="wide", initial_sidebar_state="expanded")

def get_connection():
    return sqlite3.connect('isyeri_verileri.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Ana Tablo
    c.execute('''CREATE TABLE IF NOT EXISTS gunluk_kayitlar 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih DATE, 
                  pet_nakit REAL, pet_kart REAL, 
                  kuafor_nakit REAL, kuafor_kart REAL,
                  gider REAL, musteri_sayisi INTEGER, personel_ad TEXT)''')
    # Personel Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS personeller 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ad TEXT UNIQUE)''')
    conn.commit()
    conn.close()

# Veritabanını başlat
init_db()

# --- YARDIMCI FONKSİYONLAR ---
def veri_cek(sorgu="SELECT * FROM gunluk_kayitlar"):
    conn = get_connection()
    df = pd.read_sql_query(sorgu, conn)
    conn.close()
    return df

def veri_isleme(df):
    if not df.empty:
        df['tarih'] = pd.to_datetime(df['tarih'])
        df['pet_toplam'] = df['pet_nakit'] + df['pet_kart']
        df['kuafor_toplam'] = df['kuafor_nakit'] + df['kuafor_kart']
        df['toplam_ciro'] = df['pet_toplam'] + df['kuafor_toplam']
        df['net_kar'] = df['toplam_ciro'] - df['gider']
        # Sepet ortalaması (Sıfıra bölme hatasını önlemek için)
        df['sepet_ort'] = df.apply(lambda x: x['toplam_ciro'] / x['musteri_sayisi'] if x['musteri_sayisi'] > 0 else 0, axis=1)
    return df

# --- SAYFA YÖNETİMİ (SESSION STATE) ---
if 'sayfa' not in st.session_state:
    st.session_state.sayfa = 'Dashboard'
if 'secilen_tarih_ozeti' not in st.session_state:
    st.session_state.secilen_tarih_ozeti = datetime.date.today()

def sayfa_degistir(sayfa_adi):
    st.session_state.sayfa = sayfa_adi

# --- MENÜ (SIDEBAR) ---
with st.sidebar:
    st.title("🐾 Acıbadem Mağazası Yönetim Paneli")
    st.markdown("---")
    if st.button("📊 Genel Dashboard", use_container_width=True): sayfa_degistir('Dashboard')
    if st.button("💰 Veri Girişi", use_container_width=True): sayfa_degistir('Veri Girişi')
    if st.button("📅 Aylık Özet", use_container_width=True): sayfa_degistir('Aylık Özet')
    if st.button("📅 Günün Özeti", use_container_width=True): sayfa_degistir('Günün Özeti')
    st.markdown("---")
    if st.button("👤 Personel Performans", use_container_width=True): sayfa_degistir('Personel Performans')
    if st.button("⚙️ Ayarlar & Düzenleme", use_container_width=True): sayfa_degistir('Ayarlar')

# =================================================================================================
# 1. DASHBOARD SAYFASI (TÜM ZAMANLAR)
# =================================================================================================
if st.session_state.sayfa == 'Dashboard':
    st.header("📊 Genel İşletme Paneli (Tüm Zamanlar)")
    df = veri_cek()
    df = veri_isleme(df)

    if df.empty:
        st.info("Henüz veri girişi yapılmadı.")
    else:
        # --- Üst Metrikler ---
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Toplam Ciro", f"{df['toplam_ciro'].sum():,.0f} TL")
        col2.metric("Toplam Net Kâr", f"{df['net_kar'].sum():,.0f} TL")
        col3.metric("Ort. Sepet", f"{df['sepet_ort'].mean():,.2f} TL")
        col4.metric("Toplam Müşteri", f"{df['musteri_sayisi'].sum()}")
        col5.metric("Gider Toplamı", f"{df['gider'].sum():,.0f} TL")

        st.markdown("---")

        # --- Grafikler ---
        c_left, c_right = st.columns([2, 1])
        
        with c_left:
            st.subheader("📅 Hangi Gün Daha Çok Kazanıyorum? (Haftalık Analiz)")
            df['Gun'] = df['tarih'].dt.day_name()
            gun_sirasi = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            gun_tr = {"Monday":"Pazartesi", "Tuesday":"Salı", "Wednesday":"Çarşamba", "Thursday":"Perşembe", 
                      "Friday":"Cuma", "Saturday":"Cumartesi", "Sunday":"Pazar"}
            df['Gun_Tr'] = df['Gun'].map(gun_tr)
            
            # Günlük ortalama ciro
            gunluk_analiz = df.groupby('Gun_Tr')['toplam_ciro'].mean().reindex(gun_tr.values()).reset_index()
            fig_hafta = px.bar(gunluk_analiz, x='Gun_Tr', y='toplam_ciro', color='toplam_ciro',
                               title="Günlere Göre Ortalama Ciro", labels={'Gun_Tr':'Gün', 'toplam_ciro':'Ort. Ciro'})
            st.plotly_chart(fig_hafta, use_container_width=True)

        with c_right:
            st.subheader("💳 Gelir Dağılımı")
            # Petshop vs Kuaför
            fig_bolum = px.pie(values=[df['pet_toplam'].sum(), df['kuafor_toplam'].sum()], 
                               names=['Petshop', 'Kuaför'], hole=0.4, title="Departman Payı")
            st.plotly_chart(fig_bolum, use_container_width=True)
            
            # Nakit vs Kart
            nakit = df['pet_nakit'].sum() + df['kuafor_nakit'].sum()
            kart = df['pet_kart'].sum() + df['kuafor_kart'].sum()
            fig_odeme = px.pie(values=[nakit, kart], names=['Nakit', 'Kart'], 
                               title="Ödeme Yöntemi Dağılımı", color_discrete_sequence=['#00CC96', '#636EFA'])
            st.plotly_chart(fig_odeme, use_container_width=True)

        # Trend Grafiği
        st.subheader("📈 Ciro ve Kâr Trendi")
        fig_trend = px.line(df.sort_values('tarih'), x='tarih', y=['toplam_ciro', 'net_kar', 'gider'], markers=True)
        st.plotly_chart(fig_trend, use_container_width=True)

# =================================================================================================
# 2. VERİ GİRİŞİ SAYFASI
# =================================================================================================
elif st.session_state.sayfa == 'Veri Girişi':
    st.header("📝 Günlük Veri Girişi")
    
    # Personel Kontrolü
    personeller = veri_cek("SELECT ad FROM personeller")['ad'].tolist()
    
    if not personeller:
        st.error("⚠️ Önce 'Ayarlar' sayfasından personel eklemelisiniz!")
    else:
        with st.form("veri_formu"):
            col_date, col_pers = st.columns(2)
            tarih = col_date.date_input("Tarih", datetime.date.today())
            personel = col_pers.selectbox("Personel", personeller)
            
            st.markdown("### 🛒 Petshop")
            c1, c2 = st.columns(2)
            pn = c1.number_input("Pet Nakit", min_value=0.0)
            pk = c2.number_input("Pet Kart", min_value=0.0)
            
            st.markdown("### ✂️ Kuaför")
            c3, c4 = st.columns(2)
            kn = c3.number_input("Kuaför Nakit", min_value=0.0)
            kk = c4.number_input("Kuaför Kart", min_value=0.0)
            
            st.markdown("### 📉 Gider ve Müşteri")
            c5, c6 = st.columns(2)
            gider = c5.number_input("Toplam Gider", min_value=0.0)
            musteri = c6.number_input("Müşteri Sayısı", min_value=1, step=1)
            
            if st.form_submit_button("Kaydet ve Özeti Göster"):
                conn = get_connection()
                conn.execute('''INSERT INTO gunluk_kayitlar 
                    (tarih, pet_nakit, pet_kart, kuafor_nakit, kuafor_kart, gider, musteri_sayisi, personel_ad) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                    (tarih, pn, pk, kn, kk, gider, musteri, personel))
                conn.commit()
                conn.close()
                
                # YÖNLENDİRME MANTIĞI
                st.session_state.secilen_tarih_ozeti = tarih # Tarihi hafızaya al
                st.session_state.sayfa = 'Günün Özeti' # Sayfayı değiştir
                st.rerun() # Uygulamayı yenile

# =================================================================================================
# 3. GÜNÜN ÖZETİ SAYFASI
# =================================================================================================
elif st.session_state.sayfa == 'Günün Özeti':
    secilen_t = st.session_state.secilen_tarih_ozeti
    st.header(f"📅 Günün Özeti: {secilen_t}")
    
    # Sadece o günün verisini çek
    df_all = veri_cek()
    df_all = veri_isleme(df_all)
    # Tarihi stringe çevirip filtrele (saat farkı olmaması için)
    df_gun = df_all[df_all['tarih'].dt.date == secilen_t]
    
    if df_gun.empty:
        st.warning("Bu tarih için kayıt bulunamadı.")
        if st.button("Veri Girişine Dön"):
            st.session_state.sayfa = 'Veri Girişi'
            st.rerun()
    else:
        # Verileri topla (Birden fazla giriş varsa o gün için toplar)
        t_ciro = df_gun['toplam_ciro'].sum()
        t_kar = df_gun['net_kar'].sum()
        t_pet = df_gun['pet_toplam'].sum()
        t_kua = df_gun['kuafor_toplam'].sum()
        t_mus = df_gun['musteri_sayisi'].sum()
        ort_sepet = t_ciro / t_mus if t_mus > 0 else 0
        
        # --- KARTLAR ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Günün Cirosu", f"{t_ciro:,.0f} TL")
        m2.metric("Net Kâr", f"{t_kar:,.0f} TL")
        m3.metric("Müşteri", f"{t_mus}")
        m4.metric("Sepet Ort.", f"{ort_sepet:,.2f} TL")
        
        st.markdown("---")
        
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            st.subheader("Departman Geliri")
            st.write(f"🛒 **Petshop:** {t_pet:,.2f} TL")
            st.write(f"✂️ **Kuaför:** {t_kua:,.2f} TL")
            fig_dep = px.bar(x=['Petshop', 'Kuaför'], y=[t_pet, t_kua], color=['Petshop', 'Kuaför'])
            st.plotly_chart(fig_dep, use_container_width=True)
            
        with col_g2:
            st.subheader("Ödeme Yöntemi")
            n_top = df_gun['pet_nakit'].sum() + df_gun['kuafor_nakit'].sum()
            k_top = df_gun['pet_kart'].sum() + df_gun['kuafor_kart'].sum()
            fig_pay = px.pie(values=[n_top, k_top], names=['Nakit', 'Kart'], hole=0.5, color_discrete_sequence=['orange', 'blue'])
            st.plotly_chart(fig_pay, use_container_width=True)
            
        with col_g3:
            st.info("Bu sayfada, az önce girdiğiniz veya seçtiğiniz tarihe ait verilerin özetini görüyorsunuz.")
            if st.button("Yeni Kayıt Ekle"):
                st.session_state.sayfa = 'Veri Girişi'
                st.rerun()

# =================================================================================================
# 4. AYLIK ÖZET SAYFASI
# =================================================================================================
elif st.session_state.sayfa == 'Aylık Özet':
    st.header("📅 Aylık Konsolide Rapor")
    df = veri_cek()
    df = veri_isleme(df)
    
    if not df.empty:
        df['Ay'] = df['tarih'].dt.strftime('%Y-%m') # Yıl-Ay formatı
        
        # Aylık gruplama
        aylik = df.groupby('Ay').agg({
            'toplam_ciro': 'sum', 'net_kar': 'sum', 'gider': 'sum',
            'pet_toplam': 'sum', 'kuafor_toplam': 'sum', 'musteri_sayisi': 'sum'
        }).reset_index()
        
        st.dataframe(aylik, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Aylık Ciro ve Kâr")
            fig_ay = px.bar(aylik, x='Ay', y=['toplam_ciro', 'net_kar'], barmode='group')
            st.plotly_chart(fig_ay, use_container_width=True)
        with c2:
            st.subheader("Aylık Departman Yarışı")
            fig_yaris = px.line(aylik, x='Ay', y=['pet_toplam', 'kuafor_toplam'], markers=True)
            st.plotly_chart(fig_yaris, use_container_width=True)

# =================================================================================================
# 5. PERSONEL PERFORMANS SAYFASI
# =================================================================================================
elif st.session_state.sayfa == 'Personel Performans':
    st.header("👤 Personel Performans Analizi")
    df = veri_cek()
    df = veri_isleme(df)
    
    personeller = veri_cek("SELECT ad FROM personeller")['ad'].tolist()
    
    if personeller:
        secilen_p = st.selectbox("Personel Seçiniz:", personeller)
        
        # Filtrele
        p_df = df[df['personel_ad'] == secilen_p]
        
        if not p_df.empty:
            k1, k2, k3 = st.columns(3)
            k1.metric("Toplam Kazandırdığı Ciro", f"{p_df['toplam_ciro'].sum():,.2f} TL")
            k2.metric("Toplam İşlem Sayısı", f"{len(p_df)}")
            k3.metric("Ortalama Günlük Ciro", f"{p_df['toplam_ciro'].mean():,.2f} TL")
            
            st.subheader(f"{secilen_p} - Zaman İçindeki Performansı")
            fig_p = px.bar(p_df, x='tarih', y='toplam_ciro', color='toplam_ciro')
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.warning("Bu personelin henüz satış kaydı yok.")
    else:
        st.error("Personel bulunamadı.")

# =================================================================================================
# 6. AYARLAR & DÜZENLEME (Kayıt ve Personel Yönetimi)
# =================================================================================================
elif st.session_state.sayfa == 'Ayarlar':
    st.header("⚙️ Sistem Ayarları")
    
    tab_p, tab_d = st.tabs(["👥 Personel Yönetimi", "✏️ Kayıt Düzenle/Sil"])
    
    # --- Personel Ekle/Çıkar ---
    with tab_p:
        col_add, col_list = st.columns(2)
        
        with col_add:
            st.subheader("Yeni Personel Ekle")
            yeni_ad = st.text_input("Ad Soyad")
            if st.button("Ekle"):
                try:
                    conn = get_connection()
                    conn.execute("INSERT INTO personeller (ad) VALUES (?)", (yeni_ad,))
                    conn.commit()
                    conn.close()
                    st.success(f"{yeni_ad} eklendi.")
                    st.rerun()
                except:
                    st.error("Hata veya mükerrer isim.")
        
        with col_list:
            st.subheader("Mevcut Personeller")
            p_df = veri_cek("SELECT * FROM personeller")
            for i, row in p_df.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.text(f"• {row['ad']}")
                if c2.button("Sil", key=f"del_p_{row['id']}"):
                    conn = get_connection()
                    conn.execute("DELETE FROM personeller WHERE id = ?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.rerun()

    # --- Veri Düzenle/Sil (Data Editor) ---
    with tab_d:
        st.subheader("Geçmiş Kayıtları Düzenle")
        st.info("Tablodaki değerleri üzerine çift tıklayarak değiştirebilirsiniz. Silmek için satırı seçip 'Delete' tuşuna basmayın, yandaki kutucuğu işaretleyip sil butonunu kullanın.")
        
        # Verileri çek
        conn = get_connection()
        df_edit = pd.read_sql_query("SELECT * FROM gunluk_kayitlar ORDER BY tarih DESC", conn)
        conn.close()

        # Data Editor (Excel gibi düzenleme)
        edited_df = st.data_editor(df_edit, num_rows="dynamic", key="data_editor")

        # Değişiklikleri Kaydet Butonu
        if st.button("Değişiklikleri Veritabanına Kaydet"):
            # Orijinal veritabanını güncellemek biraz karmaşıktır, en temizi silip yeniden yazmaktır
            # Ancak ID'leri korumak için satır bazlı güncelleme yapalım.
            
            # Bu demo için basit yöntem:
            try:
                conn = get_connection()
                # Önce tüm tabloyu temizle (Riskli ama basit projeler için pratik)
                # Profesyonel yöntem UPDATE sorgusu kullanmaktır ama data_editor çıktısı ile zordur.
                # Biz burada data_editor'un bize verdiği son hali veritabanına yazacağız.
                
                # Ancak 'id' çakışması olmaması için:
                edited_df.to_sql('gunluk_kayitlar', conn, if_exists='replace', index=False)
                conn.close()
                st.success("Tablo güncellendi!")
                st.rerun()
            except Exception as e:
                st.error(f"Hata oluştu: {e}")

