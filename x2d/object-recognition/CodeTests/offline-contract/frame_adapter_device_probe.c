/* 同一合成数据契约在 Android 独立进程执行；无原厂模型或真实帧访问。 */
#include <errno.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <unistd.h>
#define main descriptor_contract_main
#include "test_frame_descriptor_native.c"
#undef main

#define DENY(n) BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_##n, 0, 1), \
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM)
static int restrict_probe(void) {
    struct rlimit cpu = {2, 2}, memory = {64UL<<20, 64UL<<20};
    struct rlimit core = {0, 0}, file = {16384, 16384};
    if (setrlimit(RLIMIT_CPU, &cpu) || setrlimit(RLIMIT_AS, &memory) ||
        setrlimit(RLIMIT_CORE, &core) || setrlimit(RLIMIT_FSIZE, &file) ||
        setpriority(PRIO_PROCESS, 0, 19)) return -1;
    alarm(5);
    struct sock_filter rules[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_AARCH64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        DENY(ioctl), DENY(socket), DENY(socketpair), DENY(connect),
        DENY(clone), DENY(execve), DENY(execveat), DENY(ptrace),
        DENY(process_vm_writev), DENY(kill), DENY(tgkill),
        DENY(mount), DENY(umount2), DENY(reboot), DENY(unlinkat),
        DENY(openat),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW)
    };
    struct sock_fprog filter = {sizeof(rules) / sizeof(rules[0]), rules};
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) return -1;
    return prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &filter);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    for (int fd = 3; fd < 1024; ++fd) close(fd);
    if (restrict_probe()) { puts("SANDBOX_FAILED"); _exit(77); }
    puts("FRAME_DESCRIPTOR_SANDBOX_READY");
    int result = descriptor_contract_main();
    if (result) _exit(result);
    puts("FRAME_DESCRIPTOR_PASS_NO_CAMERA_FRAME_OR_AF");
    _exit(0);
}
