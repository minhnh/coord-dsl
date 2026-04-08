cmake_minimum_required(VERSION 3.20)
project(fsm_example)

find_package(coord2b REQUIRED)

include_directories(
  ${coord2b_INCLUDE_DIRS}
)

add_executable(fsm_test
  test_fsm.cpp
  ex_fsm.hpp
)
target_compile_features(fsm_test PUBLIC
  c_std_99 cxx_std_17 cxx_std_20
)
target_link_libraries(fsm_test
  coord2b
)
