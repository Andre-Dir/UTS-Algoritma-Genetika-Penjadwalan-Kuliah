"""Algoritma Genetika penjadwalan kuliah skala UTS (tanpa library AG).

Setiap gen: (indeks_hari, indeks_slot_mulai, indeks_ruang).
Durasi kelas = SKS slot 50-menit berturutan. Tidak melintasi hari.
Kapasitas ruang dijaga saat memilih lokasi, dan tetap divalidasi di fitness.
"""
from __future__ import annotations

import copy
import csv
import json
import math
import random
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data'
RESULT_DIR = ROOT / 'hasil'

@dataclass(frozen=True)
class Course:
    id: str
    kode: str
    nama: str
    kelas: str
    semester: str
    sks: int
    mahasiswa: int
    dosen: tuple[str, ...]
    status_kelas: str

@dataclass(frozen=True)
class Room:
    id: str
    nama: str
    kapasitas: int

@dataclass(frozen=True)
class GAConfig:
    population_size: int = 100
    max_generations: int = 350
    crossover_rate: float = 0.85
    mutation_rate: float = 0.09  # probabilitas mutasi PER GEN
    elitism: int = 2
    tournament_size: int = 3


def load_data(folder=DATA_DIR):
    folder = Path(folder)
    with open(folder/'mata_kuliah.csv', encoding='utf-8-sig', newline='') as fp:
        lines = list(csv.DictReader(fp))
    courses = [Course(
        id=r['ID_MK'],kode=r['Kode_MK'],nama=r['Nama_Mata_Kuliah'],
        kelas=r['ID_Kelas'],semester=r['Semester'],sks=int(r['SKS']),
        mahasiswa=int(r['Jumlah_Mahasiswa']),dosen=tuple(x.strip() for x in r['ID_Dosen_Pengampu'].split(';') if x.strip()),
        status_kelas=r['Status_Kelas']) for r in lines]
    with open(folder/'ruangan.csv',encoding='utf-8-sig',newline='') as fp:
        rooms = [Room(id=r['ID_Ruang'],nama=r['Nama_Ruangan'],kapasitas=int(r['Kapasitas_Simulasi'])) for r in csv.DictReader(fp)]
    with open(folder/'hari.csv', encoding='utf-8-sig',newline='') as fp:
        days = [r['Nama_Hari'] for r in csv.DictReader(fp)]
    with open(folder/'slot_jam.csv',encoding='utf-8-sig',newline='') as fp:
        slots = list(csv.DictReader(fp))
    with open(folder/'dosen.csv',encoding='utf-8-sig',newline='') as fp:
        teachers = {r['ID_Dosen']:r['Nama_Dosen'] for r in csv.DictReader(fp)}
    assert len(courses)==20 and len(rooms)==5 and len(days)==5 and len(slots)==5
    assert len(teachers)==8 and len({c.id for c in courses})==20
    assert all(1<=c.sks<=len(slots) for c in courses)
    assert all(all(d in teachers for d in c.dosen) and len(c.dosen)>0 for c in courses)
    assert all(any(r.kapasitas>=c.mahasiswa for r in rooms) for c in courses), 'Ada mata kuliah melebihi kapasitas semua ruang'
    return courses, rooms, days, slots, teachers


def allowed_rooms(course, rooms):
    return [i for i, room in enumerate(rooms) if room.kapasitas >= course.mahasiswa]


def random_gene(course, rooms, days, slots, rng):
    return (rng.randrange(len(days)), rng.randrange(len(slots)-course.sks+1), rng.choice(allowed_rooms(course,rooms)))


def random_population(courses,rooms,days,slots, config, rng):
    return [[random_gene(c,rooms,days,slots,rng) for c in courses] for _ in range(config.population_size)]


def count_violations(chromosome, courses, rooms, days, slots):
    """Pelanggaran bentrok dihitung PER SLOT 50 menit.
    Teacher collision, class collision, room collision, room capacity.
    Jumlah pelanggaran adalah jumlah kejadian pasangan yang bentrok untuk tiap slot.
    """
    violations = dict(dosen=0, kelas=0, ruangan=0, kapasitas=0, indeks=0)
    teacher_count, class_count, room_count = Counter(), Counter(), Counter()
    for gene, course in zip(chromosome, courses):
        day, start, room_index = gene
        if not (0<=day<len(days) and 0<=room_index<len(rooms) and 0<=start<=len(slots)-course.sks):
            violations['indeks'] += 1
            continue
        if rooms[room_index].kapasitas < course.mahasiswa:
            violations['kapasitas'] += 1
        for sl in range(start,start+course.sks):
            # Counter agar lebih dari dua sesi di slot yang sama tetap dikenai penalti berpasangan.
            for lecturer in course.dosen:
                key = (lecturer,day,sl)
                violations['dosen'] += teacher_count[key]
                teacher_count[key] += 1
            ck = (course.kelas,day,sl)
            violations['kelas'] += class_count[ck]
            class_count[ck] += 1
            rk = (room_index,day,sl)
            violations['ruangan'] += room_count[rk]
            room_count[rk] += 1
    return violations


def fitness(chromosome, courses, rooms, days, slots):
    total = sum(count_violations(chromosome,courses,rooms,days,slots).values())
    return 1.0/(1.0+total)


def roulette_selection(population, scores, rng):
    total = sum(scores)
    if total <= 0:
        return rng.choice(population)
    point = rng.random()*total
    acc = 0.0
    for candidate,score in zip(population,scores):
        acc += score
        if acc >= point:
            return candidate
    return population[-1]


def tournament_selection(population,scores,rng,k=3):
    selected_indices = rng.sample(range(len(population)), k=min(k,len(population)))
    return population[max(selected_indices,key=lambda i:scores[i])]


def one_point_crossover(p1,p2,rng):
    if len(p1)<2:
        return p1[:],p2[:]
    split=rng.randrange(1,len(p1))
    return p1[:split]+p2[split:],p2[:split]+p1[split:]


def uniform_crossover(p1,p2,rng):
    mask=[rng.getrandbits(1) for _ in p1]
    return ([a if m else b for a,b,m in zip(p1,p2,mask)],
            [b if m else a for a,b,m in zip(p1,p2,mask)])


def mutate(chromosome,courses,rooms,days,slots,rng,mutation_rate):
    result=chromosome[:]
    for i,course in enumerate(courses):
        if rng.random()<mutation_rate:
            # Pertahankan nilai lain atau randomisasi salah satu komponen gen.
            day,start,room=result[i]
            what=rng.randrange(3)
            if what==0: day=rng.randrange(len(days))
            elif what==1: start=rng.randrange(len(slots)-course.sks+1)
            else: room=rng.choice(allowed_rooms(course,rooms))
            result[i]=(day,start,room)
    return result


def run_ga(courses,rooms,days,slots,seed,config=GAConfig(),selection='tournament',crossover='uniform'):
    if selection not in ('roulette','tournament') or crossover not in ('one_point','uniform'):
        raise ValueError('Jenis seleksi atau crossover tidak didukung')
    rng=random.Random(seed)
    t0=time.perf_counter()
    population=random_population(courses,rooms,days,slots,config,rng)
    best_schedule=None
    best_fitness=-1.0
    first_valid_generation=None
    history=[]
    for generation in range(config.max_generations+1):
        scores=[fitness(c,courses,rooms,days,slots) for c in population]
        best_idx=max(range(len(population)),key=lambda i:scores[i])
        if scores[best_idx]>best_fitness:
            best_fitness=scores[best_idx]
            best_schedule=population[best_idx][:]
        history.append({'generasi':generation,'fitness_terbaik':round(best_fitness,10),
                        'fitness_rata_populasi':round(statistics.mean(scores),10)})
        if best_fitness>=1.0-1e-12 and first_valid_generation is None:
            first_valid_generation=generation
            break
        if generation>=config.max_generations: break
        order=sorted(range(len(population)),key=lambda i:scores[i],reverse=True)
        next_population=[population[i][:] for i in order[:config.elitism]]
        def pick():
            if selection=='roulette': return roulette_selection(population,scores,rng)
            return tournament_selection(population,scores,rng,config.tournament_size)
        while len(next_population)<config.population_size:
            p1,p2=pick(),pick()
            if rng.random()<config.crossover_rate:
                if crossover=='one_point': child1,child2=one_point_crossover(p1,p2,rng)
                else: child1,child2=uniform_crossover(p1,p2,rng)
            else: child1,child2=p1[:],p2[:]
            next_population.append(mutate(child1,courses,rooms,days,slots,rng,config.mutation_rate))
            if len(next_population)<config.population_size:
                next_population.append(mutate(child2,courses,rooms,days,slots,rng,config.mutation_rate))
        population=next_population
    v=count_violations(best_schedule,courses,rooms,days,slots)
    return dict(seed=seed,selection=selection,crossover=crossover,
                fitness_terbaik=best_fitness,fitness_rata_populasi_akhir=history[-1]['fitness_rata_populasi'],
                generasi_valid_pertama=first_valid_generation,generasi_berjalan=history[-1]['generasi'],
                durasi_detik=round(time.perf_counter()-t0,3),pelanggaran=v,
                jadwal=best_schedule,history=history)


def schedule_records(chromosome,courses,rooms,days,slots,teachers):
    records=[]
    for gene,course in zip(chromosome,courses):
        day,start,room_i=gene
        end=start+course.sks-1
        records.append({
           'ID_MK':course.id,'Kode_MK':course.kode,'Mata_Kuliah':course.nama,
           'Kelas':course.kelas,'Status_Kelas':course.status_kelas,
           'Semester':course.semester,'SKS':course.sks,'Jumlah_Mahasiswa':course.mahasiswa,
           'ID_Dosen':'; '.join(course.dosen),
           'Nama_Dosen':'; '.join(teachers[d] for d in course.dosen),
           'Hari':days[day],'ID_Slot_Mulai':slots[start]['ID_Slot'],
           'ID_Slot_Selesai':slots[end]['ID_Slot'],
           'Jam_Mulai':slots[start]['Jam_Mulai'],'Jam_Selesai':slots[end]['Jam_Selesai'],
           'ID_Ruang':rooms[room_i].id,'Ruangan':rooms[room_i].nama,
           'Kapasitas_Ruang':rooms[room_i].kapasitas})
    records.sort(key=lambda r:(days.index(r['Hari']), r['Jam_Mulai'],r['Ruangan']))
    return records


def write_csv(path, rows, fieldnames=None):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    if fieldnames is None: fieldnames=list(rows[0].keys())
    with path.open('w',encoding='utf-8-sig',newline='') as file:
        wr=csv.DictWriter(file, fieldnames=fieldnames)
        wr.writeheader()
        wr.writerows(rows)


def write_chart(best_run, out_file):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('matplotlib belum terpasang; grafik tidak dibuat. Install: pip install matplotlib')
        return False
    hist=best_run['history']
    fig,ax=plt.subplots(figsize=(10,4.5))
    ax.plot([p['generasi'] for p in hist],[p['fitness_terbaik'] for p in hist],label='Fitness terbaik',linewidth=2.3)
    ax.plot([p['generasi'] for p in hist],[p['fitness_rata_populasi'] for p in hist],label='Rata-rata populasi',linewidth=1.5,alpha=.85)
    ax.set_title(f"Konvergensi AG | Seed {best_run['seed']} | {best_run['selection']} / {best_run['crossover']}")
    ax.set_xlabel('Generasi')
    ax.set_ylabel('Fitness = 1 / (1 + total pelanggaran)')
    ax.set_ylim(0,1.04)
    ax.grid(alpha=.2)
    ax.legend(loc='lower right')
    fig.tight_layout()
    fig.savefig(out_file,dpi=180)
    plt.close(fig)
    return True


def run_experiments(config=GAConfig(),seed_values=tuple(range(101,111))):
    courses,rooms,days,slots,teachers=load_data()
    RESULT_DIR.mkdir(parents=True,exist_ok=True)
    runs=[]
    for idx,seed in enumerate(seed_values):
        # Keduanya dipakai nyata pada 10 run: roulette/one-point dan tournament/uniform.
        selection='roulette' if idx<5 else 'tournament'
        crossover='one_point' if idx<5 else 'uniform'
        r=run_ga(courses,rooms,days,slots,seed,config,selection,crossover)
        runs.append(r)
        print(f"Run {idx+1:02d} | seed={seed} | {selection}/{crossover} | best={r['fitness_terbaik']:.5f} | pelanggaran={sum(r['pelanggaran'].values())} | generasi_valid={r['generasi_valid_pertama']} | {r['durasi_detik']}s",flush=True)
    summary=[]
    for idx,r in enumerate(runs,1):
        rec={k:r[k] for k in ('seed','selection','crossover','fitness_terbaik','fitness_rata_populasi_akhir','generasi_valid_pertama','generasi_berjalan','durasi_detik')}
        rec['run']=idx
        rec.update({f'pelanggaran_{k}':v for k,v in r['pelanggaran'].items()})
        summary.append(rec)
    write_csv(RESULT_DIR/'hasil_10_run.csv', summary)
    winners=sorted(runs,key=lambda r:(r['fitness_terbaik'],-r['generasi_berjalan']),reverse=True)
    best_run=winners[0]
    schedule=schedule_records(best_run['jadwal'],courses,rooms,days,slots,teachers)
    write_csv(RESULT_DIR/'jadwal_terbaik.csv', schedule)
    write_csv(RESULT_DIR/'konvergensi_run_terbaik.csv',best_run['history'])
    write_chart(best_run,RESULT_DIR/'grafik_konvergensi.png')
    results=dict(jumlah_run=len(runs),jumlah_solusi_valid=sum(r['fitness_terbaik']==1 for r in runs),
                 rata_fitness_terbaik=round(statistics.mean(r['fitness_terbaik'] for r in runs),6),
                 rata_fitness_populasi_akhir=round(statistics.mean(r['fitness_rata_populasi_akhir'] for r in runs),6),
                 terbaik_seed=best_run['seed'],terbaik_fitness=best_run['fitness_terbaik'],
                 terbaik_generasi_valid=best_run['generasi_valid_pertama'],
                 pelanggaran_terbaik=best_run['pelanggaran'],
                 rata_waktu_detik=round(statistics.mean(r['durasi_detik'] for r in runs),3),
                 parameter=config.__dict__,simulasi=True,
                 catatan='Kapasitas ruang dan ID kelas yang kosong berasal dari asumsi simulasi. Dosen dan mata kuliah sesuai file sumber.')
    (RESULT_DIR/'ringkasan.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    return results,summary,schedule,best_run

if __name__=='__main__':
    results,*_=run_experiments()
    print('\nRINGKASAN',json.dumps(results,ensure_ascii=False,indent=2))
