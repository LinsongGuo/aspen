#include <chrono>
#include <iostream>
#include <sstream>
#include <x86intrin.h>
#include <cmath>

#include "uintr.h"
#include "runtime.h"
#include "sync.h"
#include "thread.h"
#include "timer.h"

#include <DataFrame/DataFrame.h>                   // Main DataFrame header
#include <DataFrame/DataFrameFinancialVisitors.h>  // Financial algorithms
#include <DataFrame/DataFrameMLVisitors.h>         // Machine-learning algorithms
#include <DataFrame/DataFrameStatsVisitors.h>      // Statistical algorithms
#include <DataFrame/Utils/DateTime.h>              // Cool and handy date-time object


long long now() {
	struct timespec ts;
	timespec_get(&ts, TIME_UTC);
	return ts.tv_sec * 1e9 + ts.tv_nsec;
}

// DataFrame library is entirely under hmdf name-space
using namespace hmdf;

// A DataFrame with ulong index type
using ULDataFrame = StdDataFrame<unsigned long>;

// A DataFrame with string index type
using StrDataFrame = StdDataFrame<std::string>;

// A DataFrame with DateTime index type
using DTDataFrame = StdDataFrame<DateTime>;


barrier_t barrier;

DTDataFrame ibm_dt_df;

void init() {
    ibm_dt_df.read("DataFrame/data/DT_IBM.csv", io_format::csv);

    // First let’s make sure if there are missing data in our important columns, we fill them up.
    ibm_dt_df.fill_missing<double>({ "IBM_Close", "IBM_Open", "IBM_High", "IBM_Low" },
                                   fill_policy::linear_interpolate);
                                   
    // Calculate the returns and load them as a column.
    ReturnVisitor<double>   return_v { return_policy::log };
    // const auto              &return_result =
    //     ibm_dt_df.single_act_visit<double>("IBM_Close", return_v).get_result();
    // ibm_dt_df.load_column("IBM_Return", std::move(return_result));

    ibm_dt_df.single_act_visit<double>("IBM_Close", return_v);
    ibm_dt_df.load_result_as_column(return_v, "IBM_Return");
    ibm_dt_df.get_column<double>("IBM_Return")[0] = 0;  // Remove the NaN
}

double do_max() {
    MaxVisitor<double, DateTime> max_v;
    ibm_dt_df.single_act_visit<double>("IBM_Close", max_v);
    double mx = max_v.get_result();
    return mx;
}

double do_kmeans() {
    KMeansVisitor<4, double, DateTime>  kmeans_v { 1000 };  // Iterate at most 1000 times.
    ibm_dt_df.single_act_visit<double>("IBM_Return", kmeans_v);
    const auto &cluster_means = kmeans_v.get_result();
    return cluster_means[0];
}

double do_decom() {
    // DecomposeVisitor<double, DateTime>  decom { 170, 0.1, 0.01 };
    // ibm_dt_df.single_act_visit<double>("IBM_Return", decom);
    // return decom.get_seasonal()[0];
    return 0;
}

const unsigned N = 1000;
double loop_max() {
    double res;
    for (unsigned i = 0; i < N * 430; ++i) {
        res = do_max();
    }
    return res;
}

std::vector<double> kmeans_res;
double loop_kmeans() {
    double res;
    for (unsigned i = 0; i < N; ++i) {
        res = do_kmeans();
        kmeans_res.push_back(res);
    }
    return res;
}

double loop_decom() {
    double res;
    for (unsigned i = 0; i < N; ++i) {
        res = do_decom();
        // kmeans_res.push_back(res);
    }
    return res;
}

typedef double (*task_type)(void);
const unsigned TASK_NUM = 3;
std::string task_name_options[TASK_NUM] = {"max", "kmeans", "decom"};
task_type task_ptr_options[TASK_NUM] = {loop_max, loop_kmeans, loop_decom};
unsigned task_num = 0;
std::string task_name[10];
task_type task_ptr[10];

task_type name2ptr(std::string name) {
	task_type ptr = nullptr;
	for (unsigned i = 0; i < TASK_NUM; ++i) {
		if (name == task_name_options[i]) {
			ptr = task_ptr_options[i];
		}
	}
    BUG_ON(ptr == nullptr);
	return ptr;
}

void parse(std::string input) {
    char delimiter = '+';
    std::stringstream ss(input);
    std::string name, num_;

	while(getline(ss, name, delimiter)) {
        task_name[task_num] = name;
		task_ptr[task_num++] = name2ptr(name);  
    }

	std::cout << "tasks:";
    for (unsigned i = 0; i < task_num; ++i) {
        std::cout << ' ' << task_name[i];
    }
	std::cout << std::endl;
}


void MainHandler_local(void *arg) {	
    rt::WaitGroup wg(task_num);
	barrier_init(&barrier, 1);
		
    init();

    double results[10];

    rt::UintrTimerStart();    

    for (unsigned i = 0; i < task_num; ++i) {
        rt::Spawn([&, i]() {
            results[i] = task_ptr[i]();
            wg.Done();
        });
    }

    wg.Wait();
	rt::UintrTimerEnd();
	rt::UintrTimerSummary();


    std::cout << "Results: ";
    for (unsigned i = 0; i < task_num; ++i) {
        std::cout << results[i] << ' ';
    }
    std::cout << std::endl;

    // rt::Spawn([&]() {
    //     res1 = loop_max();
    //     wg.Done();
    // });
	
    // rt::Spawn([&]() {
    //     res2 = loop_kmeans();
    //     wg.Done();
    // });
	
    for (unsigned i = 0; i < N; ++i) {
        std::cout << kmeans_res[i] << ' ';
    }
    // std::cout << std::endl;
    // long long start = now();
    // double res = do_max();
    // long long end = now();
    // std::cout << "max: " << res << ' ' << end - start << std::endl;

    // start = now();
    // res = do_kmeans();
    // end = now();
    // std::cout << "k-means: " << res << ' ' << end - start << std::endl;

    // start = now();
    // loop_max();
    // end = now();
    // std::cout << "loop max: " << end - start << std::endl;

    // start = now();
    // loop_kmeans();
    // end = now();
    // std::cout << "loop k-means: " << end - start << std::endl;
}


int main(int argc, char *argv[]) {
	int ret;
	
	if (argc != 3) {
		std::cerr << "usage: [config_file] [work_spec]"
              << std::endl;
		return -EINVAL;
	}

    std::string task_spec = std::string(argv[2]);
	parse(task_spec);
	ret = runtime_init(argv[1], MainHandler_local, NULL);

	if (ret) {
		printf("failed to start runtime\n");
		return ret;
	}
	
	return 0;
}
