#define _POSIX_C_SOURCE 200809L

/* keno_break — algebraic recovery of an MT19937 state from ORDERED keno draws (20 of 80).
 *
 *   ./keno_break demo <draws> <seed> <skip> <sampler> <mapping> [stride]
 *                    [--state-out <path>] [--predict <count>]
 *   ./keno_break file <path> <sampler> <mapping> [stride]
 *                    [--state-out <path>] [--predict <count>]
 *   ./keno_break scanfile <path> [min_stride] [max_stride]
 *                    [--state-out <path>] [--predict <count>]
 *   ./keno_break predict <state-path> [count]
 *
 * <path> holds one draw per line, 20 numbers in DRAW order (not sorted).
 *
 * samplers  0 fisher-yates forward   1 fisher-yates backward   2 floyd
 * mappings  0 mulhi (u*k)>>32        1 u%k                     2 (u>>16)%k
 *
 * Every mapping leaks F2-linear bits of the 32-bit output u:
 *   mulhi  -> the common leading bits of the interval u must lie in   (~4.5 bits)
 *   u%k    -> 80 = 16*5, so u mod 16 = j mod 16, i.e. bits 0..3       (4 bits)
 *   u>>16  -> bits 16..19                                            (4 bits)
 * MT19937 is F2-linear, so those bits are linear forms over the 19968 state bits
 * and Gaussian elimination over GF(2) finishes the job. ``stride`` is the fixed
 * number of outputs consumed per draw; outputs after the first 20 are latent.
 *
 * Exit status: 0 recovered, 2 rejected, 3 input is sorted, 4 inconclusive rank.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <inttypes.h>
#include <sys/stat.h>
#include <unistd.h>
#define NB 19968
#define NW (NB/64)
#define MT_RANK 19937
#define UNKNOWN_INDEX UINT32_MAX
#define MATRIX_A 0x9908b0dfU
#define MAX_STRIDE 4096
#define MAX_PREDICTIONS 10000

typedef struct{uint32_t mt[624];int mti;}MT;
typedef struct{
  MT state;
  int sampler,mapping,stride,draws_consumed,holdout;
  uint64_t input_hash;
}Checkpoint;

#define STATE_MAGIC "KENO_BREAK_MT19937"
#define STATE_VERSION 1U

static void mt_seed(MT*S,uint32_t s){S->mt[0]=s;for(int i=1;i<624;i++)S->mt[i]=1812433253U*(S->mt[i-1]^(S->mt[i-1]>>30))+i;S->mti=624;}
static void mt_twist(MT*S){uint32_t y;int k;
  for(k=0;k<227;k++){y=(S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU);S->mt[k]=S->mt[k+397]^(y>>1)^((y&1)?MATRIX_A:0);}
  for(;k<623;k++){y=(S->mt[k]&0x80000000U)|(S->mt[k+1]&0x7fffffffU);S->mt[k]=S->mt[k-227]^(y>>1)^((y&1)?MATRIX_A:0);}
  y=(S->mt[623]&0x80000000U)|(S->mt[0]&0x7fffffffU);S->mt[623]=S->mt[396]^(y>>1)^((y&1)?MATRIX_A:0);S->mti=0;}
static uint32_t mt_next(MT*S){ if(S->mti>=624)mt_twist(S);
  uint32_t y=S->mt[S->mti++];y^=y>>11;y^=(y<<7)&0x9d2c5680U;y^=(y<<15)&0xefc60000U;y^=y>>18;return y;}

/* ---------- index mapping ---------- */
static inline uint32_t mapk(int m,uint32_t u,uint32_t k){
  if(m==0) return (uint32_t)(((uint64_t)u*k)>>32);
  if(m==1) return u%k;
  return (u>>16)%k;
}
/* known F2-linear bits of u given the index j and the range k.
   Fills bitpos[]/bitval[], returns how many. */
static int known_bits(int m,uint32_t j,uint32_t k,int*bitpos,int*bitval){
  int n=0;
  if(m==0){
    uint64_t lo=((uint64_t)j<<32)/k + ((((uint64_t)j<<32)%k)?1:0);
    uint64_t hi=(((uint64_t)j+1)<<32)/k + (((((uint64_t)j+1)<<32)%k)?1:0);
    hi-=1;
    uint32_t x=(uint32_t)(lo^hi);
    int nb = x ? __builtin_clz(x) : 32;          /* leading bits that agree */
    for(int b=31;b>=32-nb;b--){bitpos[n]=b;bitval[n]=(lo>>b)&1;n++;}
    return n;
  }
  /* u = j (mod k) also fixes u mod 2^a where a = v2(k), i.e. a low bits of u.
     Over k = 80..61 that is 22 linear bits per draw (k=64 alone gives 6). */
  int a=__builtin_ctz(k); if(a>16)a=16; if(!a) return 0;
  int base = (m==1)?0:16;
  uint32_t r = j & ((1u<<a)-1);
  for(int b=0;b<a;b++){bitpos[n]=base+b;bitval[n]=(r>>b)&1;n++;}
  return n;
}
/* ---------- samplers: value sequence <-> index sequence ---------- */
/* forward: returns the 20 raw indices r_i in [0,80-i) */
static int invert_sampler(int s,const int*v,uint32_t*r){
  uint8_t a[81]; for(int i=0;i<80;i++)a[i]=i+1;
  if(s==0){
    for(int i=0;i<20;i++){int j=-1; for(int q=i;q<80;q++) if(a[q]==v[i]){j=q;break;}
      if(j<0)return 0;
      r[i]=j-i; uint8_t t=a[i];a[i]=a[j];a[j]=t;}
    return 1;
  }
  if(s==1){
    for(int i=79,c=0;i>=60;i--,c++){int j=-1; for(int q=0;q<=i;q++) if(a[q]==v[c]){j=q;break;}
      if(j<0)return 0;
      r[c]=j; uint8_t t=a[i];a[i]=a[j];a[j]=t;}
    return 1;
  }
  /* floyd: for j=61..80, t=rnd(j)+1 ; value = t if unseen else j */
  int seen[81]={0};
  for(int c=0,jj=61;jj<=80;jj++,c++){
    int val=v[c];
    if(val<1||val>jj||seen[val])return 0;
    /* val==jj is ambiguous: t may be jj or any previously selected value.
       It still consumes one output, but contributes no safe linear equation. */
    r[c]=(val==jj)?UNKNOWN_INDEX:(uint32_t)(val-1);
    seen[val]=1;
  }
  return 1;
}
static void run_sampler(int s,int m,MT*G,int*out){
  uint8_t a[81]; for(int i=0;i<80;i++)a[i]=i+1;
  if(s==0){for(int i=0;i<20;i++){uint32_t j=i+mapk(m,mt_next(G),80-i);uint8_t t=a[i];a[i]=a[j];a[j]=t;out[i]=a[i];}return;}
  if(s==1){for(int i=79,c=0;i>=60;i--,c++){uint32_t j=mapk(m,mt_next(G),i+1);uint8_t t=a[i];a[i]=a[j];a[j]=t;out[c]=a[i];}return;}
  int seen[81]={0};
  for(int c=0,jj=61;jj<=80;jj++,c++){uint32_t t=mapk(m,mt_next(G),jj)+1;
    int val = seen[t]? jj : (int)t; seen[val]=1; out[c]=val;}
}
static uint32_t range_at(int s,int i){ if(s==0)return 80-i; if(s==1)return 80-i; return 61+i; }

/* ---------- versioned recovery checkpoint ---------- */
static uint64_t fnv_byte(uint64_t h,uint8_t value){return (h^value)*UINT64_C(1099511628211);}
static uint64_t fnv_u32(uint64_t h,uint32_t value){
  for(int shift=0;shift<32;shift+=8)h=fnv_byte(h,(uint8_t)(value>>shift));
  return h;
}
static uint64_t fnv_u64(uint64_t h,uint64_t value){
  for(int shift=0;shift<64;shift+=8)h=fnv_byte(h,(uint8_t)(value>>shift));
  return h;
}
/* FNV-1a binds a checkpoint to its ordered input and detects accidental file
   corruption.  It is deliberately not presented as a cryptographic proof. */
static uint64_t hash_draws(const int (*draws)[20],int count){
  uint64_t h=UINT64_C(14695981039346656037);
  h=fnv_u32(h,(uint32_t)count);
  for(int d=0;d<count;d++)for(int i=0;i<20;i++)h=fnv_u32(h,(uint32_t)draws[d][i]);
  return h;
}
static uint64_t checkpoint_checksum(const Checkpoint*C){
  uint64_t h=UINT64_C(14695981039346656037);
  const unsigned char*p=(const unsigned char*)STATE_MAGIC;
  while(*p)h=fnv_byte(h,*p++);
  h=fnv_u32(h,STATE_VERSION);
  h=fnv_u32(h,(uint32_t)C->sampler); h=fnv_u32(h,(uint32_t)C->mapping);
  h=fnv_u32(h,(uint32_t)C->stride); h=fnv_u32(h,(uint32_t)C->draws_consumed);
  h=fnv_u32(h,(uint32_t)C->holdout); h=fnv_u64(h,C->input_hash);
  h=fnv_u32(h,(uint32_t)C->state.mti);
  for(int i=0;i<624;i++)h=fnv_u32(h,C->state.mt[i]);
  return h;
}
static int parse_int_arg(const char*text,int minimum,int maximum,int*out);
static int read_labeled_token(FILE*f,const char*label,char*value){
  char key[64];
  return fscanf(f,"%63s %63s",key,value)==2&&!strcmp(key,label);
}
static int parse_fixed_hex(const char*text,size_t digits,uint64_t*out){
  if(strlen(text)!=digits)return 0;
  for(size_t i=0;i<digits;i++)if(!isxdigit((unsigned char)text[i]))return 0;
  errno=0; char*end=NULL; unsigned long long value=strtoull(text,&end,16);
  if(errno==ERANGE||end==text||*end)return 0;
  *out=(uint64_t)value; return 1;
}
static int write_checkpoint(const char*path,const Checkpoint*C){
  size_t path_length=strlen(path);
  char*temporary=malloc(path_length+12); if(!temporary){fprintf(stderr,"failed to allocate checkpoint path\n");return 0;}
  memcpy(temporary,path,path_length); memcpy(temporary+path_length,".tmp.XXXXXX",12);
  int descriptor=mkstemp(temporary);
  if(descriptor<0){perror(temporary);free(temporary);return 0;}
  FILE*f=fdopen(descriptor,"w");
  if(!f){perror(temporary);close(descriptor);remove(temporary);free(temporary);return 0;}
  uint64_t checksum=checkpoint_checksum(C); int failed=0;
  if(fprintf(f,"%s %u\n",STATE_MAGIC,STATE_VERSION)<0)failed=1;
  if(fprintf(f,"sampler %d\nmapping %d\nstride %d\n",C->sampler,C->mapping,C->stride)<0)failed=1;
  if(fprintf(f,"draws_consumed %d\nholdout %d\n",C->draws_consumed,C->holdout)<0)failed=1;
  if(fprintf(f,"input_fnv1a64 %016" PRIx64 "\nmti %d\nwords 624\n",C->input_hash,C->state.mti)<0)failed=1;
  for(int i=0;i<624;i++)if(fprintf(f,"%08" PRIx32 "%c",C->state.mt[i],i%8==7?'\n':' ')<0)failed=1;
  if(fprintf(f,"checksum_fnv1a64 %016" PRIx64 "\nend\n",checksum)<0)failed=1;
  if(!failed&&fflush(f)!=0)failed=1;
  if(!failed&&fsync(descriptor)!=0)failed=1;
  if(fclose(f)!=0)failed=1;
  if(failed){fprintf(stderr,"%s: failed to write complete checkpoint\n",temporary);remove(temporary);free(temporary);return 0;}
  if(rename(temporary,path)!=0){perror(path);remove(temporary);free(temporary);return 0;}
  free(temporary);
  printf("checkpoint written: %s (next draw after %d known draws)\n",path,C->draws_consumed);
  return 1;
}
static int read_checkpoint(const char*path,Checkpoint*C){
  FILE*f=fopen(path,"r"); if(!f){perror(path);return 0;}
  Checkpoint tmp; memset(&tmp,0,sizeof tmp);
  char magic[64],value[64],end[64],extra[2]; int version=0,words=0; uint64_t parsed=0,stored_checksum=0;
  int byte=0; while((byte=fgetc(f))!=EOF)if(byte==0)goto invalid;
  if(ferror(f))goto invalid;
  rewind(f);
  if(fscanf(f,"%63s %63s",magic,value)!=2||strcmp(magic,STATE_MAGIC)||
     !parse_int_arg(value,(int)STATE_VERSION,(int)STATE_VERSION,&version))goto invalid;
  if(!read_labeled_token(f,"sampler",value)||!parse_int_arg(value,0,2,&tmp.sampler))goto invalid;
  if(!read_labeled_token(f,"mapping",value)||!parse_int_arg(value,0,2,&tmp.mapping))goto invalid;
  if(!read_labeled_token(f,"stride",value)||!parse_int_arg(value,20,MAX_STRIDE,&tmp.stride))goto invalid;
  if(!read_labeled_token(f,"draws_consumed",value)||!parse_int_arg(value,1,INT_MAX,&tmp.draws_consumed))goto invalid;
  if(!read_labeled_token(f,"holdout",value)||!parse_int_arg(value,1,tmp.draws_consumed,&tmp.holdout))goto invalid;
  if(!read_labeled_token(f,"input_fnv1a64",value)||!parse_fixed_hex(value,16,&tmp.input_hash))goto invalid;
  if(!read_labeled_token(f,"mti",value)||!parse_int_arg(value,0,624,&tmp.state.mti))goto invalid;
  if(!read_labeled_token(f,"words",value)||!parse_int_arg(value,624,624,&words))goto invalid;
  uint32_t state_or=0;
  for(int i=0;i<624;i++){
    if(fscanf(f,"%63s",value)!=1||!parse_fixed_hex(value,8,&parsed)||parsed>UINT32_MAX)goto invalid;
    tmp.state.mt[i]=(uint32_t)parsed; state_or|=tmp.state.mt[i];
  }
  if(!read_labeled_token(f,"checksum_fnv1a64",value)||!parse_fixed_hex(value,16,&stored_checksum))goto invalid;
  if(fscanf(f,"%63s",end)!=1||strcmp(end,"end")||fscanf(f,"%1s",extra)==1)goto invalid;
  if(!state_or||stored_checksum!=checkpoint_checksum(&tmp))goto invalid;
  fclose(f); *C=tmp; return 1;
invalid:
  fclose(f); fprintf(stderr,"%s: invalid or corrupted %s v%u checkpoint\n",path,STATE_MAGIC,STATE_VERSION); return 0;
}
static void print_predictions(const Checkpoint*C,int count){
  MT G=C->state; int ordered[20],sorted[20];
  printf("checkpoint model: sampler %d, mapping %d, stride %d, after %d draws, holdout %d\n",
      C->sampler,C->mapping,C->stride,C->draws_consumed,C->holdout);
  for(int d=0;d<count;d++){
    run_sampler(C->sampler,C->mapping,&G,ordered);
    for(int i=20;i<C->stride;i++)mt_next(&G);
    memcpy(sorted,ordered,sizeof sorted);
    for(int i=0;i<20;i++)for(int j=i+1;j<20;j++)if(sorted[j]<sorted[i]){int t=sorted[i];sorted[i]=sorted[j];sorted[j]=t;}
    printf("prediction %d ordered:",d+1); for(int i=0;i<20;i++)printf(" %d",ordered[i]); printf("\n");
    printf("prediction %d sorted:",d+1); for(int i=0;i<20;i++)printf(" %d",sorted[i]); printf("\n");
  }
}

typedef struct{const char*state_out;int predict_count;}OutputOptions;
static int parse_int_arg(const char*text,int minimum,int maximum,int*out){
  errno=0; char*end=NULL; long value=strtol(text,&end,10);
  if(errno==ERANGE||end==text||*end||value<minimum||value>maximum)return 0;
  *out=(int)value; return 1;
}
static int parse_u32_arg(const char*text,uint32_t*out){
  errno=0; char*end=NULL; unsigned long long value=strtoull(text,&end,0);
  if(errno==ERANGE||end==text||*end||value>UINT32_MAX)return 0;
  *out=(uint32_t)value; return 1;
}
static int parse_output_options(int argc,char**argv,int start,OutputOptions*options){
  int seen_predict=0;
  for(int i=start;i<argc;i++){
    if(!strcmp(argv[i],"--state-out")){
      if(options->state_out||i+1>=argc){fprintf(stderr,"--state-out requires one path and may appear once\n");return 0;}
      options->state_out=argv[++i];
    }else if(!strcmp(argv[i],"--predict")){
      if(seen_predict||i+1>=argc||!parse_int_arg(argv[i+1],1,MAX_PREDICTIONS,&options->predict_count)){
        fprintf(stderr,"--predict requires one count in 1..%d and may appear once\n",MAX_PREDICTIONS);return 0;
      }
      seen_predict=1; i++;
    }else{
      fprintf(stderr,"unknown option: %s\n",argv[i]); return 0;
    }
  }
  return 1;
}
static int publish_recovery(const OutputOptions*options,const MT*state,int sampler,int mapping,int stride,
    int (*draws)[20],int draws_consumed,int holdout){
  Checkpoint checkpoint; memset(&checkpoint,0,sizeof checkpoint);
  checkpoint.state=*state; checkpoint.sampler=sampler; checkpoint.mapping=mapping; checkpoint.stride=stride;
  checkpoint.draws_consumed=draws_consumed; checkpoint.holdout=holdout;
  checkpoint.input_hash=hash_draws((const int (*)[20])draws,draws_consumed);
  if(options->state_out&&!write_checkpoint(options->state_out,&checkpoint))return 0;
  if(options->predict_count)print_predictions(&checkpoint,options->predict_count);
  return 1;
}
static void report_output_refused(const OutputOptions*options){
  if(options->state_out||options->predict_count)
    fprintf(stderr,"checkpoint export/prediction refused: recovery is not uniquely validated\n");
}
static int same_existing_file(const char*left,const char*right){
  struct stat a,b;
  return stat(left,&a)==0&&stat(right,&b)==0&&a.st_dev==b.st_dev&&a.st_ino==b.st_ino;
}

/* ---------- symbolic MT ---------- */
static uint64_t *SS;
#define SB(i,b) (SS+(((size_t)(i)*32+(b))*NW))
static inline void rxor(uint64_t*d,const uint64_t*s){for(int w=0;w<NW;w++)d[w]^=s[w];}
static inline void rcpy(uint64_t*d,const uint64_t*s){memcpy(d,s,NW*8);}
static void sym_twist(void){
  static uint64_t nw_[32][NW];
  for(int k=0;k<624;k++){int k1=(k+1)%624,kf=(k+397)%624;
    for(int b=0;b<32;b++){ rcpy(nw_[b],SB(kf,b));
      if(b<=30){int yb=b+1; const uint64_t*src=(yb==31)?SB(k,31):SB(k1,yb); rxor(nw_[b],src);}
      if((MATRIX_A>>b)&1) rxor(nw_[b],SB(k1,0)); }
    for(int b=0;b<32;b++) rcpy(SB(k,b),nw_[b]); }
}
static uint64_t TEMPO[32][NW];
static void sym_temper(int idx){
  static uint64_t y[32][NW],t[32][NW];
  for(int b=0;b<32;b++) rcpy(y[b],SB(idx,b));
  for(int b=0;b<32;b++){rcpy(t[b],y[b]); if(b+11<32) rxor(t[b],y[b+11]);}
  for(int b=0;b<32;b++) rcpy(y[b],t[b]);
  for(int b=0;b<32;b++){rcpy(t[b],y[b]); if(b-7>=0&&((0x9d2c5680U>>b)&1)) rxor(t[b],y[b-7]);}
  for(int b=0;b<32;b++) rcpy(y[b],t[b]);
  for(int b=0;b<32;b++){rcpy(t[b],y[b]); if(b-15>=0&&((0xefc60000U>>b)&1)) rxor(t[b],y[b-15]);}
  for(int b=0;b<32;b++) rcpy(y[b],t[b]);
  for(int b=0;b<32;b++){rcpy(t[b],y[b]); if(b+18<32) rxor(t[b],y[b+18]);}
  for(int b=0;b<32;b++) rcpy(TEMPO[b],t[b]);
}
/* ---------- GF(2) elimination ---------- */
static uint64_t **PIV; static uint8_t *PRHS; static int NPIV,CONTRA;
static void insert_eq(uint64_t*row,int rhs){
  for(int w=0;w<NW;w++){
    while(row[w]){ int p=w*64+__builtin_ctzll(row[w]);
      if(PIV[p]){ for(int q=w;q<NW;q++) row[q]^=PIV[p][q]; rhs^=PRHS[p]; }
      else { PIV[p]=malloc(NW*8); memcpy(PIV[p],row,NW*8); PRHS[p]=rhs; NPIV++; return; } } }
  if(rhs) CONTRA++;
}
static void reset_basis(void){ for(int p=0;p<NB;p++) if(PIV[p]){free(PIV[p]);PIV[p]=NULL;} NPIV=0;CONTRA=0; }

enum result { REJECTED=0, INCONCLUSIVE=1, RECOVERED=2 };

/* Attempt one exact fixed-layout hypothesis.  On RECOVERED, next_state is
   positioned immediately before the first output of the next draw. */
static enum result attempt(int s,int m,int stride,int D,uint32_t (*R)[20],int (*draws)[20],int nchk,int verbose,MT*next_state){
  reset_basis();
  memset(SS,0,(size_t)624*32*NW*8);
  for(int i=0;i<624;i++)for(int b=0;b<32;b++){int p=i*32+b; SB(i,b)[p/64]|=1ULL<<(p%64);}
  uint64_t row[NW]; int pos=624, eqs=0;
  int bitpos[32],bitval[32];
  for(int d=0;d<D && !CONTRA;d++){
    for(int i=0;i<stride && !CONTRA;i++){
      if(pos>=624){sym_twist();pos=0;}
      if(i<20 && R[d][i]!=UNKNOWN_INDEX){
        int nb=known_bits(m,R[d][i],range_at(s,i),bitpos,bitval);
        if(nb){ sym_temper(pos);
          for(int q=0;q<nb;q++){ memcpy(row,TEMPO[bitpos[q]],NW*8); insert_eq(row,bitval[q]); eqs++; } }
      }
      pos++;
    }
  }
  if(CONTRA){
    if(verbose)printf("    sampler %d mapping %d stride %d : REJECTED (rank %d, %d eqs, %d contradiction)\n",s,m,stride,NPIV,eqs,CONTRA);
    return REJECTED;
  }
  if(NPIV<MT_RANK){
    if(verbose)printf("    sampler %d mapping %d stride %d : INCONCLUSIVE (rank %d/%d, %d eqs)\n",s,m,stride,NPIV,MT_RANK,eqs);
    return INCONCLUSIVE;
  }
  uint64_t x[NW]; memset(x,0,NW*8);
  for(int p=NB-1;p>=0;p--){ if(!PIV[p])continue;
    uint64_t acc=0; for(int w=0;w<NW;w++) acc^=PIV[p][w]&x[w];
    if(PRHS[p]^__builtin_parityll(acc)) x[p/64]|=1ULL<<(p%64); }
  MT G; for(int i=0;i<624;i++){uint32_t v=0;for(int b=0;b<32;b++) if((x[(i*32+b)/64]>>((i*32+b)%64))&1) v|=1u<<b; G.mt[i]=v;} G.mti=624;
  int okobs=0,okfut=0,o[20];
  for(int d=0;d<D+nchk;d++){ run_sampler(s,m,&G,o); int mt2=1;
    for(int i=0;i<20;i++) if(o[i]!=draws[d][i]) mt2=0;
    if(d<D) okobs+=mt2; else okfut+=mt2;
    for(int i=20;i<stride;i++) mt_next(&G);
  }
  if(verbose) printf("    sampler %d mapping %d stride %d : rank %d/%d, %d eqs -> replayed %d/%d, holdout %d/%d\n",
      s,m,stride,NPIV,MT_RANK,eqs,okobs,D,okfut,nchk);
  if(okobs!=D || (nchk>0 && okfut!=nchk)) return REJECTED;
  /* Full rank and replay are not a prospective validation.  Never announce a
     recovery from a file that contains no untouched holdout. */
  if(nchk<=0)return INCONCLUSIVE;
  if(next_state)*next_state=G;
  return RECOVERED;
}

int main(int argc,char**argv){
  const char*mode = argc>1?argv[1]:"demo";
  if(strcmp(mode,"demo")&&strcmp(mode,"file")&&strcmp(mode,"scanfile")&&strcmp(mode,"predict")){
    fprintf(stderr,"mode must be demo, file, scanfile, or predict\n"); return 1;
  }
  if(!strcmp(mode,"predict")){
    int count=1; Checkpoint checkpoint;
    if(argc<3||argc>4||(argc==4&&!parse_int_arg(argv[3],1,MAX_PREDICTIONS,&count))){
      fprintf(stderr,"usage: %s predict <state-path> [count]\n",argv[0]); return 1;
    }
    if(!read_checkpoint(argv[2],&checkpoint))return 1;
    print_predictions(&checkpoint,count); return 0;
  }
  SS=calloc((size_t)624*32*NW,8); PIV=calloc(NB,sizeof(uint64_t*)); PRHS=calloc(NB,1);
  if(!SS||!PIV||!PRHS){fprintf(stderr,"failed to allocate solver state\n");return 1;}
  if(!strcmp(mode,"demo")){
    int D=400,skip=0,s=0,m=0,stride=20,argi=2; uint32_t seed=0xC0FFEE42U;
    if(argi<argc&&strncmp(argv[argi],"--",2)){if(!parse_int_arg(argv[argi],1,INT_MAX-50,&D)){fprintf(stderr,"invalid demo draws\n");return 1;}argi++;}
    if(argi<argc&&strncmp(argv[argi],"--",2)){if(!parse_u32_arg(argv[argi],&seed)){fprintf(stderr,"invalid demo seed\n");return 1;}argi++;}
    if(argi<argc&&strncmp(argv[argi],"--",2)){if(!parse_int_arg(argv[argi],0,INT_MAX,&skip)){fprintf(stderr,"invalid demo skip\n");return 1;}argi++;}
    if(argi<argc&&strncmp(argv[argi],"--",2)){if(!parse_int_arg(argv[argi],0,2,&s)){fprintf(stderr,"invalid demo sampler\n");return 1;}argi++;}
    if(argi<argc&&strncmp(argv[argi],"--",2)){if(!parse_int_arg(argv[argi],0,2,&m)){fprintf(stderr,"invalid demo mapping\n");return 1;}argi++;}
    if(argi<argc&&strncmp(argv[argi],"--",2)){if(!parse_int_arg(argv[argi],20,MAX_STRIDE,&stride)){fprintf(stderr,"invalid demo stride\n");return 1;}argi++;}
    OutputOptions options={0};
    if(!parse_output_options(argc,argv,argi,&options))return 1;
    printf("demo: %d ordered draws, hidden seed 0x%08X, skip %d, sampler %d, mapping %d, stride %d\n",D,seed,skip,s,m,stride);
    MT G; mt_seed(&G,seed); for(int i=0;i<skip;i++)mt_next(&G);
    int (*draws)[20]=malloc(sizeof(int)*20*(D+50));
    uint32_t (*R)[20]=malloc(sizeof(uint32_t)*20*D);
    if(!draws||!R){fprintf(stderr,"failed to allocate demo data\n");return 1;}
    for(int d=0;d<D+50;d++){ run_sampler(s,m,&G,draws[d]);
      if(d<D && !invert_sampler(s,draws[d],R[d])){printf("  sampler %d not invertible on draw %d\n",s,d);return 1;}
      for(int i=20;i<stride;i++)mt_next(&G);
    }
    clock_t c0=clock();
    MT recovered_state;
    enum result result=attempt(s,m,stride,D,R,draws,50,1,&recovered_state);
    const char*label=result==RECOVERED?"*** RECOVERED: holdout predicted exactly ***":result==INCONCLUSIVE?"INCONCLUSIVE":"REJECTED";
    printf("  %s   [%.1fs]\n",label,
           (double)(clock()-c0)/CLOCKS_PER_SEC);
    if(result==RECOVERED){
      if(!publish_recovery(&options,&recovered_state,s,m,stride,draws,D+50,50))return 1;
    }else report_output_refused(&options);
    return result==RECOVERED?0:result==INCONCLUSIVE?4:2;
  }
  /* file / scanfile: one draw per line, 20 numbers in DRAW order */
  const char*path = argc>2?argv[2]:"ordered.txt";
  int lo_s=0,hi_s=3,lo_m=0,hi_m=3,min_stride=20,max_stride=20,argi=3;
  OutputOptions options={0};
  if(!strcmp(mode,"file")){
    int value=0;
    if(argi<argc&&strncmp(argv[argi],"--",2)){
      if(!parse_int_arg(argv[argi++],0,2,&value)){fprintf(stderr,"invalid sampler\n");return 1;}
      lo_s=value; hi_s=value+1;
    }else{lo_s=0;hi_s=1;}
    if(argi<argc&&strncmp(argv[argi],"--",2)){
      if(!parse_int_arg(argv[argi++],0,2,&value)){fprintf(stderr,"invalid mapping\n");return 1;}
      lo_m=value; hi_m=value+1;
    }else{lo_m=0;hi_m=1;}
    if(argi<argc&&strncmp(argv[argi],"--",2)){
      if(!parse_int_arg(argv[argi++],20,MAX_STRIDE,&min_stride)){fprintf(stderr,"invalid stride\n");return 1;}
      max_stride=min_stride;
    }
  }else{
    if(argi<argc&&strncmp(argv[argi],"--",2)){
      if(!parse_int_arg(argv[argi++],20,MAX_STRIDE,&min_stride)){fprintf(stderr,"invalid minimum stride\n");return 1;}
      max_stride=min_stride;
    }
    if(argi<argc&&strncmp(argv[argi],"--",2)){
      if(!parse_int_arg(argv[argi++],min_stride,MAX_STRIDE,&max_stride)){fprintf(stderr,"invalid maximum stride\n");return 1;}
    }
  }
  if(!parse_output_options(argc,argv,argi,&options))return 1;
  if(options.state_out&&(!strcmp(path,options.state_out)||same_existing_file(path,options.state_out))){
    fprintf(stderr,"checkpoint path must differ from the ordered-draw input\n");return 1;
  }
  FILE*f=fopen(path,"r"); if(!f){perror(path);return 1;}
  int cap=4096,D=0,line_number=0; int (*draws)[20]=malloc(sizeof(int)*20*cap);
  char line[512];
  while(fgets(line,sizeof line,f)){
    line_number++;
    int v[20],n=0; char*p=line;
    while(isspace((unsigned char)*p))p++;
    if(!*p||*p=='#')continue;
    while(*p&&*p!='#'){
      while(isspace((unsigned char)*p))p++;
      if(!*p||*p=='#')break;
      if(n>=20){fprintf(stderr,"%s:%d: expected exactly 20 integers\n",path,line_number);fclose(f);return 1;}
      errno=0; char*end=NULL; long value=strtol(p,&end,10);
      if(end==p||errno==ERANGE||value<INT_MIN||value>INT_MAX){
        fprintf(stderr,"%s:%d: invalid integer token\n",path,line_number);fclose(f);return 1;
      }
      v[n++]=(int)value; p=end;
      if(*p&&!isspace((unsigned char)*p)&&*p!='#'){
        fprintf(stderr,"%s:%d: invalid trailing token\n",path,line_number);fclose(f);return 1;
      }
    }
    if(n!=20){fprintf(stderr,"%s:%d: expected exactly 20 integers, got %d\n",path,line_number,n);fclose(f);return 1;}
    int seen[81]={0};
    for(int i=0;i<20;i++) if(v[i]<1||v[i]>80||seen[v[i]]++){
      fprintf(stderr,"%s:%d: expected 20 unique values in 1..80\n",path,line_number); fclose(f); return 1;
    }
    if(D>=cap){cap*=2;draws=realloc(draws,sizeof(int)*20*cap);}
    memcpy(draws[D++],v,sizeof v);
  }
  fclose(f);
  printf("%s: %d ordered draws read\n",path,D);
  if(!D){fprintf(stderr,"no complete draws\n");return 1;}
  if(D<300) printf("  WARNING: %d draws; MT19937 needs ~300 (19937 bits / ~90 usable bits per draw)\n",D);
  /* sanity: is the feed really ordered, or already sorted? */
  int sortedcount=0,reversecount=0,rankhist[20]={0};
  for(int d=0;d<D;d++){ int srt[20]; memcpy(srt,draws[d],sizeof srt);
    for(int a=0;a<20;a++)for(int b=a+1;b<20;b++) if(srt[b]<srt[a]){int t=srt[a];srt[a]=srt[b];srt[b]=t;}
    int issorted=1; for(int i=0;i<20;i++) if(srt[i]!=draws[d][i]) issorted=0;
    int isreverse=1; for(int i=0;i<20;i++) if(srt[19-i]!=draws[d][i]) isreverse=0;
    sortedcount+=issorted; reversecount+=isreverse;
    for(int i=0;i<20;i++) if(srt[i]==draws[d][0]){rankhist[i]++;break;} }
  printf("  already-sorted lines: %d/%d  (%.1f%%; a real draw order gives ~0%%)\n",sortedcount,D,100.0*sortedcount/D);
  printf("  rank of the first drawn ball inside the sorted set:");
  for(int i=0;i<20;i++)printf(" %d",rankhist[i]);
  printf("\n");
  if(sortedcount>D/2||reversecount>D/2){ printf("  -> the feed publishes a deterministic sort; the order attack cannot run.\n"); return 3; }
  int nchk = D>450 ? 50 : (D>350 ? 25 : 0); int Duse = D-nchk;
  uint32_t (*R)[20]=malloc(sizeof(uint32_t)*20*Duse);
  if(!R){fprintf(stderr,"failed to allocate inverted draws\n");return 1;}
  int inconclusive=0,recovered=0,tested=0,rec_s=-1,rec_m=-1,rec_stride=-1;
  MT recovered_state;
  for(int s=lo_s;s<hi_s;s++){
    int bad=0; for(int d=0;d<Duse;d++) if(!invert_sampler(s,draws[d],R[d])){bad=1;break;}
    if(bad){ printf("    sampler %d : draw order not consistent with this sampler\n",s); continue; }
    for(int m=lo_m;m<hi_m;m++) for(int stride=min_stride;stride<=max_stride;stride++){
      MT candidate_state;
      enum result result=attempt(s,m,stride,Duse,R,draws,nchk,1,&candidate_state); tested++;
      if(result==RECOVERED){
        recovered++; rec_s=s; rec_m=m; rec_stride=stride; recovered_state=candidate_state;
      }
      inconclusive+=result==INCONCLUSIVE;
    }
  }
  if(recovered==1&&!inconclusive){
    printf("  *** UNIQUE RECOVERED MODEL: sampler %d, mapping %d, stride %d ***\n",rec_s,rec_m,rec_stride);
    if(!publish_recovery(&options,&recovered_state,rec_s,rec_m,rec_stride,draws,D,nchk))return 1;
    return 0;
  }
  if(recovered){
    if(recovered>1)printf("  %d recovered candidates; no unique model selected",recovered);
    else printf("  one recovered candidate");
    if(inconclusive)printf(", with %d additional model(s) still inconclusive",inconclusive);
    printf("\n");
    report_output_refused(&options);
    return 4;
  }
  if(inconclusive){
    printf("  no recovered hypothesis; %d/%d models remain INCONCLUSIVE (insufficient rank)\n",inconclusive,tested);
    report_output_refused(&options);
    return 4;
  }
  printf("  all %d exact fixed-layout MT19937 hypotheses were rejected\n",tested);
  report_output_refused(&options);
  return 2;
}
