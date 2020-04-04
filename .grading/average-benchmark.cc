#include <algorithm>
#include <cassert>
#include <iomanip>
#include <iostream>
#include <random>

#include "average.h"
#include "timer.h"

[[noreturn]] static void error(const std::string &msg) {
  std::cerr << msg;
  if (!msg.empty() && msg.back() != '\n') {
    std::cerr << '\n';
  }
  std::cerr << std::flush;
  std::exit(EXIT_FAILURE);
}

static std::pair<int, int> random_interval(std::mt19937 rng, int n, int s) {
  if (s > 0) {
    std::uniform_int_distribution<int> dist(0, n - s);
    int v0 = dist(rng);
    int v1 = v0 + s;
    return {v0, v1};
  } else {
    std::uniform_int_distribution<int> dist(0, n - 1);
    int v0 = dist(rng);
    int v1 = dist(rng);
    if (v0 > v1) {
      std::swap(v0, v1);
    } else if (v0 == v1) {
      if (v0 == 0)
        v1++;
      else
        v0--;
    }
    return {v0, v1};
  }
}

static void benchmark(int ny, int nx, int sy, int sx) {
  std::mt19937 rng;
  std::uniform_real_distribution<float> u(0.0f, 1.0f);
  std::vector<float> data(3 * ny * nx);
  for (int i = 0; i < 3 * ny * nx; ++i) {
    data[i] = u(rng);
  }
  auto [x0, x1] = random_interval(rng, nx, sx);
  auto [y0, y1] = random_interval(rng, ny, sy);

  std::cout << "average\t" << ny << "\t" << nx << "\t" << sy << "\t" << sx
            << "\t" << std::flush;
  {
    ppc::timer t;
    calculate(ny, nx, data.data(), y0, x0, y1, x1);
  }
  std::cout << std::endl;
}

int main(int argc, const char **argv) {
  if (argc != 5 && argc != 6) {
    error("Usage:\n  average-benchmark <ny> <nx> <sy> <sx> [iterations]");
  }
  int ny = std::stoi(argv[1]);
  int nx = std::stoi(argv[2]);
  int sy = std::stoi(argv[3]);
  int sx = std::stoi(argv[4]);
  int iter = argc == 6 ? std::stoi(argv[5]) : 1;
  for (int i = 0; i < iter; i++) {
    benchmark(ny, nx, sy, sx);
  }
}