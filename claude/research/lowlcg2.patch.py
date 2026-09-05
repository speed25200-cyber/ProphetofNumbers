"""Broaden lowlcg: more nibble positions, and the bonus-rank channel.

Two things the first version left out.

The nibble position. The observed bits sit at s bits shift..shift+3 where `shift` is
where the sampler reads its 32-bit word from. `j = u % 80` gives shift = the output
shift, but `j = (u >> 16) % 80` — the shr16mod style the seed sweep also tests — moves
it 16 higher. For java that is bits 32..35, i.e. L = 36, still inside the budget.

The channel. If the bonus is not the first ball but an extra pick sorted[u % 20], then
20 = 4*5 fixes only u mod 4: two bits per draw instead of four, at bits shift..shift+1.
Fewer bits per draw, but a narrower unknown (L = shift+2) and more draws available.
"""
import re

src = open("lowlcg.c").read()

src = src.replace(
    'typedef struct { const char *name; uint64_t a, c; int M, shift; } LCG;',
    'typedef struct { const char *name; uint64_t a, c; int M, shift; } LCG;\n'
    '/* NB is how many low bits each draw reveals: 4 for u %% 80, 2 for a rank via u %% 20. */\n'
    'static int NB = 4;\n'
    'static int CHANNEL = 0;   /* 0 = bonus is the first ball, 1 = bonus is sorted[u %% 20] */')

src = src.replace(
    '  {"java.util.Random",    25214903917ULL,          11ULL,                  48, 16},',
    '  {"java.util.Random",    25214903917ULL,          11ULL,                  48, 16},\n'
    '  {"java (u>>16 %% 80)",   25214903917ULL,          11ULL,                  48, 32},')
src = src.replace(
    '  {"MSVC",                214013ULL,               2531011ULL,             32, 16},',
    '  {"MSVC",                214013ULL,               2531011ULL,             32, 16},\n'
    '  {"MSVC (u>>4 %% 80)",    214013ULL,               2531011ULL,             32, 20},')

src = src.replace('int L = g->shift + 4;', 'int L = g->shift + NB;')
src = src.replace('uint64_t himask  = mask >> (sh + 4);', 'uint64_t himask  = mask >> (sh + NB);')
src = src.replace('uint64_t nib0 = (uint64_t)obs[0] << sh;', 'uint64_t nib0 = (uint64_t)obs[0] << sh;')
src = src.replace('uint64_t hipart = hi << (sh + 4);', 'uint64_t hipart = hi << (sh + NB);')
src = src.replace('if((int)((t >> sh) & 15) != obs[d]) break;',
                  'if((int)((t >> sh) & ((1<<NB)-1)) != obs[d]) break;')
src = src.replace('if((int)((s >> g->shift) & 15) != obs[d]) break;',
                  'if((int)((s >> g->shift) & ((1<<NB)-1)) != obs[d]) break;')
src = src.replace('for(int d = 0; d < 14; d++){ obs[d] = (int)((s >> g->shift) & 15); s = (A*s + C) & mask; }',
                  'for(int d = 0; d < 14; d++){ obs[d] = (int)((s >> g->shift) & ((1<<NB)-1)); s = (A*s + C) & mask; }')

# the observation: first ball (4 bits of bonus-1) or the rank of bonus (2 bits)
src = src.replace(
    'static inline int nib(int d, int first){ return (BONUS[first+d]-1) & 15; }',
    '''static int rank_of_bonus(int d, int first){
  for(int q = 0; q < 20; q++) if(NUMS[(size_t)(first+d)*20+q] == BONUS[first+d]) return q;
  return -1;
}
static inline int nib(int d, int first){
  if(CHANNEL == 0) return (BONUS[first+d]-1) & ((1<<NB)-1);
  int r = rank_of_bonus(d, first); return r < 0 ? 0 : (r & ((1<<NB)-1));
}''')

src = src.replace('  int maxW = argc > 2 ? atoi(argv[2]) : 48;',
'''  int maxW = argc > 2 ? atoi(argv[2]) : 48;
  for(int i = 1; i < argc; i++){
    if(!strcmp(argv[i], "rank")){ CHANNEL = 1; NB = 2; }
    if(!strcmp(argv[i], "first")){ CHANNEL = 0; NB = 4; }
  }
  printf("channel: %s, %d bits per draw\\n",
         CHANNEL ? "bonus = sorted[u %% 20]" : "bonus = first ball, j = u %% 80", NB);''')
src = src.replace('  int ndraws = 16;', '  int ndraws = (NB == 2) ? 34 : 16;')
src = src.replace('printf("  a wrong candidate survives with probability 16^-%d = 2^-%d\\n\\n", ndraws, 4*ndraws);',
                  'printf("  a wrong candidate survives with probability 2^-%d\\n\\n", NB*ndraws);')

open("lowlcg.c", "w").write(src)
print("lowlcg.c broadened: nibble width, extra shifts, bonus-rank channel")
