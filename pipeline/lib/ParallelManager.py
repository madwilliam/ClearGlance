import multiprocessing
import socket
from multiprocessing.pool import Pool
from concurrent.futures.process import ProcessPoolExecutor
from multiprocessing import Pool, Manager
import copy
from datetime import datetime, timedelta

from utilities.utilities_process import workernoshell, submit_proxy


class ParallelManager:

    def get_hostname(self):
        hostname = socket.gethostname()
        hostname = hostname.split(".")[0]
        return hostname

    def get_nworkers(self):
        """There is little point in setting two different levels in one host
        """
        usecpus = 4
        cpus = {}
        cpus['mothra'] = 2
        cpus['godzilla'] = 2
        cpus['muralis'] = 10
        cpus['basalis'] = 4
        cpus['ratto'] = 4
        hostname = self.get_hostname()
        if hostname in cpus.keys():
            usecpus = cpus[hostname]
        return usecpus

    def run_commands_concurrently(self, function, file_keys, workers):
        if self.debug:
            for file_key in file_keys:
                function(file_key)
        else:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                executor.map(function, sorted(file_keys))


    def run_commands_in_parallel_with_shell(self, commands, workers):
        if self.debug:
            print("debugging with single core")
            for command in commands:
                workernoshell(command)
        else:
            with Pool(workers) as p:
                p.map(workernoshell, commands)

    def run_commands_in_parallel_with_multiprocessing(
        self, file_keys, workers, function
    ):
        if self.function_belongs_to_a_pipeline_object(function):
            function = self.make_picklable_copy_of_function(function)
        if self.debug:
            print("debugging with single core")
            for file_key in zip(*file_keys):
                function(*file_key)
        else:
            processes = []
            file_keys = list(zip(*file_keys))
            i = 0
            for _ in range(workers):
                p = multiprocessing.Process(target=function, args=file_keys[i])
                p.start()
                processes.append(p)
                i += 1

    def function_belongs_to_a_pipeline_object(self, function):
        if not hasattr(function, "__self__"):
            return False
        else:
            return type(function.__self__) == type(self)

    def make_picklable_copy_of_function(self, function):
        object = copy.copy(function.__self__)
        del object.sqlController
        return getattr(object, function.__name__)

    def run_commands_in_parallel_with_executor(
            self, file_keys, workers, function, batch_size=3
        ):
            results = []
            n_processing_elements = len(list(zip(*file_keys)))
            print(f"PROCESSING {function.__name__}")
            print(f"ELEMENTS TO PROCESS: {n_processing_elements}")
            if function.__name__ == "clean_image":
                now = datetime.now()
                estimated_unitary_completion_time = (
                    # SECONDS (BASED ON DK59 FULL RESOLUTION n=21 ON ratto SERVER)
                    330
                )
                time_to_complete_step = (
                    n_processing_elements * estimated_unitary_completion_time / batch_size
                )
                estimated_completion_timestamp = now + timedelta(
                    seconds=time_to_complete_step
                )

                print(
                    f"ESTIMATED STEP COMPLETION TIME (ELEMENTS * AVG UNITARY COMPLETION TIME ({estimated_unitary_completion_time} sec) / CONCURRENT PROCESSES): {round(time_to_complete_step / 60 / 60, 1)} hours"
                )
                print(
                    f"ESTIMATED STEP COMPLETION TIMESTAMP: {estimated_completion_timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )

            if self.function_belongs_to_a_pipeline_object(function):
                function = self.make_picklable_copy_of_function(function)
            if self.debug:
                print("debugging with single core")
                for file_key in zip(*file_keys):
                    result = function(*file_key)
                    results.append(result)
                    print(f"DEBUG result value: {result}")
            else:
                # ORG - START
                # with ProcessPoolExecutor(max_workers=workers) as executor:
                #     results = executor.map(function, *file_keys)
                # ORG - END

                print(
                    f"PROCESSING ELMENTS: {n_processing_elements}, BATCH SIZE: {batch_size}"
                )
                with Manager() as manager:  # create a manager for sharing the semaphore
                    semaphore = manager.Semaphore(
                        batch_size
                    )  # semaphore to limit the queue size to the pool
                    with ProcessPoolExecutor(workers) as executor:

                        futures = [
                            submit_proxy(function, semaphore, executor, *file_key)
                            for file_key in zip(*file_keys)
                        ]

                        # print([i for i in futures], flush=True)
                        # wait for all tasks to complete
                        print("All tasks are submitted, waiting...")

            return results