"""Amorce le registre avec les tests déjà consommés par `claude/AUDIT-CLAUDE.md`.

Sans cela, la correction de multiplicité compterait les expériences du labo
comme les premières jamais tentées — ce qui est faux, et faux dans le sens
confortable. L'audit a dépensé plusieurs milliers de tests ; toute découverte
ultérieure doit franchir un seuil qui en tient compte.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab

# (id, description, p rapporté, tests supplémentaires de la même famille)
PRIOR = [
    ("audit.chi2",            "Uniformité du champ, null Monte-Carlo 400 réplicats",      0.58,   9),
    ("audit.paires",          "3 160 paires, |z|max = 3,68, Bonferroni 4,06",             0.0002, 3159),
    ("audit.geometrie",       "Adjacences sur la grille 8x10, z = +1,09",                 0.276,  0),
    ("audit.antirejeu",       "2,489 G paires, recouvrement max 16/20",                   0.35,   0),
    ("audit.bonus_position",  "Rang du bonus dans le tirage trié, chi2(19) = 27,46",      0.094,  0),
    ("audit.derive",          "14 fenêtres de 5 000, overlap lag-1",                      0.50,  13),
    ("nist.monobit",          "Monobit sur 2 798 192 bits de rang colex",                 0.376,  0),
    ("nist.blocs",            "Fréquence par blocs M = 20 000",                           0.592,  0),
    ("nist.runs",             "Alternances",                                              0.988,  0),
    ("nist.longest",          "Plus longue série de 1, null Monte-Carlo",                 0.411,  0),
    ("nist.dft",              "Spectral DFT",                                             0.017,  0),
    ("nist.cusum",            "Sommes cumulées",                                          0.023,  0),
    ("nist.entropie",         "Entropie de blocs 10 bits",                                0.883,  0),
    ("nist.bm",               "Complexité linéaire Berlekamp-Massey, M = 500",            0.310,  0),
    ("audit.analogues",       "Analogues, 4,98 G paires, 6 prédicteurs",                  0.30,   5),
    ("audit.maurer",          "Test universel de Maurer, 9 configurations L = 6..14",      0.041,  8),
    ("audit.boost_memoire",   "boost(i) == boost(i+1), 34,46 % vs 34,51 %",               0.80,   0),
    ("audit.bonus_overlap",   "overlap | bonus_i == bonus_{i+1}, null simulé 6 M paires", 0.044,  0),
    ("audit.fenetres_bm",     "BM par fichier, 8 fenêtres",                               0.0425, 7),
    ("audit.fenetres_maurer", "Maurer par fichier, 8 fenêtres",                           0.051,  7),
]

if __name__ == "__main__":
    if os.path.exists(lab.LEDGER):
        rows = lab.ledger()
        if any(r["id"].startswith(("audit.", "nist.")) for r in rows):
            print(f"registre déjà amorcé ({len(rows)} entrées)")
            sys.exit(0)
    for eid, desc, p, extra in PRIOR:
        tok = lab.preregister(eid, desc, "voir claude/AUDIT-CLAUDE.md",
                              "simulé (Monte-Carlo) sauf mention contraire",
                              "conforme si p > seuil Holm du registre entier", track="A")
        row = lab.record(tok, observed=float("nan"), p=p, verdict="conforme",
                         notes="antériorité: test déjà dépensé par l'audit")
        if extra:
            import json
            with open(lab.LEDGER) as fh:
                lines = fh.readlines()
            obj = json.loads(lines[-1]); obj["m_extra"] = extra
            lines[-1] = json.dumps(obj, ensure_ascii=False) + "\n"
            with open(lab.LEDGER, "w") as fh:
                fh.writelines(lines)
    rows = lab.ledger()
    m = len(rows) + sum(int(r.get("m_extra", 0)) for r in rows)
    print(f"registre amorcé : {len(rows)} entrées, m = {m} tests déjà dépensés")
    print(f"seuil Holm le plus strict à alpha=0,05 : p < {0.05/m:.2e}")
