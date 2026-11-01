// SPDX-License-Identifier: MIT
// Offline frame adapter. Codec/container/capture implementation is in GPR.
#include "gpr_capture.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/resource.h>

static uint64_t number(const std::string &s) {
    if(s.empty() || s.find_first_not_of("0123456789")!=std::string::npos)
        throw std::runtime_error("expected an unsigned decimal number");
    size_t end=0;auto n=std::stoull(s,&end);
    if(end!=s.size())throw std::runtime_error("invalid number");return n;
}
static std::string relative(const std::string &manifest,const std::string &path) {
    if(path.empty())throw std::runtime_error("empty input path");
    if(path[0]=='/')return path;
    auto slash=manifest.find_last_of('/');
    return (slash==std::string::npos ? "":manifest.substr(0,slash+1))+path;
}
static std::string metadata(const std::string &path) {
    std::ifstream in(path,std::ios::binary);
    if(!in)throw std::runtime_error("cannot open frame metadata");
    std::string data;char block[4096];
    while(in.read(block,sizeof block) || in.gcount()) {
        data.append(block,size_t(in.gcount()));
        if(data.size()>GPR_GVID_METADATA_LIMIT)throw std::runtime_error("frame metadata exceeds 64 KiB");
    }
    if(!in.eof())throw std::runtime_error("metadata read failed");
    return data;
}
static int write_bytes(void *user,const uint8_t *p,size_t n) {
    return std::fwrite(p,1,n,static_cast<FILE *>(user))==n ? 0:-1;
}
static void completed(void *,const gpr_capture_completion *frame) {
    std::cout<<"{\"event\":\"frame\",\"index\":"<<frame->index
             <<",\"payload_bytes\":"<<frame->payload_bytes
             <<",\"encode_ms\":"<<double(frame->encode_ns)/1e6<<"}\n";
}
static void release_input(void *) {} // One stable source buffer, flush before reuse.

int main(int argc,char **argv) {
    try {
        if(argc!=8)throw std::runtime_error("usage: gvid_raw_demo width height bits quality fps manifest.tsv output.gvid");
        uint64_t values[5];for(unsigned i=0;i<5;++i) {
            values[i]=number(argv[i+1]);
            if(values[i]>UINT32_MAX)throw std::runtime_error("configuration exceeds uint32");
        }
        if(!values[0] || !values[1] || values[0]>GPR_GVID_MAX_DIMENSION ||
           values[1]>GPR_GVID_MAX_DIMENSION || values[0]*values[1]>GPR_GVID_MAX_PIXELS)
            throw std::runtime_error("geometry exceeds GVID v3 limits");
        gpr_capture_config cfg={};
        cfg.video={uint32_t(values[0]),uint32_t(values[1]),uint32_t(values[4]),1,
                   uint32_t(values[3]),uint32_t(values[2]),{'R','G','G','B'}};
        cfg.stride_bytes=cfg.video.width*2;cfg.max_inflight=1;cfg.workspace_bytes=1024*1024;
        const std::string clip_meta="{\"schema\":\"x2d.gpr_gvid.demo.v1\",\"timestamp_source\":\"manifest\"}";
        cfg.metadata=clip_meta.data();cfg.metadata_size=clip_meta.size();
        std::ifstream manifest(argv[6]);if(!manifest)throw std::runtime_error("cannot open manifest");
        for(const char *flag:{"GPR_STREAM_UNPACK","GPR_BAND_STREAM","GPR_COMPACT_BANDS","GPR_DIRECT_BANDS"})
            if(setenv(flag,"1",1))throw std::runtime_error("cannot configure codec");
        std::unique_ptr<FILE,decltype(&std::fclose)> file(std::fopen(argv[7],"wbx"),std::fclose);
        if(!file)throw std::runtime_error("cannot exclusively create output");
        gpr_capture_callbacks callbacks={write_bytes,completed,file.get()};gpr_capture *created=nullptr;
        if(gpr_capture_create(&cfg,&callbacks,&created))throw std::runtime_error("capture configuration rejected");
        std::unique_ptr<gpr_capture,decltype(&gpr_capture_destroy)> capture(created,gpr_capture_destroy);
        std::vector<uint8_t> raw(size_t(cfg.video.width)*cfg.video.height*2);
        const uint16_t endian=1;
        if(*reinterpret_cast<const uint8_t *>(&endian)!=1)
            throw std::runtime_error("demo requires a little-endian host");
        std::string line;uint64_t index=0;
        while(std::getline(manifest,line)) {
            if(line.empty() || line[0]=='#')continue;
            auto a=line.find('\t'),b=a==std::string::npos ? a:line.find('\t',a+1);
            if(a==std::string::npos || b==std::string::npos || line.find('\t',b+1)!=std::string::npos)
                throw std::runtime_error("manifest requires RAW path, metadata path, PTS ns separated by tabs");
            std::ifstream input(relative(argv[6],line.substr(0,a)),std::ios::binary);
            if(!input.read(reinterpret_cast<char *>(raw.data()),raw.size()) || input.peek()!=EOF)
                throw std::runtime_error("RAW input size differs from declared packed geometry");
            if(cfg.video.sample_bits<16) {
                const uint16_t *samples=reinterpret_cast<const uint16_t *>(raw.data());
                const uint32_t limit=1u<<cfg.video.sample_bits;
                for(size_t sample=0;sample<raw.size()/2;++sample)
                    if(samples[sample]>=limit)throw std::runtime_error("sample exceeds declared count domain");
            }
            auto meta=metadata(relative(argv[6],line.substr(a+1,b-a-1)));
            gpr_capture_frame frame={raw.data(),raw.size(),index,number(line.substr(b+1)),meta.data(),meta.size(),release_input,nullptr};
            if(gpr_capture_submit(created,&frame,UINT32_MAX) || gpr_capture_flush(created))
                throw std::runtime_error("capture rejected frame or writer failed");
            ++index;
        }
        if(!manifest.eof() || !index)throw std::runtime_error("empty or unreadable manifest");
        if(gpr_capture_finish(created) || std::fflush(file.get()))throw std::runtime_error("recording finalization failed");
        if(std::fclose(file.release()))throw std::runtime_error("recording close failed");
        gpr_capture_stats stats={};gpr_capture_get_stats(created,&stats);
        struct rusage usage={};getrusage(RUSAGE_SELF,&usage);
        uint64_t rss=uint64_t(usage.ru_maxrss);
#if !defined(__APPLE__)
        rss*=1024;
#endif
        std::cout<<"{\"event\":\"summary\",\"frames\":"<<stats.written<<",\"payload_bytes\":"<<stats.payload_bytes
                 <<",\"encode_mean_ms\":"<<(double(stats.encode_ns)/index/1e6)
                 <<",\"peak_rss_bytes\":"<<rss<<",\"cnn\":false,\"complete\":true}\n";
        return 0;
    } catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}
}
