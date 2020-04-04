
all: average-test average-benchmark

CXXFLAGS=-g -std=c++1z -Wall -Wextra
CXXFLAGS+=-Werror -Wno-error=unknown-pragmas -Wno-error=unused-but-set-variable -Wno-error=unused-local-typedefs -Wno-error=unused-function -Wno-error=unused-label -Wno-error=unused-value -Wno-error=unused-variable -Wno-error=unused-parameter -Wno-error=unused-but-set-parameter
CXXFLAGS+=-march=native
CXXFLAGS+=-I . -I ./.grading

vpath %.h .grading
vpath %.cc .grading

# ASAN flags if debug mode, otherwise -O3
ifeq ($(DEBUG),1)
else ifeq ($(DEBUG),2)
CXXFLAGS+=-fsanitize=address -fsanitize=undefined
LDFLAGS+=-fsanitize=address -fsanitize=undefined
else ifeq ($(DEBUG),3)
CXXFLAGS+=-D_GLIBCXX_DEBUG
CXXFLAGS+=-fsanitize=address -fsanitize=undefined
LDFLAGS+=-fsanitize=address -fsanitize=undefined
else
CXXFLAGS+=-O3
endif

SOURCES:=*.cc
SOURCES+=./.grading/*.cc

average-test: average-test.o average.o                                               
	$(CXX) $^ $(LDFLAGS)  -o $@ 

average-benchmark: average-benchmark.o average.o                                               
	$(CXX) $^ $(LDFLAGS)  -o $@ 

depend:
	$(CXX) -MM $(CXXFLAGS) -x c++ $(wildcard $(SOURCES)) > Makefile.dep

clean:
	rm -f *.o average-test average-benchmark

include Makefile.dep