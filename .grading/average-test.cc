#include <algorithm>
#include <cassert>
#include <iomanip>
#include <iostream>
#include <random>

#include "average.h"
#include "timer.h"

static constexpr float THRESHOLD = 1e-6;

struct Rect {
  int y0;
  int x0;
  int y1;
  int x1;
};

struct TestCase {
  float expected[3];
  std::vector<float> input;
  int ny;
  int nx;
  Rect rect;
};

[[noreturn]] static void error(const std::string &msg) {
  std::cerr << msg;
  if (!msg.empty() && msg.back() != '\n') {
    std::cerr << '\n';
  }
  std::cerr << std::flush;
  std::exit(EXIT_FAILURE);
}

static void print_color(const float color[3]) {
  std::cout << '(' << std::setprecision(7) << std::setw(9) << std::fixed
            << color[0] << ", " << std::setprecision(7) << std::setw(9)
            << std::fixed << color[1] << ", " << std::setprecision(7)
            << std::setw(9) << std::fixed << color[2] << ')';
}

static void print(int ny, int nx, Rect rect, const float *data) {
  for (int y = 0; y <= ny; y++) {
    if (y == rect.y0) {
      for (int x = 0; x <= nx; x++) {
        if (x < rect.x0) {
          std::cout << "                                    ";
        } else if (x == rect.x0) {
          std::cout << " ┌──────────────────────────────────";
        } else if (x < rect.x1) {
          std::cout << "────────────────────────────────────";
        } else if (x == rect.x1) {
          std::cout << "─┐";
        }
      }
    } else if (rect.y0 < y && y < rect.y1) {
      for (int x = 0; x <= nx; x++) {
        if (x < rect.x0) {
          std::cout << "                                    ";
        } else if (x == rect.x0) {
          std::cout << " │                                  ";
        } else if (x < rect.x1) {
          std::cout << "                                    ";
        } else if (x == rect.x1) {
          std::cout << " │";
        }
      }
    } else if (y == rect.y1) {
      for (int x = 0; x <= nx; x++) {
        if (x < rect.x0) {
          std::cout << "                                    ";
        } else if (x == rect.x0) {
          std::cout << " └──────────────────────────────────";
        } else if (x < rect.x1) {
          std::cout << "────────────────────────────────────";
        } else if (x == rect.x1) {
          std::cout << "─┘";
        }
      }
    }
    std::cout << '\n';
    if (y == ny)
      break;
    for (int x = 0; x <= nx; x++) {
      if (x == rect.x0 || x == rect.x1) {
        if (rect.y0 <= y && y < rect.y1) {
          std::cout << " │ ";
        } else {
          std::cout << "   ";
        }
      } else {
        std::cout << "   ";
      }
      if (x == nx)
        break;
      float color[3] = {
          data[(y * nx + x) * 3 + 0],
          data[(y * nx + x) * 3 + 1],
          data[(y * nx + x) * 3 + 2],
      };
      print_color(color);
    }
    std::cout << '\n';
  }
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

static Rect random_rect(std::mt19937 rng, int ny, int nx, int sy, int sx) {
  auto [x0, x1] = random_interval(rng, nx, sx);
  auto [y0, y1] = random_interval(rng, ny, sy);
  return {y0, x0, y1, x1};
}

// All pixels have the same color
static TestCase generate_all_equal(int ny, int nx, int sy, int sx) {
  std::mt19937 rng;
  for (int i = 0; i < ny * 10000 + nx; i++)
    rng();
  Rect rect = random_rect(rng, ny, nx, sy, sx);
  std::uniform_real_distribution<float> color_dist(0.0f, 1.0f);

  float color[3] = {color_dist(rng), color_dist(rng), color_dist(rng)};
  std::vector<float> data(3 * nx * ny);
  for (int y = 0; y < ny; y++) {
    for (int x = 0; x < nx; x++) {
      data[(y * nx + x) * 3 + 0] = color[0];
      data[(y * nx + x) * 3 + 1] = color[1];
      data[(y * nx + x) * 3 + 2] = color[2];
    }
  }

  return {
      {color[0], color[1], color[2]}, data, ny, nx, rect,
  };
}

static TestCase generate_gradient(int ny, int nx, int sy, int sx) {
  std::mt19937 rng;
  for (int i = 0; i < ny * 10000 + nx; i++)
    rng();
  Rect rect = random_rect(rng, ny, nx, sy, sx);
  // Generate random colos for the corners
  std::uniform_real_distribution<float> color_dist(0.0f, 1.0f);
  float top_left[3] = {color_dist(rng), color_dist(rng), color_dist(rng)};
  float top_right[3] = {color_dist(rng), color_dist(rng), color_dist(rng)};
  float bottom_left[3] = {color_dist(rng), color_dist(rng), color_dist(rng)};
  float bottom_right[3] = {color_dist(rng), color_dist(rng), color_dist(rng)};

  std::vector<float> data(3 * nx * ny);
  for (int y = 0; y < ny; y++) {
    for (int x = 0; x < nx; x++) {
      // Linearly interpolate the colors
      double x_fact = double(x) / nx;
      double y_fact = double(y) / ny;
      data[(y * nx + x) * 3 + 0] = float(
          y_fact * (x_fact * top_left[0] + (1.0 - x_fact) * top_right[0]) +
          (1.0 - y_fact) *
              (x_fact * bottom_left[0] + (1.0 - x_fact) * bottom_right[0]));
      data[(y * nx + x) * 3 + 1] = float(
          y_fact * (x_fact * top_left[1] + (1.0 - x_fact) * top_right[1]) +
          (1.0 - y_fact) *
              (x_fact * bottom_left[1] + (1.0 - x_fact) * bottom_right[1]));
      data[(y * nx + x) * 3 + 2] = float(
          y_fact * (x_fact * top_left[2] + (1.0 - x_fact) * top_right[2]) +
          (1.0 - y_fact) *
              (x_fact * bottom_left[2] + (1.0 - x_fact) * bottom_right[2]));
    }
  }

  // Compute the expected color. It is the average of the corners.
  double x_fact = 0.5 * double(rect.x0 + rect.x1 - 1) / nx;
  double y_fact = 0.5 * double(rect.y0 + rect.y1 - 1) / ny;
  float r =
      float(y_fact * (x_fact * top_left[0] + (1.0 - x_fact) * top_right[0]) +
            (1.0 - y_fact) *
                (x_fact * bottom_left[0] + (1.0 - x_fact) * bottom_right[0]));
  float g =
      float(y_fact * (x_fact * top_left[1] + (1.0 - x_fact) * top_right[1]) +
            (1.0 - y_fact) *
                (x_fact * bottom_left[1] + (1.0 - x_fact) * bottom_right[1]));
  float b =
      float(y_fact * (x_fact * top_left[2] + (1.0 - x_fact) * top_right[2]) +
            (1.0 - y_fact) *
                (x_fact * bottom_left[2] + (1.0 - x_fact) * bottom_right[2]));

  return {
      {r, g, b}, data, ny, nx, rect,
  };
}

static TestCase generate_small_noise(int ny, int nx, int sy, int sx) {
  std::mt19937 rng;
  for (int i = 0; i < ny * 10000 + nx; i++)
    rng();
  Rect rect = random_rect(rng, ny, nx, sy, sx);
  std::uniform_real_distribution<float> color_dist(0.0f, 1.0f);

  float color[3] = {color_dist(rng), color_dist(rng), color_dist(rng)};
  std::vector<float> data(3 * nx * ny);
  for (int y = 0; y < ny; y++) {
    for (int x = 0; x < nx; x++) {
      data[(y * nx + x) * 3 + 0] = color[0];
      data[(y * nx + x) * 3 + 1] = color[1];
      data[(y * nx + x) * 3 + 2] = color[2];
    }
  }

  // Add some small noise
  std::uniform_int_distribution<int> x_dist(rect.x0, rect.x1 - 1);
  std::uniform_int_distribution<int> y_dist(rect.y0, rect.y1 - 1);
  for (int c = 0; c < 3; c++) {
    for (int i = 0; i < 3 * nx * ny; i++) {
    retry_plus:
      int x = x_dist(rng);
      int y = y_dist(rng);
      if (!(data[(y * nx + x) * 3 + c] < 1.0f))
        goto retry_plus;
      data[(y * nx + x) * 3 + c] += std::numeric_limits<float>::epsilon();
    }
    for (int i = 0; i < 3 * nx * ny; i++) {
    retry_minus:
      int x = x_dist(rng);
      int y = y_dist(rng);
      if (!(data[(y * nx + x) * 3 + c] > std::numeric_limits<float>::epsilon()))
        goto retry_minus;
      data[(y * nx + x) * 3 + c] -= std::numeric_limits<float>::epsilon();
    }
  }

  return {
      {color[0], color[1], color[2]}, data, ny, nx, rect,
  };
}

static TestCase generate_color_rects(int ny, int nx, int sy, int sx) {
  std::mt19937 rng;
  for (int i = 0; i < ny * 10000 + nx; i++)
    rng();
  Rect rect = random_rect(rng, ny, nx, sy, sx);
  std::uniform_real_distribution<float> color_dist(0.0f, 1.0f);

  std::vector<double> data(3 * nx * ny);
  double r = 0.0;
  double g = 0.0;
  double b = 0.0;
  for (int i = 0; i < 100; i++) {
    Rect new_rect = random_rect(rng, ny, nx, -1, -1);
    float color[3] = {color_dist(rng), color_dist(rng), color_dist(rng)};
    for (int y = new_rect.y0; y < new_rect.y1; y++) {
      for (int x = new_rect.x0; x < new_rect.x1; x++) {
        data[(y * nx + x) * 3 + 0] += color[0];
        data[(y * nx + x) * 3 + 1] += color[1];
        data[(y * nx + x) * 3 + 2] += color[2];
      }
    }
    double size = std::max(0, std::min(new_rect.x1, rect.x1) -
                                  std::max(new_rect.x0, rect.x0)) *
                  std::max(0, std::min(new_rect.y1, rect.y1) -
                                  std::max(new_rect.y0, rect.y0));
    r += size * color[0];
    g += size * color[1];
    b += size * color[2];
  }

  double r_scale = 0.0;
  double g_scale = 0.0;
  double b_scale = 0.0;
  for (int i = 0; i < nx * ny; i++) {
    r_scale = std::max(r_scale, data[3 * i + 0]);
    g_scale = std::max(g_scale, data[3 * i + 1]);
    b_scale = std::max(b_scale, data[3 * i + 2]);
  }
  r_scale = 1.0 / r_scale;
  g_scale = 1.0 / g_scale;
  b_scale = 1.0 / b_scale;
  for (int i = 0; i < nx * ny; i++) {
    data[3 * i + 0] *= r_scale;
    data[3 * i + 1] *= g_scale;
    data[3 * i + 2] *= b_scale;
  }
  r_scale /= (rect.x1 - rect.x0) * (rect.y1 - rect.y0);
  g_scale /= (rect.x1 - rect.x0) * (rect.y1 - rect.y0);
  b_scale /= (rect.x1 - rect.x0) * (rect.y1 - rect.y0);

  std::vector<float> fdata(3 * nx * ny);
  std::copy(data.begin(), data.end(), fdata.begin());

  return {
      {float(r * r_scale), float(g * g_scale), float(b * b_scale)},
      fdata,
      ny,
      nx,
      rect,
  };
}

static bool test(int ny, int nx, int mode, int sy, int sx, bool verbose) {
  TestCase test_case;
  switch (mode) {
  case 1:
    test_case = generate_all_equal(ny, nx, sy, sx);
    break;
  case 2:
    test_case = generate_gradient(ny, nx, sy, sx);
    break;
  case 3:
    test_case = generate_small_noise(ny, nx, sy, sx);
    break;
  case 4:
    test_case = generate_color_rects(ny, nx, sy, sx);
    break;
  default:
    error("unknown MODE");
  }

  const Result result =
      calculate(ny, nx, test_case.input.data(), test_case.rect.y0,
                test_case.rect.x0, test_case.rect.y1, test_case.rect.x1);

  const float error =
      std::max({std::abs(result.avg[0] - test_case.expected[0]),
                std::abs(result.avg[1] - test_case.expected[1]),
                std::abs(result.avg[2] - test_case.expected[2])});

  const bool pass = error <= THRESHOLD;
  std::cout << std::setw(6) << std::setprecision(4) << std::fixed
            << error / THRESHOLD << ' ';

  if (verbose) {
    if (ny < 25 && nx < 25) {
      std::cout << "\ninput:\n";
      print(ny, nx, test_case.rect, test_case.input.data());
      std::cout << "\n  y0: " << test_case.rect.y0 << '\n';
      std::cout << "  x0: " << test_case.rect.x0 << '\n';
      std::cout << "  y1: " << test_case.rect.y1 << '\n';
      std::cout << "  x1: " << test_case.rect.x1 << '\n';
    }
    std::cout << "\nexpected:\n  ";
    print_color(test_case.expected);
    std::cout << "\n\ngot:\n  ";
    print_color(result.avg);
    std::cout << "\n\n";
  }

  return pass;
}

static bool has_fails = false;
static struct {
  int ny;
  int nx;
  int mode;
} first_fail = {};
static int passcount = 0;
static int testcount = 0;

static void run_test(int ny, int nx, int mode, int sy, int sx, bool verbose) {
  std::cout << "average-test " << std::setw(4) << ny << ' ' << std::setw(4)
            << nx << ' ' << std::setw(1) << mode << ' ' << std::flush;
  const bool pass = test(ny, nx, mode, sy, sx, verbose);

  std::cout << (pass ? "OK\n" : "ERR\n");
  if (pass) {
    passcount++;
  } else if (!has_fails) {
    has_fails = true;
    first_fail.ny = ny;
    first_fail.nx = nx;
    first_fail.mode = mode;
  }
  testcount++;
}

int main(int argc, const char **argv) {
  if (argc == 1) {
    // Run the whole suite
    for (int ny : {1, 2, 3, 5, 10, 50, 100, 1000}) {
      for (int nx : {1, 2, 3, 5, 10, 50, 100, 1000}) {
        run_test(ny, nx, 1, -1, -1, false);
        run_test(ny, nx, 2, -1, -1, false);
        run_test(ny, nx, 3, -1, -1, false);
        run_test(ny, nx, 4, -1, -1, false);
      }
    }

    std::cout << passcount << '/' << testcount << " tests passed.\n";
    if (has_fails) {
      std::cout << "To repeat the first failed test with more output, run:\n"
                << argv[0] << " " << first_fail.ny << " " << first_fail.nx
                << " " << first_fail.mode << std::endl;
      exit(EXIT_FAILURE);
    }
  } else if (argc == 4) {
    // Run a specific test
    int ny = std::stoi(argv[1]);
    int nx = std::stoi(argv[2]);
    int mode = std::stoi(argv[3]);
    run_test(ny, nx, mode, -1, -1, true);
    if (has_fails) {
      exit(EXIT_FAILURE);
    }
  } else if (argc == 6) {
    // Run a specific test
    int ny = std::stoi(argv[1]);
    int nx = std::stoi(argv[2]);
    int mode = std::stoi(argv[3]);
    int sy = std::stoi(argv[4]);
    int sx = std::stoi(argv[5]);
    run_test(ny, nx, mode, sy, sx, true);
    if (has_fails) {
      exit(EXIT_FAILURE);
    }
  } else {
    std::cout << "Usage:\n  average-test\n  average-test <ny> <nx> <mode>\n  "
                 "average-test <ny> <nx> <mode> <sy> <sx>\n";
  }
}