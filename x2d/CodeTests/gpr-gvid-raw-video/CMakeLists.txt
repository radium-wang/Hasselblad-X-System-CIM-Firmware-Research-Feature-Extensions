cmake_minimum_required(VERSION 3.20)
project(x2d_gpr_gvid_demo LANGUAGES C CXX)
if(NOT UNIX)
  message(FATAL_ERROR "This offline prototype currently targets macOS/Linux")
endif()

# Codec implementation stays in the upstream dependency, never copied here.
set(GPR_REVISION "0a194995f481d09f347e99252d41558de3d97c77")
set(GPR_SOURCE_DIR "" CACHE PATH "Optional local checkout at the pinned GPR revision")
if(NOT GPR_SOURCE_DIR)
  include(FetchContent)
  FetchContent_Declare(gpr_dependency
    URL "https://github.com/dcliftreaves/gpr/archive/${GPR_REVISION}.tar.gz"
    URL_HASH SHA256=3f41df424d7b6ffca9e4c6a15c3fabae3e59e5b6290ddc98b74f4f74ab688ab4)
  FetchContent_GetProperties(gpr_dependency)
  if(NOT gpr_dependency_POPULATED)
    FetchContent_Populate(gpr_dependency)
  endif()
  set(GPR_SOURCE_DIR "${gpr_dependency_SOURCE_DIR}")
endif()
foreach(option GPR_BUILD_SDK GPR_BUILD_STILL_APPS GPR_BUILD_LEGACY_CLI
    GPR_BUILD_PREVIEW_TOOLS GPR_ENABLE_PREVIEW GPR_BUILD_STOCK_VIDEO_EXPERIMENT
    GPR_BUILD_CAPTURE_APP GPR_BUILD_VIDEO_TESTS GPR_BUILD_PREVIEW_TESTS
    GPR_BUILD_MEDIA_TESTS GPR_BUILD_CODEC_TESTS GPR_BUILD_MOV_TOOLS
    GPR_BUILD_RENDER_TOOLS GPR_BUILD_METAL_TOOLS)
  set(${option} OFF CACHE BOOL "Dependency feature selection" FORCE)
endforeach()
set(GPR_ENABLE_VIDEO ON CACHE BOOL "Native GVID capture" FORCE)
set(GPR_BUILD_ENCODER ON CACHE BOOL "Stock VC-5 encoder" FORCE)
set(GPR_BUILD_DECODER ON CACHE BOOL "Stock VC-5 decoder" FORCE)
add_subdirectory("${GPR_SOURCE_DIR}" gpr EXCLUDE_FROM_ALL)
add_library(gvid_mapped_input STATIC mapped_input.cpp)
target_compile_features(gvid_mapped_input PUBLIC cxx_std_11)
target_include_directories(gvid_mapped_input PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(gvid_mapped_input PUBLIC gpr_video)
add_executable(gvid_raw_demo demo.cpp)
target_compile_features(gvid_raw_demo PRIVATE cxx_std_11)
target_link_libraries(gvid_raw_demo PRIVATE gvid_mapped_input)
add_executable(gvid_decode_frame decode_frame.cpp)
target_compile_features(gvid_decode_frame PRIVATE cxx_std_11)
target_link_libraries(gvid_decode_frame PRIVATE vc5_decoder)
include(CTest)
if(BUILD_TESTING)
  add_executable(gvid_mapped_input_test test_mapped_input.cpp)
  target_link_libraries(gvid_mapped_input_test PRIVATE gvid_mapped_input)
  add_test(NAME mapped_input_lifetime COMMAND gvid_mapped_input_test)
  find_package(Python3 COMPONENTS Interpreter REQUIRED)
  add_test(NAME raw_video_offline COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/test_offline.py
    --binary $<TARGET_FILE:gvid_raw_demo>
    --decoder $<TARGET_FILE:gvid_decode_frame>
    --gpr-source ${GPR_SOURCE_DIR})
endif()
