# match_engine.py - Motore di Matching Avanzato tra Scuole
"""
Questo modulo fornisce funzioni per il matching avanzato tra scuole,
basato su multiple strategie: similarità, complementarità, prossimità.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
import json
import os

# Dimensioni principali per il matching
DIMENSIONS = [
    'mean_finalita',
    'mean_obiettivi',
    'mean_governance',
    'mean_didattica_orientativa',
    'mean_opportunita'
]

DIMENSION_LABELS = {
    'mean_finalita': 'Finalità',
    'mean_obiettivi': 'Obiettivi',
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica Orientativa',
    'mean_opportunita': 'Opportunità'
}


def euclidean_distance(v1: np.ndarray, v2: np.ndarray) -> float:
    """Calcola la distanza euclidea tra due vettori."""
    return np.sqrt(np.sum((v1 - v2) ** 2))


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Calcola la similarità coseno tra due vettori."""
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return np.dot(v1, v2) / (norm1 * norm2)


def get_school_vector(school_row: pd.Series, dimensions: List[str] = None) -> np.ndarray:
    """Estrae il vettore delle dimensioni da una riga scuola."""
    if dimensions is None:
        dimensions = DIMENSIONS
    values = []
    for dim in dimensions:
        val = school_row.get(dim, 0)
        values.append(float(val) if pd.notna(val) else 0.0)
    return np.array(values)


def score_categorical_similarity(school1: pd.Series, school2: pd.Series) -> Tuple[float, Dict]:
    """
    Calcola un punteggio di similarità categorica tra due scuole.

    Returns:
        Tuple[float, Dict]: (score 0-100, dettagli dei match)
    """
    weights = {
        'tipo_match': 30,
        'grado_match': 25,
        'territorio_match': 15,
        'regione_match': 10,
        'statale_match': 10,
        'size_similarity': 10
    }

    score = 0
    details = {}

    # Tipo scuola match
    tipo1 = set(str(school1.get('tipo_scuola', '')).split(', '))
    tipo2 = set(str(school2.get('tipo_scuola', '')).split(', '))
    tipo_overlap = len(tipo1 & tipo2) / max(len(tipo1 | tipo2), 1)
    score += weights['tipo_match'] * tipo_overlap
    details['tipo_match'] = tipo_overlap

    # Ordine grado match
    grado1 = set(str(school1.get('ordine_grado', '')).split(', '))
    grado2 = set(str(school2.get('ordine_grado', '')).split(', '))
    grado_overlap = len(grado1 & grado2) / max(len(grado1 | grado2), 1)
    score += weights['grado_match'] * grado_overlap
    details['grado_match'] = grado_overlap

    # Territorio match
    terr_match = 1.0 if school1.get('territorio') == school2.get('territorio') else 0.0
    score += weights['territorio_match'] * terr_match
    details['territorio_match'] = terr_match

    # Regione match
    reg_match = 1.0 if school1.get('regione') == school2.get('regione') else 0.0
    score += weights['regione_match'] * reg_match
    details['regione_match'] = reg_match

    # Statale/Paritaria match
    stat_match = 1.0 if school1.get('statale_paritaria') == school2.get('statale_paritaria') else 0.0
    score += weights['statale_match'] * stat_match
    details['statale_match'] = stat_match

    # Size similarity (basata su partnership count)
    size1 = float(school1.get('partnership_count', 0) or 0)
    size2 = float(school2.get('partnership_count', 0) or 0)
    if max(size1, size2) > 0:
        size_sim = 1 - abs(size1 - size2) / max(size1, size2)
    else:
        size_sim = 1.0
    score += weights['size_similarity'] * size_sim
    details['size_similarity'] = size_sim

    return score, details


def score_dimensional_similarity(school1: pd.Series, school2: pd.Series) -> Tuple[float, Dict]:
    """
    Calcola la similarità multidimensionale tra due scuole basata sulle 5 dimensioni RO.

    Returns:
        Tuple[float, Dict]: (score 0-100, dettagli per dimensione)
    """
    v1 = get_school_vector(school1)
    v2 = get_school_vector(school2)

    # Distanza euclidea normalizzata (max distanza teorica = sqrt(5 * 6^2) = ~13.4)
    max_dist = np.sqrt(5 * 36)  # 5 dimensioni, range 1-7 = diff max 6
    dist = euclidean_distance(v1, v2)
    similarity = 1 - (dist / max_dist)

    # Dettagli per dimensione
    details = {}
    for i, dim in enumerate(DIMENSIONS):
        details[dim] = {
            'school1': v1[i],
            'school2': v2[i],
            'diff': abs(v1[i] - v2[i])
        }

    return similarity * 100, details


def score_profile_similarity(school1: pd.Series, school2: pd.Series) -> Tuple[float, Dict]:
    """
    Calcola la similarità del profilo (forma del radar) usando cosine similarity.
    Due scuole con punteggi diversi ma stesso "profilo" avranno alta similarità.

    Returns:
        Tuple[float, Dict]: (score 0-100, dettagli)
    """
    v1 = get_school_vector(school1)
    v2 = get_school_vector(school2)

    cos_sim = cosine_similarity(v1, v2)

    details = {
        'cosine_similarity': cos_sim,
        'profile1': v1.tolist(),
        'profile2': v2.tolist()
    }

    return cos_sim * 100, details


def score_complementarity(school1: pd.Series, school2: pd.Series, gap_threshold: float = 2.0) -> Tuple[float, Dict]:
    """
    Calcola quanto school2 è complementare a school1.
    Alta complementarità = school2 è forte dove school1 è debole.

    Args:
        gap_threshold: soglia per considerare una dimensione come "debole"

    Returns:
        Tuple[float, Dict]: (score 0-100, dettagli aree complementari)
    """
    v1 = get_school_vector(school1)
    v2 = get_school_vector(school2)

    # Trova le debolezze di school1 (sotto soglia rispetto al max 7)
    weaknesses = []
    complements = []

    for i, dim in enumerate(DIMENSIONS):
        gap1 = 7 - v1[i]
        if gap1 >= gap_threshold:  # school1 è debole qui
            weaknesses.append(dim)
            if v2[i] >= 5:  # school2 è forte qui (>=5)
                complements.append({
                    'dimension': dim,
                    'school1_score': v1[i],
                    'school2_score': v2[i],
                    'gap_covered': v2[i] - v1[i]
                })

    # Score basato su quante debolezze sono coperte
    if len(weaknesses) == 0:
        score = 0  # school1 non ha debolezze significative
    else:
        score = (len(complements) / len(weaknesses)) * 100

    details = {
        'weaknesses': weaknesses,
        'complements': complements,
        'coverage_ratio': len(complements) / max(len(weaknesses), 1)
    }

    return score, details


def score_adjacency(school1: pd.Series, school2: pd.Series, margin: float = 1.0) -> Tuple[float, Dict]:
    """
    Calcola quanto school2 è "adiacente" a school1 (leggermente migliore).
    Utile per trovare modelli raggiungibili.

    Args:
        margin: margine di miglioramento desiderato (default 1 punto)

    Returns:
        Tuple[float, Dict]: (score 0-100, dettagli)
    """
    ro1 = float(school1.get('ptof_orientamento_maturity_index', 0) or 0)
    ro2 = float(school2.get('ptof_orientamento_maturity_index', 0) or 0)

    # Ideale: school2 ha RO leggermente superiore (tra 0.5 e 2 punti in più)
    diff = ro2 - ro1

    if 0.3 <= diff <= 2.0:
        # Perfetto range di adiacenza
        score = 100 - abs(diff - margin) * 30
    elif diff > 2.0:
        # Troppo avanti
        score = max(0, 50 - (diff - 2) * 20)
    else:
        # Indietro o uguale
        score = max(0, 50 + diff * 25)

    details = {
        'ro_school1': ro1,
        'ro_school2': ro2,
        'difference': diff,
        'is_adjacent': 0.3 <= diff <= 2.0
    }

    return max(0, min(100, score)), details


def advanced_peer_matching(
    target_school: pd.Series,
    df: pd.DataFrame,
    strategy: str = 'balanced',
    top_n: int = 10,
    exclude_same: bool = True
) -> pd.DataFrame:
    """
    Trova le scuole più simili/complementari alla scuola target.

    Args:
        target_school: Serie con i dati della scuola target
        df: DataFrame con tutte le scuole
        strategy: 'similar', 'complementary', 'adjacent', 'balanced'
        top_n: numero di risultati da restituire
        exclude_same: escludere la stessa scuola dai risultati

    Returns:
        DataFrame con le scuole match e i loro scores
    """
    target_id = target_school.get('school_id', '')

    results = []

    for idx, row in df.iterrows():
        if exclude_same and row.get('school_id') == target_id:
            continue

        # Calcola tutti i punteggi
        cat_score, cat_details = score_categorical_similarity(target_school, row)
        dim_score, dim_details = score_dimensional_similarity(target_school, row)
        prof_score, prof_details = score_profile_similarity(target_school, row)
        comp_score, comp_details = score_complementarity(target_school, row)
        adj_score, adj_details = score_adjacency(target_school, row)

        # Calcola score finale basato sulla strategia
        if strategy == 'similar':
            final_score = 0.3 * cat_score + 0.4 * dim_score + 0.3 * prof_score
            explanation = "Profilo simile al tuo"
        elif strategy == 'complementary':
            final_score = 0.2 * cat_score + 0.1 * dim_score + 0.7 * comp_score
            explanation = f"Forte dove tu sei debole ({len(comp_details.get('complements', []))} aree)"
        elif strategy == 'adjacent':
            final_score = 0.3 * cat_score + 0.2 * dim_score + 0.5 * adj_score
            explanation = f"Leggermente migliore (+{adj_details['difference']:.1f} RO)"
        else:  # balanced
            final_score = (
                0.25 * cat_score +
                0.25 * dim_score +
                0.15 * prof_score +
                0.20 * comp_score +
                0.15 * adj_score
            )
            explanation = "Match bilanciato"

        results.append({
            'school_id': row.get('school_id'),
            'denominazione': row.get('denominazione'),
            'regione': row.get('regione'),
            'provincia': row.get('provincia'),
            'tipo_scuola': row.get('tipo_scuola'),
            'ptof_orientamento_maturity_index': row.get('ptof_orientamento_maturity_index'),
            'final_score': final_score,
            'categorical_score': cat_score,
            'dimensional_score': dim_score,
            'profile_score': prof_score,
            'complementary_score': comp_score,
            'adjacency_score': adj_score,
            'explanation': explanation,
            'complements': comp_details.get('complements', []),
            # Dimensioni per radar
            'mean_finalita': row.get('mean_finalita'),
            'mean_obiettivi': row.get('mean_obiettivi'),
            'mean_governance': row.get('mean_governance'),
            'mean_didattica_orientativa': row.get('mean_didattica_orientativa'),
            'mean_opportunita': row.get('mean_opportunita')
        })

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('final_score', ascending=False).head(top_n)

    return results_df


def get_improvement_suggestions(
    target_school: pd.Series,
    peers_df: pd.DataFrame,
    analysis_results_path: str = 'analysis_results'
) -> List[Dict]:
    """
    Genera suggerimenti di miglioramento basati sulle pratiche dei peer.

    Args:
        target_school: Serie con i dati della scuola target
        peers_df: DataFrame con le scuole peer (output di advanced_peer_matching)
        analysis_results_path: path alla cartella con i JSON delle analisi

    Returns:
        Lista di suggerimenti con dettagli
    """
    suggestions = []

    # Trova le dimensioni deboli della scuola target
    target_vector = get_school_vector(target_school)
    weak_dimensions = []

    for i, dim in enumerate(DIMENSIONS):
        if target_vector[i] < 4:  # Sotto la sufficienza
            weak_dimensions.append({
                'dimension': dim,
                'label': DIMENSION_LABELS.get(dim, dim),
                'score': target_vector[i],
                'gap': 7 - target_vector[i]
            })

    # Per ogni dimensione debole, cerca peer che eccellono
    for weakness in weak_dimensions:
        dim = weakness['dimension']

        # Trova peer forti in questa dimensione
        strong_peers = peers_df[peers_df[dim] >= 5].head(3)

        for _, peer in strong_peers.iterrows():
            # Prova a caricare il JSON della scuola peer
            peer_id = peer.get('school_id', '')
            json_path = os.path.join(analysis_results_path, f"{peer_id}_PTOF_analysis.json")

            evidence = None
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        peer_analysis = json.load(f)
                    # Estrai evidenze rilevanti
                    evidence = extract_evidence_for_dimension(peer_analysis, dim)
                except Exception:
                    pass

            suggestions.append({
                'dimension': weakness['label'],
                'your_score': weakness['score'],
                'peer_name': peer.get('denominazione', 'N/D'),
                'peer_score': peer.get(dim, 0),
                'peer_region': peer.get('regione', 'N/D'),
                'peer_type': peer.get('tipo_scuola', 'N/D'),
                'similarity_score': peer.get('categorical_score', 0),
                'evidence': evidence,
                'recommendation': f"La scuola {peer.get('denominazione', 'N/D')} ({peer.get('regione', 'N/D')}), "
                                 f"simile alla tua per tipologia, ha un punteggio di {peer.get(dim, 0):.1f} "
                                 f"in {weakness['label']}. Potresti prendere ispirazione dalle loro pratiche."
            })

    return suggestions


def extract_evidence_for_dimension(analysis_json: Dict, dimension: str) -> Optional[Dict]:
    """
    Estrae evidenze dal JSON di analisi per una specifica dimensione.
    """
    try:
        ptof_section = analysis_json.get('ptof_section2', {})

        # Mappa dimensioni a sezioni del JSON
        dim_mapping = {
            'mean_finalita': '2_3_finalita',
            'mean_obiettivi': '2_4_obiettivi',
            'mean_governance': '2_5_azioni_sistema',
            'mean_didattica_orientativa': '2_6_didattica_orientativa',
            'mean_opportunita': '2_7_opzionali_facoltative'
        }

        section_key = dim_mapping.get(dimension)
        if section_key and section_key in ptof_section:
            section = ptof_section[section_key]

            # Estrai quote e evidenze
            quotes = []
            for key, value in section.items():
                if isinstance(value, dict):
                    quote = value.get('evidence_quote', '')
                    if quote and len(quote) > 20:
                        quotes.append({
                            'indicator': key,
                            'quote': quote[:500],  # Limita lunghezza
                            'score': value.get('score', 0)
                        })

            return {'quotes': quotes[:3]} if quotes else None
    except Exception:
        pass

    return None


def search_schools_by_methodology(
    df: pd.DataFrame,
    keyword: str,
    analysis_results_path: str = 'analysis_results',
    top_n: int = 20
) -> pd.DataFrame:
    """
    Cerca scuole che utilizzano una specifica metodologia/progetto.

    Args:
        df: DataFrame con tutte le scuole
        keyword: parola chiave da cercare (es. "STEM", "PBL")
        analysis_results_path: path ai file JSON/MD
        top_n: numero massimo di risultati

    Returns:
        DataFrame con le scuole che matchano e il contesto
    """
    results = []
    keyword_lower = keyword.lower()

    for idx, row in df.iterrows():
        school_id = row.get('school_id', '')

        # Cerca nel file markdown
        md_path = os.path.join(analysis_results_path, f"{school_id}_PTOF_analysis.md")

        matches = []
        if os.path.exists(md_path):
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Cerca occorrenze
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if keyword_lower in line.lower():
                        # Estrai contesto (linea precedente e successiva)
                        context_start = max(0, i - 1)
                        context_end = min(len(lines), i + 2)
                        context = '\n'.join(lines[context_start:context_end])
                        matches.append(context[:300])
            except Exception:
                pass

        if matches:
            results.append({
                'school_id': school_id,
                'denominazione': row.get('denominazione'),
                'regione': row.get('regione'),
                'provincia': row.get('provincia'),
                'tipo_scuola': row.get('tipo_scuola'),
                'ptof_orientamento_maturity_index': row.get('ptof_orientamento_maturity_index'),
                'match_count': len(matches),
                'first_match': matches[0] if matches else '',
                'mean_finalita': row.get('mean_finalita'),
                'mean_obiettivi': row.get('mean_obiettivi'),
                'mean_governance': row.get('mean_governance'),
                'mean_didattica_orientativa': row.get('mean_didattica_orientativa'),
                'mean_opportunita': row.get('mean_opportunita')
            })

    results_df = pd.DataFrame(results)
    if not results_df.empty:
        results_df = results_df.sort_values(
            ['match_count', 'ptof_orientamento_maturity_index'],
            ascending=[False, False]
        ).head(top_n)

    return results_df


def compare_two_schools(school1: pd.Series, school2: pd.Series) -> Dict:
    """
    Confronto dettagliato tra due scuole.

    Returns:
        Dict con tutte le metriche comparative
    """
    v1 = get_school_vector(school1)
    v2 = get_school_vector(school2)

    comparison = {
        'school1': {
            'id': school1.get('school_id'),
            'name': school1.get('denominazione'),
            'region': school1.get('regione'),
            'type': school1.get('tipo_scuola'),
            'ro_index': float(school1.get('ptof_orientamento_maturity_index', 0) or 0),
            'dimensions': {dim: v1[i] for i, dim in enumerate(DIMENSIONS)}
        },
        'school2': {
            'id': school2.get('school_id'),
            'name': school2.get('denominazione'),
            'region': school2.get('regione'),
            'type': school2.get('tipo_scuola'),
            'ro_index': float(school2.get('ptof_orientamento_maturity_index', 0) or 0),
            'dimensions': {dim: v2[i] for i, dim in enumerate(DIMENSIONS)}
        },
        'differences': {},
        'similarities': [],
        'winner_by_dimension': {}
    }

    # Calcola differenze per dimensione
    for i, dim in enumerate(DIMENSIONS):
        diff = v1[i] - v2[i]
        comparison['differences'][dim] = {
            'value': diff,
            'school1_better': diff > 0.5,
            'school2_better': diff < -0.5,
            'similar': abs(diff) <= 0.5
        }

        if abs(diff) <= 0.5:
            comparison['similarities'].append(DIMENSION_LABELS.get(dim, dim))
        elif diff > 0:
            comparison['winner_by_dimension'][dim] = 'school1'
        else:
            comparison['winner_by_dimension'][dim] = 'school2'

    # Scores complessivi
    cat_score, _ = score_categorical_similarity(school1, school2)
    dim_score, _ = score_dimensional_similarity(school1, school2)
    prof_score, _ = score_profile_similarity(school1, school2)

    comparison['overall'] = {
        'categorical_similarity': cat_score,
        'dimensional_similarity': dim_score,
        'profile_similarity': prof_score,
        'ro_difference': comparison['school1']['ro_index'] - comparison['school2']['ro_index']
    }

    return comparison
