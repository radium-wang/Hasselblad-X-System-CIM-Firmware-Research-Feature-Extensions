/* X2D 4.2.0 声音候选。固定素材、仅回环地址；不修改混音器或相机状态。
 * 独立服务预载 PCM；不注入 camera-gui，不因播放失败重启相机。
 * 通过原厂 libaudioclient 交付预载数据；空闲时不持有播放设备或流。
 */
typedef unsigned long size_t;
typedef long ssize_t;
extern int open(const char *, int, ...), close(int), puts(const char *);
extern ssize_t read(int,void *,size_t), write(int,const void *,size_t);
extern void *malloc(size_t);
extern int memcmp(const void *,const void *,size_t);
extern size_t strlen(const char *);
extern void *memcpy(void *,const void *,size_t);
extern void *memset(void *,int,size_t);
extern int strcmp(const char *,const char *);
extern char *getenv(const char *);
extern int pthread_create(unsigned long *,const void *,void *(*)(void *),void *);
extern int pthread_mutex_lock(void *), pthread_mutex_unlock(void *);
extern int pthread_cond_wait(void *,void *), pthread_cond_signal(void *);
extern int socket(int,int,int), bind(int,const void *,unsigned), listen(int,int);
extern int accept(int,void *,void *), setsockopt(int,int,int,const void *,unsigned);
extern int usleep(unsigned);
extern long time(void *);
extern void _exit(int);
extern void (*signal(int,void (*)(int)))(int);
static int log_line(const char *s) {write(1,s,strlen(s));write(1,"\n",1);return 0;}
#define puts log_line
/* 仅限第一代 4.2.0：与原厂 test_audio_client / libaudioclient ABI 核对。 */
struct stream_handle { unsigned id, bytes; void *buffer; };
struct audio_frame { void *buffer; unsigned bytes, valid; unsigned char reserved[56]; };
_Static_assert(sizeof(struct stream_handle)==16,"stream ABI");
_Static_assert(sizeof(struct audio_frame)==72,"frame ABI");
extern int audio_client_get_dev_volume(const char *,unsigned *);
extern int audio_client_player_open_dev(const char *,const void *,int *);
extern int audio_client_player_close_dev(int);
extern int audio_client_player_open_stream(int,unsigned *,struct stream_handle *);
extern int audio_client_player_close_stream(int,struct stream_handle *);
extern int audio_client_player_write_frame(int,struct audio_frame *);
static unsigned long mutex[8], cond[8];
static int busy, failed;
static unsigned char *samples;
static unsigned sample_bytes;
static int play_samples(void) {
    int player=-1, error=0;
    struct stream_handle stream={0};
    /* rate,bits,channels,interleaved,front_center,planar,volume,flags,buffer,... */
    unsigned config[11]={48000,16,2,0,2,0,100,0,0,0,0};
    if(audio_client_player_open_dev("speaker",0,&player)<0)return 1;
    if(audio_client_player_open_stream(player,config,&stream)<0){
        audio_client_player_close_dev(player);return 1;
    }
    if(!stream.buffer || !stream.bytes || stream.bytes>1048576 || stream.bytes%4)error=1;
    for(unsigned pos=0;!error && pos<sample_bytes;){
        unsigned n=sample_bytes-pos;if(n>stream.bytes)n=stream.bytes;
        struct audio_frame frame={0};
        frame.buffer=stream.buffer;frame.bytes=stream.bytes;frame.valid=stream.bytes;
        if(n<stream.bytes)memset(stream.buffer,0,stream.bytes);
        memcpy(stream.buffer,samples+pos,n);
        if(audio_client_player_write_frame(player,&frame)<0)error=1;
        pos+=n;
    }
    /* 原厂测试客户端同样在提交完数据后关闭流、关闭所属播放器。 */
    if(audio_client_player_close_stream(player,&stream)<0)error=1;
    if(audio_client_player_close_dev(player)<0)error=1;
    return error;
}
static int sendall(int fd,const char *s) {
    size_t n=strlen(s); while(n){ssize_t k=write(fd,s,n);if(k<=0)return -1;s+=k;n-=k;}return 0;
}
static void *play_worker(void *unused) {
    (void)unused;
    for (;;) {
        pthread_mutex_lock(mutex);
        while(!busy) pthread_cond_wait(cond,mutex);
        pthread_mutex_unlock(mutex);
        puts("AUDIO_PLAY_BEGIN");
        int error=play_samples();
        pthread_mutex_lock(mutex);busy=0;failed=error;pthread_mutex_unlock(mutex);
        puts(error ? "AUDIO_PLAY_FAILED" : "AUDIO_PLAY_FINISHED");
    }
    return 0;
}
static void *serve(void *unused) {
    (void)unused;
    int fd=open("/system/etc/x2d-ciallo.wav",0);
    unsigned char header[44];
    if(fd<0 || read(fd,header,44)!=44 || memcmp(header,"RIFF",4) ||
       memcmp(header+8,"WAVEfmt ",8) || memcmp(header+36,"data",4))return 0;
    unsigned *h=(unsigned *)header;
    if(h[4]!=16 || header[20]!=1 || header[22]!=2 || h[6]!=48000 || header[34]!=16)return 0;
    sample_bytes=h[10]; if(sample_bytes<4 || sample_bytes>48000*4*5 || sample_bytes%4)return 0;
    samples=malloc(sample_bytes);if(!samples)return 0;
    for(unsigned pos=0;pos<sample_bytes;){ssize_t n=read(fd,samples+pos,sample_bytes-pos);if(n<=0)return 0;pos+=n;}
    close(fd);
    /* 只读查询预热原厂服务连接，不打开 PCM、不修改全局音量。 */
    int ready=0;
    for(int attempt=0;attempt<50;attempt++) {
        unsigned volume[3]={0};
        if(audio_client_get_dev_volume("speaker",volume)>=0){ready=1;break;}
        usleep(200000);
    }
    if(!ready){puts("AUDIO_FACTORY_SERVICE_UNAVAILABLE");return 0;}
    unsigned long thread;
    if(pthread_create(&thread,0,play_worker,0))return 0;
    int server=socket(2,1,0); if(server<0)return 0;
    /* 端口 38491，只允许相机本机访问；不接收路径或任意命令。 */
    unsigned char address[16]={2,0,150,91,127,0,0,1};
    int reuse=1;setsockopt(server,1,2,&reuse,sizeof(reuse));
    if(bind(server,address,16) || listen(server,4)) {puts("AUDIO_BIND_FAILED");return 0;}
    puts("AUDIO_FACTORY_PRELOADED_READY");
    for(;;){
        int client=accept(server,0,0);if(client<0)break;
        long timeout[2]={1,0};
        setsockopt(client,1,20,timeout,sizeof(timeout));
        setsockopt(client,1,21,timeout,sizeof(timeout));
        char request[256];ssize_t n=read(client,request,255);
        int valid=(n>=15 && !memcmp(request,"GET /play HTTP/",15)) || (n>=16 && !memcmp(request,"GET /ready HTTP/",16));
        pthread_mutex_lock(mutex);
        if(valid && !failed && !memcmp(request,"GET /play ",10) && !busy){busy=1;pthread_cond_signal(cond);}
        int ok=valid && !failed;
        pthread_mutex_unlock(mutex);
        sendall(client,ok ? "HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: *\r\nCache-Control: no-store\r\nConnection: close\r\nContent-Length: 2\r\n\r\nOK" :
                           "HTTP/1.1 503 Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n");
        close(client);
    }
    return 0;
}
__attribute__((constructor)) static void start(void) {
    const char *enabled=getenv("X2D_AUDIO_SERVICE");
    if(!enabled || strcmp(enabled,"1"))return;
    signal(13,(void (*)(int))1);
    /* 构造函数占据专用 sleep 进程；错误退出而不留下空闲假服务。 */
    serve(0);
    _exit(1);
}
