"""
Gestione centralizzata dei pesi per il calcolo degli indici ORIENTA+

Questo modulo fornisce funzionalita per:
- Caricare e salvare la configurazione dei pesi
- Validare e normalizzare i pesi
- Calcolare indici pesati dinamicamente
- Gestire preset predefiniti
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Any
import copy

# Percorso file configurazione pesi
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "weights_config.json"

# Mappatura nomi indicatori -> colonne CSV
INDICATOR_TO_COLUMN = {
    "finalita": {
        "attitudini": "2_3_finalita_attitudini_score",
        "interessi": "2_3_finalita_interessi_score",
        "progetto_vita": "2_3_finalita_progetto_vita_score",
        "transizioni": "2_3_finalita_transizioni_formative_score",
        "capacita_orientative": "2_3_finalita_capacita_orientative_opportunita_score"
    },
    "obiettivi": {
        "ridurre_abbandono": "2_4_obiettivo_ridurre_abbandono_score",
        "continuita_territorio": "2_4_obiettivo_continuita_territorio_score",
        "contrastare_neet": "2_4_obiettivo_contrastare_neet_score",
        "lifelong_learning": "2_4_obiettivo_lifelong_learning_score"
    },
    "governance": {
        "coordinamento": "2_5_azione_coordinamento_servizi_score",
        "dialogo": "2_5_azione_dialogo_docenti_studenti_score",
        "rapporto_genitori": "2_5_azione_rapporto_scuola_genitori_score",
        "monitoraggio": "2_5_azione_monitoraggio_azioni_score",
        "inclusione": "2_5_azione_sistema_integrato_inclusione_fragilita_score"
    },
    "didattica": {
        "esperienza_studenti": "2_6_didattica_da_esperienza_studenti_score",
        "laboratoriale": "2_6_didattica_laboratoriale_score",
        "flessibilita": "2_6_didattica_flessibilita_spazi_tempi_score",
        "interdisciplinare": "2_6_didattica_interdisciplinare_score"
    },
    "opportunita": {
        "culturali": "2_7_opzionali_culturali_score",
        "laboratoriali": "2_7_opzionali_laboratoriali_espressive_score",
        "ludiche": "2_7_opzionali_ludiche_ricreative_score",
        "volontariato": "2_7_opzionali_volontariato_score",
        "sportive": "2_7_opzionali_sportive_score"
    }
}

# Mappatura inversa: colonna CSV -> (dimensione, indicatore)
COLUMN_TO_INDICATOR = {}
for dim, indicators in INDICATOR_TO_COLUMN.items():
    for ind_key, col_name in indicators.items():
        COLUMN_TO_INDICATOR[col_name] = (dim, ind_key)

# Colonne delle medie dimensionali nel CSV
DIMENSION_COLUMNS = {
    "finalita": "mean_finalita",
    "obiettivi": "mean_obiettivi",
    "governance": "mean_governance",
    "didattica": "mean_didattica_orientativa",
    "opportunita": "mean_opportunita"
}

# Etichette italiane per UI
DIMENSION_LABELS = {
    "finalita": "Finalita",
    "obiettivi": "Obiettivi",
    "governance": "Governance",
    "didattica": "Didattica Orientativa",
    "opportunita": "Opportunita"
}

INDICATOR_LABELS = {
    "finalita": {
        "attitudini": "Attitudini",
        "interessi": "Interessi",
        "progetto_vita": "Progetto di Vita",
        "transizioni": "Transizioni Formative",
        "capacita_orientative": "Capacita Orientative"
    },
    "obiettivi": {
        "ridurre_abbandono": "Ridurre Abbandono",
        "continuita_territorio": "Continuita Territorio",
        "contrastare_neet": "Contrastare NEET",
        "lifelong_learning": "Lifelong Learning"
    },
    "governance": {
        "coordinamento": "Coordinamento Servizi",
        "dialogo": "Dialogo Docenti-Studenti",
        "rapporto_genitori": "Rapporto con Genitori",
        "monitoraggio": "Monitoraggio Azioni",
        "inclusione": "Inclusione Fragilita"
    },
    "didattica": {
        "esperienza_studenti": "Esperienza Studenti",
        "laboratoriale": "Laboratoriale",
        "flessibilita": "Flessibilita Spazi/Tempi",
        "interdisciplinare": "Interdisciplinare"
    },
    "opportunita": {
        "culturali": "Culturali",
        "laboratoriali": "Laboratoriali/Espressive",
        "ludiche": "Ludiche/Ricreative",
        "volontariato": "Volontariato",
        "sportive": "Sportive"
    }
}


def get_default_config() -> Dict:
    """Restituisce la configurazione di default con pesi uguali."""
    return {
        "version": "1.0",
        "last_modified": datetime.utcnow().isoformat() + "Z",
        "modified_by": "system",
        "dimension_weights": {
            "finalita": 0.20,
            "obiettivi": 0.20,
            "governance": 0.20,
            "didattica": 0.20,
            "opportunita": 0.20
        },
        "indicator_weights": {
            "finalita": {k: 1.0/5 for k in INDICATOR_LABELS["finalita"]},
            "obiettivi": {k: 1.0/4 for k in INDICATOR_LABELS["obiettivi"]},
            "governance": {k: 1.0/5 for k in INDICATOR_LABELS["governance"]},
            "didattica": {k: 1.0/4 for k in INDICATOR_LABELS["didattica"]},
            "opportunita": {k: 1.0/5 for k in INDICATOR_LABELS["opportunita"]}
        },
        "presets": {}
    }


def load_weights_config() -> Dict:
    """Carica la configurazione pesi dal file JSON."""
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            # Validazione base
            if "dimension_weights" in config and "indicator_weights" in config:
                return config
        except Exception as e:
            print(f"Errore caricamento weights_config.json: {e}")
    return get_default_config()


def save_weights_config(config: Dict, modified_by: str = "admin") -> bool:
    """Salva la configurazione pesi nel file JSON."""
    try:
        config["last_modified"] = datetime.utcnow().isoformat() + "Z"
        config["modified_by"] = modified_by
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        return True
    except Exception as e:
        print(f"Errore salvataggio pesi: {e}")
        return False


def validate_weights(weights: Dict[str, float], tolerance: float = 0.01) -> Tuple[bool, str]:
    """
    Valida che i pesi sommino a 1.0 (con tolleranza).
    Restituisce (is_valid, message).
    """
    if not weights:
        return False, "Nessun peso fornito"

    total = sum(weights.values())
    if abs(total - 1.0) > tolerance:
        return False, f"La somma dei pesi e {total:.4f}, deve essere 1.0"

    for key, val in weights.items():
        if val < 0:
            return False, f"Il peso '{key}' non puo essere negativo"

    return True, "Pesi validi"


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Normalizza i pesi affinche sommino a 1.0."""
    if not weights:
        return {}

    total = sum(weights.values())
    if total == 0:
        # Se tutti zero, distribuisci equamente
        n = len(weights)
        return {k: 1.0/n for k in weights}

    return {k: v/total for k, v in weights.items()}


def get_dimension_weights() -> Dict[str, float]:
    """Restituisce i pesi delle dimensioni."""
    config = load_weights_config()
    return config.get("dimension_weights", get_default_config()["dimension_weights"])


def get_indicator_weights(dimension: str) -> Dict[str, float]:
    """Restituisce i pesi degli indicatori per una dimensione."""
    config = load_weights_config()
    ind_weights = config.get("indicator_weights", {})
    if dimension in ind_weights:
        return ind_weights[dimension]
    return get_default_config()["indicator_weights"].get(dimension, {})


def get_all_indicator_weights() -> Dict[str, Dict[str, float]]:
    """Restituisce tutti i pesi degli indicatori per tutte le dimensioni."""
    config = load_weights_config()
    return config.get("indicator_weights", get_default_config()["indicator_weights"])


def calculate_weighted_dimension_mean(row_data: Dict[str, Any], dimension: str) -> float:
    """
    Calcola la media pesata di una dimensione per una riga di dati.
    row_data: dict con chiavi = nomi colonne CSV, valori = punteggi
    """
    weights = get_indicator_weights(dimension)
    col_map = INDICATOR_TO_COLUMN.get(dimension, {})

    weighted_sum = 0.0
    weight_sum = 0.0

    for ind_key, col_name in col_map.items():
        score = row_data.get(col_name, 0)
        # Converti a float e gestisci valori non validi
        try:
            score = float(score) if score else 0
        except (ValueError, TypeError):
            score = 0

        if score > 0 and ind_key in weights:
            weight = weights.get(ind_key, 0)
            weighted_sum += score * weight
            weight_sum += weight

    return weighted_sum / weight_sum if weight_sum > 0 else 0.0


def calculate_weighted_maturity_index(row_data: Dict[str, Any]) -> float:
    """
    Calcola l'indice di maturita pesato completo per una riga di dati.

    1. Calcola la media pesata per ogni dimensione
    2. Combina le medie dimensionali con i pesi delle dimensioni
    """
    dim_weights = get_dimension_weights()

    dimension_means = {}
    for dim_key in INDICATOR_TO_COLUMN.keys():
        dimension_means[dim_key] = calculate_weighted_dimension_mean(row_data, dim_key)

    # Calcola indice finale pesato
    weighted_sum = 0.0
    weight_sum = 0.0

    for dim_key, mean_val in dimension_means.items():
        if mean_val > 0 and dim_key in dim_weights:
            weight = dim_weights.get(dim_key, 0.2)
            weighted_sum += mean_val * weight
            weight_sum += weight

    return weighted_sum / weight_sum if weight_sum > 0 else 0.0


def calculate_weighted_index_from_means(dimension_means: Dict[str, float]) -> float:
    """
    Calcola l'indice pesato dalle medie dimensionali gia calcolate.

    dimension_means: dict con chiavi = nomi dimensioni (finalita, obiettivi, etc.)
    """
    dim_weights = get_dimension_weights()

    weighted_sum = 0.0
    weight_sum = 0.0

    for dim_key, mean_val in dimension_means.items():
        if mean_val > 0 and dim_key in dim_weights:
            weight = dim_weights.get(dim_key, 0.2)
            weighted_sum += mean_val * weight
            weight_sum += weight

    return weighted_sum / weight_sum if weight_sum > 0 else 0.0


def get_presets() -> Dict[str, Dict]:
    """Restituisce tutti i preset disponibili."""
    config = load_weights_config()
    return config.get("presets", {})


def apply_preset(preset_name: str) -> bool:
    """Applica un preset predefinito."""
    config = load_weights_config()
    presets = config.get("presets", {})

    if preset_name not in presets:
        return False

    preset = presets[preset_name]
    if "dimension_weights" in preset:
        config["dimension_weights"] = copy.deepcopy(preset["dimension_weights"])
    if "indicator_weights" in preset:
        config["indicator_weights"] = copy.deepcopy(preset["indicator_weights"])

    return save_weights_config(config, modified_by=f"preset:{preset_name}")


def save_as_preset(preset_id: str, name: str, description: str = "") -> bool:
    """Salva la configurazione corrente come nuovo preset."""
    config = load_weights_config()

    new_preset = {
        "name": name,
        "description": description,
        "dimension_weights": copy.deepcopy(config.get("dimension_weights", {})),
        "indicator_weights": copy.deepcopy(config.get("indicator_weights", {}))
    }

    if "presets" not in config:
        config["presets"] = {}

    config["presets"][preset_id] = new_preset
    return save_weights_config(config, modified_by=f"save_preset:{preset_id}")


def delete_preset(preset_id: str) -> bool:
    """Elimina un preset."""
    config = load_weights_config()
    presets = config.get("presets", {})

    if preset_id in presets:
        del presets[preset_id]
        return save_weights_config(config)

    return False


def get_weight_summary() -> List[Dict]:
    """
    Restituisce un riepilogo completo dei pesi per visualizzazione.
    """
    dim_weights = get_dimension_weights()
    all_ind_weights = get_all_indicator_weights()

    summary = []
    for dim_key, dim_label in DIMENSION_LABELS.items():
        dim_weight = dim_weights.get(dim_key, 0.20)
        ind_weights = all_ind_weights.get(dim_key, {})

        for ind_key, ind_label in INDICATOR_LABELS.get(dim_key, {}).items():
            ind_weight = ind_weights.get(ind_key, 0)
            # Peso effettivo = peso dimensione * peso indicatore
            effective_weight = dim_weight * ind_weight
            summary.append({
                "dimensione": dim_label,
                "dimensione_key": dim_key,
                "indicatore": ind_label,
                "indicatore_key": ind_key,
                "peso_dimensione": dim_weight,
                "peso_indicatore": ind_weight,
                "peso_effettivo": effective_weight
            })

    return summary
