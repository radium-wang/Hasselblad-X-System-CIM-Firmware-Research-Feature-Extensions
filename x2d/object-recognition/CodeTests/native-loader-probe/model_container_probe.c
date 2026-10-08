/* X2D 4.2.0: one stock verify-to-memory call, not NNF/CNN/AF execution.
 * Exact encrypted input and stock libraries are hash-gated by the runner.
 * No verification bypass, payload export, firmware install or live frames.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#ifdef USE_STOCK_FACE_MODEL
#define MODEL_SIZE 746144U
#else
#define MODEL_SIZE 4206912U
#endif
#define DONOR_CA_PATH "./libfw_util_ca.so"
#define DENY(n) BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_##n, 0, 1), \
                BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM)

static int restrict_process(void) {
    struct rlimit cpu = {5, 5}, memory = {256UL << 20, 256UL << 20};
    struct rlimit core = {0, 0}, file = {65536, 65536};
    if (setrlimit(RLIMIT_CPU, &cpu) || setrlimit(RLIMIT_AS, &memory) ||
        setrlimit(RLIMIT_CORE, &core) || setrlimit(RLIMIT_FSIZE, &file) ||
        setpriority(PRIO_PROCESS, 0, 19)) return -1;
    alarm(10);
    /* ioctl is intentionally allowed for ORIGINAL ION/TEE libraries.
     * This is a resource-limited probe, not a device-isolating sandbox. */
    struct sock_filter rules[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_AARCH64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        DENY(socket), DENY(socketpair), DENY(connect), DENY(clone),
        DENY(execve), DENY(execveat), DENY(ptrace), DENY(process_vm_writev),
        DENY(kill), DENY(tgkill), DENY(mount), DENY(umount2), DENY(reboot),
        DENY(unlinkat),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW)
    };
    struct sock_fprog filter = {sizeof(rules) / sizeof(rules[0]), rules};
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) return -1;
    return prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &filter);
}

static void wipe(void *p, size_t n) {
    volatile unsigned char *bytes = p;
    while (n--) *bytes++ = 0;
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    for (int fd = 3; fd < 1024; ++fd) close(fd);
    if (restrict_process()) { puts("RESOURCE_LIMIT_FAILED"); _exit(77); }
    int fd = open("model.enc", O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    struct stat st;
    if (fd < 0 || fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_size != MODEL_SIZE) {
        puts("INPUT_REJECTED"); _exit(65);
    }
    unsigned char *input = mmap(NULL, MODEL_SIZE, PROT_READ, MAP_PRIVATE, fd, 0);
    close(fd);
    if (input == MAP_FAILED) _exit(71);
    uint32_t segments;
    memcpy(&segments, input + 0x9c, sizeof(segments));
    if (memcmp(input, "IM*H", 4) || segments != 1) {
        puts("HEADER_REJECTED"); _exit(65);
    }
#ifdef USE_STOCK_FACE_MODEL
    puts("INPUT_PINNED_X2D_FACE_MODEL");
#else
    puts("INPUT_PINNED_X2DII_PET_MODEL");
#endif
    long page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0 || ((unsigned long)page_size & ((unsigned long)page_size - 1))) _exit(71);
    size_t page = (size_t)page_size;
    size_t rounded = (MODEL_SIZE + page - 1) & ~(page - 1);
    size_t allocation = rounded + 2 * page;
    unsigned char *mapping = mmap(NULL, allocation, PROT_NONE,
                                 MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (mapping == MAP_FAILED || mprotect(mapping + page, rounded, PROT_READ | PROT_WRITE)) _exit(71);
    /* Right-align output so a write past the exact capacity hits a guard page. */
    unsigned char *output = mapping + page + rounded - MODEL_SIZE;
    memset(mapping + page, 0xa5, rounded - MODEL_SIZE);
#ifdef USE_DONOR_CA
    /* One untouched donor user-space library; no system/TA/driver replacement. */
    void *donor = dlopen(DONOR_CA_PATH, RTLD_NOW | RTLD_GLOBAL);
    if (!donor) { printf("DONOR_CA_LOAD_FAILED %s\n", dlerror()); _exit(74); }
#endif
    void *library = dlopen("/system/lib64/libfw_util.so", RTLD_NOW | RTLD_LOCAL);
    if (!library) { puts("STOCK_LIBRARY_LOAD_FAILED"); _exit(74); }
    typedef int (*verify_memory_fn)(const void *, uint32_t, void *, uint32_t *);
    verify_memory_fn verify = (verify_memory_fn)dlsym(library, "dji_fw_verify_load2mem");
    if (!verify) { puts("STOCK_ENTRY_MISSING"); _exit(75); }
#ifdef USE_DONOR_CA
    Dl_info caller, callee, tee;
    if (!dladdr((void *)verify, &caller) ||
        strcmp(caller.dli_fname, "/system/lib64/libfw_util.so")) _exit(75);
    /* Read this isolated process's hash-pinned, BIND_NOW PLT relocation.
     * Checking dlsym alone would not prove the actual call target. */
    void *bound_ca = NULL;
    memcpy(&bound_ca, (const unsigned char *)caller.dli_fbase + 0x1ffe0, sizeof(bound_ca));
    void *expected_ca = dlsym(donor, "fw_util_verify_load2ion");
    void *tee_invoke = dlsym(donor, "TEEC_InvokeCommand");
    if (!bound_ca || bound_ca != expected_ca || !dladdr(bound_ca, &callee) ||
        strcmp(callee.dli_fname, DONOR_CA_PATH) ||
        (uintptr_t)bound_ca - (uintptr_t)callee.dli_fbase != 0x1700 ||
        !tee_invoke || !dladdr(tee_invoke, &tee) ||
        strcmp(tee.dli_fname, "/system/lib64/libteec.so")) {
        puts("DONOR_CA_BINDING_REJECTED"); _exit(75);
    }
    puts("DONOR_CA_CALL_TARGET_CONFIRMED_STOCK_TEE_RETAINED");
#endif
    uint32_t output_size = 0;
    struct timespec start, end;
    if (clock_gettime(CLOCK_MONOTONIC, &start)) _exit(71);
    puts("STOCK_VERIFY_TO_MEMORY_BEGIN_NO_INFERENCE");
    int status = verify(input, MODEL_SIZE, output, &output_size);
    if (clock_gettime(CLOCK_MONOTONIC, &end)) _exit(71);
    long long elapsed = (end.tv_sec - start.tv_sec) * 1000LL +
                        (end.tv_nsec - start.tv_nsec) / 1000000LL;
    int prefix_ok = 1;
    for (size_t i = 0; i < rounded - MODEL_SIZE; ++i)
        if (mapping[page + i] != 0xa5) prefix_ok = 0;
    int accepted = status == 0 && output_size > 0 && output_size <= MODEL_SIZE && prefix_ok;
    printf("STOCK_VERIFY_RESULT status=%d output_bytes=%u elapsed_ms=%lld bounds_ok=%d\n",
           status, output_size, elapsed, prefix_ok && output_size <= MODEL_SIZE);
    /* Never print or write the returned plaintext. On signal, no core dump. */
    wipe(mapping + page, rounded);
    munmap(mapping, allocation);
    munmap(input, MODEL_SIZE);
    puts("PROBE_OUTPUT_RAM_CLEARED_NO_PAYLOAD_EXPORT");
    if (accepted) puts("MODEL_CONTAINER_ACCEPTED_NO_INFERENCE_OR_AF");
    else puts("MODEL_CONTAINER_NOT_ACCEPTED_NO_INFERENCE_OR_AF");
    _exit(accepted ? 0 : 76);
}
