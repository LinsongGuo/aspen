extern "C" {
#include <base/byteorder.h>
#include <base/log.h>
#include <runtime/runtime.h>
#include <runtime/udp.h>
#include <runtime/uintr.h>
}

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


// DataFrame library is entirely under hmdf name-space
using namespace hmdf;

// A DataFrame with ulong index type
using ULDataFrame = StdDataFrame<unsigned long>;

// A DataFrame with string index type
using StrDataFrame = StdDataFrame<std::string>;

// A DataFrame with DateTime index type
using DTDataFrame = StdDataFrame<DateTime>;

struct Payload {
  uint32_t id;
  uint32_t req_type;
  uint32_t reqsize;
  uint32_t run_ns;
};
static netaddr listen_addr;

// barrier_t barrier;

DTDataFrame ibm_dt_df;
char* df_input;

void init() {
    // ibm_dt_df.read("DataFrame/data/DT_IBM.csv", io_format::csv2);
    std::ifstream file(df_input); 
    if (!file) {
        std::cerr << "Error: Unable to open file " << df_input << std::endl;
        return;
    }
    ibm_dt_df.read(file, io_format::csv2);

    // First let’s make sure if there are missing data in our important columns, we fill them up.
    ibm_dt_df.fill_missing<double, 4>({ "IBM_Close", "IBM_Open", "IBM_High", "IBM_Low" },
                                   fill_policy::fill_forward);
                                   
    // Calculate the returns and load them as a column.
    ReturnVisitor<double>   return_v { return_policy::log };
    const auto              &return_result =
        ibm_dt_df.single_act_visit<double>("IBM_Close", return_v).get_result();
    ibm_dt_df.load_column("IBM_Return", std::move(return_result));

    // ibm_dt_df.single_act_visit<double>("IBM_Close", return_v);
    // ibm_dt_df.load_result_as_column(return_v, "IBM_Return");
    ibm_dt_df.get_column<double>("IBM_Return")[0] = 0;  // Remove the NaN
}

double do_max() {
    MaxVisitor<double, DateTime> max_v;
    ibm_dt_df.single_act_visit<double>("IBM_Close", max_v);
    double mx = max_v.get_result();
    return mx;
}

double do_kmeans() {
    KMeansVisitor<4, double, DateTime>  kmeans_v { 10 };  // Iterate at most 1000 times.
    ibm_dt_df.single_act_visit<double>("IBM_Return", kmeans_v);
    const auto &cluster_means = kmeans_v.get_result();
    double res = cluster_means[0];
    // assert (fabs(res - 0.008) < 0.01);
    return res;
}

double do_decom() {
    DecomposeVisitor<double, DateTime>  decom { 170, 0.01, 1 };
    // preempt_disable();
    ibm_dt_df.single_act_visit<double>("IBM_Return", decom);
    // preempt_enable();
    return decom.get_seasonal()[2000];
}

double do_decay() {
    DecayVisitor<double, DateTime>  decay(5, true);
    ibm_dt_df.single_act_visit<double>("IBM_Close", decay);
    double res = decay.get_result()[2000];
    // assert (fabs(res - 124.913) < 0.01);
    return res;
}

double do_ad() {
    AccumDistVisitor<double, DateTime>  ad;
    ibm_dt_df.single_act_visit<double, double, double, double, long>("IBM_Low", "IBM_High", "IBM_Open", "IBM_Close", "IBM_Volume", ad);
    double res = ad.get_result()[2000];
    // assert (fabs(res - 941602377.791) < 0.01);
    return res;
}

double do_ppo() {
    PercentPriceOSCIVisitor<double, DateTime>  ppo(5, 9, 4);
    ibm_dt_df.single_act_visit<double>("IBM_Close", ppo);
    double res = ppo.get_result()[2000];
    // assert (fabs(res + 0.239) < 0.01);
    return res;
}

double do_rmv() {
    RollingMidValueVisitor<double, DateTime>  rmv (15);
    ibm_dt_df.single_act_visit<double, double>("IBM_Low", "IBM_High", rmv);
    double res = rmv.get_result()[2000];
    // assert (fabs(res - 123.030) < 0.01);
    return res;
}

static void HandleRequest(udp_spawn_data *d) {
    const Payload *p = static_cast<const Payload *>(d->buf);
    
    uint32_t res = 0;
    if (p->req_type == 1) { // req1 : decay
        res = (uint32_t) do_decay();
    } else if (p->req_type == 2) { // req2: ad
        res = (uint32_t) do_ad();
    } else if (p->req_type == 3) { // req3: rmv
        res = (uint32_t) do_rmv();
    } else if (p->req_type == 4) {
        res = (uint32_t) do_ppo(); // req4: ppo
    } else if (p->req_type == 5) {
        // res = (uint32_t) do_decom(); // req5: decom
        res = (uint32_t) do_kmeans(); // req5: kmeans
    } else {
        panic("bad req type %u", p->req_type);
    }
    
    Payload rp = *p;
    rp.run_ns = res;

    ssize_t wret = udp_respond(&rp, sizeof(rp), d);
    if (unlikely(wret <= 0)) panic("wret");
    udp_spawn_data_release(d->release_data);
}


static void HandleLoop(udpconn_t *c) {
    char buf[20];
	ssize_t ret;
	struct netaddr addr;

	while (true) {
		ret = udp_read_from(c, buf, sizeof(Payload), &addr);
        assert(ret == sizeof(Payload));

        const Payload *p = static_cast<const Payload *>((void*)buf);
    
        uint32_t res = 0;
        if (p->req_type == 1) { // req1 : decay
            res = (uint32_t) do_decay();
        } else if (p->req_type == 2) { // req2: ad
            res = (uint32_t) do_ad();
        } else if (p->req_type == 3) { // req3: rmv
            res = (uint32_t) do_rmv();
        } else if (p->req_type == 4) {
            res = (uint32_t) do_ppo(); // req4: ppo
        } else if (p->req_type == 5) {
            // res = (uint32_t) do_decom(); // req5: decom
            res = (uint32_t) do_kmeans(); // req5: kmeans
        } else {
            panic("bad req type %u", p->req_type);
        }
        
        Payload rp = *p;
        rp.run_ns = res;

        ret = udp_write_to(c, &rp, sizeof(Payload), &addr);
        assert(ret == sizeof(Payload));
	}
}

const unsigned N = 3000;
double loop_max() {
    double res;
    for (unsigned i = 0; i < 39000; ++i) {
        res = do_max();
    }
    return res;
}

double loop_kmeans() {
    double res;
    for (unsigned i = 0; i < N; ++i) {
        res = do_kmeans();
    }
    return res;
}

double loop_decom() {
    double res;
    for (unsigned i = 0; i < N; ++i) {
        res = do_decom();
    }
    return res;
}

// std::vector<double> res_vec;
double loop_ad() {
    double res;
    for (unsigned i = 0; i < 39000; ++i) {
        res = do_ad();
        rt::Yield();
        // res_vec.push_back(res);
    }
    return res;
}

double loop_ppo() {
    double res;
    for (unsigned i = 0; i < 9000; ++i) {
        res = do_ppo();
        // res_vec.push_back(res);
    }
    return res;
}

double loop_decay() {
    double res;
    for (unsigned i = 0; i < 39000; ++i) {
        res = do_decay();
        rt::Yield();
        // res_vec.push_back(res);
    }
    return res;
}

double loop_rmv() {
    double res;
    for (unsigned i = 0; i < 27000; ++i) {
        res = do_rmv();
        // res_vec.push_back(res);
    }
    return res;
}

typedef double (*task_type)(void);
const unsigned TASK_NUM = 7;
// std::string task_name_options[TASK_NUM] = {"max", "kmeans", "ad", "ppo", "decay", "rmv"};
// task_type task_ptr_options[TASK_NUM] = {loop_max, loop_kmeans, loop_ad, loop_ppo, loop_decay, loop_rmv};
std::string task_name_options[TASK_NUM] = {"max", "kmeans", "ad", "ppo", "decay", "rmv", "decom"};
task_type task_ptr_options[TASK_NUM] = {loop_max, loop_kmeans, loop_ad, loop_ppo, loop_decay, loop_rmv, loop_decom};
// task_type task_ptr_options[TASK_NUM] = {do_max, do_kmeans, do_ad, do_ppo, do_decay, do_rmv, do_decom};
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

void MainHandler(void *arg) {
    init();

    rt::UintrTimerStart();

    udpspawner_t *s;
    int ret = udp_create_spawner(listen_addr, HandleRequest, &s);
    if (ret) panic("ret %d", ret);

    rt::WaitGroup w(1);
    w.Wait();
}

unsigned num_port, num_conn;
void MainHandler_udpconn(void *arg) {
    init();

    rt::UintrTimerStart();
    
    for (unsigned port = 0; port < num_port; ++port) {
        udpconn_t *c;
        ssize_t ret;
        listen_addr.port = 5000 + port;
        ret = udp_listen(listen_addr, &c);
        if (ret) {
            log_err("stat: udp_listen failed, ret = %ld", ret);
            return;
        }
        
        for (unsigned i = 0; i < num_conn; ++i) {
            rt::Spawn([&, c]() {
                HandleLoop(c);
            });
        }
    }

    rt::WaitGroup w(1);
    w.Wait();
}

void MainHandler_local(void *arg) {	
    rt::WaitGroup wg(task_num);
	// barrier_init(&barrier, 1);
		
    init();

    // printf("init ends\n");

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
        // std::cout << results[i] << ' ';
        printf("%.4f ", results[i]);
    }
    std::cout << std::endl;
	
    // for (unsigned i = 0; i < N; ++i) {
    //     std::cout << res_vec[i] << ' ';
    // }
}


int main(int argc, char *argv[]) {
	int ret;
	
	if (argc < 4) {
		std::cerr << "usage: [config_file] [mode=local|udp|udpconn] [input_file]"
              << std::endl;
		return -EINVAL;
	}

    std::string mode = argv[2];
    df_input = argv[3];
    if (mode == "local") {
        if (argc < 4) {
            std::cerr << "usage: [cfg_file] local [input_file] [task_spec]" << std::endl;
            return -EINVAL;
        }
        std::string task_spec = std::string(argv[4]);
        parse(task_spec);
        ret = runtime_init(argv[1], MainHandler_local, NULL);
    } else if (mode == "udp") {
        listen_addr.port = 5000;
        ret = runtime_init(argv[1], MainHandler, NULL);
    } else if (mode == "udpconn") {
        if (argc < 5) {
            std::cerr << "usage: [cfg_file] udpconn [input_file] [num of ports] [num of connections]" << std::endl;
            return -EINVAL;
        }
        listen_addr.port = 5000;
        num_port = atoi(argv[4]);
        num_conn = atoi(argv[5]);
        ret = runtime_init(argv[1], MainHandler_udpconn, NULL);
    } else {
        panic ("wrong runtime mode!");
    }

    if (ret) {
		printf("failed to start runtime\n");
		return ret;
	}

	return 0;
}