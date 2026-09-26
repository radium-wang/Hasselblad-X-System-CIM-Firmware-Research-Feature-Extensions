/* Diagnostic only: no original initialization, model, frame or AF calls. */
#include <dlfcn.h>
#include <errno.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <stdio.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <unistd.h>

#define DENY(n) BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_##n, 0, 1), \
                BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM)
static int restrict_process(void) {
    struct rlimit cpu = {5, 5}, memory = {256UL<<20, 256UL<<20};
    struct rlimit core = {0, 0}, file = {65536, 65536};
    if (setrlimit(RLIMIT_CPU, &cpu) || setrlimit(RLIMIT_AS, &memory) ||
        setrlimit(RLIMIT_CORE, &core) || setrlimit(RLIMIT_FSIZE, &file)) return -1;
    if (setpriority(PRIO_PROCESS, 0, 19)) return -1;
    alarm(10);
    struct sock_filter rules[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_AARCH64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        DENY(ioctl), DENY(socket), DENY(socketpair), DENY(connect),
        DENY(clone), DENY(execve), DENY(execveat), DENY(ptrace),
        DENY(process_vm_writev), DENY(kill), DENY(tgkill),
        DENY(mount), DENY(umount2), DENY(reboot), DENY(unlinkat),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW)
    };
    struct sock_fprog filter = {sizeof(rules) / sizeof(rules[0]), rules};
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) return -1;
    return prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &filter);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    for (int fd = 3; fd < 1024; ++fd) close(fd);
    if (restrict_process()) { printf("SANDBOX_FAILED errno=%d\n", errno); _exit(77); }
    puts("LINK_ONLY_SANDBOX_READY");
    const char *libs[] = {"libnn_framework.so", "libcnntk_cbb.so"};
    for (unsigned i = 0; i < 2; ++i) {
        printf("LOAD_BEGIN %s\n", libs[i]);
        void *handle = dlopen(libs[i], RTLD_NOW | RTLD_GLOBAL);
        if (!handle) { printf("LOAD_FAILED %s: %s\n", libs[i], dlerror()); _exit(74); }
        printf("LOAD_OK %s\n", libs[i]);
    }
    const char *symbols[] = {"__emutls_get_address", "CNNTKInit", "CNNTKSingleTrackerUpdate"};
    for (unsigned i = 0; i < 3; ++i) {
        dlerror();
        void *symbol = dlsym(RTLD_DEFAULT, symbols[i]);
        const char *error = dlerror();
        if (error || !symbol) { printf("SYMBOL_FAILED %s\n", symbols[i]); _exit(75); }
        printf("SYMBOL_RESOLVED_NOT_CALLED %s\n", symbols[i]);
    }
    puts("LINK_ONLY_PASS_NO_ALGORITHM_OR_AF_EXECUTION");
    _exit(0); /* no dlclose or destructors */
}
