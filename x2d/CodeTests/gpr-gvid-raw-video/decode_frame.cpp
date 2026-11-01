// SPDX-License-Identifier: MIT
// A thin RGGB decoder adapter; all inverse codec work is in the GPR dependency.
#include "vc5_decoder.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc,char **argv) {
    try {
        if(argc!=4)throw std::runtime_error("usage: gvid_decode_frame 12|14|16 input.vc5 output.raw");
        const std::string bits=argv[1];
        if(bits!="12" && bits!="14" && bits!="16")throw std::runtime_error("unsupported sample domain");
        std::ifstream file(argv[2],std::ios::binary|std::ios::ate);
        if(!file)throw std::runtime_error("cannot open payload");
        auto size=file.tellg();
        if(size<=0 || size>512*1024*1024)throw std::runtime_error("payload exceeds operational limit");
        file.seekg(0);std::vector<uint8_t> payload(static_cast<size_t>(size));
        if(!file.read(reinterpret_cast<char *>(payload.data()),payload.size()))throw std::runtime_error("payload read failed");
        vc5_decoder_parameters params={};vc5_decoder_parameters_set_default(&params);
        params.pixel_format=bits=="16" ? VC5_DECODER_PIXEL_FORMAT_RGGB_16:
            bits=="14" ? VC5_DECODER_PIXEL_FORMAT_RGGB_14:VC5_DECODER_PIXEL_FORMAT_RGGB_12;
        params.rgb_resolution=GPR_RGB_RESOLUTION_NONE;params.mem_alloc=std::malloc;params.mem_free=std::free;
        gpr_buffer input={payload.data(),payload.size()},raw={nullptr,0};
        auto error=vc5_decoder_process(&params,&input,&raw,nullptr);
        std::unique_ptr<void,decltype(&std::free)> owner(raw.buffer,std::free);
        if(error || !raw.buffer || !raw.size)throw std::runtime_error("codec rejected frame");
        std::unique_ptr<FILE,decltype(&std::fclose)> out(std::fopen(argv[3],"wbx"),std::fclose);
        if(!out)throw std::runtime_error("cannot exclusively create RAW output");
        if(std::fwrite(raw.buffer,1,raw.size,out.get())!=raw.size || std::fflush(out.get()))
            throw std::runtime_error("RAW write failed");
        if(std::fclose(out.release()))throw std::runtime_error("RAW close failed");
        std::cout<<"{\"raw_bytes\":"<<raw.size<<",\"cnn\":false}\n";
        return 0;
    } catch(const std::exception &e) {std::cerr<<e.what()<<'\n';return 1;}
}
