"""GENETICA — dashboard Streamlit UTS Algoritma Genetika.

Jalankan: python -m streamlit run app.py
Model simulasi: data dosen/mata kuliah mengikuti sumber; kapasitas dan beberapa kelas simulasi.
"""
from __future__ import annotations

import csv
import html
import io
import math
import statistics
from collections import Counter
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from src.excel_export import create_xlsx
from src.config_modes import AUTOMATIC_SEED, get_automatic_config, choose_operators
from src.genetic_timetable import (
    GAConfig, count_violations, load_data, run_ga, schedule_records,
    write_csv, write_chart, ROOT, RESULT_DIR,
)

st.set_page_config(page_title='GENETICA • Optimasi Jadwal', page_icon='🧬', layout='wide', initial_sidebar_state='expanded')
css = Path(__file__).parent / 'assets' / 'style.css'
st.markdown(f'<style>{css.read_text(encoding="utf-8")}</style>', unsafe_allow_html=True)

C = {'violet':'#9B8CF9','mint':'#43D6D7','blue':'#63A8F8','warn':'#FFBD75','muted':'#9BABCA','surface':'#151D31'}


def clean(value):
    return html.escape(str(value))


def section(label, title, description=None):
    st.markdown(f'<div class="sectioncap">{clean(label)}</div>', unsafe_allow_html=True)
    st.markdown(f'## {title}')
    if description:
        st.caption(description)


def hero(title, description, tag='PROJECT DASHBOARD'):
    st.markdown(f'''<div class="hero"><span class="eyebrow">{clean(tag)} • S1 Teknik Informatika</span>
    <h1>{clean(title)}</h1><p>{clean(description)}</p></div>''', unsafe_allow_html=True)


def feature(icon, title, description):
    st.markdown(f'<div class="feature"><span class="icon">{icon}</span><h4>{clean(title)}</h4><p>{clean(description)}</p></div>', unsafe_allow_html=True)


def badge(text):
    st.markdown(f'<span class="chip">{clean(text)}</span>', unsafe_allow_html=True)


def graph_theme(fig, height=390, y_max=None):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='DM Sans, Arial', color='#b4c4e1',size=12),
        margin=dict(l=16,r=18,t=25,b=24), height=height,
        hovermode='x unified', legend=dict(orientation='h',yanchor='bottom',y=1.01,x=0),
        xaxis=dict(showgrid=False,zeroline=False,linecolor='#293b55'),
        yaxis=dict(gridcolor='rgba(128,151,190,.12)',zeroline=False),
    )
    if y_max is not None:
        fig.update_yaxes(range=[0,y_max])
    return fig


def rows_to_csv(rows):
    if not rows:
        return b''
    output=io.StringIO()
    writer=csv.DictWriter(output,fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode('utf-8-sig')


def run_rows(runs):
    rows=[]
    for i,r in enumerate(runs,1):
        rows.append({
            'Run':i,'Seed':r['seed'],'Seleksi':r['selection'],'Crossover':r['crossover'],
            'Fitness_Terbaik':round(r['fitness_terbaik'],8),
            'Fitness_Rata_Populasi_Akhir':round(r['fitness_rata_populasi_akhir'],8),
            'Generasi_Valid_Pertama':r['generasi_valid_pertama'],
            'Generasi_Terakhir':r['generasi_berjalan'],
            'Total_Pelanggaran':sum(r['pelanggaran'].values()),
            'Durasi_Detik':r['durasi_detik'],
        })
    return rows


def make_xlsx_bytes(runs, chosen, records, courses, rooms, run_settings=None):
    """Bangun file Excel dari hasil optimasi yang sudah ada, tanpa efek samping."""
    summary = [
        ['Keterangan','Hasil'],['Mode','Simulasi UTS'],['Jumlah percobaan',len(runs)],
        ['Solusi valid',sum(v['fitness_terbaik']>=1 for v in runs)],
        ['Fitness rata-rata',round(statistics.mean(r['fitness_terbaik'] for r in runs),6)],
        ['Seed solusi terbaik',chosen['seed']],
        ['Fitness jadwal terbaik',chosen['fitness_terbaik']],
        ['Generasi valid pertama',chosen['generasi_valid_pertama']],
        ['Total bentrok',sum(chosen['pelanggaran'].values())],
        ['CATATAN','Kapasitas ruangan dan identitas sebagian kelas adalah SIMULASI, bukan data resmi.'],
    ]
    if run_settings:
        cfg = run_settings['config']
        summary.extend([
            ['Mode konfigurasi',run_settings['config_mode']],
            ['Mode pengujian',run_settings['run_mode']],
            ['Ukuran populasi',cfg.population_size],
            ['Maksimum generasi',cfg.max_generations],
            ['Probabilitas crossover',cfg.crossover_rate],
            ['Probabilitas mutasi per gen',cfg.mutation_rate],
            ['Elitisme',cfg.elitism],
            ['Seed awal',run_settings['seed']],
            ['Kebijakan seleksi',run_settings['selection_policy']],
            ['Kebijakan crossover',run_settings['crossover_policy']],
        ])
    datas = {
        'Ringkasan':summary,
        'Jadwal_Terbaik':records,
        'Hasil_Pengujian':run_rows(runs),
        'Grafik_Konvergensi':chosen['history'],
        'Validasi_Kendala':[['Jenis Kendala','Jumlah Pelanggaran']]+[[k,v] for k,v in chosen['pelanggaran'].items()],
        'Kapasitas_Simulasi':[['ID Ruang','Ruangan','Kapasitas simulasi']]+[[r.id,r.nama,r.kapasitas] for r in rooms],
        'Data_Mata_Kuliah':[['ID','Kode','Nama','Kelas','Dosen','SKS','Peserta','Status kelas']]+[
            [c.id,c.kode,c.nama,c.kelas,'; '.join(c.dosen),c.sks,c.mahasiswa,c.status_kelas] for c in courses
        ],
    }
    return create_xlsx(datas)


def save_outputs(runs, chosen, records, courses, rooms, run_settings=None):
    """Ekspor hasil ke folder hasil/ dan kembalikan bytes Excel untuk UI."""
    xlsx_bytes = make_xlsx_bytes(runs, chosen, records, courses, rooms, run_settings)
    RESULT_DIR.mkdir(parents=True,exist_ok=True)
    (RESULT_DIR/'Hasil_Optimasi_Genetica.xlsx').write_bytes(xlsx_bytes)
    write_csv(RESULT_DIR/'hasil_eksperimen_ui.csv',run_rows(runs))
    write_csv(RESULT_DIR/'jadwal_ui.csv',records)
    write_csv(RESULT_DIR/'konvergensi_ui.csv',chosen['history'])
    write_chart(chosen,RESULT_DIR/'grafik_konvergensi_ui.png')
    return xlsx_bytes


def available_excel_bytes(courses, rooms):
    """Pulihkan Excel apabila session_state belum memuatnya, misalnya setelah rerun."""
    data = st.session_state.get('xlsx_bytes')
    if data is None and st.session_state.get('best_run') and st.session_state.get('records'):
        data = make_xlsx_bytes(st.session_state['runs'], st.session_state['best_run'],
                               st.session_state['records'], courses, rooms,
                               st.session_state.get('run_settings'))
        st.session_state['xlsx_bytes'] = data
    return data


@st.cache_data(show_spinner=False)
def get_data():
    return load_data()


try:
    courses,rooms,days,slots,teachers = get_data()
except (AssertionError,FileNotFoundError,KeyError,ValueError) as exc:
    st.error(f'Dataset belum bisa dibaca: {exc}. Cek folder data/ dan README.')
    st.stop()

if 'runs' not in st.session_state:
    st.session_state['runs'] = []
if 'best_run' not in st.session_state:
    st.session_state['best_run'] = None
if 'records' not in st.session_state:
    st.session_state['records'] = []
if 'xlsx_bytes' not in st.session_state:
    st.session_state['xlsx_bytes'] = None
if 'run_settings' not in st.session_state:
    st.session_state['run_settings'] = None

# Perpindahan menu via tombol dilakukan sebelum widget radio dibuat.
if 'nav_next' in st.session_state:
    st.session_state['nav'] = st.session_state.pop('nav_next')

with st.sidebar:
    st.markdown('<div class="brand-title">◈ GENE<span>TICA</span></div><div class="brand-sub">TIMETABLE OPTIMIZER / UTS</div>', unsafe_allow_html=True)
    st.write('')
    choices=['Beranda','Optimasi AG','Jadwal Kuliah','Analisis Pengujian','Dataset & Aturan','Panduan']
    icons=['⌂','⬡','▦','⌁','▤','◉']
    page=st.radio('MENU UTAMA',choices,format_func=lambda x:f'{icons[choices.index(x)]}   {x}', label_visibility='collapsed',key='nav')
    st.divider()
    st.markdown('<div class="sectioncap">STATUS PROYEK</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="side-note">🟢 Dataset siap<br><strong>{len(courses)} mata kuliah</strong> · {len(rooms)} ruang · {len(teachers)} dosen<br><br>📍 Mode: <strong>Simulasi akademik</strong></div>',unsafe_allow_html=True)
    st.write('')
    if st.session_state['runs']:
        st.caption(f'✅ {len(st.session_state["runs"])} percobaan terakhir tersedia')
    else:
        st.caption('Belum menjalankan optimasi pada sesi ini.')
    st.caption('© 2026 • Proyek UTS Algoritma Genetika')


if page == 'Beranda':
    hero('Jadwal lebih cerdas. Tanpa bentrok.',
         'Dashboard optimasi jadwal kuliah menggunakan Algoritma Genetika yang diimplementasikan sendiri. Siap diuji, divisualisasikan, dan dipresentasikan saat UTS.')
    a,b,c,d=st.columns(4)
    a.metric('Mata kuliah',len(courses),help='20 entitas unik dari dataset sumber')
    b.metric('Dosen pengampu',len(teachers))
    c.metric('Ruangan',len(rooms),help='Kapasitas masing-masing masih simulasi')
    d.metric('Slot tersedia',len(days)*len(slots),help='5 hari × 5 slot 50 menit')
    st.write('')
    section('KENALI SISTEM','Dari dataset menjadi jadwal terbaik',
            'Alur kerja UTS yang dapat kamu jelaskan ketika presentasi.')
    x,y,z=st.columns(3,gap='medium')
    with x: feature('🧾','01 • Dataset','20 mata kuliah dan dosen sesuai sumber; beberapa kapasitas ruang dan identitas kelas diasumsikan.')
    with y: feature('🧬','02 • Evolusi','Seleksi, crossover, mutasi, dan elitisme menyusun kandidat jadwal dari generasi ke generasi.')
    with z: feature('📈','03 • Hasil','Fitness, validasi bentrok, grafik konvergensi, jadwal akhir, dan unduhan Excel atau CSV.')
    st.write('')
    l,r=st.columns([1.45,1],gap='large')
    with l:
        st.markdown('### ⚙️ Komponen algoritma')
        for text in ['Representasi satu gen = (hari, slot mulai, ruangan)',
                     'Seleksi roulette wheel dan turnamen',
                     'Crossover satu titik dan uniform',
                     'Mutasi acak serta elitisme',
                     'Evaluasi hard constraint dan minimal 10 run']:
            st.markdown(f'✓ &nbsp; {text}')
    with r:
        st.markdown('### ✨ Siap mencoba?')
        st.info('Masuk ke **Optimasi AG** → pilih **Otomatis** dan **10 run** → klik Jalankan. Semua parameter sudah tersedia; hasil muncul pada Jadwal dan Analisis.')
        if st.button('Mulai Optimasi  →',type='primary',use_container_width=True):
            st.session_state['nav_next']='Optimasi AG'
            st.rerun()
    st.warning('Dataset ini untuk SIMULASI. Kapasitas ruang dan beberapa identitas kelas bukan data resmi, sehingga solusi tanpa bentrok hanya berlaku untuk model simulasi.', icon='⚠️')

elif page == 'Optimasi AG':
    hero('Mesin optimasi Algoritma Genetika',
         'Atur parameter evolusi lalu jalankan pencarian jadwal. Semua operator AG ditulis manual, bukan menggunakan DEAP atau PyGAD.',
         'GENETIC ENGINE')
    left,right=st.columns([1.2,.8],gap='large')
    with left:
        section('KONFIGURASI','Parameter Algoritma Genetika')
        st.markdown('**Pilih cara pengaturan parameter:**')
        config_mode = st.radio(
            'Mode konfigurasi',
            ['⚡ Otomatis (Default)', '🛠️ Manual (Advanced)'],
            horizontal=True, label_visibility='collapsed', key='config_mode_ui',
        )
        is_automatic = config_mode.startswith('⚡')
        if is_automatic:
            st.caption('Parameter rekomendasi sudah disiapkan oleh aplikasi. Tidak perlu mengatur slider; tinggal jalankan optimasi.')
        else:
            st.caption('Sesuaikan seluruh parameter untuk mencoba konfigurasi atau melakukan eksperimen sendiri.')

        # Mode konfigurasi ≠ jumlah percobaan. Dipisah agar perubahan langsung memperbarui form.
        st.markdown('**Jumlah percobaan:**')
        run_mode=st.radio(
            'Jumlah run',
            ['10 run • UTS (direkomendasikan)','1 run • coba cepat'],
            horizontal=True, label_visibility='collapsed', key='run_mode_ui',
        )
        n=10 if run_mode.startswith('10') else 1

        with st.form('settings'):
            if is_automatic:
                settings = get_automatic_config()
                seed = AUTOMATIC_SEED
                selection_policy = 'bergantian'
                crossover_policy = 'bergantian'
                st.markdown(f"""<div class="auto-config-grid">
                    <div><span>POPULASI</span><strong>{settings.population_size}</strong></div>
                    <div><span>GENERASI MAKS.</span><strong>{settings.max_generations}</strong></div>
                    <div><span>CROSSOVER</span><strong>{settings.crossover_rate:.0%}</strong></div>
                    <div><span>MUTASI PER GEN</span><strong>{settings.mutation_rate:.0%}</strong></div>
                    <div><span>ELITISME</span><strong>{settings.elitism}</strong></div>
                    <div><span>SEED AWAL</span><strong>{seed}</strong></div>
                </div>""", unsafe_allow_html=True)
                if n == 10:
                    st.info('10 percobaan dengan seed berbeda: 5 memakai **roulette + one-point**, 5 memakai **tournament + uniform**.')
                else:
                    st.info('Coba cepat: **tournament selection + uniform crossover** dengan parameter default.')
            else:
                population=st.slider('Ukuran populasi',20,200,100,10,help='Banyaknya individu per generasi')
                generations=st.slider('Maksimum generasi',25,600,350,25)
                l1,l2=st.columns(2)
                with l1:
                    crossrate=st.slider('Probabilitas crossover',0.0,1.0,0.85,0.05)
                    elitism=st.number_input('Elitisme',min_value=1,max_value=10,value=2,step=1)
                with l2:
                    mutation=st.slider('Mutasi per gen',0.0,0.5,0.09,0.01)
                    seed=st.number_input('Seed awal',min_value=1,max_value=99999,value=101,step=1)
                settings=GAConfig(
                    population_size=int(population),max_generations=int(generations),
                    crossover_rate=float(crossrate),mutation_rate=float(mutation),
                    elitism=int(elitism),
                )
                if n == 10:
                    selection_label=st.selectbox('Kebijakan seleksi',[
                        'Bergantian (5 Roulette + 5 Tournament)',
                        'Roulette saja', 'Tournament saja',
                    ])
                    crossover_label=st.selectbox('Kebijakan crossover',[
                        'Bergantian (5 One-point + 5 Uniform)',
                        'One-point saja', 'Uniform saja',
                    ])
                    selection_policy = {
                        'Bergantian (5 Roulette + 5 Tournament)':'bergantian',
                        'Roulette saja':'roulette','Tournament saja':'tournament',
                    }[selection_label]
                    crossover_policy = {
                        'Bergantian (5 One-point + 5 Uniform)':'bergantian',
                        'One-point saja':'one_point','Uniform saja':'uniform',
                    }[crossover_label]
                else:
                    selection_policy=st.selectbox('Metode seleksi',['tournament','roulette'])
                    crossover_policy=st.selectbox('Metode crossover',['uniform','one_point'])
                st.caption('Pengaturan ini hanya digunakan pada proses optimasi berikutnya, tidak mengubah dataset sumber.')
            launched=st.form_submit_button('▶  Jalankan Optimasi Sekarang',use_container_width=True,type='primary')
    with right:
        section('MODEL UTS','Apa yang dihitung?')
        st.markdown('''<div class="panel"><span class="eyebrow">FUNGSI FITNESS</span>
        <h2 style="margin:12px 0;font-size:2rem">1 / (1 + P)</h2>
        <p class="small-note">P adalah total pelanggaran kendala keras. Fitness = 1 berarti tidak ditemukan bentrok pada model simulasi.</p>
        <div style="height:1px;background:#293752;margin:16px 0"></div>
        <span class="pill">5 hari • 5 slot/hari</span><br><br>
        <span class="pill">2 SKS → 2 slot</span> <span class="pill">3 SKS → 3 slot</span></div>''',unsafe_allow_html=True)
        st.write('')
        st.caption('Kendala dinilai untuk dosen, kelas, ruangan, kapasitas, dan indeks waktu. Slot kuliah berlangsung berurutan tanpa melewati hari.')
    if launched:
        run_settings = {
            'config_mode':'Otomatis' if is_automatic else 'Manual',
            'run_mode':run_mode,
            'config':settings,
            'seed':int(seed),
            'selection_policy':selection_policy,
            'crossover_policy':crossover_policy,
        }
        st.markdown('### Proses optimasi')
        progress=st.progress(0,text='Menyiapkan populasi...')
        info=st.empty()
        results=[]
        try:
            for i in range(n):
                s=int(seed)+i
                selection,crossover=choose_operators(
                    i, n, selection_policy, crossover_policy,
                )
                info.caption(f'Percobaan {i+1}/{n} · seed {s} · {selection} / {crossover}')
                result=run_ga(courses,rooms,days,slots,s,settings,selection,crossover)
                results.append(result)
                progress.progress(int((i+1)/n*100),text=f'{i+1} dari {n} run selesai')
            best=min(results,key=lambda r:(-r['fitness_terbaik'],
                                            r['generasi_valid_pertama'] if r['generasi_valid_pertama'] is not None else math.inf,
                                            r['durasi_detik']))
            records=schedule_records(best['jadwal'],courses,rooms,days,slots,teachers)
            # Tetap validasi ulang jadwal terbaik sebelum ditampilkan dan diekspor.
            assert sum(count_violations(best['jadwal'],courses,rooms,days,slots).values()) == sum(best['pelanggaran'].values())
            # Siapkan workbook terlebih dulu, baru tandai sesi sebagai berhasil.
            # Dengan begitu halaman jadwal tidak pernah memiliki records tanpa XLSX.
            workbook = save_outputs(results,best,records,courses,rooms,run_settings)
            st.session_state['xlsx_bytes']=workbook
            st.session_state['runs']=results
            st.session_state['best_run']=best
            st.session_state['records']=records
            st.session_state['config_used']=settings
            st.session_state['run_settings']=run_settings
            info.empty()
            st.success(f'Selesai! {sum(r["fitness_terbaik"]==1 for r in results)}/{n} run menemukan jadwal valid pada data simulasi.')
        except Exception as exc:
            st.error(f'Optimasi gagal: {exc}. Silakan cek data dan parameter.')
    best=st.session_state.get('best_run')
    if best:
        st.divider()
        section('HASIL TERAKHIR','Ringkasan optimasi')
        runs=st.session_state['runs']
        last_settings=st.session_state.get('run_settings')
        if last_settings:
            st.caption(f"Konfigurasi terakhir: **{last_settings['config_mode']}** · {last_settings['run_mode']} · seed {last_settings['seed']}")
        a,b,c,d=st.columns(4)
        a.metric('Fitness terbaik',f'{best["fitness_terbaik"]:.4f}')
        b.metric('Total pelanggaran',sum(best['pelanggaran'].values()))
        c.metric('Generasi valid',best['generasi_valid_pertama'] if best['generasi_valid_pertama'] is not None else 'Belum')
        d.metric('Run berhasil',f'{sum(r["fitness_terbaik"]==1 for r in runs)}/{len(runs)}')
        history=best['history']
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=[r['generasi'] for r in history],y=[r['fitness_terbaik'] for r in history],
                                 name='Fitness terbaik',mode='lines',line=dict(color=C['violet'],width=3),fill='tozeroy',fillcolor='rgba(133,115,249,.09)'))
        fig.add_trace(go.Scatter(x=[r['generasi'] for r in history],y=[r['fitness_rata_populasi'] for r in history],
                                 name='Rata-rata populasi',mode='lines',line=dict(color=C['mint'],width=2,dash='dot')))
        fig.update_xaxes(title='Generasi')
        fig.update_yaxes(title='Fitness')
        st.plotly_chart(graph_theme(fig,y_max=1.05),use_container_width=True)
        x,y=st.columns(2)
        with x:
            try:
                excel_data = available_excel_bytes(courses,rooms)
            except Exception as exc:
                excel_data = None
                st.warning(f'File Excel belum bisa dibuat: {exc}')
            if excel_data is not None:
                st.download_button('⬇  Download Hasil Excel', data=excel_data,
                                   file_name='Hasil_Optimasi_Genetica.xlsx',
                                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                   use_container_width=True,type='primary')
            else:
                st.info('File Excel belum tersedia. Jalankan optimasi terlebih dahulu.')
        with y:
            st.download_button('⬇  Download Jadwal CSV',rows_to_csv(st.session_state['records']),
                               file_name='Jadwal_Optimasi_Genetica.csv',mime='text/csv',use_container_width=True)

elif page == 'Jadwal Kuliah':
    hero('Jadwal terbaik yang berhasil ditemukan',
         'Lihat penempatan mata kuliah menurut hari, jam, dosen, kelas, dan ruangan. Kamu bisa menyaring dan mengunduh jadwal.',
         'SCHEDULE VIEW')
    records=st.session_state['records']
    if not records:
        st.info('Belum ada jadwal untuk sesi ini. Jalankan optimasi terlebih dahulu melalui menu **Optimasi AG**.')
        st.caption('Di folder hasil/ terdapat contoh jadwal dari pengujian sebelumnya, tetapi UI tidak akan menganggapnya sebagai hasil run sesi saat ini.')
    else:
        best=st.session_state['best_run']
        v=best['pelanggaran']
        a,b,c,d=st.columns(4)
        a.metric('Dosen bentrok',v['dosen'])
        b.metric('Kelas bentrok',v['kelas'])
        c.metric('Ruangan bentrok',v['ruangan'])
        d.metric('Kapasitas bermasalah',v['kapasitas'])
        st.write('')
        section('FILTER JADWAL','Telusuri hasil penjadwalan')
        a,b,c=st.columns(3)
        with a: chosen_day=st.selectbox('Hari',['Semua hari']+days)
        with b: chosen_room=st.selectbox('Ruangan',['Semua ruangan']+[r.nama for r in rooms])
        with c: chosen_class=st.selectbox('Kelas',['Semua kelas']+sorted({r['Kelas'] for r in records}))
        filtered=[r for r in records if (chosen_day=='Semua hari' or r['Hari']==chosen_day)
                  and (chosen_room=='Semua ruangan' or r['Ruangan']==chosen_room)
                  and (chosen_class=='Semua kelas' or r['Kelas']==chosen_class)]
        st.dataframe(filtered,hide_index=True,use_container_width=True,height=425,
                     column_order=['Hari','Jam_Mulai','Jam_Selesai','Mata_Kuliah','SKS','Nama_Dosen','Kelas','Ruangan','Jumlah_Mahasiswa','Kapasitas_Ruang'])
        st.caption(f'{len(filtered)} dari {len(records)} sesi ditampilkan. Tabel lengkap tersedia pada Excel dan CSV.')
        l,r=st.columns(2)
        with l:
            st.download_button('⬇  Unduh Jadwal CSV',rows_to_csv(filtered),file_name='Jadwal_Terfilter.csv',mime='text/csv',use_container_width=True)
        with r:
            try:
                excel_data = available_excel_bytes(courses,rooms)
            except Exception as exc:
                excel_data = None
                st.warning(f'File Excel belum bisa dibuat: {exc}')
            if excel_data is not None:
                st.download_button('⬇  Unduh Semua Hasil Excel', data=excel_data,
                                   file_name='Hasil_Optimasi_Genetica.xlsx',
                                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                   use_container_width=True)
            else:
                st.info('File Excel belum tersedia. Jalankan optimasi terlebih dahulu.')
        st.write('')
        section('TIMETABLE','Matriks jadwal berdasarkan hari × slot')
        st.caption('Setiap sel bisa berisi beberapa kuliah dari kelas/ruang berbeda. Untuk kuliah multi-SKS, sesi ditampilkan di setiap slot yang dipakai.')
        occupancy={}
        for rec in records:
            start=next(i for i,s in enumerate(slots) if s['ID_Slot']==rec['ID_Slot_Mulai'])
            for sidx in range(start,start+rec['SKS']):
                occupancy.setdefault((rec['Hari'],sidx),[]).append(f"{rec['Mata_Kuliah']} · {rec['Ruangan']} · {rec['Kelas']}")
        matrix=[]
        for day in days:
            row={'Hari':day}
            for j,slot in enumerate(slots):
                row[f"{slot['Jam_Mulai']}–{slot['Jam_Selesai']}"]='\n'.join(occupancy.get((day,j),[])) or '—'
            matrix.append(row)
        st.dataframe(matrix,hide_index=True,use_container_width=True,height=380)

elif page == 'Analisis Pengujian':
    hero('Bukti pengujian, bukan perkiraan.',
         'Evaluasi pengaruh proses evolusi: bandingkan 10 run dengan seed berbeda, fitness, waktu komputasi, dan generasi menemukan jadwal valid.',
         'EXPERIMENTAL RESULTS')
    runs=st.session_state['runs']
    if not runs:
        st.info('Belum ada pengujian sesi ini. Pilih **10 run • UTS** pada menu Optimasi AG agar hasil analisis lengkap.')
    else:
        summary=run_rows(runs)
        a,b,c,d=st.columns(4)
        a.metric('Total run',len(runs))
        b.metric('Fitness rata-rata',f'{statistics.mean(r["fitness_terbaik"] for r in runs):.4f}')
        c.metric('Berhasil fitness 1',f'{sum(r["fitness_terbaik"]==1 for r in runs)}/{len(runs)}')
        d.metric('Rata-rata waktu',f'{statistics.mean(r["durasi_detik"] for r in runs):.2f} s')
        st.write('')
        section('PERBANDINGAN','Ringkasan performa per run')
        chart=go.Figure()
        chart.add_trace(go.Bar(x=[f'#{r["Run"]} · {r["Seleksi"][:3]}' for r in summary],
                               y=[r['Generasi_Valid_Pertama'] if r['Generasi_Valid_Pertama'] is not None else r['Generasi_Terakhir'] for r in summary],
                               name='Generasi',marker_color=C['violet'],marker_line_width=0))
        chart.update_xaxes(title='Run / seleksi')
        chart.update_yaxes(title='Generasi saat jadwal valid ditemukan')
        st.plotly_chart(graph_theme(chart),use_container_width=True)
        st.dataframe(summary,hide_index=True,use_container_width=True,height=365)
        st.write('')
        st.markdown('### Detail validasi kendala jadwal terbaik')
        v=st.session_state['best_run']['pelanggaran']
        st.dataframe([{'Jenis kendala':key.capitalize(),'Jumlah pelanggaran':val} for key,val in v.items()],hide_index=True,use_container_width=True)
        st.download_button('⬇  Unduh Hasil Pengujian 10 Run (CSV)',rows_to_csv(summary),
                           file_name='Hasil_Pengujian_Genetica.csv',mime='text/csv',use_container_width=True)
        if len(runs)<10:
            st.warning('Saat ini baru 1 run. Dokumen UTS mewajibkan minimal 10 run dengan seed berbeda.')

elif page == 'Dataset & Aturan':
    hero('Data yang jelas. Hasil yang bisa diperiksa.',
         'Periksa data 20 mata kuliah, dosen, ruangan dan slot waktu yang digunakan oleh mesin optimasi.',
         'DATASET EXPLORER')
    st.warning('Kapasitas ruang dan identitas kelas tertentu adalah asumsi simulasi. Jangan menyebutnya sebagai data resmi.')
    a,b,c,d=st.tabs(['Mata kuliah','Dosen','Ruangan','Hari & slot'])
    with a:
        st.markdown('### 20 mata kuliah unik')
        data=[{'ID':co.id,'Kode MK':co.kode,'Mata kuliah':co.nama,'Dosen':'; '.join(teachers[d] for d in co.dosen),
               'Kelas':co.kelas,'Semester':co.semester or '—','SKS':co.sks,'Mahasiswa':co.mahasiswa,
               'Status kelas':co.status_kelas} for co in courses]
        st.dataframe(data,hide_index=True,use_container_width=True,height=540)
        st.download_button('⬇  Data mata kuliah CSV',rows_to_csv(data),file_name='mata_kuliah.csv',mime='text/csv')
        st.caption(f'{sum(co.status_kelas.startswith("SIMULASI") for co in courses)} mata kuliah masih memiliki kelas simulasi.')
    with b:
        st.markdown('### 8 dosen pengampu')
        rows=[{'ID':tid,'Nama dosen':name,'Jumlah mata kuliah':sum(tid in co.dosen for co in courses)}
              for tid,name in teachers.items()]
        st.dataframe(rows,hide_index=True,use_container_width=True)
    with c:
        st.markdown('### 5 ruangan')
        st.dataframe([{'Kode':r.id,'Ruangan':r.nama,'Kapasitas':r.kapasitas,'Status':'SIMULASI'} for r in rooms],
                     hide_index=True,use_container_width=True)
        st.info('Ganti kapasitas di **data/ruangan.csv** sesuai data riil jika sudah tersedia, lalu refresh aplikasi. Nilai awal saat ini hanya asumsi.')
    with d:
        st.markdown('### 5 hari × 5 slot')
        st.write('Hari: '+', '.join(days))
        st.dataframe([{'Slot':s['ID_Slot'],'Mulai':s['Jam_Mulai'],'Selesai':s['Jam_Selesai']} for s in slots],
                     hide_index=True,use_container_width=True)
        st.caption('Mata kuliah 2 SKS memakai 2 slot berturutan; 3 SKS memakai 3 slot berturutan (1 slot = 50 menit).')
    st.divider()
    section('HARD CONSTRAINT','Aturan penjadwalan')
    a,b=st.columns(2)
    with a:
        feature('👨‍🏫','Tidak bentrok dosen','Seorang dosen tidak boleh mengampu lebih dari satu sesi di hari dan slot yang sama.')
        st.write('')
        feature('🏫','Tidak bentrok ruangan','Satu ruangan tidak boleh digunakan lebih dari satu sesi pada waktu bersamaan.')
    with b:
        feature('👨‍🎓','Tidak bentrok kelas','Mahasiswa dalam satu kelompok kelas tidak mendapat dua mata kuliah pada slot yang sama.')
        st.write('')
        feature('📏','Kapasitas mencukupi','Jumlah peserta suatu sesi tidak boleh melebihi kapasitas ruangan yang ditugaskan.')

else:
    hero('Panduan aplikasi & proyek UTS',
         'Kumpulan langkah sederhana untuk memahami aplikasi, menjalankan demo, dan menjelaskan algoritma saat presentasi.',
         'USER GUIDE')
    with st.expander('01 · Bagaimana cara menjalankan di VS Code?',expanded=True):
        st.code('py -m venv .venv\n.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n.venv\\Scripts\\python.exe -m streamlit run app.py',language='powershell')
        st.caption('Jalankan dari folder akar proyek pada terminal VS Code (Windows).')
    with st.expander('02 · Apa yang harus didemokan saat UTS?'):
        st.markdown('''1. Buka **Dataset & Aturan** dan jelaskan entitas serta hard constraint.  
2. Buka **Optimasi AG**, pilih **Otomatis** + **10 run** dan jalankan. Tunjukkan opsi Manual bila diminta dosen.  
3. Jelaskan rumus fitness serta grafik konvergensi.  
4. Buka **Jadwal Kuliah** untuk cek bentrok dan tabel jadwal.  
5. Buka **Analisis Pengujian** untuk menunjukkan hasil 10 seed.  
6. Unduh Excel sebagai bukti hasil.''')
    with st.expander('03 · Apa beda mode Otomatis dan Manual?'):
        st.markdown('**Otomatis:** populasi 100, generasi maksimal 350, crossover 85%, mutasi 9% per gen, elitisme 2, seed awal 101. Cocok untuk demo tanpa mengisi konfigurasi. **Manual:** slider dan pilihan operator dapat diubah. Kedua mode menggunakan fungsi AG yang sama dan tetap mendukung 1 atau 10 run.')
    with st.expander('04 · Apa arti kromosom dan gen?'):
        st.markdown('**Kromosom** adalah satu alternatif jadwal lengkap yang berisi 20 gen. **Gen** menyimpan `(hari, slot_mulai, ruangan)` untuk satu mata kuliah. Operator genetika memperbaiki kombinasi tersebut.')
    with st.expander('05 · Apa bedanya roulette, tournament, crossover, mutasi dan elitisme?'):
        st.markdown('''**Roulette:** peluang terpilih sebanding dengan fitness.  
**Tournament:** beberapa individu dipilih secara acak lalu diambil yang paling fit.  
**One-point crossover:** kromosom orang tua dipotong sekali lalu segmen ditukar.  
**Uniform crossover:** setiap posisi gen memilih dari salah satu orang tua.  
**Mutasi:** hari, slot, atau ruangan sebuah gen diubah acak.  
**Elitisme:** individu terbaik dipertahankan langsung ke generasi berikutnya.''')
    with st.expander('06 · Apakah semua data sudah asli?'):
        st.markdown('Belum. Nama mata kuliah, dosen, SKS, dan jumlah peserta mengikuti file sumber yang digunakan. **Kapasitas ruangan dan beberapa identitas kelas ditetapkan sebagai simulasi.** Hasil tanpa bentrok valid terhadap model ini, bukan bukti jadwal resmi universitas.')
    st.info('Kode inti Algoritma Genetika ada di `src/genetic_timetable.py`, sedangkan UI yang kamu lihat ada di `app.py`. Keduanya sebaiknya dipelajari untuk tanya jawab individu.')
