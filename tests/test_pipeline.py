from ptof_pipeline.pipeline import main, load_data, process_school, RESULTS_FILE
import pandas as pd
import logging

# Override main to run only on first 3 items
def test_run():
    logging.info("Starting Test Run (3 schools)...")
    
    # Load from the manually created CSV if exists, to get the links I added
    try:
        df = pd.read_csv("test_risultati_analisi.csv", sep=';')
        logging.info("Loaded manual test data.")
    except Exception:
        logging.info("Manual test data not found, loading raw data.")
        df = load_data().head(3).copy()
        df['sito_web'] = ""
        df['ptof_link'] = ""
        df['analisi_orientamento'] = ""

    for index, row in df.iterrows():
        url, ptof, analysis = process_school(row, index + 1, len(df))
        df.at[index, 'sito_web'] = url
        df.at[index, 'ptof_link'] = ptof
        df.at[index, 'analisi_orientamento'] = analysis
    
    output = "test_risultati_analisi_final.csv"
    df.to_csv(output, sep=';', index=False, encoding='utf-8-sig')
    logging.info(f"Test run complete. Saved to {output}")

if __name__ == "__main__":
    test_run()
