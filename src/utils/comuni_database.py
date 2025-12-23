#!/usr/bin/env python3
"""
Database dei comuni italiani per l'arricchimento dei dati.
Usa il database open source da: https://github.com/matteocontrini/comuni-json
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

class ComuniDatabase:
    """Database dei comuni italiani con informazioni geografiche complete."""
    
    _instance = None
    _loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not ComuniDatabase._loaded:
            self._load_database()
            ComuniDatabase._loaded = True
    
    def _load_database(self):
        """Carica il database dei comuni."""
        # Trova il file JSON
        possible_paths = [
            Path(__file__).parent.parent.parent / "data" / "comuni_italiani.json",
            Path("data/comuni_italiani.json"),
            Path("/Users/danieledragoni/git/LIste/data/comuni_italiani.json")
        ]
        
        db_path = None
        for p in possible_paths:
            if p.exists():
                db_path = p
                break
        
        if not db_path:
            raise FileNotFoundError("Database comuni_italiani.json non trovato!")
        
        with open(db_path, 'r', encoding='utf-8') as f:
            self.comuni_raw = json.load(f)
        
        # Crea indici per ricerca veloce
        self._build_indexes()
        
        print(f"✓ ComuniDatabase: caricati {len(self.comuni_raw)} comuni")
    
    def _build_indexes(self):
        """Costruisce indici per ricerca veloce."""
        # Indice per nome comune (normalizzato)
        self.by_nome = {}
        # Indice per nome + provincia
        self.by_nome_provincia = {}
        
        for comune in self.comuni_raw:
            # Normalizza il nome
            nome_norm = self._normalize(comune['nome'])
            
            # Salva nel dizionario per nome
            if nome_norm not in self.by_nome:
                self.by_nome[nome_norm] = []
            self.by_nome[nome_norm].append(comune)
            
            # Salva nel dizionario per nome + provincia
            provincia_norm = self._normalize(comune['provincia']['nome'])
            key = f"{nome_norm}|{provincia_norm}"
            self.by_nome_provincia[key] = comune
    
    def _normalize(self, text: str) -> str:
        """Normalizza il testo per la ricerca."""
        if not text:
            return ""
        # Converti in minuscolo, rimuovi accenti comuni
        text = text.lower().strip()
        replacements = {
            'à': 'a', 'á': 'a', 'è': 'e', 'é': 'e', 
            'ì': 'i', 'í': 'i', 'ò': 'o', 'ó': 'o',
            'ù': 'u', 'ú': 'u', "'": "", "-": " "
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    def get_comune_info(self, comune_nome: str, provincia: str = None) -> Optional[Dict[str, Any]]:
        """
        Cerca un comune e restituisce le sue informazioni geografiche.
        
        Args:
            comune_nome: Nome del comune da cercare
            provincia: Nome della provincia (opzionale, per disambiguare)
        
        Returns:
            Dict con provincia, regione, area_geografica o None se non trovato
        """
        if not comune_nome:
            return None
        
        nome_norm = self._normalize(comune_nome)
        
        # Prima prova con provincia se fornita
        if provincia:
            provincia_norm = self._normalize(provincia)
            key = f"{nome_norm}|{provincia_norm}"
            if key in self.by_nome_provincia:
                return self._format_result(self.by_nome_provincia[key])
        
        # Poi cerca solo per nome
        if nome_norm in self.by_nome:
            matches = self.by_nome[nome_norm]
            if len(matches) == 1:
                return self._format_result(matches[0])
            elif len(matches) > 1:
                # Più comuni con lo stesso nome, restituisci il primo
                # (meglio di niente, in genere sono pochi casi)
                return self._format_result(matches[0])
        
        # Prova ricerca parziale per i nomi composti
        for key in self.by_nome:
            if nome_norm in key or key in nome_norm:
                matches = self.by_nome[key]
                if matches:
                    return self._format_result(matches[0])
        
        return None
    
    def _format_result(self, comune: Dict) -> Dict[str, Any]:
        """Formatta il risultato con le informazioni geografiche."""
        # Mappa le zone del database ISTAT alle nostre area_geografica
        # Il database ISTAT ha: Nord-ovest, Nord-est, Centro, Sud, Isole
        # Noi usiamo: Nord Ovest, Nord Est, Centro, Sud, Isole
        zona_to_area = {
            'Nord-ovest': 'Nord Ovest',
            'Nord-est': 'Nord Est',
            'Centro': 'Centro',
            'Sud': 'Sud',
            'Isole': 'Isole'
        }
        
        zona = comune['zona']['nome']
        area_geo = zona_to_area.get(zona, zona)
        
        return {
            'comune': comune['nome'],
            'provincia': comune['provincia']['nome'],
            'sigla_provincia': comune.get('sigla', ''),
            'regione': comune['regione']['nome'],
            'zona_istat': zona,
            'area_geografica': area_geo
        }
    
    def get_area_geografica_by_regione(self, regione: str) -> Optional[str]:
        """
        Determina l'area geografica dalla regione.
        
        Args:
            regione: Nome della regione
        
        Returns:
            Area geografica (Nord, Centro, Sud e Isole) o None
        """
        if not regione:
            return None
        
        regione_norm = self._normalize(regione)
        
        # Trova un comune di quella regione
        for comune in self.comuni_raw:
            if self._normalize(comune['regione']['nome']) == regione_norm:
                result = self._format_result(comune)
                return result['area_geografica']
        
        # Fallback: usa la mappa statica
        REGIONE_TO_AREA = {
            'piemonte': 'Nord Ovest',
            'valle d\'aosta': 'Nord Ovest',
            'valle daosta': 'Nord Ovest',
            'lombardia': 'Nord Ovest',
            'liguria': 'Nord Ovest',
            'trentino-alto adige': 'Nord Est',
            'trentino alto adige': 'Nord Est',
            'veneto': 'Nord Est',
            'friuli-venezia giulia': 'Nord Est',
            'friuli venezia giulia': 'Nord Est',
            'emilia-romagna': 'Nord Est',
            'emilia romagna': 'Nord Est',
            'toscana': 'Centro',
            'umbria': 'Centro',
            'marche': 'Centro',
            'lazio': 'Centro',
            'abruzzo': 'Sud',
            'molise': 'Sud',
            'campania': 'Sud',
            'puglia': 'Sud',
            'basilicata': 'Sud',
            'calabria': 'Sud',
            'sicilia': 'Isole',
            'sardegna': 'Isole',
        }
        
        return REGIONE_TO_AREA.get(regione_norm)


# Test rapido
if __name__ == "__main__":
    db = ComuniDatabase()
    
    # Test comuni
    test_comuni = ["Roma", "Milano", "Napoli", "Agrigento", "Trento", "Firenze"]
    print("\nTest ricerca comuni:")
    for comune in test_comuni:
        info = db.get_comune_info(comune)
        if info:
            print(f"  {comune}: {info['provincia']} - {info['regione']} - {info['area_geografica']}")
        else:
            print(f"  {comune}: NON TROVATO")
    
    # Test regioni
    print("\nTest area geografica per regione:")
    test_regioni = ["LOMBARDIA", "Lazio", "sicilia", "CAMPANIA"]
    for reg in test_regioni:
        area = db.get_area_geografica_by_regione(reg)
        print(f"  {reg}: {area}")
