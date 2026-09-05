// gohunt — Go math/rand contre l'archive, avec le VRAI math/rand (pas une reimplementation).
//
// Go est courant dans les back-ends et son math/rand ensemence (rand.NewSource(seed)) est
// un Fibonacci retarde additif de 607 mots amorce par un LCG, avec une table « cooked »
// de 607 constantes : reimplementer expose a une erreur de table. On utilise donc la
// bibliotheque elle-meme.
//
// Seed() coute ~2000 operations, donc 2^32 est hors budget. Deux espaces motives :
//   (1) reensemencement par tirage sur l'horloge : seed = unix_utc du tirage (+/- 8 s),
//       ou l'identifiant, ou 0/1/42 — teste sur CHAQUE tirage de l'archive ;
//   (2) petite constante : seeds 0..2^26 sur le tirage 0.
// Quatre methodes : Perm(80)[:20], Shuffle, boucle Intn(80)+1 avec rejet des doublons,
// et boucle Intn(80)+1 sans rejet du generateur (rejet applicatif).
package main

import (
	"bufio"
	"encoding/binary"
	"fmt"
	"math/rand"
	"os"
	"sort"
)

var N uint32
var IDS, TS []uint32
var NUMS []uint8

func load(fn string) {
	f, err := os.Open(fn)
	if err != nil { panic(err) }
	defer f.Close()
	r := bufio.NewReader(f)
	binary.Read(r, binary.LittleEndian, &N)
	IDS = make([]uint32, N); TS = make([]uint32, N)
	lo := make([]uint64, N); hi := make([]uint64, N)
	NUMS = make([]uint8, 20*N)
	bo := make([]uint8, N); bn := make([]uint8, N)
	binary.Read(r, binary.LittleEndian, IDS)
	binary.Read(r, binary.LittleEndian, TS)
	binary.Read(r, binary.LittleEndian, lo)
	binary.Read(r, binary.LittleEndian, hi)
	binary.Read(r, binary.LittleEndian, NUMS)
	binary.Read(r, binary.LittleEndian, bo)
	binary.Read(r, binary.LittleEndian, bn)
}

func draw(d int) []uint8 { return NUMS[20*d : 20*d+20] }

func equal(a []int, row []uint8) bool {
	if len(a) != 20 { return false }
	b := make([]int, 20); copy(b, a); sort.Ints(b)
	for i := 0; i < 20; i++ { if uint8(b[i]) != row[i] { return false } }
	return true
}

// les quatre facons courantes d'ecrire « 20 parmi 80 » en Go
func method(r *rand.Rand, m int) []int {
	switch m {
	case 0: // Perm
		p := r.Perm(80)
		out := make([]int, 20)
		for i := 0; i < 20; i++ { out[i] = p[i] + 1 }
		return out
	case 1: // Shuffle
		a := make([]int, 80)
		for i := range a { a[i] = i + 1 }
		r.Shuffle(80, func(i, j int) { a[i], a[j] = a[j], a[i] })
		return a[:20]
	case 2: // Intn avec rejet des doublons
		seen := [81]bool{}
		out := make([]int, 0, 20)
		for len(out) < 20 {
			v := r.Intn(80) + 1
			if !seen[v] { seen[v] = true; out = append(out, v) }
		}
		return out
	default: // Int63n
		seen := [81]bool{}
		out := make([]int, 0, 20)
		for len(out) < 20 {
			v := int(r.Int63n(80)) + 1
			if !seen[v] { seen[v] = true; out = append(out, v) }
		}
		return out
	}
}

var MNAME = []string{"Perm", "Shuffle", "Intn+rejet", "Int63n+rejet"}

func main() {
	if len(os.Args) > 1 && os.Args[1] == "selftest" {
		// plante : graine connue, methode connue, 3 tirages ; puis on la retrouve
		fails := 0
		for m := 0; m < 4; m++ {
			const SEED = 987654321
			r := rand.New(rand.NewSource(SEED))
			var planted [3][]uint8
			for d := 0; d < 3; d++ {
				a := method(r, m)
				sort.Ints(a)
				row := make([]uint8, 20)
				for i := range a { row[i] = uint8(a[i]) }
				planted[d] = row
			}
			found := int64(-1)
			for s := int64(SEED - 500); s <= SEED+500; s++ {
				rr := rand.New(rand.NewSource(s))
				ok := true
				for d := 0; d < 3 && ok; d++ { if !equal(method(rr, m), planted[d]) { ok = false } }
				if ok { found = s; break }
			}
			st := "RECOVERED"
			if found != SEED { st = "FAIL"; fails++ }
			fmt.Printf("  %-13s : %s (graine %d)\n", MNAME[m], st, found)
		}
		// negatif : tirages equitables d'un AUTRE generateur ne doivent rien donner
		src := rand.New(rand.NewSource(1))
		worst := 0
		var rows [3][]uint8
		for d := 0; d < 3; d++ {
			p := src.Perm(80)[:20]; sort.Ints(p)
			row := make([]uint8, 20); for i := range p { row[i] = uint8(p[i] + 1) }
			rows[d] = row
		}
		// on decale les rows d'un tirage pour que la vraie graine 1 ne colle pas
		for m := 0; m < 4; m++ {
			for s := int64(2); s < 20000; s++ {
				rr := rand.New(rand.NewSource(s))
				k := 0
				for d := 0; d < 3; d++ { if equal(method(rr, m), rows[d]) { k++ } else { break } }
				if k > worst { worst = k }
			}
		}
		fmt.Printf("\n  controle negatif : 80 000 essais, meilleur %d/3  %s\n", worst,
			map[bool]string{true: "PASS", false: "FAIL"}[worst == 0])
		if fails == 0 && worst == 0 { fmt.Println("\n  controles: tous passes") } else { fmt.Println("\n  *** CONTROLES ECHOUES ***"); os.Exit(1) }
		return
	}
	load(os.Args[1])
	fmt.Printf("archive : %d tirages ; Go math/rand (le vrai), 4 methodes\n\n", N)
	skip1 := len(os.Args) > 3 && os.Args[3] == "skip1"

	// (1) reensemencement par tirage sur l'horloge ou l'identifiant, chaque tirage
	alarms := 0
	trials := 0
	if !skip1 { fmt.Println("(1) graine = horodatage du tirage (+/- 8 s), identifiant (+/- 2), 0, 1, 42, 1234") }
	for d := 0; d < int(N) && !skip1; d++ {
		row := draw(d)
		seeds := []int64{0, 1, 42, 1234, int64(IDS[d]), int64(IDS[d]) - 1, int64(IDS[d]) + 1, int64(IDS[d]) - 2, int64(IDS[d]) + 2}
		for k := -8; k <= 8; k++ { seeds = append(seeds, int64(TS[d])+int64(k)) }
		seeds = append(seeds, int64(TS[d])*1000, int64(TS[d])*1000000000)
		for _, s := range seeds {
			for m := 0; m < 4; m++ {
				r := rand.New(rand.NewSource(s))
				trials++
				if equal(method(r, m), row) {
					alarms++
					fmt.Printf("  ALARME tirage %d id=%d graine=%d methode=%s\n", d, IDS[d], s, MNAME[m])
				}
			}
		}
		if d%10000 == 0 && d > 0 { fmt.Printf("  ...%d/%d\n", d, N) }
	}
	if !skip1 { fmt.Printf("  essais %d ; un tirage reproduit vaut 2^-61,6 ; alarmes %d\n\n", trials, alarms) }

	// (2) petite constante, tirage 0
	limit := int64(1) << 26
	if len(os.Args) > 2 { fmt.Sscan(os.Args[2], &limit) }
	fmt.Printf("(2) graine = constante 0..%d, tirage 0, 4 methodes\n", limit)
	row0 := draw(0)
	a2 := 0
	for s := int64(0); s < limit; s++ {
		for m := 0; m < 4; m++ {
			r := rand.New(rand.NewSource(s))
			if equal(method(r, m), row0) { a2++; fmt.Printf("  ALARME graine=%d methode=%s\n", s, MNAME[m]) }
		}
		if s%(1<<22) == 0 && s > 0 { fmt.Printf("  ...%d\n", s) }
	}
	fmt.Printf("  alarmes %d\n\nTOTAL alarmes : %d\n", a2, alarms+a2)
}
