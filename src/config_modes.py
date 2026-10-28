"""Pilihan mode konfigurasi GENETICA tanpa dependensi Streamlit."""

from src.genetic_timetable import GAConfig

AUTOMATIC_SEED = 101


def get_automatic_config() -> GAConfig:
    """Preset UTS untuk mode Otomatis, sama dengan parameter default AG."""
    return GAConfig(
        population_size=100,
        max_generations=350,
        crossover_rate=0.85,
        mutation_rate=0.09,
        elitism=2,
    )


def choose_operators(run_index: int, total_runs: int,
                     selection_policy: str = 'bergantian',
                     crossover_policy: str = 'bergantian') -> tuple[str, str]:
    """Tentukan operator untuk satu run tanpa mengubah mesin AG.

    'bergantian' pada 10 run: lima pertama roulette + one-point,
    lima berikutnya tournament + uniform. Pada 1 run: tournament + uniform.
    Kebijakan tunggal juga bisa dipakai pada mode Manual.
    """
    if total_runs not in (1, 10) or not 0 <= run_index < total_runs:
        raise ValueError('Jumlah percobaan harus 1 atau 10 dan indeks run harus valid')
    if selection_policy not in ('bergantian', 'roulette', 'tournament'):
        raise ValueError('Kebijakan seleksi tidak dikenal')
    if crossover_policy not in ('bergantian', 'one_point', 'uniform'):
        raise ValueError('Kebijakan crossover tidak dikenal')
    selection = (('roulette' if run_index < 5 else 'tournament')
                 if total_runs == 10 else 'tournament') if selection_policy == 'bergantian' else selection_policy
    crossover = (('one_point' if run_index < 5 else 'uniform')
                 if total_runs == 10 else 'uniform') if crossover_policy == 'bergantian' else crossover_policy
    return selection, crossover
