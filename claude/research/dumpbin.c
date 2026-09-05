/* dumpbin — print what the C tools actually read out of draws.bin.
 *
 * Every negative result on the real archive is "the tool found no consistent model".
 * The one way that could be a systematic false negative is if the tools were reading
 * garbage: a misaligned draws.bin would make every hypothesis inconsistent for a
 * reason that has nothing to do with the generator. This prints the same fields the
 * attacks use, to be diffed against the source CSV.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
int main(int argc,char**argv){
  const char*p = argc>1?argv[1]:"draws.bin";
  int first = argc>2?atoi(argv[2]):0, n = argc>3?atoi(argv[3]):3;
  FILE*f=fopen(p,"rb"); uint32_t N;
  if(!f||fread(&N,4,1,f)!=1){perror(p);return 1;}
  uint32_t*ids=malloc(4*N),*ts=malloc(4*N);
  uint64_t*lo=malloc(8*N),*hi=malloc(8*N);
  uint8_t*nums=malloc(20*N),*bo=malloc(N),*bn=malloc(N);
  if(fread(ids,4,N,f)!=N||fread(ts,4,N,f)!=N||fread(lo,8,N,f)!=N||fread(hi,8,N,f)!=N||
     fread(nums,20,N,f)!=N||fread(bo,1,N,f)!=N||fread(bn,1,N,f)!=N){fprintf(stderr,"short read\n");return 1;}
  fclose(f);
  printf("N=%u\n",N);
  for(int d=first; d<first+n && d<(int)N; d++){
    printf("id=%u ts=%u nums=",ids[d],ts[d]);
    for(int j=0;j<20;j++) printf("%d%s",nums[(size_t)d*20+j], j<19?",":"");
    /* the bitmask the attacks actually test against, decoded back */
    printf(" boost=%d bonus=%d mask=",bo[d],bn[d]);
    int cnt=0;
    for(int v=1;v<=80;v++){ int in = v<65 ? (int)((lo[d]>>(v-1))&1ULL) : (int)((hi[d]>>(v-65))&1ULL);
      if(in){ printf("%d%s",v,cnt<19?",":""); cnt++; } }
    printf(" (popcount=%d)\n",cnt);
  }
  return 0;
}
