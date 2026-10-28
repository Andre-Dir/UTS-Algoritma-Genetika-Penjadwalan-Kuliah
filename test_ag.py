"""Unit test ringan tanpa pytest, jalankan python test_ag.py"""
import random
from src.genetic_timetable import (
    load_data,random_population,GAConfig,count_violations,fitness,
    roulette_selection,tournament_selection,one_point_crossover,uniform_crossover,
    mutate,Course)


def main():
    courses,rooms,days,slots,_=load_data()
    rng=random.Random(5)
    p=random_population(courses,rooms,days,slots,GAConfig(population_size=5),rng)
    assert len(p)==5 and all(len(x)==20 for x in p)
    scores=[fitness(x,courses,rooms,days,slots) for x in p]
    assert roulette_selection(p,scores,rng) in p
    assert tournament_selection(p,scores,rng) in p
    for f in (one_point_crossover,uniform_crossover):
        a,b=f(p[0],p[1],rng)
        assert len(a)==len(b)==len(courses)
    assert len(mutate(p[0],courses,rooms,days,slots,rng,.8))==20
    bad=p[0][:]
    bad[1]=bad[0]  # course 1 and 2 both taught by D01; check clash
    assert count_violations(bad,courses,rooms,days,slots)['dosen']>=3
    bad_capacity=p[0][:]
    bad_capacity[1]=(0,0,4) # 97 students in R05, simulation capacity 50
    assert count_violations(bad_capacity,courses,rooms,days,slots)['kapasitas']>=1
    dups=courses[:]
    # Additional instructor for course 2; course 1 has D01, so still counts teacher collisions
    dups[1]=Course(**{**courses[1].__dict__,'dosen':('D01','D03')})
    assert count_violations(bad,dups,rooms,days,slots)['dosen']>=3
    print('SELURUH UJI UNIT LULUS (8 kelompok pemeriksaan).')

if __name__=='__main__':
    main()
