#!/usr/bin/env python3

import datetime
import json
import os
import platform
import socket
import subprocess
import sys
import textwrap

# Constants
inf = float("inf")

# Course setup

WEEK0 = (2020, 15)
WEEKS = 6
MAARI_A = 'albatrossi, broileri, dodo, drontti, emu, fasaani, flamingo, iibis, kakadu, kalkkuna, karakara, kasuaari, kiuru, kiwi, kolibri, kondori, kookaburra, koskelo, kuikka, lunni, moa, pelikaani, piekana, pulu, ruokki, sorsa, strutsi, suula, tavi, tukaani, undulaatti'.split(', ')
MAARI_C = 'akaatti, akvamariini, ametisti, baryytti, berylli, dioptaasi, fluoriitti, granaatti, hypersteeni, jade, jaspis, karneoli, korundi, kuukivi, lapislatsuli, malakiitti, meripihka, opaali, peridootti, rubiini, safiiri, sitriini, smaragdi, spektroliitti, spinelli, timantti, topaasi, turkoosi, turmaliini, vuorikide, zirkoni'.split(', ')

HOSTS = set()

for host in MAARI_A + MAARI_C:
    HOSTS.add(host + '.aalto.fi')
    HOSTS.add(host + '.org.aalto.fi')

URL_BASE = 'http://ppc.cs.aalto.fi/2020/'

# Task setup

REPORT = 'report.pdf'

class default:
    MAX = [5,3]

    # Before each test iteration, a command list from here is run
    TEST_DEBUG_COMMAND_LISTS_CPU = [
        [['make', 'clean'], ['make', '-j', 'DEBUG=2']],
        [['make', 'clean'], ['make', '-j']],
    ]

    TEST_DEBUG_COMMAND_LISTS_GPU = [
        [['make', 'clean'], ['make', '-j']],
    ]

CPU_BASELINE = 'Implement a simple *sequential* baseline solution. Make sure it works correctly. Do not use any form of parallelism yet.'
CPU_FAST = 'Using all resources that you have in the CPU, solve the task *as fast as possible*. You are encouraged to exploit instruction-level parallelism, multithreading, and vector instructions whenever possible, and also to optimize the memory access pattern.'
GPU_BASELINE = 'Implement a simple baseline solution for the *GPU*. Make sure it works correctly and that it is reasonably efficient. Make sure that all performance-critical parts are executed on the GPU; you can do some lightweight preprocessing and postprocessing also on the CPU.'
GPU_FAST = 'Using all resources that you have in the *GPU*, solve the task *as fast as possible*.'
DOUBLE = 'Please do all arithmetic with *double-precision* floating point numbers.'
SINGLE = 'In this task, you are permitted to use *single-precision* floating point numbers.'
SOURCE_AND_REPORT = 'Your submission has to contain the source code of your implementation and a written report.'
AT_LEAST_REPORT = 'Your submission has to contain at least a written report.'

TASKS = [
    {
        'id': 'prereq',
        'title': 'Prerequisite test',
        'descr': [
            CPU_BASELINE,
            DOUBLE,
        ],
        'benchmark': ['./average-benchmark', '2000', '2000', '1500', '1500'],
        'benchmarktest': ['./average-test', '2000', '2000', '4', '1500', '1500'],
        'max': [0, 0],
        'time': [0.2],
        'week': 1,
    },
]

# Generic

class col:
    reset = '\033[0m'
    error = '\033[31;1m'
    good = '\033[34;1m'
    task = '\033[35;1m'
    bold = '\033[1m'
    cmd = '\033[34m'

def warning(s):
    print('\n' + col.error + s + col.reset + '\n')

def error(s):
    sys.exit('\n' + col.error + s + col.reset + '\n')

def pcmd(c, indent=0):
    print(" " * indent + col.cmd + " ".join(c) + col.reset)

def ptask(task):
    print()
    print(col.task + "TASK {}: {}".format(task.id.upper(), task.title) + col.reset)
    print(col.cmd + task.url + col.reset)
    print()

def plural(x,l):
    if x == 1:
        return "{} {}".format(x,l)
    else:
        return "{} {}s".format(x,l)

def weeks(x):
    return plural(x, "week")

def week_range(x,y):
    if x == y:
        return "week {}".format(x)
    else:
        return "weeks {}-{}".format(x,y)

def print_run(c, output=False, timelimit=inf):
    print()
    pcmd(c)
    try:
        if output:
            return subprocess.check_output(c, timeout=min(timelimit, 600)).decode('utf-8')
        else:
            subprocess.check_call(c, timeout=timelimit)
    except subprocess.TimeoutExpired:
        error("Command {} took too long".format(" ".join(c)))
    except:
        error("Command '{}' failed".format(" ".join(c)))

def read_benchmarkfile():
    with open("benchmark.run", "r") as benchmarksfile:
        ret = [float(x) for x in benchmarksfile.read().split('\n') if len(x) > 0]
    return ret

# Runs command and retuns the results of "benchmarks.run" file as array of float
def run_timed(c, timelimit=inf):
    print()
    pcmd(c)
    ppc_env = os.environ
    ppc_env["PPC_BENCHMARK"] = "1"
    try:
        subprocess.check_call(c, timeout=timelimit, env=ppc_env)
        ret = read_benchmarkfile();
    except subprocess.TimeoutExpired:
        error("Command {} took too long".format(" ".join(c)))
    except:
        error("Command '{}' failed".format(" ".join(c)))
    finally:
        if os.path.exists("benchmark.run"):
            os.remove("benchmark.run")
    return ret



def dnone(x, s=""):
    return s if x is None else "{:d}".format(x)



class Result:
    def __init__(self, task, i):
        self.index = i
        self.week = i + 1
        self.task = task
        sfile = 'submission-{}.txt'.format(self.week)
        ffile = 'feedback-{}.txt'.format(self.week)
        self.sfile_short = os.path.join(task.id, sfile)
        self.ffile_short = os.path.join(task.id, ffile)
        self.sfile = os.path.join(task.path, sfile)
        self.ffile = os.path.join(task.path, ffile)
        self.submission = None
        self.feedback = None
        self.max = task.get_max(self.week)
        try:
            with open(self.sfile) as f:
                self.submission = float(f.readline().rstrip())
            with open(self.ffile) as f:
                self.feedback = int(f.readline().rstrip())
        except IOError:
            pass
        self.automatic = None
        self.final = None
        if self.submission is not None:
            self.automatic = task.score(self.week, self.submission)
        if self.automatic is not None and self.feedback is not None:
            self.final = self.automatic + self.feedback


class Task:
    def __init__(self, grading, t):
        self.grading = grading
        self.id = t['id']
        self.report = t.get('report', False)
        self.title = t['title']
        self.descr = t['descr']
        self.contest = t.get('contest', False)
        if not self.report:
            self.gpu = t.get('gpu', False)
            self.benchmark = t['benchmark']
            self.benchmarktest = t.get('benchmarktest', None)
            self.time = t['time']
            self.timelimit = t.get('timelimit', self.time[-1] * 2.5)
        self.max = t.get('max', default.MAX)
        assert len(self.max) == 2
        self.range = max(self.max)
        self.week = t.get('week', WEEKS)
        if self.week == WEEKS:
            self.max = self.max[:1]
        # assert len(self.id) <= 4
        self.family = self.id
        if self.family == 'prereq':
            self.url = URL_BASE + 'test' + "/"
        else:
            self.url = URL_BASE + self.family + "/"
        self.path = grading.root

        if self.report:
            self.filename = os.path.join(self.path, REPORT)

        self.week_ranges = []
        for j,m in enumerate(self.max):
            if j == 0:
                w1 = 1
                w2 = self.week
            else:
                w1 = self.week + 1
                w2 = WEEKS
            self.week_ranges.append([w1, w2])
        self.point_table = [] # array of type: [points, [limit, limit (late)]]

        if self.report: # for reports any time is ok
            self.point_table = [[self.range-x, [inf]] for x in range(self.max[0])]
        else:
            for point_i in range(self.range):
                points = self.range-point_i;
                row = [] # row to append to point table
                # process on-time case
                row.append(self.time[point_i])
                # late case
                if self.week != WEEKS:
                    late_point_i = self.max[-1] - points
                    if late_point_i < 0:
                        row.append(None)
                    elif late_point_i < len(self.time):
                        row.append(self.time[late_point_i])
                    else:
                        row.append(self.time[-1])
                self.point_table.append([points, row]);

    def export(self):
        r = {
            'id': self.id,
            'family': self.family,
            'report': self.report,
            'max': self.max,
            'range': self.range,
            'week': self.week,
            'url': self.url,
            'title': self.title,
            'descr': self.descr,
        }
        if not self.report:
            r['gpu'] = self.gpu
            r['contest'] = self.contest
            r['time'] = self.time
        return r

    def get_results(self):
        self.results = [Result(self, -1)]

    def get_max(self, week):
        if week <= self.week:
            return self.max[0]
        else:
            return self.max[1]

    def score(self, week, time):
        if self.report:
            assert time == 0
            return 0
        assert time > 0
        col = 0 if week <= self.week else 1
        for p, row in self.point_table:
            t = row[col]
            if t is not None and time < t:
                return p
        return 0


    # Run tests for a task
    def test(self):
        if self.family == "cp":
            print_run(['./cp-test'])
        elif self.family == "mf":
            print_run(['./mf-test'])
        elif self.family == "is":
            if self.id == "is6a" or self.id == "is6b":
                print_run(['./is-test', 'binary'])
            else:
                print_run(['./is-test'])
        elif self.family == "so":
            print_run(['./so-test'])
        elif self.family == "nn":
            print_run(['./nn-test'])
        elif self.family == "prereq":
            print_run(['./average-test'])
        else:
            error("Tests for task not found")
        print(col.good + "Test OK" + col.reset)



    # Run tests with all debug combinations
    def test_with_debug(self):
        command_list_array = default.TEST_DEBUG_COMMAND_LISTS_GPU if self.gpu else default.TEST_DEBUG_COMMAND_LISTS_CPU
        for command_list in command_list_array:
            for command in command_list:
                print_run(command)
            self.test()

    def run_benchmarktest(self):
        if self.benchmarktest != None:
            print("\nRunning test with benchmark size:")
            print_run(self.benchmarktest)
            print(col.good + "Test OK" + col.reset)



class Grading:
    def __init__(self):
        # Directories
        try:
            self.root = os.getcwd()
        except:
            error("Sorry, I could not find the current working directory")

        # Tasks
        self.all_tasks = [t['id'] for t in TASKS]
        self.task_map = {t['id']: Task(self, t) for t in TASKS}
        assert len(self.all_tasks) == len(self.task_map)
        self.current_task = 'prereq'

        # Computers
        try:
            self.host = subprocess.check_output(['hostname', '-f']).decode('utf-8').rstrip('\n')
        except:
            error("Sorry, I could not figure out the hostname of this computer")
        self.system = platform.system()
        self.valid_host = self.host in HOSTS and self.system == 'Linux'
        if 'PPC_FORCE' in os.environ:
            self.valid_host = True

        # Date
        override = os.environ.get('PPC_DATE')
        if override is not None:
            date = datetime.datetime.strptime(override, "%Y-%m-%d")
        else:
            date = datetime.date.today()
        year, week, day = date.isocalendar()
        year0, week0 = WEEK0
        self.outside = 0
        self.week = 0
        if year < year0:
            self.outside = -1
            self.week_label = 'wrong year'
        elif year > year0:
            self.outside = +1
            self.week_label = 'wrong year'
        else:
            offset = week - week0
            if offset <= 0:
                self.outside = -1
                self.week_label = '{} before the course starts'.format(weeks(1 - offset))
            elif offset > WEEKS:
                self.outside = +1
                self.week_label = '{} after the course ends'.format(weeks(offset - WEEKS))
            else:
                # self.week = offset
                self.week_label = 'week {} of the course'.format(offset)

    def task_table(self, task, time=None):
        cell = "{:18s}"
        print("         ", end=' ')
        for x,y in task.week_ranges:
            print(cell.format(week_range(x,y)), end=' ')
        print()
        print()
        for p, row in task.point_table:
            print("  {:2d} pt: ".format(p), end=' ')
            for t in row:
                if t is None:
                    v = "-"
                elif t == inf:
                    if task.report:
                        v = "+"
                    else:
                        v = "any time"
                else:
                    v = "time < {:.1f}".format(t)
                if t is not None and time is not None:
                    if time < t:
                        print(col.good + cell.format(v) + col.reset, end=' ')
                    else:
                        print(col.error + cell.format(v) + col.reset, end=' ')
                else:
                    print(cell.format(v), end=' ')
            print()
        print()

    def task_table_compact(self, task):
        for i,m in enumerate(task.max):
            x,y = task.week_ranges[i]
            print("  {}:  {}-{} pt".format(week_range(x,y), 0, m))
        print()

    def info(self, tasks):
        for taskid in tasks:
            task = self.task_map[taskid]
            ptask(task)
            for descr in task.descr:
                print(textwrap.fill(descr.replace("*", "").replace("_", "")))
                print()

            if task.report:
                print("This is an open-ended task.")
                print("I will just check that the following file exists:")
                print()
                pcmd([task.filename], 2)
                print()
                print("The grading scale is:")
                print()
                self.task_table_compact(task)
            else:
                print("For grading, I will use the following command:")
                print()
                pcmd(task.benchmark, 2)
                print()
                # print("It should print {} with {}".format(
                #     plural(task.rows, 'row'),
                #     plural(task.columns, 'column'),
                # ))
                # print("The relevant part is at row {}, column {}.".format(
                #     task.trow + 1,
                #     task.tcol + 1,
                # ))
                # print("The grading thresholds are:")
                # print()
                # self.task_table(task)

    def overview(self, tasks):
        print()
        print("Maximum score for each task and each week:")
        print()
        print(col.bold + "week:      ", end=' ')
        for w in range(1, WEEKS+1):
            print("{:2d}".format(w), end=' ')
        print(col.reset)
        print("           ", end=' ')
        for w in range(1, WEEKS+1):
            m = ""
            if self.week is not None and self.week == w:
                m = "*"
            print("{:>2s}".format(m), end=' ')
        print()
        family = None
        for taskid in tasks:
            task = self.task_map[taskid]
            if task.family != family:
                if family is not None:
                    print()
                family = task.family
            print(col.bold + "{:5s} ".format(taskid + ":") + col.reset, end=' ')
            if task.report:
                special = ''
            elif task.gpu:
                special = 'gpu'
            else:
                special = 'cpu'
            print('{:4s}'.format(special), end=' ')
            for w in range(1, WEEKS+1):
                x = task.get_max(w)
                v = "{:2d}".format(x)
                if x < task.range:
                    print(v, end=' ')
                else:
                    print(col.good + v + col.reset, end=' ')
            print()
        print()

    def export(self, tasks):
        r = { taskid: self.task_map[taskid].export() for taskid in tasks }
        json.dump(r, sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write('\n')

    def save(self, task, time):
        w = self.week
        assert w is not None
        task.get_results()
        r = task.results[w-1]
        if task.report:
            assert time == 0
            if r.submission is not None:
                assert r.submission == 0
                print("You have apparently already submitted this task, skipping.")
                print()
                return
        else:
            assert time > 0
            if r.submission is not None and r.submission <= time:
                assert r.submission > 0
                print("You have already submitted this task with a better running time: {}".format(r.submission))
                print("Delete {} if you really want to overwrite it.".format(r.sfile_short))
                print()
                return
        try:
            with open(r.sfile, 'w') as f:
                f.write('{}\n'.format(time))
        except:
            sys.exit("Could not create {}".format(r.sfile_short))
        print("Your submission is now stored in the following file:")
        print()
        pcmd([r.sfile], 2)
        print()
        print("Please add, commit, and " + col.error + "push it to Github" + col.reset + ", together with the source code.")
        print("Remember that only what is successfully pushed to Github counts.")
        print()

    def show(self, tasks):
        print()
        print("? = tasks waiting for grading")
        print()
        print(col.bold + "Task   Week   Time   Points + Feedback = Total   Max" + col.reset)
        print()
        total = 0
        maxtotal = 0
        for taskid in tasks:
            task = self.task_map[taskid]
            task.get_results()
            idprint = task.id
            best = 0
            best_time = inf
            for r in task.results:
                if r.submission is not None:
                    print("{t}{:<4s}{n}   {:<4d} {:>6}    {:>4}  +  {:<4}    = {b}{:<5}{n}   {}".format(
                        idprint,
                        r.week,
                        "-" if task.report else "{:.1f}".format(r.submission),
                        r.automatic,
                        dnone(r.feedback, "?"),
                        dnone(r.final, "?"),
                        r.max,
                        b=col.bold,
                        t=col.task,
                        n=col.reset,
                    ))
                    if r.final is not None:
                        best = max(best, r.final)
                    best_time = min(best_time, r.submission)
                    idprint = ""
            tprint = ""
            if not task.report and best_time < inf:
                tprint = "{:.1f}".format(best_time)
            print("{t}{:<4s}{n}   best {:>6}                       {b}{:<5}{n}   {}".format(
                idprint,
                tprint,
                best,
                task.range,
                b=col.bold,
                t=col.task,
                n=col.reset,
            ))
            print()
            total += best
            maxtotal += task.range
        print("{b}total                                    {:<5}   {}{n}".format(
            total, maxtotal,
            b=col.bold,
            t=col.task,
            n=col.reset,
        ))
        print()


    def export_score(self, tasks):
        result = {}
        for taskid in tasks:
            task = self.task_map[taskid]
            task.get_results()
            for r in task.results:
                if r.submission is not None:
                    if task.id not in result:
                        result[task.id] = {}
                    result[task.id][r.week] = {
                        'submission': r.submission,
                        'automatic': r.automatic,
                        'feedback': r.feedback,
                        'final': r.final,
                    }
        json.dump(result, sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write('\n')

    def submit(self, tasks):
        if self.outside:
            error("The course is not currently open")
        for taskid in tasks:
            task = self.task_map[taskid]
            ptask(task)
            if not task.report:
                print("Normal task, skipping (try 'do').")
                print()
                continue
            print("Checking that the following file exists:")
            print()
            pcmd([task.filename], 2)
            if not os.path.exists(task.filename):
                error("Could not find {}".format(task.filename))
            print()
            print("Looks good.")
            print()
            self.save(task, 0)

    def do(self, tasks, dryrun=False, skiptest=False):
        # if self.outside:
        #     if not dryrun:
        #         error("The course is not currently open; try 'dryrun'")
        if not self.valid_host:
            if not dryrun:
                error("This does not seem to be a valid classroom computer; try 'dryrun'")
            else:
                warning("This does not seem to be a valid classroom computer, but proceeding anyway...")
        loads = os.getloadavg()
        high_load = loads[0] > 1
        print()
        print("Load average for 1 min: {b}{:.2f}{n},  5 min: {b}{:.2f}{n},  15 min: {b}{:.2f}{n}".format(
            *loads, b=col.bold, n=col.reset
        ))
        if high_load:
            warning("System load is fairly high, careful!")
        for taskid in tasks:
            task = self.task_map[taskid]
            try:
                ptask(task)
                if task.report:
                    print("Open-ended task, skipping (try 'submit').")
                    continue
                print("Running tests...")
                print()
                pcmd(["cd", task.path])
                try:
                    os.chdir(task.path)
                except:
                    error("Could not enter directory {}".format(task.path))
                if not skiptest:
                    task.test_with_debug()
                    task.run_benchmarktest()

                output = run_timed(task.benchmark, timelimit=task.timelimit)
                time = output[-1]
                print()
                print("Success! Your running time: {}{}{}".format(col.bold, time, col.reset))
                # print("The grading thresholds are:")
                # print()
                # self.task_table(task, time)
                if not dryrun:
                    self.save(task, time)

            except Exception as e:
                error("{}: {}".format(type(e).__name__, str(e)))

            except KeyboardInterrupt:
                error("Interrupted")

        if high_load:
            warning("System load was fairly high when you started grading, careful!")

    def test(self, tasks):
        for taskid in tasks:
            task = self.task_map[taskid]
            pcmd(["cd", task.path])
            try:
                os.chdir(task.path)
            except:
                error("Could not enter directory {}".format(task.path))
            task.test()
            print(col.good + "Tests passed" + col.reset)

    def ui(self):
        args = sys.argv[1:]
        if len(args) == 0:
            self.help()
            return
        cmd = args[0]
        tasks = args[1:]
        if len(tasks) == 0:
            if self.current_task is None:
                error("No task specified")
            else:
                tasks = [self.current_task]
        elif tasks == ['all']:
            tasks = self.all_tasks
        elif tasks == ['cpu']:
            tasks = [t for t in self.all_tasks if not self.task_map[t].report and not self.task_map[t].gpu]
        elif tasks == ['gpu']:
            tasks = [t for t in self.all_tasks if not self.task_map[t].report and self.task_map[t].gpu]
        elif tasks == ['contest']:
            tasks = [t for t in self.all_tasks if not self.task_map[t].report and self.task_map[t].contest]
        for t in tasks:
            if t not in self.task_map:
                error("Unknown task: {}".format(t))
        if cmd == 'info':
            self.info(tasks)
        # elif cmd == 'overview':
        #     self.overview(tasks)
        # elif cmd == 'show':
        #     self.show(tasks)
        elif cmd == 'do':
            self.do(tasks)
        elif cmd == 'dryrun':
            self.do(tasks, dryrun=True)
        elif cmd == 'benchmark':
            self.do(tasks, dryrun=True, skiptest=True)
        # elif cmd == 'submit':
        #     self.submit(tasks)
        # elif cmd == 'export':
        #     self.export(tasks)
        # elif cmd == 'export-score':
        #     self.export_score(tasks)
        elif cmd == 'test':
            self.test(tasks)
        else:
            error("Unknown command: {}".format(cmd))

    def help(self):
        loads = os.getloadavg()
        print("""
Usage: grading COMMAND [TASK ...]

    grading info      - Show information on the task

    grading do        - Do grading
    grading dryrun    - Do grading but do not record the result
    grading benchmark - Run benchmark without re-compiling
    grading test      - Run tests without re-compiling

Status:

  - root directory of your repository: {root}
  - computer: {host}, {system} ({valid_host})
  - load averages: {l1:.2f}, {l5:.2f}, {l15:.2f}
  - date: {week}

Workflow:   {url}workflow/
Cheatsheet: {url}workflow/cheatsheet/
""".format(
            current_task="not specified" if self.current_task is None else self.current_task,
            all_tasks=" ".join(self.all_tasks),
            host=self.host,
            system=self.system,
            valid_host='valid' if self.valid_host else 'not valid',
            root=self.root,
            week=self.week_label,
            l1=loads[0],
            l5=loads[1],
            l15=loads[2],
            url=URL_BASE,
        ))


Grading().ui()
