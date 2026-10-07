// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (c) 2026 Radium Wang. Adapter for pixelomer/libshijima.
#include <shijima/mascot/factory.hpp>
#include <shijima/scripting/context.hpp>
#include <shijima/behavior/base.hpp>
#include <fstream>
#include <sstream>
#include <iostream>
#include <chrono>
#include <thread>
#include <csignal>
#include <cmath>
#include <cstdio>
#include <set>
#include <unistd.h>

static volatile std::sig_atomic_t alive = 1;
static void stop(int) { alive = 0; }
static std::string read(const std::string &path) {
    std::ifstream in(path); if (!in) throw std::runtime_error("Cannot read " + path);
    std::ostringstream s; s << in.rdbuf(); return s.str();
}
static std::string quote(const std::string &s) {
    std::string out = "\"";
    for (unsigned char c : s) { if(c=='\\' || c=='\"') out+='\\'; if(c>=32) out+=c; }
    return out + "\"";
}
int main(int argc, char **argv) {
    if((argc != 3 && argc != 4) || (argc == 4 && std::string(argv[3]) != "selftest")) { std::cerr << "engine CHARACTER_DIRECTORY STATE_DIRECTORY [selftest]\n"; return 2; }
    const std::string pack=argv[1], root=argv[2]; bool test=argc==4 && std::string(argv[3])=="selftest";
    std::signal(SIGTERM,stop); std::signal(SIGINT,stop);
    try {
        shijima::mascot::factory factory;
        factory.script_ctx=std::make_shared<shijima::scripting::context>();
        factory.env=std::make_shared<shijima::mascot::environment>();
        auto &env=*factory.env;
        env.seed(20261006); env.subtick_count=test?1:3;
        double stageHeight=test?450:540;
        env.work_area=env.screen={0,720,stageHeight,0}; env.floor={stageHeight,0,720}; env.ceiling={0,0,720};
        env.active_ie={-50,50,-50,50}; env.allows_breeding=false; env.allows_hotspots=true; env.mascot_count=1;
        shijima::mascot::factory::tmpl tmpl;
        tmpl.name="Neuron"; tmpl.path=pack; tmpl.actions_xml=read(pack+"/actions.xml"); tmpl.behaviors_xml=read(pack+"/behaviors.xml");
        factory.register_template(tmpl);
        auto pet=factory.spawn("Neuron",{{360,200},"Fall"}); auto state=pet.manager->get_state(); state->can_breed=false;
        long sequence=-1; double cx=360,cy=220; bool dragging=false; double dragLeft=296,dragTop=72;bool visualDrag=false;
        std::set<std::string> frames; int changes=0; std::string previous;
        bool dragChecked=false,climbChecked=false,patChecked=false;
        auto next=std::chrono::steady_clock::now();
        for(int tick=0; alive && tick<(test ? 1500 : 45000); ++tick) {
            if(!test && std::ifstream(root+"/engine.stop")) break;
            std::ifstream input(root+"/input"); long n; double x,y; int d; std::string behavior;
            if(input >> n >> x >> y >> d >> behavior) {
                if(n>sequence && std::isfinite(x) && std::isfinite(y) && x>=0 && x<=720 && y>=0 && y<=stageHeight && (d==0 || d==1)) {
                    sequence=n; cx=x; cy=y; dragging=d;
                    double left,top;
                    if(input>>left>>top && std::isfinite(left) && std::isfinite(top) && left>=0 && left<=720 && top>=0 && top<=stageHeight){dragLeft=left;dragTop=top;visualDrag=true;}
                    if(behavior!="-") {
                        const std::set<std::string> allowed={"StandUp","SitDown","WalkAlongWorkAreaFloor","ClimbAlongWall","LieDown","StandBlush","Fall"};
                        if(allowed.count(behavior)) pet.manager->next_behavior(behavior);
                    }
                }
            }
            if(test) {
                if(tick==200) pet.manager->next_behavior("WalkAlongWorkAreaFloor");
                if(tick==400) {dragging=true;cx=300;cy=180;}
                if(tick==425) dragging=false;
                if(tick==650) {state->anchor={0,350};pet.manager->next_behavior("ClimbAlongWall");}
                if(tick==950) {state->anchor={360,450};pet.manager->next_behavior("StandBlush");}
            }
            auto old=env.cursor; env.cursor={cx,cy,cx-old.x,cy-old.y}; state->dragging=dragging;
            pet.manager->tick();
            if(test && tick==410) dragChecked=state->behavior && state->behavior->name=="Dragged";
            if(test && tick==680) climbChecked=state->anchor.y<350 && state->anchor.x==0;
            if(test && tick==952) patChecked=state->behavior && state->behavior->name=="StandBlush";
            if(state->dead) throw std::runtime_error("Unexpected mascot self-destruction");
            auto &f=state->active_frame;
            if(dragging && visualDrag){state->anchor={dragLeft+f.anchor.x,dragTop+f.anchor.y};}
            auto image=f.get_name(state->looking_right);
            if(f.visible) {
                if(image.empty() || image.find("..")!=std::string::npos || image[0]!='/') throw std::runtime_error("Unsafe image name");
                std::ifstream asset(pack+"/img"+image); if(!asset) throw std::runtime_error("Missing frame " + image);
                frames.insert(image); if(image!=previous) ++changes; previous=image;
            }
            if(!std::isfinite(state->anchor.x)||!std::isfinite(state->anchor.y)) throw std::runtime_error("Nonfinite position");
            std::ofstream out(root+"/state.next");
            out << "{\"tick\":"<<tick<<",\"input\":"<<sequence<<",\"x\":"<<state->anchor.x<<",\"y\":"<<state->anchor.y
                <<",\"ax\":"<<f.anchor.x<<",\"ay\":"<<f.anchor.y<<",\"right\":"<<(state->looking_right?"true":"false")
                <<",\"mirror\":"<<(state->looking_right && f.right_name.empty()?"true":"false")
                <<",\"visible\":"<<(f.visible?"true":"false")<<",\"dragging\":"<<(dragging?"true":"false")
                <<",\"image\":"<<quote(image)<<",\"behavior\":"<<quote(state->behavior?state->behavior->name:"")<<"}\n";
            out.close(); if(!out || std::rename((root+"/state.next").c_str(),(root+"/state.json").c_str())) throw std::runtime_error("State write failed");
            if(!test) {next+=std::chrono::microseconds(40000/env.subtick_count);std::this_thread::sleep_until(next);}
        }
        std::cout<<"{\"engine\":\"libshijima\",\"distinctFrames\":"<<frames.size()<<",\"frameChanges\":"<<changes<<",\"drag\":"<<dragChecked<<",\"climb\":"<<climbChecked<<",\"pat\":"<<patChecked<<",\"selftest\":"<<(test?"true":"false")<<"}\n";
        if(test && (frames.size()<10 || changes<20 || !dragChecked || !climbChecked || !patChecked)) return 3;
    } catch(const std::exception &e) {std::cerr<<e.what()<<"\n";return 1;}
    return 0;
}
