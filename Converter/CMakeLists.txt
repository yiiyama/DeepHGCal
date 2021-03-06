cmake_minimum_required(VERSION 2.8)
project(DeepHGCal2)


set(CMAKE_CXX_STANDARD 11)
list(APPEND CMAKE_PREFIX_PATH $ENV{ROOTSYS})
MESSAGE(STATUS "ROOTSYS $ENV{ROOTSYS}")
find_package(ROOT REQUIRED Core)
include(${ROOT_USE_FILE})

set (CMAKE_CXX_FLAGS "-pthread -std=c++11 -Wno-deprecated-declarations -m64 ${CMAKE_CXX_FLAGS}")


include_directories(${ROOT_INCLUDE_DIR} include)
link_directories(${ROOT_LIBRARY_DIR})

set(SOURCE_FILES include/Converter.h
        src/Converter.cpp
        src/HGCalSel.cpp
        include/HGCalSel.h
        src/NTupleGlobals.cpp
        include/NTupleGlobals.h
        src/NTupleRecHits.cpp
        include/NTupleRecHits.h
        src/NTupleContent.cpp
        include/NTupleContent.h
        src/helpers.cpp
        include/helpers.h
        src/NTupleSimClusters.cpp
        include/NTupleSimClusters.h
        include/MergeDescriptor.h
        src/MergeDescriptor.cpp
        include/NTupleConfig.h
        src/IndexSimClusters.cpp
        include/IndexSimClusters.h)

add_executable(convert2 mainConvert.cpp ${SOURCE_FILES})
add_executable(createMergeList mainCreateMergeList.cpp ${SOURCE_FILES})
add_executable(merge mainMerge.cpp ${SOURCE_FILES})
add_executable(index mainIndex.cpp ${SOURCE_FILES})

target_link_libraries(convert2 ${ROOT_LIBRARIES})
target_link_libraries(createMergeList ${ROOT_LIBRARIES})
target_link_libraries(merge ${ROOT_LIBRARIES})
target_link_libraries(index ${ROOT_LIBRARIES})
