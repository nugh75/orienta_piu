import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.proportion import proportion_confint
try:
    import scikit_posthocs as sp
except ImportError:
    sp = None

def compute_descriptive_stats(df: pd.DataFrame) -> dict:
    """
    Calcola statistiche descrittive generali per il dataframe delle attività.
    """
    if df.empty:
        return {}

    stats_dict = {
        "n_total": len(df),
        "n_scuole": df['codice_meccanografico'].nunique() if 'codice_meccanografico' in df.columns else 0,
        "n_regioni": df['regione'].nunique() if 'regione' in df.columns else 0,
        "categorie_dist": df['categoria'].value_counts().to_dict(),
        "categorie_pct": (df['categoria'].value_counts(normalize=True) * 100).to_dict()
    }

    if 'maturity_index' in df.columns:
        mi = pd.to_numeric(df['maturity_index'], errors='coerce').dropna()
        if not mi.empty:
            stats_dict["ro_stats"] = {
                "mean": mi.mean(),
                "median": mi.median(),
                "std": mi.std(),
                "min": mi.min(),
                "max": mi.max(),
                "mode": mi.mode().tolist()
            }
            # Shapiro-Wilk test for normality
            if len(mi) >= 3:
                shapiro_stat, shapiro_p = stats.shapiro(mi)
                stats_dict["ro_normality"] = {"stat": shapiro_stat, "p_value": shapiro_p}

    return stats_dict

def compute_chi2_analysis(df: pd.DataFrame, var1: str, var2: str) -> dict:
    """
    Esegue test Chi-quadrato o Fisher exact test tra due variabili categoriali.
    Calcola Cramer's V come effect size.
    """
    if df.empty or var1 not in df.columns or var2 not in df.columns:
        return {}

    # Costruisci tabella di contingenza
    # Se le variabili sono liste (es. ambiti), esplodile prima? 
    # Per ora assumiamo categoriche singole per semplicità, o gestiamo l'explode nel chiamante.
    # Tuttavia, activity_stats dovrebbe essere robusto.
    
    # Check for list-like columns (containing pipe |) and explode if necessary is handled by caller usually for clean cross-tabs.
    # Here we assume df is input ready or we do a cleanup on the fly if needed. 
    # Let's simple check invalid values.
    
    valid_df = df.dropna(subset=[var1, var2])
    ctab = pd.crosstab(valid_df[var1], valid_df[var2])
    
    if ctab.empty or ctab.shape[0] < 2 or ctab.shape[1] < 2:
        return {"error": "Insufficient data/dimensions for Chi2"}

    chi2, p, dof, expected = stats.chi2_contingency(ctab)
    n = ctab.sum().sum()
    min_dim = min(ctab.shape) - 1
    cramer_v = np.sqrt(chi2 / (n * min_dim)) if n > 0 and min_dim > 0 else 0

    results = {
        "test": "Chi-squared",
        "chi2": chi2,
        "p_value": p,
        "dof": dof,
        "cramers_v": cramer_v,
        "contingency_table": ctab,
        "expected": pd.DataFrame(expected, index=ctab.index, columns=ctab.columns)
    }

    # Post-hoc residuals (Standardized Residuals)
    # R = (Obs - Exp) / sqrt(Exp)
    # Adjusted Standardized Residuals would be better but simple std residuals are common
    with np.errstate(divide='ignore', invalid='ignore'):
        residuals = (ctab - expected) / np.sqrt(expected)
    results["residuals"] = residuals

    return results

def compute_kruskal_analysis(df: pd.DataFrame, group_var: str, value_var: str) -> dict:
    """
    Esegue Kruskal-Wallis H test per confrontare una variabile numerica (value_var)
    tra gruppi definiti da group_var.
    """
    if df.empty or group_var not in df.columns or value_var not in df.columns:
        return {}

    clean_df = df[[group_var, value_var]].dropna()
    clean_df[value_var] = pd.to_numeric(clean_df[value_var], errors='coerce')
    clean_df = clean_df.dropna()

    groups = []
    labels = []
    
    for label, group in clean_df.groupby(group_var):
        vals = group[value_var].values
        if len(vals) > 0:
            groups.append(vals)
            labels.append(label)

    if len(groups) < 2:
        return {"error": "At least 2 groups required"}

    stat, p = stats.kruskal(*groups)
    
    # Epsilon squared
    n = len(clean_df)
    k = len(groups)
    epsilon2 = (stat - k + 1) / (n - k) if n > k else 0
    epsilon2 = max(0, epsilon2) # Clip at 0

    return {
        "test": "Kruskal-Wallis",
        "statistic": stat,
        "p_value": p,
        "epsilon_squared": epsilon2,
        "groups": labels,
        "n_samples": n,
        "medians": clean_df.groupby(group_var)[value_var].median().to_dict()
    }

def compute_dunn_posthoc(df: pd.DataFrame, group_var: str, value_var: str) -> pd.DataFrame:
    """
    Esegue test di Dunn post-hoc con correzione Bonferroni.
    Richiede scikit-posthocs.
    """
    if sp is None:
        return pd.DataFrame() # Return empty if module missing

    clean_df = df[[group_var, value_var]].dropna()
    clean_df[value_var] = pd.to_numeric(clean_df[value_var], errors='coerce')
    clean_df = clean_df.dropna()
    
    if clean_df[group_var].nunique() < 2:
        return pd.DataFrame()

    try:
        p_values = sp.posthoc_dunn(clean_df, val_col=value_var, group_col=group_var, p_adjust='bonferroni')
        return p_values
    except Exception as e:
        print(f"Error in Dunn test: {e}")
        return pd.DataFrame()

def generate_stats_report(df: pd.DataFrame, stats_results: dict = None) -> str:
    """
    Genera un report testuale basato sui risultati statistici disponibili.
    """
    if df.empty:
        return "Nessun dato disponibile per l'analisi."
        
    n_total = len(df)
    report = f"**Sintesi Report Statistico**\n\n"
    report += f"L'analisi è stata condotta su un campione di **N={n_total}** attività.\n\n"
    
    # 1. Descrittiva
    desc = compute_descriptive_stats(df)
    cat_stats = desc.get("categorie_dist", {})
    if cat_stats:
        top_cat = max(cat_stats, key=cat_stats.get)
        top_pct = cat_stats[top_cat] / n_total * 100
        report += f"**Distribuzione Categorie**: La categoria prevalente è *{top_cat}* ({top_pct:.1f}%). "
        if len(cat_stats) > 1:
            min_cat = min(cat_stats, key=cat_stats.get)
            min_pct = cat_stats[min_cat] / n_total * 100
            report += f"La meno rappresentata è *{min_cat}* ({min_pct:.1f}%).\n"
    
    ro_stats = desc.get("ro_stats", {})
    if ro_stats:
        report += f"**Indice RO**: Media={ro_stats['mean']:.2f} (SD={ro_stats['std']:.2f}), Mediana={ro_stats['median']:.2f}.\n\n"

    # 2. Associazioni (Esempio: Categoria x Area)
    # Calcoliamo al volo alcune associazioni chiave per il report automatico
    if 'area_geografica' in df.columns:
        chi_res = compute_chi2_analysis(df, 'categoria', 'area_geografica')
        if "p_value" in chi_res:
            p = chi_res['p_value']
            sig = "significativa" if p < 0.05 else "non significativa"
            v = chi_res['cramers_v']
            v_label = "trascurabile" if v < 0.1 else "piccolo" if v < 0.3 else "medio" if v < 0.5 else "grande"
            
            report += f"**Associazione Categoria-Area**: La distribuzione per area geografica risulta statisticamente {sig} "
            report += f"(χ²(dof={chi_res['dof']})={chi_res['chi2']:.1f}, p={p:.4f}), con un effetto {v_label} (V={v:.2f}).\n"

    # 3. Differenze Indice RO (Esempio: per Categoria)
    if ro_stats:
        k_res = compute_kruskal_analysis(df, 'categoria', 'maturity_index')
        if "p_value" in k_res:
            p = k_res['p_value']
            sig = "differisce" if p < 0.05 else "non differisce"
            eps = k_res['epsilon_squared']
            eps_label = "trascurabile" if eps < 0.01 else "piccolo" if eps < 0.08 else "medio" if eps < 0.26 else "grande"
            
            report += f"**Confronto Indice RO**: L'indice {sig} significativamente tra le diverse categorie "
            report += f"(Kruskal-Wallis H={k_res['statistic']:.1f}, p={p:.4f}), con una dimensione dell'effetto {eps_label} (ε²={eps:.2f}).\n"

    return report
