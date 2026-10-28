"""Jalankan dari root proyek: python main.py"""
from src.genetic_timetable import GAConfig,run_experiments

if __name__=='__main__':
    run_experiments(GAConfig(population_size=100,max_generations=350,crossover_rate=0.85,mutation_rate=0.09,elitism=2))
