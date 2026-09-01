#!/usr/bin/env python3
"""signalr_capture — se brancher sur un flux SignalR et en tirer l'ORDRE D'ÉMISSION.

POURQUOI CE FICHIER EXISTE
===========================
Tout le dossier bute sur une seule rareté : l'archive REST publie l'ENSEMBLE TRIÉ
des vingt numéros, jamais leur ORDRE. Les douze tirages ordonnés dont on dispose
viennent de vidéos filmées à la main, et ils valent, à eux seuls, plus que les
70 560 tirages de l'archive (§110, §136).

    UN TIRAGE ORDONNÉ VAUT ~90 ÉQUATIONS EXACTES. UN TIRAGE TRIÉ EN VAUT ZÉRO,
    parce qu'il faudrait brancher sur 20 valeurs par mot pour en extraire une.

Si la plateforme anime le tirage boule par boule, elle POUSSE ces boules une par
une — et l'ordre d'arrivée des messages EST l'ordre d'émission. À 204 tirages par
jour, cela donne 18 360 équations par jour :

        MT19937      19 937 équations   ->   1,1 jour de capture
        WELL44497b   44 497 équations   ->   2,4 jours

C'est le plus gros levier jamais identifié dans ce dossier, et de loin.

CE QUE FAIT CE FICHIER, ET CE QU'IL NE FAIT PAS
================================================
Il PARLE le protocole SignalR Core (négociation HTTP puis WebSocket, messages
JSON séparés par 0x1E), SANS AUCUNE DÉPENDANCE — bibliothèque standard seule,
WebSocket compris, pour qu'il tourne sur n'importe quel Python 3.

Il NE DEVINE PAS l'URL du concentrateur. Trois modes :

    --discover BASE     essaie une liste de chemins plausibles et dit lesquels
                        répondent à /negotiate
    --capture URL       se connecte et écrit TOUS les messages en JSONL, avec
                        leur horodatage de RÉCEPTION à la milliseconde
    --decode FICHIER    relit une capture et en tire des lignes au format de
                        `lab/draws_ordered.csv`

COMMENT TROUVER L'URL EN TRENTE SECONDES
=========================================
Le plus sûr n'est pas de deviner, c'est de regarder :

    1. ouvrir la page du tirage dans un navigateur ;
    2. DevTools -> Réseau -> filtrer « WS » (ou chercher « negotiate ») ;
    3. l'URL qui apparaît est celle du concentrateur.

Ou, sans navigateur : télécharger le bundle JavaScript de la page et y chercher
la chaîne `negotiate` ou `HubConnectionBuilder`.

LE DÉCODEUR N'INFÈRE PAS LE SCHÉMA EN LE DEVINANT : IL L'APPREND
=================================================================
Le schéma des messages est inconnu tant qu'on n'a pas vu le flux. Plutôt que de
supposer un nom de champ, le décodeur repère le champ qui porte le numéro par sa
SIGNATURE :

    il vaut toujours entre 1 et 80 ; sur toute fenêtre de vingt messages
    consécutifs ses valeurs sont DISTINCTES — c'est Fisher-Yates sans remise —
    et elles ne forment PAS une plage contiguë de vingt entiers, ce qui
    signerait un compteur de position et non un numéro.

Le troisième critère est celui qui sépare `number` de `index`, et il tient parce
que vingt numéros tirés parmi quatre-vingts ne sont contigus qu'avec probabilité
61/C(80,20) ~ 1,7e-17.

TÉMOIN
=======
`--selftest` lance des concentrateurs SignalR FACTICES en local — vrai WebSocket,
vrai protocole — qui émettent un tirage scripté boule par boule sous DEUX SCHÉMAS
DIFFÉRENTS, dont un où le numéro arrive en chaîne de caractères et où un champ
de position piège le décodeur. Il vérifie ensuite que l'ordre d'émission est
rendu EXACT dans les deux cas.

    python3 tools/signalr_capture.py --selftest
"""

import argparse
import base64
import hashlib
import json
import os
import re
import socket
import ssl
import struct
import sys
import threading
import time
from urllib.parse import urlparse, urlencode
from urllib.request import Request, urlopen

RS = "\x1e"                                   # séparateur d'enregistrement SignalR
GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
POOL_MIN, POOL_MAX = 1, 80
DRAWN = 20

CHEMINS = [                                   # essais de --discover, dans l'ordre
    "/hub", "/hubs", "/signalr", "/gamehub", "/game-hub",
    "/hubs/game", "/hubs/draw", "/hubs/draws", "/hubs/lotoexpress",
    "/hubs/notification", "/hubs/notifications", "/hubs/live",
    "/api/hub", "/api/hubs/game", "/api/dbg/hub", "/api/signalr",
    "/lotoexpress/hub", "/games/lotoexpress/hub", "/live/hub",
]


def say(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------------------
# WebSocket minimal, côté client ET côté serveur (pour le témoin). Sans
# dépendance : c'est le prix à payer pour que l'outil tourne partout.
# ---------------------------------------------------------------------------
class WS:
    def __init__(self, sock, cote_client=True):
        self.s = sock
        self.client = cote_client
        self.reste = b""

    def _lire(self, n):
        while len(self.reste) < n:
            b = self.s.recv(65536)
            if not b:
                raise ConnectionError("flux ferme")
            self.reste += b
        out, self.reste = self.reste[:n], self.reste[n:]
        return out

    def envoie(self, data, opcode=0x1):
        if isinstance(data, str):
            data = data.encode()
        t = bytearray([0x80 | opcode])
        n = len(data)
        masque = 0x80 if self.client else 0
        if n < 126:
            t.append(masque | n)
        elif n < 65536:
            t.append(masque | 126)
            t += struct.pack(">H", n)
        else:
            t.append(masque | 127)
            t += struct.pack(">Q", n)
        if self.client:
            k = os.urandom(4)
            t += k
            data = bytes(c ^ k[i & 3] for i, c in enumerate(data))
        t += data
        self.s.sendall(bytes(t))

    def recoit(self):
        """Rend (opcode, charge utile). Recolle les trames fragmentées."""
        morceaux, op0 = b"", None
        while True:
            b0, b1 = self._lire(2)
            fin, op = b0 & 0x80, b0 & 0x0F
            masque, n = b1 & 0x80, b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._lire(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._lire(8))[0]
            k = self._lire(4) if masque else None
            d = self._lire(n)
            if k:
                d = bytes(c ^ k[i & 3] for i, c in enumerate(d))
            if op0 is None and op != 0:
                op0 = op
            morceaux += d
            if fin:
                return op0 if op0 is not None else op, morceaux


def poignee_client(sock, host, chemin, entetes=None):
    cle = base64.b64encode(os.urandom(16)).decode()
    h = [f"GET {chemin} HTTP/1.1", f"Host: {host}",
         "Upgrade: websocket", "Connection: Upgrade",
         f"Sec-WebSocket-Key: {cle}", "Sec-WebSocket-Version: 13"]
    for k, v in (entetes or {}).items():
        h.append(f"{k}: {v}")
    sock.sendall(("\r\n".join(h) + "\r\n\r\n").encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        b = sock.recv(4096)
        if not b:
            raise ConnectionError("pas de reponse a la poignee")
        buf += b
    tete, reste = buf.split(b"\r\n\r\n", 1)
    if b" 101 " not in tete.split(b"\r\n")[0]:
        raise ConnectionError("upgrade refuse : " + tete.split(b"\r\n")[0].decode())
    attendu = base64.b64encode(hashlib.sha1((cle + GUID).encode()).digest()).decode()
    if attendu.lower() not in tete.decode(errors="replace").lower():
        raise ConnectionError("Sec-WebSocket-Accept invalide")
    ws = WS(sock, True)
    ws.reste = reste
    return ws


# ---------------------------------------------------------------------------
# SignalR Core : negociation puis poignee de protocole.
# ---------------------------------------------------------------------------
def negocie(url, entetes=None, delai=10):
    """POST {url}/negotiate?negotiateVersion=1. Rend le JSON, ou leve."""
    u = url.rstrip("/") + "/negotiate?" + urlencode({"negotiateVersion": "1"})
    req = Request(u, data=b"", method="POST")
    req.add_header("Content-Type", "text/plain;charset=UTF-8")
    for k, v in (entetes or {}).items():
        req.add_header(k, v)
    with urlopen(req, timeout=delai) as r:
        return json.loads(r.read().decode())


def ouvre(url, entetes=None, delai=15):
    """Negocie puis ouvre le WebSocket SignalR, poignee de protocole comprise."""
    neg = negocie(url, entetes, delai)
    jeton = neg.get("connectionToken") or neg.get("connectionId")
    if not jeton:
        raise RuntimeError("negociation sans connectionToken : " + json.dumps(neg))
    p = urlparse(url)
    tls = p.scheme in ("https", "wss")
    port = p.port or (443 if tls else 80)
    chemin = (p.path or "/") + "?" + urlencode({"id": jeton})
    s = socket.create_connection((p.hostname, port), timeout=delai)
    if tls:
        s = ssl.create_default_context().wrap_socket(s, server_hostname=p.hostname)
    ws = poignee_client(s, p.netloc, chemin, entetes)
    ws.envoie(json.dumps({"protocol": "json", "version": 1}) + RS)
    op, d = ws.recoit()
    rep = json.loads(d.decode().split(RS)[0] or "{}")
    if rep.get("error"):
        raise RuntimeError("poignee SignalR refusee : " + rep["error"])
    return ws, neg


def messages(ws):
    """Itère sur les messages SignalR décodés, en répondant aux pings."""
    tampon = ""
    while True:
        op, d = ws.recoit()
        if op == 0x8:
            return
        if op == 0x9:
            ws.envoie(d, 0xA)
            continue
        if op not in (0x1, 0x2, 0x0):
            continue
        tampon += d.decode(errors="replace")
        while RS in tampon:
            brut, tampon = tampon.split(RS, 1)
            if not brut:
                continue
            try:
                m = json.loads(brut)
            except json.JSONDecodeError:
                continue
            if m.get("type") == 6:              # ping : on repond pour rester vivant
                ws.envoie(json.dumps({"type": 6}) + RS)
                continue
            if m.get("type") == 7:              # close
                return
            yield m


# ---------------------------------------------------------------------------
# Décodeur : il n'INFÈRE PAS le schéma en le devinant, il l'APPREND du flux.
#
# Un flux de tirage animé pousse un message par boule. Ces messages partagent
# une même `target` et une même forme ; l'un de leurs champs porte le numéro.
# On repère ce champ par sa SIGNATURE plutôt que par son nom :
#
#   - il vaut toujours entre 1 et 80 ;
#   - sur toute fenêtre de vingt messages consécutifs, ses vingt valeurs sont
#     DISTINCTES — c'est Fisher-Yates sans remise ;
#   - et ses valeurs ne forment PAS une plage contiguë de vingt entiers, ce qui
#     signerait un compteur de position et non un numéro.
#
# Le troisième critère est celui qui sépare `number` de `index`, et il tient
# parce que vingt numéros tirés parmi quatre-vingts ne sont contigus qu'avec une
# probabilité de 61/C(80,20) ~ 1,7e-17.
# ---------------------------------------------------------------------------
def aplati(o, prefixe="", out=None):
    """Rend {chemin: valeur} pour toutes les valeurs entières du message."""
    if out is None:
        out = {}
    if isinstance(o, bool):
        return out
    if isinstance(o, int):
        out[prefixe] = o
    elif isinstance(o, str):
        t = re.fullmatch(r"\s*(-?\d+)\s*", o)
        if t:
            out[prefixe] = int(t.group(1))
    elif isinstance(o, dict):
        for k, v in o.items():
            aplati(v, f"{prefixe}.{k}" if prefixe else str(k), out)
    elif isinstance(o, (list, tuple)):
        for i, v in enumerate(o):
            aplati(v, f"{prefixe}[{i}]" if prefixe else f"[{i}]", out)
    return out


def _fenetres_distinctes(vals, k=DRAWN):
    return all(len(set(vals[i:i + k])) == k for i in range(0, len(vals) - k + 1))


def _contigu(vals, k=DRAWN):
    """Signature d'un compteur de position : les k premières valeurs forment
    exactement une plage d'entiers consécutifs."""
    f = vals[:k]
    return len(set(f)) == k and max(f) - min(f) == k - 1


def trouve_champ_boule(msgs):
    """Rend (cible, chemin) du champ qui porte le numéro, ou (None, None)."""
    groupes = {}
    for m in msgs:
        cible = m.get("target") or "?"
        groupes.setdefault(cible, []).append(aplati(m.get("arguments", m)))
    best = None
    for cible, plats in groupes.items():
        if len(plats) < DRAWN:
            continue
        chemins = set()
        for p in plats:
            chemins |= set(p)
        for ch in chemins:
            vals = [p[ch] for p in plats if ch in p]
            if len(vals) < DRAWN:
                continue
            if not all(POOL_MIN <= v <= POOL_MAX for v in vals):
                continue
            if not _fenetres_distinctes(vals):
                continue
            if _contigu(vals):                 # c'est un index, pas un numéro
                continue
            score = (len(vals), max(vals) - min(vals))
            if best is None or score > best[0]:
                best = (score, cible, ch)
    return (best[1], best[2]) if best else (None, None)


def decode(lignes, trace=False):
    """Rend [(id_tirage|None, [20 numéros dans l'ordre], bonus|None)]."""
    msgs = [l["msg"] for l in lignes
            if isinstance(l, dict) and "msg" in l and "meta" not in l]
    cible, chemin = trouve_champ_boule(msgs)
    if trace:
        say(f"   champ de boule infere : target={cible!r} chemin={chemin!r}")
    if cible is None:
        return []

    tirages, courant, tid = [], [], None
    for m in msgs:
        plat = aplati(m.get("arguments", m))
        c = m.get("target") or "?"
        for v in plat.values():                # un identifiant de tirage plausible
            if 100000 <= v <= 100000000:
                tid = v
        if c == cible and chemin in plat and len(courant) < DRAWN:
            courant.append(plat[chemin])
            continue
        if len(courant) == DRAWN:
            bonus = next((v for v in plat.values() if v in courant), None)
            tirages.append((tid, courant, bonus))
            courant, tid = [], None
    if len(courant) == DRAWN:
        tirages.append((tid, courant, None))
    return tirages


def ligne_csv(tid, ordre, bonus, etiquette="signalr"):
    ch = [str(tid if tid else ""), etiquette] + [str(n) for n in ordre]
    if bonus:
        ch.append(str(bonus))
    return ",".join(ch)


# ---------------------------------------------------------------------------
# Les trois modes.
# ---------------------------------------------------------------------------
def mode_discover(base, entetes):
    say(f"   negociation essayee sur {len(CHEMINS)} chemins sous {base}\n")
    say(f"   {'chemin':>28} {'code':>6}   reponse")
    trouves = []
    for c in CHEMINS:
        u = base.rstrip("/") + c
        try:
            neg = negocie(u, entetes, delai=8)
            t = ",".join(a.get("transport", "?")
                         for a in neg.get("availableTransports", []))
            say(f"   {c:>28} {'200':>6}   TROUVE  transports = {t or '?'}")
            trouves.append(u)
        except Exception as e:
            code = getattr(e, "code", None)
            say(f"   {c:>28} {str(code or '-'):>6}   {type(e).__name__}")
    say("")
    if trouves:
        say("   concentrateur(s) trouve(s) :")
        for u in trouves:
            say(f"     {u}")
    else:
        say("   Aucun. Ne pas insister a l'aveugle : ouvrir la page dans un\n"
            "   navigateur, DevTools -> Reseau -> filtre « WS », et lire l'URL.")
    return trouves


def mode_capture(url, sortie, entetes, secondes=None, verbeux=True):
    ws, neg = ouvre(url, entetes)
    t0 = time.time()
    n = 0
    with open(sortie, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": t0, "meta": "negotiate", "msg": neg},
                            ensure_ascii=False) + "\n")
        fh.flush()
        for m in messages(ws):
            n += 1
            fh.write(json.dumps({"t": time.time(), "msg": m},
                                ensure_ascii=False) + "\n")
            fh.flush()                            # l'ordre d'arrivee est la donnee
            if verbeux and n <= 20:
                say(f"   [{n:>3}] {json.dumps(m, ensure_ascii=False)[:160]}")
            if secondes and time.time() - t0 > secondes:
                break
    return n


def mode_decode(chemin):
    lignes = [json.loads(l) for l in open(chemin, encoding="utf-8") if l.strip()]
    tirages = decode(lignes)
    say(f"   {len(lignes)} messages -> {len(tirages)} tirage(s) ordonne(s)\n")
    for tid, ordre, bonus in tirages:
        say("   " + ligne_csv(tid, ordre, bonus))
    return tirages


# ---------------------------------------------------------------------------
# TÉMOIN : un concentrateur SignalR factice, en local, vrai protocole.
# ---------------------------------------------------------------------------
ORDRE_TEST = [17, 74, 45, 36, 69, 60, 4, 47, 7, 75,
              28, 12, 8, 22, 54, 25, 56, 62, 52, 15]
BONUS_TEST = 45
ID_TEST = 1381278


SCHEMAS = {
    # nom          debut         boule    champ num   champ pos   extra
    "A": ("DrawStarted", "drawId", "BallDrawn", "number", "index", "ExtraBall"),
    # schema B : autres noms, numero en CHAINE, et un champ de position qui
    # forme une plage contigue 0..19 — exactement le piege a eviter.
    "B": ("start", "ref", "ball", "n", "pos", "extra"),
}


def _faux_hub(port, pret, schema="A"):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(4)
    pret.set()
    for _ in range(2):                            # negotiate, puis websocket
        c, _a = srv.accept()
        buf = b""
        while b"\r\n\r\n" not in buf:
            b = c.recv(4096)
            if not b:
                break
            buf += b
        tete = buf.decode(errors="replace")
        if "negotiate" in tete.split("\r\n")[0]:
            corps = json.dumps({
                "connectionId": "TEMOIN", "connectionToken": "TEMOIN",
                "negotiateVersion": 1,
                "availableTransports": [{"transport": "WebSockets",
                                         "transferFormats": ["Text", "Binary"]}]})
            c.sendall(("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                       f"Content-Length: {len(corps)}\r\n\r\n{corps}").encode())
            c.close()
            continue
        cle = re.search(r"Sec-WebSocket-Key:\s*(\S+)", tete, re.I).group(1)
        acc = base64.b64encode(hashlib.sha1((cle + GUID).encode()).digest()).decode()
        c.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                   f"Connection: Upgrade\r\nSec-WebSocket-Accept: {acc}\r\n\r\n").encode())
        ws = WS(c, False)
        deb, cid, bal, num, pos, ext = SCHEMAS[schema]
        chaine = schema == "B"                    # le numero arrive en CHAINE
        ws.recoit()                               # poignee de protocole du client
        ws.envoie("{}" + RS)
        ws.envoie(json.dumps({"type": 1, "target": deb,
                              "arguments": [{cid: ID_TEST}]}) + RS)
        for i, n in enumerate(ORDRE_TEST):        # UNE boule par message
            v = str(n) if chaine else n
            ws.envoie(json.dumps({"type": 1, "target": bal,
                                  "arguments": [{pos: i, num: v}]}) + RS)
        b = str(BONUS_TEST) if chaine else BONUS_TEST
        ws.envoie(json.dumps({"type": 1, "target": ext,
                              "arguments": [{num: b}]}) + RS)
        ws.envoie(json.dumps({"type": 7}) + RS)
        time.sleep(0.2)
        c.close()
    srv.close()


def selftest():
    ok = tot = 0
    for k, (schema, port) in enumerate((("A", 45789), ("B", 45790))):
        say(f"  -- schema {schema} --")
        pret = threading.Event()
        th = threading.Thread(target=_faux_hub, args=(port, pret, schema),
                              daemon=True)
        th.start()
        pret.wait(5)
        tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                           f"signalr_temoin_{schema}.jsonl")
        if os.path.exists(tmp):
            os.remove(tmp)

        tot += 1
        try:
            n = mode_capture(f"http://127.0.0.1:{port}/hub", tmp, None,
                             verbeux=False)
            bon = n == 22                          # 1 debut + 20 boules + 1 extra
            ok += bon
            say(f"  capture : {n} messages recus (attendu 22)  "
                f"{'OK' if bon else 'ECHEC'}")
        except Exception as e:
            say(f"  capture : ECHEC {type(e).__name__}: {e}")
            continue

        lignes = [json.loads(l) for l in open(tmp, encoding="utf-8") if l.strip()]
        t = decode(lignes, trace=True)

        tot += 1
        bon = len(t) == 1
        ok += bon
        say(f"  decodage : {len(t)} tirage (attendu 1)  {'OK' if bon else 'ECHEC'}")
        if not t:
            continue

        tid, ordre, bonus = t[0]
        for nom, got, att in (("ordre d'emission", ordre, ORDRE_TEST),
                              ("bonus", bonus, BONUS_TEST),
                              ("identifiant", tid, ID_TEST)):
            tot += 1
            bon = got == att
            ok += bon
            say(f"  {nom:>18} : {'EXACT' if bon else f'{got} != {att}'}  "
                f"{'OK' if bon else 'ECHEC'}")
        tot += 1
        bon = sorted(ordre) != ordre               # l'ordre n'est pas le tri
        ok += bon
        say(f"  {'ordre != tri':>18} : {'OK' if bon else 'ECHEC — ordre perdu'}")
        tot += 1
        lc = ligne_csv(tid, ordre, bonus)
        att = ("1381278,signalr,17,74,45,36,69,60,4,47,7,75,"
               "28,12,8,22,54,25,56,62,52,15,45")
        bon = lc == att
        ok += bon
        say(f"  {'ligne CSV':>18} : {'OK' if bon else 'ECHEC'}")

    say(f"autotest : {ok}/{tot}")
    return ok == tot


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--discover", metavar="BASE")
    ap.add_argument("--capture", metavar="URL")
    ap.add_argument("--decode", metavar="FICHIER")
    ap.add_argument("--out", default="signalr_capture.jsonl")
    ap.add_argument("--seconds", type=int, default=None)
    ap.add_argument("--origin", default=None)
    ap.add_argument("--cookie", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    ent = {"User-Agent": "Mozilla/5.0"}
    if a.origin:
        ent["Origin"] = a.origin
        ent["Referer"] = a.origin + "/"
    if a.cookie:
        ent["Cookie"] = a.cookie

    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if a.discover:
        mode_discover(a.discover, ent)
    elif a.capture:
        say(f"   capture -> {a.out}   (Ctrl-C pour arreter)")
        n = mode_capture(a.capture, a.out, ent, a.seconds)
        say(f"   {n} messages ecrits dans {a.out}")
    elif a.decode:
        mode_decode(a.decode)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
