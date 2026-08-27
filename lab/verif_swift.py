"""Vérification syntaxique réelle des sources Swift, par une grammaire Swift.

Aucune toolchain Swift n'est joignable depuis cet environnement
(`download.swift.org` bloqué par la politique réseau, le paquet apt « swift »
est le stockage OpenStack) et SwiftUI ne compile de toute façon que sur
Apple. Compter les accolades ne prouve rien.

`tree-sitter` avec la grammaire Swift, elle, parse pour de vrai : elle
signale les nœuds ERROR et MISSING, c'est-à-dire exactement les fautes de
syntaxe. Elle ne vérifie pas les types — mais l'ordre des arguments des
initialiseurs par membre, qui est le risque de typage le plus probable ici,
est contrôlé séparément.
"""
import subprocess
import sys
from tree_sitter import Language, Parser
import tree_sitter_swift

parser = Parser(Language(tree_sitter_swift.language()))


def check_bytes(src: bytes):
    tree = parser.parse(src)
    bad = []
    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type == "ERROR" or n.is_missing:
            line = src[:n.start_byte].count(b"\n") + 1
            snippet = src.split(b"\n")[line - 1].decode("utf-8", "replace").strip()
            bad.append((line, "MISSING" if n.is_missing else "ERROR", snippet[:90]))
        stack.extend(n.children)
    return sorted(set(bad))


def main():
    """Compare les nœuds invalides à une référence git.

    Sortir en échec sur *tout* nœud ERROR serait inutilisable : la grammaire
    a des limites connues sur `x as? T ?? y` et sur un opérateur en tête de
    ligne de suite, deux constructions présentes dans du code qui compile en
    production. Ce qui se contrôle utilement est le DELTA : un changement ne
    doit introduire aucun nœud invalide de plus que ce que la référence en
    portait déjà.
    """
    ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    files = subprocess.run(["git", "diff", "--name-only", ref, "--", "Prophet/", "ProphetTests/"],
                           capture_output=True, text=True).stdout.split()
    if not files:
        print(f"aucun fichier Swift modifié depuis {ref}")
        return 0
    print(f"référence : {ref}\n")
    print(f"  {'fichier':<40}{'avant':>8}{'après':>8}")
    introduced = 0
    for f in files:
        base = subprocess.run(["git", "show", f"{ref}:{f}"], capture_output=True).stdout
        before = check_bytes(base) if base else []
        after = check_bytes(open(f, "rb").read())
        delta = len(after) - len(before)
        introduced += max(0, delta)
        print(f"  {f:<40}{len(before):>8}{len(after):>8}"
              f"{'   <-- NOUVEAU' if delta > 0 else ''}")
        if delta > 0:
            for line, kind, snip in [x for x in after if x not in before]:
                print(f"       L{line} {kind}: {snip}")
    print(f"\n{introduced} nœud(s) de syntaxe invalide introduit(s) depuis {ref}")
    return 1 if introduced else 0


if __name__ == "__main__":
    sys.exit(main())
