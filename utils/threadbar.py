import multiprocessing
import queue
import sys
from multiprocessing.dummy import Pool


class threadProcBar():
    def __init__(self, func, tasks, pool=multiprocessing.cpu_count()):
        self.func = func
        self.tasks = tasks

        self.bar_i = 0
        self.bar_len = 50
        self.bar_max = len(tasks)

        self.p = Pool(pool)
        self.q = queue.Queue()

    def __dosth(self, percent, task):
        if percent == self.bar_max:
            return self.done
        else:
            self.func(task)
            return percent

    def worker(self):
        pool = self.p
        for i, task in enumerate(self.tasks):
            try:
                percent = pool.apply_async(self.__dosth, args=(i, task))
                self.q.put(percent)
            except BaseException:
                break

    def process(self):
        pool = self.p
        while 1:
            result = self.q.get().get()
            if result == self.bar_max:
                self.bar_i = self.bar_max
            else:
                self.bar_i += 1
            num_arrow = int(self.bar_i * self.bar_len / self.bar_max)
            num_line = self.bar_len - num_arrow
            percent = self.bar_i * 100.0 / self.bar_max
            process_bar = '[' + '>' * num_arrow + '-' * \
                num_line + ']' + '%.2f' % percent + '%' + '\r'
            sys.stdout.write(process_bar)
            sys.stdout.flush()
            if result == self.bar_max-1:
                pool.terminate()
                break
        pool.join()
        self.__close()

    def __close(self):
        print('')
