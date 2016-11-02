# -*- coding: utf-8 -*-

import signal
import subprocess
import time
from enum import Enum

from invoke import task

BIND_HOST = "127.0.0.1:4000"


class GunicornWorkTpye(Enum):
    Gevent = "gevent"
    Meinheld = "egg:meinheld#gunicorn_worker"
    Aiohttp = "gaiohttp"
    AiohttpUvloop = "aiohttp.worker.GunicornUVLoopWebWorker"


@task(help={'server': "gunicorn or uwsgi",
            'type': "In gunicorn : Gevent, Meinheld, Aiohttp, AiohttpUvloop. In uwsgi: normal, thread, gevent"})
def flask(ctx, server, type=None):

    cmd = None

    if server == "gunicorn":
        cmd = gunicorn("flaskapp:app", BIND_HOST, 4, ger_worker_type_by(type))
    elif server == "uwsgi":
        if type == "thread":
            cmd = uwsgi("flaskapp", "app", bind="127.0.0.1:4000", processes=4, threads=2)
        elif type == "gevent":
            cmd = uwsgi("flaskapp", "app", bind="127.0.0.1:4000", processes=4, gevent=20)
        else:
            cmd = uwsgi("flaskapp", "app", bind="127.0.0.1:4000", processes=4)
    else:
        print("Argument 'server' is not correct.")
        return

    print(" ".join(cmd))
    child = subprocess.Popen(cmd, shell=False)

    # wait for gunicorn create workers
    time.sleep(2)

    result = subprocess.run(["wrk", "-t12", "-c400", "-d10s", "http://"+BIND_HOST])
    # result = subprocess.run(["wrk", "-t12", "-c400", "-d10s", "http://127.0.0.1:4000/"], stdout=subprocess.PIPE)
    if result.stdout:
        print(result.stdout)

    if server == "gunicorn":
        child.terminate()
    elif server == "uwsgi":
        child.send_signal(signal.SIGQUIT)

    child.wait()


def get_gunicorn_cmd_by(worker_type):
    return gunicorn("flaskapp:app", BIND_HOST, 4, worker_type)


def ger_worker_type_by(worker_type_name):
    for worker_type in GunicornWorkTpye:
        if worker_type.name == worker_type_name:
            return worker_type
    return None


def gunicorn(app, bind="127.0.0.1:4000", worker_num=1, worker_type=None):
    # gunicorn command => gunicorn -w 4 -k gevent -b 127.0.0.1:4000 flaskapp:app
    cmd = "gunicorn -w {worker_num}".format(worker_num=worker_num).split()

    if worker_type:
        cmd.extend(["-k", worker_type.value])

    cmd.extend(["-b", bind])
    cmd.append(app)
    return cmd


def uwsgi(module, app, bind="127.0.0.1:4000", processes=1, threads=0, gevent=0):
    # uwsgi command => uwsgi --http 127.0.0.1:4000 --module flaskapp --callable app --processes 4 --threads 2

    cmd = "uwsgi --http {bind}".format(bind=bind).split()

    cmd.extend(["--module", module, "--callable", app])

    cmd.extend(["--processes", str(processes)])

    if threads and threads > 1:
        cmd.extend(["--threads", str(threads)])

    if gevent and gevent >= 0:
        cmd.extend(["--gevent", str(gevent)])

    cmd.append("--master")

    # cmd.append("--thunder-lock")

    cmd.append("--pcre-jit")

    # cmd.extend(["--max-fd", "2048"])

    cmd.append("--disable-logging")

    return cmd
